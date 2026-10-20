
# 1. IMPORTS

import pandas as pd

from main import predict_customer_churn


# 2. SAMPLE CUSTOMER DATA

sample_customer = {
    "gender": "Female",
    "SeniorCitizen": 0,
    "Partner": "No",
    "Dependents": "No",
    "tenure": 1,
    "PhoneService": "Yes",
    "MultipleLines": "No",
    "InternetService": "Fiber optic",
    "OnlineSecurity": "No",
    "OnlineBackup": "No",
    "DeviceProtection": "No",
    "TechSupport": "No",
    "StreamingTV": "No",
    "StreamingMovies": "No",
    "Contract": "Month-to-month",
    "PaperlessBilling": "Yes",
    "PaymentMethod": "Electronic check",
    "MonthlyCharges": 79.9,
    "TotalCharges": 79.9
}


# 3. RUN PREDICTION

if __name__ == "__main__":
    try:
        results = predict_customer_churn(sample_customer)

        print("\nCustomer Churn Prediction Results\n")
        print(results.to_string(index=False))

        print("\nTest completed successfully.")

    except Exception as error:
        print("\nPrediction test failed.")
        print("Error:", error)
