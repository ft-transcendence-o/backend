from django.test import TestCase, AsyncClient
from django.urls import reverse
from unittest.mock import patch, MagicMock


class UserInfoTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('user_info')
        self.valid_token = 'valid_token'
        self.invalid_token = 'invalid_token'
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'login': 'testuser',
            'usual_full_name': 'Test User',
            'image_link': 'http://example.com/image.jpg'
        }

    async def test_get_user_info_success(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = self.user_data

            response = await self.client.get(
                self.url,
                Authorization=f'Bearer {self.valid_token}'
            )

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), self.user_data)

    async def test_get_user_info_fail(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = None

            response = await self.client.get(
                self.url,
                Authorization = f'Bearer {self.valid_token}'
            )

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "Invalid token"})

    async def test_get_invalid_token(self):
        with patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = None

            response = await self.client.get(self.url)

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "No jwt in request"})


    async def test_get_no_token(self):
        with patch('authentication.auth.token_required') as mock_token_required:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "No jwt in request"}
            mock_token_required.side_effect = lambda func: lambda request, *args, **kwargs: mock_response

            response = await self.client.get(self.url)

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json(), {"error": "No jwt in request"})



class QRcodeViewTestCase(TestCase):
    def setUp(self):
        self.client = AsyncClient()
        self.url = reverse('otp_qrcode')
        self.valid_token = 'valid_token'
        self.invalid_token = 'invalid_token'
        self.user_data = {
            'id': 1,
            'email': 'test@example.com',
            'login': 'testuser',
            'usual_full_name': 'Test User',
            'image_link': 'http://example.com/image.jpg',
            'secret': 'JBSWY3DPEHPK3PXP'
        }

    async def test_get_qrcode_success(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.return_value = self.user_data

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn('otpauth_uri', response.json())

    async def test_get_user_info_no_user_data(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            mock_cache_aget.side_effect = [self.user_data, None]

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "User data not found"})

    async def test_get_user_info_no_secret(self):
        with patch('authentication.decorators.validate_jwt') as mock_validate_jwt, \
            patch('authentication.auth.cache.aget') as mock_cache_aget, \
            patch('authentication.auth.token_required') as mock_token_required:

            mock_validate_jwt.return_value = {'access_token': self.valid_token}, False
            mock_token_required.return_value = lambda f: f
            user_data_no_secret = self.user_data.copy()
            user_data_no_secret.pop('secret')
            mock_cache_aget.side_effect = [self.user_data, user_data_no_secret]

            response = await self.client.get(
                self.url,
                headers={'Authorization': f'Bearer {self.valid_token}'}
            )

            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json(), {"error": "User secret not found"})