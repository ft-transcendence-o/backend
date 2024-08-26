from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.utils import timezone
from unittest.mock import patch, MagicMock
import json
import jwt
from authentication.decorators import token_required
from authentication.models import OTPSecret, User, OTPLockInfo
from authentication.constants import JWT_SECRET


# TODO: need to set test env["JWT_SECRET"] for unittest
class TokenRequiredDecoratorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.decoded_jwt = {
            "access_token": "access_token",
            "user_id": 123,
            "otp_verified": False,
        }
        self.valid_jwt = jwt.encode(
            self.decoded_jwt,
            JWT_SECRET,
            algorithm="HS256",
        )

        self.invalid_decoded_jwt = {"access_token": "access_token", "otp_verified": False}
        self.invalid_jwt = jwt.encode(
            self.invalid_decoded_jwt,
            JWT_SECRET,
            algorithm="HS256",
        )

    @token_required
    async def dummy_view(self, request, decoded_jwt):
        return JsonResponse(decoded_jwt)

    async def test_no_jwt_in_request(self):
        request = self.factory.get("/dummy-url")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "No jwt in request"}
        )

    async def test_invalid_jwt_format(self):
        request = self.factory.get("/dummy-url")
        request.COOKIES["jwt"] = "invalid_jwt"
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "Decoding jwt failed"}
        )

    @patch("authentication.decorators.jwt.decode")
    @patch("authentication.decorators.token_refresh_if_invalid")
    async def test_no_access_token_in_jwt(self, mock_refresh, mock_jwt_decode):
        mock_jwt_decode.return_value = self.invalid_decoded_jwt
        mock_refresh.return_value = None
        request = self.factory.get("/dummy-url")
        request.COOKIES["jwt"] = self.invalid_jwt
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"error": "No user id provided"}
        )

    @patch("authentication.decorators.jwt.decode")
    @patch("authentication.decorators.cache.aget")
    @patch("authentication.decorators.token_refresh_if_invalid")
    async def test_valid_access_token(self, mock_refresh, mock_cache_get, mock_jwt_decode):
        mock_jwt_decode.return_value = self.decoded_jwt
        mock_cache_get.return_value = True
        mock_refresh.return_value = None
        request = self.factory.get("/dummy-url")
        request.COOKIES["jwt"] = self.valid_jwt
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8")), self.decoded_jwt)


class OTPTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(id="9876543", email="test@test.com")
        self.otp_secret = OTPSecret.objects.create(user=self.user, secret="testsecret")
        self.otp_lock_info = OTPLockInfo.objects.create(otp_secret=self.otp_secret)

    def test_otp_secret_creation(self):
        self.assertTrue(isinstance(self.otp_secret, OTPSecret))
        self.assertEqual(self.otp_secret.user, self.user)

    def test_secret_encryption_decryption(self):
        self.assertNotEqual(self.otp_secret.encrypted_secret, "testsecret")
        self.assertEqual(self.otp_secret.secret, "testsecret")

    def test_default_values(self):
        self.assertEqual(self.otp_lock_info.attempts, 0)
        self.assertIsNone(self.otp_lock_info.last_attempt)
        self.assertFalse(self.otp_lock_info.is_locked)
        self.assertFalse(self.otp_secret.is_verified)

    def test_update_attempts(self):
        self.otp_lock_info.attempts += 1
        self.otp_lock_info.last_attempt = timezone.now()
        self.otp_lock_info.save()

        updated_otp = OTPLockInfo.objects.get(id=self.otp_secret.id)
        self.assertEqual(updated_otp.attempts, 1)
        self.assertIsNotNone(updated_otp.last_attempt)

    def test_lock_account(self):
        self.otp_lock_info.is_locked = True
        self.otp_lock_info.save()

        locked_otp = OTPLockInfo.objects.get(id=self.otp_secret.id)
        self.assertTrue(locked_otp.is_locked)

    def test_verify_account(self):
        self.otp_secret.is_verified = True
        self.otp_secret.save()

        verified_otp = OTPSecret.objects.get(id=self.otp_secret.id)
        self.assertTrue(verified_otp.is_verified)

    def test_one_to_one_relationship(self):
        with self.assertRaises(Exception):
            OTPSecret.objects.create(user=self.user, secret="anothersecret")
