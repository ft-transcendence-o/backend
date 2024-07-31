from django.test import TestCase, AsyncClient
from django.urls import reverse
from unittest.mock import patch, MagicMock
from authentication.auth import UserInfo

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

    @patch('authentication.auth.cache.aget')
    @patch('authentication.auth.token_required')
    async def test_get_valid_token(self, mock_token_required, mock_aget):
        mock_token_required.return_value = lambda func: func
        
        mock_aget.return_value = self.user_data
        response = await self.client.get(self.url, HTTP_AUTHORIZATION=f'Bearer {self.valid_token}')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.user_data)
        mock_aget.assert_called_once_with(f'user_data_{self.valid_token}')

    @patch('authentication.auth.cache.aget')
    @patch('authentication.auth.token_required')
    async def test_get_invalid_token(self, mock_token_required, mock_aget):
        mock_token_required.return_value = lambda func: func
        
        mock_aget.return_value = None
        response = await self.client.get(self.url, HTTP_AUTHORIZATION=f'Bearer {self.invalid_token}')
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "No jwt in request"})
        mock_aget.assert_called_once_with(f'user_data_{self.invalid_token}')

    @patch('authentication.auth.token_required')
    async def test_get_no_token(self, mock_token_required):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "No jwt in request"}
        mock_token_required.side_effect = lambda func: lambda request, *args, **kwargs: mock_response

        response = await self.client.get(self.url)
        
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "No jwt in request"})