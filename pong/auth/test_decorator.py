from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
import json
import jwt

from .decorators import token_required, login_required
from .models import OTPSecret, User, OTPLockInfo
from .constants import JWT_SECRET, JWT_EXPIRED


class AuthDecoratorTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(id=1, refresh_token='test_refresh_token')
        self.user_data = {
            "email": "user1@example.com",
            "login": "login1",
            "secret": "secret",
            "is_verified": True,
            "need_otp": True,
        }
        new_custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        self.update_jwt = {
            "custom_exp": new_custom_exp,
            "access_token": "new_access_token",
            "user_id": 1,
            "otp_verified": True
        }

    def create_jwt(self, custom_exp, access_token, user_id, otp_verified):
        payload = {
            "custom_exp": custom_exp,
            "access_token": access_token,
            "user_id": user_id,
            "otp_verified": otp_verified
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    @token_required
    async def dummy_view(self, request, decoded_jwt):
        return JsonResponse({"success": True})

    async def test_no_jwt_in_request(self):
        request = self.factory.get("/duumy-url")
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "No jwt in request"
            )

    async def test_auth_decorator_invalid_jwt(self):
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = 'invalid_jwt_token'
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "Decoding jwt failed"
            )

    async def test_auth_decorator_invalid_key_in_jwt(self):
        request = self.factory.get('/dummy-url')
        payload = {
            "access_token": "access_token",
            "dummy_key": "dummy_value",
        }
        invalid_token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        request.COOKIES['jwt'] = invalid_token
        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "Invalid jwt error"
            )

    @patch('auth.decorators.refresh_access_token')
    async def test_auth_decorator_refresh_fail(self, mock_refresh_access_token):
        expired_custom_exp = (timezone.now() - timedelta(seconds=1)).timestamp()
        expired_token = self.create_jwt(expired_custom_exp, 'expired_access_token', 1, True)
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = expired_token

        mock_refresh_access_token.side_effect = Exception("Token refresh failed")

        response = await self.dummy_view(request)

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"],
            "Failed refresh access token"
        )
        mock_refresh_access_token.assert_called_once()

    @patch('auth.decorators.refresh_access_token')
    @patch('auth.decorators.get_user_data')
    @patch('auth.decorators.check_user_authorization')
    async def test_auth_decorator_expired_token(self, mock_check_user_authorization, mock_get_user_data, mock_refresh_access_token):
        expired_custom_exp = (timezone.now() - timedelta(seconds=1)).timestamp()
        expired_token = self.create_jwt(expired_custom_exp, 'expired_access_token', 1, True)
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = expired_token

        new_custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        new_token_data = {
            "custom_exp": new_custom_exp,
            "access_token": "new_access_token",
            "user_id": 1,
            "otp_verified": True
        }

        mock_refresh_access_token.return_value = new_token_data
        mock_get_user_data.return_value = self.user_data
        mock_check_user_authorization.return_value = None

        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["success"],
            True
        )

        mock_refresh_access_token.assert_called_once()
        mock_get_user_data.assert_called_once()

        self.assertIn('jwt', response.cookies)
        new_jwt = response.cookies['jwt'].value
        decoded_new_jwt = jwt.decode(new_jwt, JWT_SECRET, algorithms=["HS256"])
        self.assertEqual(decoded_new_jwt['access_token'], "new_access_token")

    @patch('auth.decorators.refresh_access_token')
    @patch('auth.decorators.get_user_data')
    async def test_auth_decorator_valid_token(self, mock_get_user_data, mock_refresh_access_token):
        custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        token = self.create_jwt(custom_exp, 'valid_access_token', 1, True)
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = token

        mock_refresh_access_token.return_value = self.update_jwt
        mock_get_user_data.return_value = self.user_data

        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8")), {"success": True}
            )

    @patch('auth.decorators.refresh_access_token')
    @patch('auth.decorators.get_user_data')
    async def test_token_required_authorization_fail(self, mock_get_user_data, mock_refresh_access_token):
        expired_custom_exp = (timezone.now() - timedelta(seconds=1)).timestamp()
        expired_token = self.create_jwt(expired_custom_exp, 'expired_access_token', 1, True)
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = expired_token

        new_custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        new_token_data = {
            "custom_exp": new_custom_exp,
            "access_token": "new_access_token",
            "user_id": 1,
            "otp_verified": True
        }

        mock_refresh_access_token.return_value = new_token_data
        mock_get_user_data.return_value = self.user_data

        response = await self.dummy_view(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"],
            "Already passed OTP authentication"
        )

        mock_refresh_access_token.assert_called_once()
        mock_get_user_data.assert_called_once()

        self.assertIn('jwt', response.cookies)
        new_jwt = response.cookies['jwt'].value
        decoded_new_jwt = jwt.decode(new_jwt, JWT_SECRET, algorithms=["HS256"])
        self.assertEqual(decoded_new_jwt['access_token'], "new_access_token")

    @patch('auth.decorators.refresh_access_token')
    @patch('auth.decorators.get_user_data')
    async def test_login_required_authorization_fail(self, mock_get_user_data, mock_refresh_access_token):
        @login_required
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})
        expired_custom_exp = (timezone.now() - timedelta(seconds=1)).timestamp()
        expired_token = self.create_jwt(expired_custom_exp, 'expired_access_token', 1, True)
        request = self.factory.get('/dummy-url')
        request.COOKIES['jwt'] = expired_token

        new_custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        new_token_data = {
            "custom_exp": new_custom_exp,
            "access_token": "new_access_token",
            "user_id": 1,
            "otp_verified": False
        }

        mock_refresh_access_token.return_value = new_token_data
        mock_get_user_data.return_value = self.user_data

        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"],
            "Need OTP authentication"
        )

        mock_refresh_access_token.assert_called_once()
        mock_get_user_data.assert_called_once()

        self.assertIn('jwt', response.cookies)
        new_jwt = response.cookies['jwt'].value
        decoded_new_jwt = jwt.decode(new_jwt, JWT_SECRET, algorithms=["HS256"])
        self.assertEqual(decoded_new_jwt['access_token'], "new_access_token")

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
