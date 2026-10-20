import unittest
from fastapi.testclient import TestClient

from main import app


class ApiEndpointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")

    def test_ready_endpoint(self):
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertTrue(data.get("models_loaded"))
        self.assertTrue(data.get("database", {}).get("configured"))

    def test_predict_single_customer(self):
        sample_payload = {
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
            "TotalCharges": 79.9,
        }
        response = self.client.post("/predict", json=sample_payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("Ensemble_Prediction", data)
        self.assertIn("Ensemble_Churn_Probability", data)
        self.assertIn("Risk_Level", data)
        self.assertIn("persistence_status", data)
        self.assertEqual(data["Ensemble_Prediction"], "Churn")

    def test_predict_rejects_missing_fields(self):
        incomplete_payload = {
            "gender": "Female",
            "MonthlyCharges": 79.9,
        }
        response = self.client.post("/predict", json=incomplete_payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Empty values found", response.json()["detail"])

    def test_history_requires_auth(self):
        response = self.client.get("/history")
        self.assertEqual(response.status_code, 401)

    def test_analytics_requires_auth(self):
        response = self.client.get("/analytics")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
