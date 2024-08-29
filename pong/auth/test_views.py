from django.test import TestCase, AsyncClient, AsyncRequestFactory
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from urllib.parse import quote
import json
import jwt
import pyotp

from .models import OTPLockInfo, OTPSecret, User
from common.constants import MAX_ATTEMPTS, JWT_SECRET
from common.fakes import (
    fake_decorators,
    FAKE_USER,
    FAKE_JWT_NO_OTP,
    FAKE_JWT_PASS_OTP,
    FAKE_USER_DATA,
)

with fake_decorators():
    from .views import OAuthView, OTPView, UserInfo, StatusView, QRcodeView


class QRcodeViewTestCase(TestCase):
    """Integration tests for QRcode View class"""

    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.view = QRcodeView()

        self.user = User.objects.create(**FAKE_USER)
        self.otp_secret = OTPSecret.objects.create(
            user_id=self.user.id, secret="TESTSECRET", is_verified=False
        )

    @patch("auth.views.get_user_data")
    async def test_successful_qr_code_generation(self, mock_get_user_data):
        mock_get_user_data.return_value = FAKE_USER_DATA
        request = self.factory.get("/otp/qrcode")
        response = await self.view.get(request)

        self.assertEqual(response.status_code, 200)
        content = json.loads(response.content.decode("utf-8"))
        self.assertIn("otpauth_uri", content)
        self.assertIn("pong_game", content["otpauth_uri"])
        self.assertIn(quote("test@example.com"), content["otpauth_uri"])

    @patch("auth.views.get_user_data")
    async def test_already_verified_user(self, mock_get_user_data):
        verified_user_data = FAKE_USER_DATA.copy()
        verified_user_data["is_verified"] = True
        mock_get_user_data.return_value = verified_user_data
        request = self.factory.get("/otp/qrcode")
        response = await self.view.get(request)

        self.assertEqual(response.status_code, 400)
        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content["error"], "Can't show QRcode")

    def test_generate_otp_uri(self):
        uri = self.view.generate_otp_uri(FAKE_USER_DATA)

        self.assertIn("pong_game", uri)
        self.assertIn(quote("test@example.com"), uri)
        self.assertIn("TESTSECRET", uri)


class OTPViewTestCase(TestCase):
    """Integration tests for OTP View class"""

    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.view = OTPView()
        self.user_id = FAKE_USER["id"]

        self.user = User.objects.create(**FAKE_USER)
        self.otp_secret = OTPSecret.objects.create(
            user_id=self.user.id, secret="TESTSECRET", is_verified=False
        )
        self.otp_lock_info = OTPLockInfo.objects.create(
            otp_secret=self.otp_secret, attempts=0, last_attempt=None, is_locked=False
        )

    def create_request(self, input_password):
        request = self.factory.post(
            "/otp/verify",
            json.dumps({"input_password": input_password}),
            content_type="application/json",
        )
        request.COOKIES["jwt"] = FAKE_JWT_NO_OTP
        return request

    @patch("auth.views.OTPView.verify_otp")
    async def test_successful_otp_verification(self, mock_verify_otp):
        mock_verify_otp.return_value = True
        request = self.create_request("right_otp")
        response = await self.view.post(request)

        # TODO: NEED CHECK COOKIE
        self.assertIn("jwt", response.cookies)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["success"], "OTP authentication verified"
        )

    @patch("auth.views.OTPView.verify_otp")
    async def test_failed_otp_verification(self, mock_verify_otp):
        mock_verify_otp.return_value = False
        request = self.create_request("wrong_otp")
        response = await self.view.post(request)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "Incorrect password."
        )

    async def test_account_locked(self):
        self.otp_lock_info.is_locked = True
        self.otp_lock_info.last_attempt = timezone.now()
        await self.otp_lock_info.asave()

        request = self.create_request("right_otp")
        response = await self.view.post(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "Account is locked. try later"
        )

    async def test_max_attempts_exceeded(self):
        self.otp_lock_info.attempts = MAX_ATTEMPTS - 1
        await self.otp_lock_info.asave()

        request = self.create_request("wrong_otp")
        response = await self.view.post(request)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"],
            "Maximum number of attempts exceeded. Please try again after 15 minutes.",
        )

    async def test_no_otp_data(self):
        await OTPSecret.objects.filter(user_id=self.user_id).adelete()
        request = self.create_request("otp")
        response = await self.view.post(request)
        self.assertEqual(response.status_code, 500)
        self.assertIn("Can't found OTP data", json.loads(response.content.decode("utf-8"))["error"])

    @patch("auth.views.OTPView.verify_otp")
    async def test_update_otp_success(self, mock_verify_otp):
        mock_verify_otp.return_value = True
        request = self.create_request("right_otp")
        await self.view.post(request)

        updated_otp_secret = await OTPSecret.objects.aget(user_id=self.user_id)
        updated_otp_lock_info = await OTPLockInfo.objects.aget(otp_secret=updated_otp_secret)

        self.assertTrue(updated_otp_secret.is_verified)
        self.assertFalse(updated_otp_lock_info.is_locked)
        self.assertEqual(updated_otp_lock_info.attempts, 0)


class StatusViewTestCase(TestCase):
    """Integration tests for Status View class"""

    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.view = StatusView.as_view()
        self.url = reverse("auth_status")
        self.user_data = FAKE_USER

    async def test_no_jwt_cookie(self):
        request = self.factory.get("/auth-status/")
        response = await self.view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["error"], "No jwt in request")

    async def test_invalid_jwt(self):
        request = self.factory.get("/auth-status/")
        request.COOKIES["jwt"] = "invalid_jwt"
        response = await self.view(request)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            json.loads(response.content.decode("utf-8"))["error"], "Decoding jwt failed"
        )

    async def test_valid_jwt_otp_not_verified(self):
        valid_jwt = FAKE_JWT_NO_OTP
        request = self.factory.get("/auth-status/")
        request.COOKIES["jwt"] = valid_jwt
        response = await self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["access_token_valid"], True)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["otp_authenticated"], False)

    async def test_valid_jwt_otp_verified(self):
        valid_jwt = FAKE_JWT_PASS_OTP
        request = self.factory.get("/auth-status/")
        request.COOKIES["jwt"] = valid_jwt
        response = await self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["access_token_valid"], True)
        self.assertEqual(json.loads(response.content.decode("utf-8"))["otp_authenticated"], True)


class UserInfoViewTestCase(TestCase):
    """Integration tests for UserInfo View class"""

    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse("user_info")
        self.user_data = FAKE_USER

    @patch("auth.views.get_user_data")
    async def test_get_invalid_token(self, mock_get_user_data):
        mock_get_user_data.return_value = None

        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Invalid token")

    @patch("auth.views.get_user_data")
    async def test_get_success(self, mock_get_user_data):
        mock_get_user_data.return_value = self.user_data

        response = await self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user_data["email"])
        self.assertEqual(response.json()["login"], self.user_data["login"])