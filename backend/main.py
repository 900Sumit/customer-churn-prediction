
# 1. IMPORTS AND MODEL LOADING

import os
import io
import csv
import json
import logging
import time
from datetime import date
import joblib
import pandas as pd
import numpy as np
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from production_pipeline import engineer_features
from database import (
    aggregate_predictions,
    close_pool,
    count_predictions,
    initialize_schema,
    is_configured as database_configured,
    list_predictions,
    save_prediction,
    save_predictions,
    test_connection,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"), override=False)
logger = logging.getLogger("churnlab")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())
logger.propagate = False

try:
    import jwt
except ImportError:
    jwt = None

MODEL_DIR = os.path.join(BASE_DIR, "models")

LR_MODEL_PATH = os.path.join(MODEL_DIR, "churn_lr_pipeline.joblib")
CATBOOST_MODEL_PATH = os.path.join(MODEL_DIR, "churn_catboost_pipeline.joblib")

if not os.path.exists(LR_MODEL_PATH):
    raise FileNotFoundError(f"LR model not found: {LR_MODEL_PATH}")

if not os.path.exists(CATBOOST_MODEL_PATH):
    raise FileNotFoundError(f"CatBoost model not found: {CATBOOST_MODEL_PATH}")

lr_pipeline = joblib.load(LR_MODEL_PATH)
catboost_pipeline = joblib.load(CATBOOST_MODEL_PATH)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if database_configured():
        try:
            initialize_schema()
            logger.info("database_schema_initialized")
        except Exception as exc:
            logger.error("database_schema_init_failed error=%s", type(exc).__name__)
    yield
    close_pool()
    logger.info("database_pool_closed")


app = FastAPI(
    title="Customer Churn Prediction API",
    description="Customer churn prediction using Logistic Regression, CatBoost, and Ensemble.",
    version="1.1.0",
    lifespan=lifespan,
)

# Allow the local Vite frontend to call the existing API. Keep the default
# limited to the development origin; production deployments can provide a
# comma-separated FRONTEND_ORIGINS environment variable.
frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def auth_configuration():
    """Return safe authentication configuration status without secret values."""
    audience_configured = bool(os.getenv("CLERK_AUDIENCE", "").strip())
    authorized_parties_configured = bool(frontend_origins)
    status = {
        "jwks_url_configured": bool(os.getenv("CLERK_JWKS_URL", "").strip()),
        "issuer_configured": bool(os.getenv("CLERK_ISSUER", "").strip()),
        "audience_configured": audience_configured,
        "authorized_parties_configured": authorized_parties_configured,
        "audience_policy": "aud" if audience_configured else "azp",
        "jwt_dependency_available": jwt is not None,
    }
    status["missing"] = [
        name for name, configured in (
            ("CLERK_JWKS_URL", status["jwks_url_configured"]),
            ("CLERK_ISSUER", status["issuer_configured"]),
            ("FRONTEND_ORIGINS", authorized_parties_configured) if not audience_configured else ("CLERK_AUDIENCE", audience_configured),
        ) if not configured
    ]
    status["ready"] = not status["missing"] and status["jwt_dependency_available"]
    return status


