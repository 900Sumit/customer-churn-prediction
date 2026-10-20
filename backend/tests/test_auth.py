import os
import time
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from starlette.requests import Request

import main


class _JwkClient:
    def __init__(self, key):
        self.key = key

    def get_signing_key_from_jwt(self, token):
        return type("SigningKey", (), {"key": self.key})()


def _request(token):
    return Request({
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode())],
    })


class ClerkVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.public_key = cls.private_key.public_key()

    def token(self, **overrides):
        claims = {
            "sub": "user_a",
            "iss": "https://issuer.example",
            "aud": "https://app.example",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,
        }
        claims.update(overrides)
        return jwt.encode(claims, self.private_key, algorithm="RS256", headers={"kid": "test-key"})

    def verify(self, token):
        environment = {
            "CLERK_JWKS_URL": "https://issuer.example/.well-known/jwks.json",
            "CLERK_ISSUER": "https://issuer.example",
            "CLERK_AUDIENCE": "https://app.example",
        }
        with patch.dict(os.environ, environment, clear=False), patch.object(
            main.jwt, "PyJWKClient", return_value=_JwkClient(self.public_key)
        ):
            return main.verified_user_id(_request(token))

    def test_valid_token_requires_signature_issuer_and_audience(self):
        self.assertEqual(self.verify(self.token()), "user_a")

    def test_wrong_issuer_is_rejected(self):
        with self.assertRaises(main.HTTPException) as error:
            self.verify(self.token(iss="https://wrong.example"))
        self.assertEqual(error.exception.status_code, 401)

    def test_wrong_audience_is_rejected(self):
        with self.assertRaises(main.HTTPException) as error:
            self.verify(self.token(aud="https://wrong.example"))
        self.assertEqual(error.exception.status_code, 401)

    def test_tampered_signature_is_rejected(self):
        token = self.token() + "tampered"
        with self.assertRaises(main.HTTPException) as error:
            self.verify(token)
        self.assertEqual(error.exception.status_code, 401)

    def test_expired_token_is_rejected(self):
        with self.assertRaises(main.HTTPException) as error:
            self.verify(self.token(exp=int(time.time()) - 1))
        self.assertEqual(error.exception.status_code, 401)

    def test_default_session_policy_uses_authorized_party_when_audience_is_absent(self):
        environment = {
            "CLERK_JWKS_URL": "https://issuer.example/.well-known/jwks.json",
            "CLERK_ISSUER": "https://issuer.example",
        }
        with patch.dict(os.environ, environment, clear=False), patch.object(
            main.jwt, "PyJWKClient", return_value=_JwkClient(self.public_key)
        ):
            os.environ.pop("CLERK_AUDIENCE", None)
            status = main.auth_configuration()
            self.assertTrue(status["ready"])
            self.assertEqual(status["audience_policy"], "azp")
            self.assertEqual(main.verified_user_id(_request(self.token())), "user_a")

    def test_default_session_policy_rejects_unknown_authorized_party(self):
        environment = {
            "CLERK_JWKS_URL": "https://issuer.example/.well-known/jwks.json",
            "CLERK_ISSUER": "https://issuer.example",
        }
        with patch.dict(os.environ, environment, clear=False), patch.object(
            main.jwt, "PyJWKClient", return_value=_JwkClient(self.public_key)
        ):
            os.environ.pop("CLERK_AUDIENCE", None)
            with self.assertRaises(main.HTTPException) as error:
                main.verified_user_id(_request(self.token(azp="https://attacker.example")))
        self.assertEqual(error.exception.status_code, 401)

    def test_authenticated_history_and_analytics_are_user_scoped(self):
        environment = {
            "CLERK_JWKS_URL": "https://issuer.example/.well-known/jwks.json",
            "CLERK_ISSUER": "https://issuer.example",
            "CLERK_AUDIENCE": "https://app.example",
        }
        history_rows = [{"id": 1, "created_at": "2026-01-01T00:00:00Z", "source": "single", "input_data": {}, "result_data": {}}]
        with patch.dict(os.environ, environment, clear=False), patch.object(
            main.jwt, "PyJWKClient", return_value=_JwkClient(self.public_key)
        ), patch.object(main, "database_configured", return_value=True), patch.object(
            main, "list_predictions", return_value=history_rows
        ) as list_mock, patch.object(main, "count_predictions", return_value=1) as count_mock, patch.object(
            main, "aggregate_predictions", return_value={"total": 1, "churn": 1, "non_churn": 0, "average_probability": 80.0}
        ) as aggregate_mock, patch.object(main, "model_feature_importance", return_value=[]):
            history = main.prediction_history(_request(self.token()), limit=20, offset=0)
            analytics = main.prediction_analytics(_request(self.token()))

        self.assertEqual(history["items"], history_rows)
        self.assertEqual(analytics["total"], 1)
        self.assertEqual(list_mock.call_args.args[0], "user_a")
        self.assertEqual(count_mock.call_args.args[0], "user_a")
        self.assertEqual(aggregate_mock.call_args.args[0], "user_a")


if __name__ == "__main__":
    unittest.main()
