from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json
from authentication.decorators import token_required
from authentication.models import OTPSecret, User


# TODO: need to set test env["JWT_SECRET"] for unittest
class TokenRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @token_required
    async def dummy_view(self, request, access_token):
        return JsonResponse({"access_token": access_token})

    async def test_no_jwt_in_request(self):
        request = self.factory.get("/dummy-url")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "No jwt in request"}
        )

    async def test_invalid_jwt_format(self):
        request = self.factory.get("/dummy-url", HTTP_AUTHORIZATION="InvalidToken")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "Decoding jwt failed"}
        )

    @patch("authentication.decorators.jwt.decode")
    async def test_no_access_token_in_jwt(self, mock_jwt_decode):
        mock_jwt_decode.return_value = {}
        request = self.factory.get("/dummy-url", HTTP_AUTHORIZATION="Bearer validJWT")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "No access token provided"}
        )

    @patch("authentication.decorators.jwt.decode")
    @patch("authentication.decorators.cache.aget")
    async def test_invalid_access_token(self, mock_cache_get, mock_jwt_decode):
        mock_jwt_decode.return_value = {"access_token": "test_token"}
        mock_cache_get.return_value = None
        request = self.factory.get("/dummy-url", HTTP_AUTHORIZATION="Bearer validJWT")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content.decode("utf-8")), {"error": "Invalid token"})

    @patch("authentication.decorators.jwt.decode")
    @patch("authentication.decorators.cache.aget")
    async def test_valid_access_token(self, mock_cache_get, mock_jwt_decode):
        mock_jwt_decode.return_value = {"access_token": "test_token"}
        mock_cache_get.return_value = True
        request = self.factory.get("/dummy-url", HTTP_AUTHORIZATION="Bearer validJWT")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"access_token": "test_token"}
        )


class OTPSecretModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(id="9876543", email="test@test.com")
        self.otp_secret = OTPSecret.objects.create(user=self.user, secret="testsecret")

    def test_otp_secret_creation(self):
        self.assertTrue(isinstance(self.otp_secret, OTPSecret))
        self.assertEqual(self.otp_secret.user, self.user)

    def test_secret_encryption_decryption(self):
        self.assertNotEqual(self.otp_secret.encrypted_secret, "testsecret")
        self.assertEqual(self.otp_secret.secret, "testsecret")

    def test_default_values(self):
        self.assertEqual(self.otp_secret.attempts, 0)
        self.assertIsNone(self.otp_secret.last_attempt)
        self.assertFalse(self.otp_secret.is_locked)
        self.assertFalse(self.otp_secret.is_verified)

    def test_update_attempts(self):
        self.otp_secret.attempts += 1
        self.otp_secret.last_attempt = timezone.now()
        self.otp_secret.save()

        updated_otp = OTPSecret.objects.get(id=self.otp_secret.id)
        self.assertEqual(updated_otp.attempts, 1)
        self.assertIsNotNone(updated_otp.last_attempt)

    def test_lock_account(self):
        self.otp_secret.is_locked = True
        self.otp_secret.save()

        locked_otp = OTPSecret.objects.get(id=self.otp_secret.id)
        self.assertTrue(locked_otp.is_locked)

    def test_verify_account(self):
        self.otp_secret.is_verified = True
        self.otp_secret.save()

        verified_otp = OTPSecret.objects.get(id=self.otp_secret.id)
        self.assertTrue(verified_otp.is_verified)

    def test_one_to_one_relationship(self):
        with self.assertRaises(Exception):
            OTPSecret.objects.create(user=self.user, secret="anothersecret")