def verified_user_id(request: Request, required=True):
    """Return the Clerk subject from a verified bearer token."""
    if jwt is None:
        if required:
            raise HTTPException(
                status_code=503,
                detail="Clerk verification is unavailable because PyJWT is not installed. Run pip install -r requirements.txt.",
            )
        return None

    jwks_url = os.getenv("CLERK_JWKS_URL", "").strip()
    if not jwks_url:
        if required:
            raise HTTPException(
                status_code=503,
                detail="Clerk verification is not configured. Set CLERK_JWKS_URL in backend/.env before using history.",
            )
        return None

    issuer = os.getenv("CLERK_ISSUER", "").strip()
    audience = os.getenv("CLERK_AUDIENCE", "").strip()
    if not issuer:
        if required:
            raise HTTPException(
                status_code=503,
                detail="Clerk verification requires CLERK_ISSUER in backend/.env.",
            )
        return None

    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        if required:
            raise HTTPException(status_code=401, detail="A valid Clerk bearer token is required.")
        return None

    token = authorization.removeprefix("Bearer ").strip()
    try:
        key = jwt.PyJWKClient(jwks_url).get_signing_key_from_jwt(token).key
        options = {
            "require": ["exp", "iss", "sub"],
            "verify_signature": True,
            "verify_exp": True,
            "verify_iss": True,
            "verify_aud": bool(audience),
        }
        kwargs = {"algorithms": ["RS256"], "issuer": issuer, "options": options}
        if audience:
            options["require"].append("aud")
            kwargs["audience"] = audience
        claims = jwt.decode(token, key, **kwargs)
        if not audience:
            authorized_party = claims.get("azp")
            if authorized_party and authorized_party not in frontend_origins:
                raise ValueError("The token authorized party is not an allowed frontend origin.")
        user_id = claims.get("sub")
        if not user_id:
            raise ValueError("Token does not contain a user subject.")
        return user_id
    except Exception as exc:
        if required:
            raise HTTPException(status_code=401, detail="The Clerk session token could not be verified.") from exc
        return None


def persist_if_configured(user_id, input_data, result_data, source):
    if not database_configured():
        return "not_configured"
    if not user_id:
        return "not_authenticated"
    try:
        save_prediction(user_id, input_data, result_data, source)
        return "saved"
    except Exception as exc:
        # Prediction remains successful; persistence failures are surfaced in
        # server logs and never expose database details to the client.
        logger.error("prediction_persistence_failed source=%s error=%s", source, type(exc).__name__)
        return "failed"




def model_feature_importance():
    """Return importance derived from the saved pipeline artifacts."""
    try:
        lr_preprocessor = lr_pipeline.named_steps["preprocessor"]
        catboost_preprocessor = catboost_pipeline.named_steps["preprocessor"]
        lr_classifier = lr_pipeline.named_steps["classifier"]
        catboost_classifier = catboost_pipeline.named_steps["classifier"]
        names = list(lr_preprocessor.get_feature_names_out())
        catboost_names = list(catboost_preprocessor.get_feature_names_out())
        lr_values = np.abs(lr_classifier.coef_[0])
        catboost_values = np.asarray(catboost_classifier.feature_importances_, dtype=float)
        if names != catboost_names or len(names) != len(lr_values) or len(names) != len(catboost_values):
            return []
        lr_total = float(lr_values.sum()) or 1.0
        catboost_total = float(catboost_values.sum()) or 1.0
        rows = [
            {
                "feature": name,
                "logistic_regression_importance_pct": round(float(lr_value / lr_total * 100), 4),
                "catboost_importance_pct": round(float(catboost_value / catboost_total * 100), 4),
                "combined_importance_pct": round(float((lr_value / lr_total + catboost_value / catboost_total) * 50), 4),
            }
            for name, lr_value, catboost_value in zip(names, lr_values, catboost_values)
        ]
        return sorted(rows, key=lambda item: item["combined_importance_pct"], reverse=True)[:15]
    except Exception as exc:
        logger.warning("model_feature_importance_unavailable error=%s", type(exc).__name__)
        return []


# 3. CUSTOMER INPUT SCHEMA

class CustomerInput(BaseModel):
    gender: str | None = None
    SeniorCitizen: int | None = Field(default=None, ge=0, le=1)
    Partner: str | None = None
    Dependents: str | None = None
    tenure: int | None = Field(default=None, ge=0)
    PhoneService: str | None = None
    MultipleLines: str | None = None
    InternetService: str | None = None
    OnlineSecurity: str | None = None
    OnlineBackup: str | None = None
    DeviceProtection: str | None = None
    TechSupport: str | None = None
    StreamingTV: str | None = None
    StreamingMovies: str | None = None
    Contract: str | None = None
    PaperlessBilling: str | None = None
    PaymentMethod: str | None = None
    MonthlyCharges: float | None = Field(default=None, ge=0)
    TotalCharges: float | None = Field(default=None, ge=0)


# 4. DATA VALIDATION CONFIGURATION

