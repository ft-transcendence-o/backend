from django.test import TestCase, RequestFactory
from django.http import JsonResponse
from django.utils import timezone
from unittest.mock import patch, MagicMock
from datetime import timedelta
import json
import jwt

from .decorators import token_required
from .models import OTPSecret, User, OTPLockInfo
from .constants import JWT_SECRET


class AuthDecoratorFactoryTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create(id=1, refresh_token='test_refresh_token')

    def create_jwt(self, custom_exp, access_token, user_id, otp_verified):
        payload = {
            "custom_exp": custom_exp,
            "access_token": access_token,
            "user_id": user_id,
            "otp_verified": otp_verified
        }
        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    @patch('authentication.views.refresh_access_token')
    @patch('authentication.views.get_user_data')
    async def test_auth_decorator_valid_token(self, mock_get_user_data, mock_refresh_access_token):
        @auth_decorator_factory(check_otp=True)
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})

        custom_exp = (timezone.now() + timedelta(seconds=300)).timestamp()
        jwt_token = self.create_jwt(custom_exp, 'valid_access_token', 1, True)
        request = self.factory.get('/dummy/')
        request.COOKIES['jwt'] = jwt_token

        mock_get_user_data.return_value = {"is_verified": True}

        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})

    @patch('authentication.views.refresh_access_token')
    @patch('authentication.views.get_user_data')
    async def test_auth_decorator_expired_token(self, mock_get_user_data, mock_refresh_access_token):
        @auth_decorator_factory(check_otp=True)
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})

        custom_exp = (timezone.now() - timedelta(seconds=300)).timestamp()
        jwt_token = self.create_jwt(custom_exp, 'expired_access_token', 1, True)
        request = self.factory.get('/dummy/')
        request.COOKIES['jwt'] = jwt_token

        new_custom_exp = (timezone.now() + timedelta(seconds=JWT_EXPIRED)).timestamp()
        mock_refresh_access_token.return_value = {
            "custom_exp": new_custom_exp,
            "access_token": "new_access_token",
            "user_id": 1,
            "otp_verified": True
        }
        mock_get_user_data.return_value = {"is_verified": True}

        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"success": True})
        mock_refresh_access_token.assert_called_once()

    async def test_auth_decorator_no_jwt(self):
        @auth_decorator_factory(check_otp=True)
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})

        request = self.factory.get('/dummy/')
        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "No jwt in request"})

    async def test_auth_decorator_invalid_jwt(self):
        @auth_decorator_factory(check_otp=True)
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})

        request = self.factory.get('/dummy/')
        request.COOKIES['jwt'] = 'invalid_jwt_token'
        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "Decoding jwt failed"})

    @patch('authentication.views.refresh_access_token')
    @patch('authentication.views.get_user_data')
    async def test_auth_decorator_otp_not_verified(self, mock_get_user_data, mock_refresh_access_token):
        @auth_decorator_factory(check_otp=True)
        async def dummy_view(self, request, decoded_jwt):
            return JsonResponse({"success": True})

        custom_exp = (timezone.now() + timedelta(seconds=300)).timestamp()
        jwt_token = self.create_jwt(custom_exp, 'valid_access_token', 1, False)
        request = self.factory.get('/dummy/')
        request.COOKIES['jwt'] = jwt_token

        mock_get_user_data.return_value = {"is_verified": True}

        response = await dummy_view(None, request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {
            "error": "Need OTP authentication",
            "otp_verified": False,
            "show_otp_qr": True
        })


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
