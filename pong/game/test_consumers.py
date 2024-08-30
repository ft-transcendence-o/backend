from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.test import TestCase
from unittest.mock import patch, AsyncMock
import json

from .utils import get_default_session_data
from .consumers import GameConsumer
from common.fakes import fake_decorators

with fake_decorators():
    from .urls import websocket_urlpatterns

class GameConsumerTest(TestCase):
    @patch('game.consumers.NormalPongGame')
    @patch('game.consumers.GameConsumer.get_session_data')
    @patch('game.consumers.GameConsumer.save_game_state')
    async def test_game_mode_normal(self, mock_save_game, mock_session_data, mock_normal_game):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/normal/123")
        connected, subprotocol = await communicator.connect()

        mock_session_data.return_value = get_default_session_data("Normal", 123)
        self.assertTrue(connected)
        self.assertTrue(mock_normal_game.called)
        await communicator.disconnect()

    @patch('game.consumers.TournamentPongGame')
    @patch('game.consumers.GameConsumer.get_session_data')
    @patch('game.consumers.GameConsumer.save_game_state')
    async def test_game_mode_tournament(self, mock_save_game, mock_session_data, mock_tournament_game):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/tournament/123")
        connected, subprotocol = await communicator.connect()

        mock_session_data.return_value = get_default_session_data("Normal", 123)
        self.assertTrue(connected)
        self.assertTrue(mock_tournament_game.called)
        await communicator.disconnect()

    @patch('game.consumers.GameConsumer.save_game_state')
    async def test_game_start(self, mock_save_game):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/normal/123")
        connected, subprotocol = await communicator.connect()

        await communicator.send_to(text_data="start")
        response = await communicator.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "state")
        self.assertIn("ball_pos", data)
        self.assertIn("panel1", data)
        self.assertIn("panel2", data)
        self.assertIn("ball_rot", data)
        await communicator.disconnect()

    async def test_receive_pause_resume(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/normal/123")
        await communicator.connect()

        await communicator.send_to(text_data="start")
        await communicator.send_to(text_data="pause")
        await communicator.send_to(text_data="resume")
        response = await communicator.receive_from()
        self.assertEqual(json.loads(response)["type"], "state")
        await communicator.disconnect()

    async def test_key_input(self):
        application = URLRouter(websocket_urlpatterns)
        communicator = WebsocketCommunicator(application, "/pong-game/normal/123")
        await communicator.connect()

        await communicator.send_to(text_data="start")
        await communicator.receive_from()

        await communicator.send_to(text_data=json.dumps({
            "KeyW": True,
            "KeyA": False,
            "KeyS": False,
            "KeyD": True,
            "ArrowUp":False,
            "ArrowDown":True,
            "ArrowLeft":False,
            "ArrowRight":True,
            }))
        response = await communicator.receive_from()
        state = json.loads(response)
        self.assertEqual(state["type"], "state")
        self.assertGreater(state["panel1"][1], 0)
        self.assertGreater(state["panel1"][0], 0)
        self.assertLess(state["panel2"][1], 0)
        self.assertLess(state["panel2"][0], 0)
        await communicator.disconnect()