REQUIRED_COLUMNS = [
    "gender", "SeniorCitizen", "Partner", "Dependents",
    "tenure", "PhoneService", "MultipleLines", "InternetService",
    "OnlineSecurity", "OnlineBackup", "DeviceProtection",
    "TechSupport", "StreamingTV", "StreamingMovies", "Contract",
    "PaperlessBilling", "PaymentMethod", "MonthlyCharges", "TotalCharges"
]

NUMERIC_COLUMNS = [
    "SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"
]

CRITICAL_COLUMNS = [
    "SeniorCitizen", "tenure", "MonthlyCharges"
]

MAX_MISSING_FRACTION = 0.30
CHURN_THRESHOLD = 0.45
MAX_CSV_FILE_BYTES = 10 * 1024 * 1024
MAX_CSV_ROWS = 10_000

ALLOWED_CATEGORIES = {
    "gender": {"Female", "Male"},
    "Partner": {"Yes", "No"},
    "Dependents": {"Yes", "No"},
    "PhoneService": {"Yes", "No"},
    "MultipleLines": {"Yes", "No", "No phone service"},
    "InternetService": {"DSL", "Fiber optic", "No"},
    "OnlineSecurity": {"Yes", "No", "No internet service"},
    "OnlineBackup": {"Yes", "No", "No internet service"},
    "DeviceProtection": {"Yes", "No", "No internet service"},
    "TechSupport": {"Yes", "No", "No internet service"},
    "StreamingTV": {"Yes", "No", "No internet service"},
    "StreamingMovies": {"Yes", "No", "No internet service"},
    "Contract": {"Month-to-month", "One year", "Two year"},
    "PaperlessBilling": {"Yes", "No"},
    "PaymentMethod": {
        "Electronic check",
        "Mailed check",
        "Bank transfer (automatic)",
        "Credit card (automatic)"
    }
}


# 5. RISK CLASSIFICATION

def classify_churn_risk(probability):
    if probability < 0.30:
        return "Low Risk"
    elif probability < 0.60:
        return "Medium Risk"
    return "High Risk"


# 6. CUSTOMER DATA VALIDATION AND PREPARATION

def prepare_customer_data(customer_data):
    # Accept a single customer, multiple customers, or a DataFrame
    if isinstance(customer_data, dict):
        customer_df = pd.DataFrame([customer_data])
        row_offset = 1

    elif isinstance(customer_data, list):
        if not customer_data:
            raise ValueError("No customer records were provided.")

        if not all(isinstance(item, dict) for item in customer_data):
            raise TypeError(
                "A list input must contain only customer dictionaries."
            )

        customer_df = pd.DataFrame(customer_data)
        row_offset = 1

    elif isinstance(customer_data, pd.DataFrame):
        customer_df = customer_data.copy()
        row_offset = 2

    else:
        raise TypeError(
            "Input must be a dictionary, a list of customer dictionaries, "
            "or a pandas DataFrame."
        )

    if customer_df.empty:
        raise ValueError("No customer records were provided.")

    # Normalize column names and validate the input structure
    customer_df.columns = customer_df.columns.astype(str).str.strip()

    if customer_df.columns.duplicated().any():
        duplicates = customer_df.columns[
            customer_df.columns.duplicated()
        ].tolist()

        raise ValueError(
            f"Duplicate input columns found: {duplicates}"
        )

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in customer_df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    customer_df = customer_df[REQUIRED_COLUMNS].copy()
    customer_df = customer_df.reset_index(drop=True)

    # Normalize blank strings and whitespace to missing values
    for col in REQUIRED_COLUMNS:
        if pd.api.types.is_object_dtype(customer_df[col]) or \
                isinstance(customer_df[col].dtype, pd.StringDtype):
            customer_df[col] = customer_df[col].map(
                lambda value: value.strip()
                if isinstance(value, str)
                else value
            )

        customer_df[col] = customer_df[col].replace(
            r"^\s*$", np.nan, regex=True
        )

    # Reject empty values in every required field
    empty_mask = customer_df[REQUIRED_COLUMNS].isna()

    if empty_mask.any().any():
        empty_details = []

        for col in REQUIRED_COLUMNS:
            bad_rows = (
                customer_df.index[empty_mask[col]] + row_offset
            ).tolist()

            if bad_rows:
                empty_details.append({
                    "column": col,
                    "customer_rows": bad_rows
                })

        raise ValueError(
            "Empty values found. Fill all required fields before prediction. "
            f"Details: {empty_details}"
        )

    # Convert numeric fields and reject invalid numeric text
    for col in NUMERIC_COLUMNS:
        original_values = customer_df[col]
        converted_values = pd.to_numeric(
            original_values,
            errors="coerce"
        )

        malformed_mask = converted_values.isna()

        if malformed_mask.any():
            bad_rows = (
                customer_df.index[malformed_mask] + row_offset
            ).tolist()

            raise ValueError(
                f"Invalid numeric values in '{col}' at row(s): {bad_rows}."
            )

        customer_df[col] = converted_values

    # Validate numeric ranges
    if not customer_df["SeniorCitizen"].isin([0, 1]).all():
        raise ValueError("SeniorCitizen must contain only 0 or 1.")

    if (customer_df["tenure"] < 0).any():
        raise ValueError("Tenure cannot be negative.")

    for col in ["MonthlyCharges", "TotalCharges"]:
        if (customer_df[col] < 0).any():
            raise ValueError(
                f"{col} cannot contain negative values."
            )

    # Validate categorical values
    for col, allowed_values in ALLOWED_CATEGORIES.items():
        invalid_mask = ~customer_df[col].isin(allowed_values)

        if invalid_mask.any():
            invalid_rows = (
                customer_df.index[invalid_mask] + row_offset
            ).tolist()

            invalid_values = (
                customer_df.loc[invalid_mask, col].unique().tolist()
            )

            raise ValueError(
                f"Invalid value(s) in '{col}': {invalid_values}. "
                f"Rows: {invalid_rows}. "
                f"Allowed values: {sorted(allowed_values)}."
            )

    # No missing values remain after strict validation
    warnings = ["None"] * len(customer_df)

    return customer_df, warnings



