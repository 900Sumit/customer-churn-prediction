
import pandas as pd
import numpy as np


# 1. Feature engineering for customer churn prediction
def engineer_features(dataframe):

    # 2. Define the required raw input features
    required_columns = [
        "gender", "SeniorCitizen", "Partner", "Dependents",
        "tenure", "PhoneService", "MultipleLines",
        "InternetService", "OnlineSecurity", "OnlineBackup",
        "DeviceProtection", "TechSupport", "StreamingTV",
        "StreamingMovies", "Contract", "PaperlessBilling",
        "PaymentMethod", "MonthlyCharges", "TotalCharges"
    ]

    # 3. Check whether required columns are present
    missing_cols = [
        col for col in required_columns
        if col not in dataframe.columns
    ]

    if missing_cols:
        raise ValueError(
            f"Input DataFrame is missing required columns: {missing_cols}"
        )

    # 4. Copy input data to preserve the original DataFrame
    df_feat = dataframe[required_columns].copy()

    # 5. Normalize categorical text and convert blank strings to NaN
    categorical_columns = df_feat.select_dtypes(
        include=["object", "string"]
    ).columns

    for col in categorical_columns:
        df_feat[col] = df_feat[col].str.strip()
        df_feat[col] = df_feat[col].replace("", np.nan)

    # 6. Convert numeric columns safely
    numeric_columns = [
        "SeniorCitizen", "tenure", "MonthlyCharges", "TotalCharges"
    ]

    for col in numeric_columns:
        df_feat[col] = pd.to_numeric(
            df_feat[col],
            errors="coerce"
        )

    # 7. Create TenureGroup while preserving missing tenure values
    def get_tenure_group(months):
        if pd.isna(months):
            return np.nan
        elif months <= 12:
            return "0-1 Year"
        elif months <= 24:
            return "1-2 Years"
        elif months <= 48:
            return "2-4 Years"
        else:
            return "Over 4 Years"

    df_feat["TenureGroup"] = df_feat["tenure"].apply(
        get_tenure_group
    )

    # 8. Create ServiceCount without treating unknown services as No
    def count_services(row):
        count = 0

        # Count only explicitly confirmed services
        if row["PhoneService"] == "Yes":
            count += 1

        if row["MultipleLines"] == "Yes":
            count += 1

        if row["InternetService"] in ["DSL", "Fiber optic"]:
            count += 1

        service_columns = [
            "OnlineSecurity", "OnlineBackup", "DeviceProtection",
            "TechSupport", "StreamingTV", "StreamingMovies"
        ]

        for col in service_columns:
            if row[col] == "Yes":
                count += 1

        # If a service value is missing, the count may be incomplete.
        # Preserve NaN so the fitted imputer can handle it.
        service_values = [
            row["PhoneService"],
            row["MultipleLines"],
            row["InternetService"]
        ] + [row[col] for col in service_columns]

        if any(pd.isna(value) for value in service_values):
            return np.nan

        return count

    df_feat["ServiceCount"] = df_feat.apply(
        count_services,
        axis=1
    )

    # 9. Calculate AverageMonthlySpending safely
    valid_tenure = df_feat["tenure"] > 0

    df_feat["AverageMonthlySpending"] = np.nan

    # Calculate average spending when tenure and TotalCharges are available
    valid_spending = (
        valid_tenure
        & df_feat["TotalCharges"].notna()
    )

    df_feat.loc[
        valid_spending,
        "AverageMonthlySpending"
    ] = (
        df_feat.loc[valid_spending, "TotalCharges"]
        / df_feat.loc[valid_spending, "tenure"]
    )

    # For zero-tenure customers, use MonthlyCharges if available
    zero_tenure = (
        df_feat["tenure"].eq(0)
        & df_feat["MonthlyCharges"].notna()
    )

    df_feat.loc[
        zero_tenure,
        "AverageMonthlySpending"
    ] = df_feat.loc[zero_tenure, "MonthlyCharges"]

    # 10. Return engineered features for model preprocessing
    return df_feat


# 11. Wrapper for production inference
class ProductionInferencePipeline:

    # 12. Initialize with a fitted model and feature engineering function
    def __init__(self, fitted_pipeline, feature_engineering_fn):
        self.pipeline = fitted_pipeline
        self.feature_engineering_fn = feature_engineering_fn

    # 13. Generate class predictions
    def predict(self, raw_df):
        engineered_df = self.feature_engineering_fn(raw_df)
        return self.pipeline.predict(engineered_df)

    # 14. Generate class probabilities
    def predict_proba(self, raw_df):
        engineered_df = self.feature_engineering_fn(raw_df)
        return self.pipeline.predict_proba(engineered_df)
