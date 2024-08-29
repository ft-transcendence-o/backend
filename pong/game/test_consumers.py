from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.test import TestCase
from unittest.mock import patch, AsyncMock

from .urls import websocket_urlpatterns
from .consumers import GameConsumer
from .utils import get_default_session_data

class GameConsumerTest(TestCase):
    @patch('game.consumers.NormalPongGame')
    @patch('game.consumers.GameConsumer.get_session_data')
    @patch('game.consumers.GameConsumer.save_game_state')
    async def test_game_consumer(self, mock_save_game, mock_session_data, mock_normal_game):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/normal/123")
        connected, subprotocol = await communicator.connect()

        mock_session_data.return_value = get_default_session_data("Normal", 123)
        self.assertTrue(connected)
        self.assertTrue(mock_normal_game.called)

        mock_game_instance = AsyncMock()
        mock_normal_game.return_value = mock_game_instance
        await communicator.send_to(text_data="start")
        # await communicator.wait()
        # mock_game_instance.move_panels.assert_called()
        # mock_game_instance.update.assert_called()

        mock_save_game.return_value = None
        await communicator.disconnect()

        # response = await communicator.receive_from()
        # assert response == "hello"
        # # Close