# 7. CUSTOMER PREDICTION ENGINE

def predict_customer_churn(customer_data):
    started = time.perf_counter()
    customer_df, warnings = prepare_customer_data(customer_data)
    logger.info("prediction_stage=validation rows=%d seconds=%.3f", len(customer_df), time.perf_counter() - started)

    feature_started = time.perf_counter()
    engineered_df = engineer_features(customer_df.copy())
    logger.info("prediction_stage=feature_engineering rows=%d seconds=%.3f", len(engineered_df), time.perf_counter() - feature_started)

    lr_started = time.perf_counter()
    lr_probabilities = lr_pipeline.predict_proba(engineered_df)[:, 1]
    logger.info("prediction_stage=logistic_regression rows=%d seconds=%.3f", len(engineered_df), time.perf_counter() - lr_started)

    catboost_started = time.perf_counter()
    catboost_probabilities = catboost_pipeline.predict_proba(
        engineered_df
    )[:, 1]
    logger.info("prediction_stage=catboost rows=%d seconds=%.3f", len(engineered_df), time.perf_counter() - catboost_started)

    ensemble_probabilities = (
        lr_probabilities + catboost_probabilities
    ) / 2

    ensemble_predictions = (
        ensemble_probabilities >= CHURN_THRESHOLD
    ).astype(int)

    results = pd.DataFrame({
        "LR_Churn_Probability": np.round(lr_probabilities * 100, 2),
        "CatBoost_Churn_Probability": np.round(
            catboost_probabilities * 100, 2
        ),
        "Ensemble_Churn_Probability": np.round(
            ensemble_probabilities * 100, 2
        ),
        "Ensemble_Prediction": [
            "Churn" if prediction == 1 else "No Churn"
            for prediction in ensemble_predictions
        ],
        "Risk_Level": [
            classify_churn_risk(probability)
            for probability in ensemble_probabilities
        ],
        "Data_Quality_Warning": warnings
    })

    logger.info("prediction_stage=ensemble rows=%d seconds=%.3f", len(results), time.perf_counter() - started)
    return results


# 8. HOME ENDPOINT

@app.get("/")
def home():
    return {
        "message": "Customer Churn Prediction API is running",
        "models": {
            "available": [
                "Logistic Regression",
                "CatBoost",
                "Ensemble"
            ],
            "description": "Predict customer churn and classify risk levels."
        },
        "endpoints": {
            "home": {
                "method": "GET",
                "path": "/",
                "description": "View API information and available endpoints."
            },
            "health": {
                "method": "GET",
                "path": "/health",
                "description": "Check API health and model loading status."
            },
            "single_prediction": {
                "method": "POST",
                "path": "/predict",
                "description": "Predict churn for one customer using JSON input."
            },
            "csv_prediction": {
                "method": "POST",
                "path": "/predict-csv-json-to-table",
                "description": "Upload a CSV and receive predictions as JSON."
            },
            "csv_download": {
                "method": "POST",
                "path": "/predict-csv/download",
                "description": "Upload a CSV and download the prediction results as a CSV file."
            },
            "documentation": {
                "method": "GET",
                "path": "/docs",
                "description": "Explore and test API endpoints."
            }
        }
    }



# 9. HEALTH CHECK ENDPOINT

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "models_loaded": True,
        "authentication": auth_configuration(),
    }


@app.get("/ready")
def readiness_check():
    auth_status = auth_configuration()
    database_status = {
        "configured": database_configured(),
        "reachable": False,
    }
    if database_status["configured"]:
        try:
            test_connection()
            database_status["reachable"] = True
        except Exception as exc:
            logger.error("database_readiness_failed error=%s", type(exc).__name__)

    auth_ready = auth_status["ready"]
    ready = database_status["configured"] and database_status["reachable"] and auth_ready
    payload = {
        "status": "ready" if ready else "not_ready",
        "models_loaded": True,
        "database": database_status,
        "authentication": auth_status,
    }
    if not ready:
        return JSONResponse(status_code=503, content=payload)
    return payload


# 10. SINGLE-CUSTOMER PREDICTION ENDPOINT

@app.post("/predict")
def predict_churn(customer: CustomerInput, request: Request):
    try:
        result = predict_customer_churn(customer.model_dump())
        result_data = result.iloc[0].to_dict()
        persistence_status = persist_if_configured(
            verified_user_id(request, required=False),
            customer.model_dump(),
            result_data,
            "single",
        )
        result_data["persistence_status"] = persistence_status
        return result_data

    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(exc)}"
        )





# 11 CSV BATCH PREDICTION PROCESSING

async def process_csv_upload(file: UploadFile):
    started = time.perf_counter()
    # Validate uploaded file
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a valid CSV file."
        )

    try:
        # Read and validate CSV data
        contents = await file.read(MAX_CSV_FILE_BYTES + 1)
        logger.info("csv_stage=file_read bytes=%d seconds=%.3f", len(contents), time.perf_counter() - started)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="Uploaded CSV file is empty."
            )

        if len(contents) > MAX_CSV_FILE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"CSV file exceeds the {MAX_CSV_FILE_BYTES // (1024 * 1024)} MB limit."
            )

        parse_started = time.perf_counter()
        input_df = pd.read_csv(io.BytesIO(contents))
        logger.info("csv_stage=parse rows=%d seconds=%.3f", len(input_df), time.perf_counter() - parse_started)

        if input_df.empty:
            raise HTTPException(
                status_code=400,
                detail="CSV contains no customer records."
            )

        if len(input_df) > MAX_CSV_ROWS:
            raise HTTPException(
                status_code=413,
                detail=f"CSV contains more than the {MAX_CSV_ROWS} row limit."
            )

        input_df.columns = input_df.columns.astype(str).str.strip()

        if input_df.columns.duplicated().any():
            duplicates = input_df.columns[
                input_df.columns.duplicated()
            ].tolist()

            raise HTTPException(
                status_code=400,
                detail=f"Duplicate CSV columns found: {duplicates}"
            )

        # Check required model input columns
        missing_columns = [
            col for col in REQUIRED_COLUMNS
            if col not in input_df.columns
        ]

        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {missing_columns}"
            )

        logger.info("csv_stage=validation rows=%d seconds=%.3f", len(input_df), time.perf_counter() - started)

        # Generate churn predictions
        prediction_started = time.perf_counter()
        model_input = input_df[REQUIRED_COLUMNS].copy()
        predictions = predict_customer_churn(model_input)
        logger.info("csv_stage=model rows=%d seconds=%.3f", len(input_df), time.perf_counter() - prediction_started)

        if len(predictions) != len(input_df):
            raise HTTPException(
                status_code=500,
                detail="Prediction count does not match the number of CSV rows."
            )

        # Combine original data with prediction results
        prediction_columns = [
            col for col in predictions.columns
            if col not in input_df.columns
        ]

        result_df = pd.concat(
            [
                input_df.reset_index(drop=True),
                predictions[prediction_columns].reset_index(drop=True)
            ],
            axis=1
        )

        logger.info("csv_stage=combine rows=%d seconds=%.3f", len(result_df), time.perf_counter() - started)
        return result_df

    except HTTPException:
        raise

    # Handle CSV validation and prediction errors
    except (
        pd.errors.ParserError,
        UnicodeDecodeError,
        ValueError,
        TypeError
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"CSV validation or prediction failed: {str(exc)}"
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"CSV prediction failed: {str(exc)}"
        )


# -> Return predictions as JSON
@app.post("/predict-csv-json-to-table")
async def predict_csv(request: Request, file: UploadFile = File(...)):
    request_started = time.perf_counter()
    result_df = await process_csv_upload(file)

    json_df = result_df.astype(object).where(
        pd.notna(result_df), None
    )

    auth_started = time.perf_counter()
    user_id = verified_user_id(request, required=False)
    logger.info("csv_stage=authentication token_present=%s seconds=%.3f", bool(user_id), time.perf_counter() - auth_started)
    records = json_df.to_dict(orient="records")
    persistence_status = "not_configured" if not database_configured() else "not_authenticated"
    if database_configured() and user_id:
        persistence_started = time.perf_counter()
        persistence_records = []
        for result_data in records:
            input_data = {
                column: result_data.get(column)
                for column in REQUIRED_COLUMNS
            }
            prediction_data = {
                key: result_data.get(key)
                for key in [
                    "LR_Churn_Probability", "CatBoost_Churn_Probability",
                    "Ensemble_Churn_Probability", "Ensemble_Prediction",
                    "Risk_Level", "Data_Quality_Warning"
                ]
            }
            persistence_records.append((input_data, prediction_data))
        try:
            save_predictions(user_id, persistence_records, "csv")
            persistence_status = "saved"
            logger.info("csv_stage=persistence rows=%d seconds=%.3f", len(persistence_records), time.perf_counter() - persistence_started)
        except Exception as exc:
            persistence_status = "failed"
            logger.error("csv_stage=persistence_failed rows=%d error=%s seconds=%.3f", len(persistence_records), type(exc).__name__, time.perf_counter() - persistence_started)

    logger.info("csv_stage=response rows=%d seconds=%.3f", len(result_df), time.perf_counter() - request_started)
    return {
        "message": "CSV predictions completed successfully.",
        "total_records": len(result_df),
        "persistence_status": persistence_status,
        "predictions": records
    }


# -> Download predictions as CSV
@app.post("/predict-csv/download")
async def download_csv_predictions(file: UploadFile = File(...)):
    result_df = await process_csv_upload(file)

    output = io.StringIO()
    result_df.to_csv(output, index=False)
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
                'attachment; filename="churn_batch_predictions.csv"'
        }
    )


def parse_date_filter(value, name):
    if not value:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{name} must use YYYY-MM-DD.") from exc


def history_filter_values(risk, prediction, source):
    allowed_risk = {"Low Risk", "Medium Risk", "High Risk"}
    allowed_prediction = {"Churn", "No Churn"}
    allowed_source = {"single", "csv"}
    if risk and risk not in allowed_risk:
        raise HTTPException(status_code=400, detail="risk must be Low Risk, Medium Risk, or High Risk.")
    if prediction and prediction not in allowed_prediction:
        raise HTTPException(status_code=400, detail="prediction must be Churn or No Churn.")
    if source and source not in allowed_source:
        raise HTTPException(status_code=400, detail="source must be single or csv.")


def history_query_args(risk=None, prediction=None, source=None, date_from=None, date_to=None):
    history_filter_values(risk, prediction, source)
    parsed_from = parse_date_filter(date_from, "date_from")
    parsed_to = parse_date_filter(date_to, "date_to")
    if parsed_from and parsed_to and parsed_from > parsed_to:
        raise HTTPException(status_code=400, detail="date_from cannot be after date_to.")
    return parsed_from, parsed_to


@app.get("/history")
def prediction_history(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    q: str | None = None,
    risk: str | None = None,
    prediction: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    if not database_configured():
        raise HTTPException(status_code=503, detail="Prediction history is not configured. Set DATABASE_URL in backend/.env.")
    user_id = verified_user_id(request)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    parsed_from, parsed_to = history_query_args(risk, prediction, source, date_from, date_to)
    try:
        filters = {
            "query": q,
            "risk": risk,
            "prediction": prediction,
            "source": source,
            "date_from": parsed_from,
            "date_to": parsed_to,
        }
        rows = list_predictions(user_id, limit, offset, **filters)
        return {"total": count_predictions(user_id, **filters), "limit": limit, "offset": offset, "items": rows}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("prediction_history_query_failed error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Prediction history is temporarily unavailable.") from exc


@app.get("/history/export")
def export_prediction_history(
    request: Request,
    q: str | None = None,
    risk: str | None = None,
    prediction: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
):
    if not database_configured():
        raise HTTPException(status_code=503, detail="Prediction history is not configured. Set DATABASE_URL in backend/.env.")
    user_id = verified_user_id(request)
    parsed_from, parsed_to = history_query_args(risk, prediction, source, date_from, date_to)
    try:
        rows = list_predictions(
            user_id,
            limit=10000,
            offset=0,
            query=q,
            risk=risk,
            prediction=prediction,
            source=source,
            date_from=parsed_from,
            date_to=parsed_to,
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "created_at", "source", "input_data",
            "LR_Churn_Probability", "CatBoost_Churn_Probability",
            "Ensemble_Churn_Probability", "Ensemble_Prediction",
            "Risk_Level", "Data_Quality_Warning",
        ])
        for row in rows:
            result = row.get("result_data") or {}
            writer.writerow([
                row.get("id"), row.get("created_at"), row.get("source"),
                json.dumps(row.get("input_data") or {}, ensure_ascii=False),
                result.get("LR_Churn_Probability"),
                result.get("CatBoost_Churn_Probability"),
                result.get("Ensemble_Churn_Probability"),
                result.get("Ensemble_Prediction"),
                result.get("Risk_Level"),
                result.get("Data_Quality_Warning"),
            ])
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="prediction_history.csv"'},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("prediction_history_export_failed error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Prediction history export is temporarily unavailable.") from exc


@app.get("/analytics")
def prediction_analytics(request: Request):
    if not database_configured():
        raise HTTPException(status_code=503, detail="Prediction analytics is not configured. Set DATABASE_URL in backend/.env.")
    user_id = verified_user_id(request)
    try:
        summary = aggregate_predictions(user_id)
        total = summary["total"] or 0
        summary["churn_rate"] = round((summary["churn"] / total) * 100, 2) if total else 0
        summary["feature_importance"] = model_feature_importance()
        metrics_path = os.path.join(MODEL_DIR, "evaluation_metrics.json")
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path) as f:
                    summary["evaluation_metrics"] = {"available": True, "data": json.load(f)}
            except Exception:
                summary["evaluation_metrics"] = {
                    "available": False,
                    "message": "Evaluation metrics file exists but could not be read.",
                }
        else:
            summary["evaluation_metrics"] = {
                "available": False,
                "message": "Run train_models.py to generate evaluation metrics.",
            }
        return summary
    except Exception as exc:
        logger.error("prediction_analytics_query_failed error=%s", type(exc).__name__)
        raise HTTPException(status_code=503, detail="Prediction analytics is temporarily unavailable.") from exc
