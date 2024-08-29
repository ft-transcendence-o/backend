from django.test import TestCase, AsyncClient, AsyncRequestFactory
from django.urls import reverse
from unittest.mock import patch, Mock
import json

from .models import Game, Tournament
from .utils import get_default_session_data
from common.constants import MAX_ATTEMPTS, JWT_SECRET
from common.fakes import (
    fake_decorators,
    FAKE_USER,
    FAKE_NORMAL_GAME,
)

with fake_decorators():
    from .views import GameView, SessionView


class GameViewTestCase(TestCase):
    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.user = FAKE_USER        

    @patch("game.views.Game.objects")
    async def test_get_games(self, mock_game):
        mock_game.filter.return_value.count.return_value = 3

        request = self.factory.get("/game/")
        view = GameView()
        response = await view.get(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn("games", data)
        self.assertIn("page", data)

    @patch("game.views.Game.objects.create")
    async def test_post_game(self, mock_game):
        fake_game = {
            "player1Nick": "player1",
            "player2Nick": "player1",
            "player1Score": 3,
            "player2Score": 2,
            "mode": "Normal",
        }
        
        game = Game()
        game.user_id = 123
        game.id = 234
        game.player1_nick = "player1"
        game.player2_nick = "player2"
        game.player1_score = 3
        game.player2_score = 2
        game.mode = "Normal"

        mock_game.return_value = game
        request = self.factory.post('/game/', json.dumps(fake_game), content_type='application/json')
        view = GameView()
        response = await view.post(request)

        self.assertEqual(response.status_code, 201)
        data = json.loads(response.content)
        self.assertEqual(data["status"], "Game created successfully")
        self.assertEqual(data["id"], 234)


class SessionViewTestCase(TestCase):
    def setUp(self):
        self.factory = AsyncRequestFactory()
        self.user = FAKE_USER
        self.normal_session_data = get_default_session_data(self.user["id"], "Normal")
        self.tournament_session_data = get_default_session_data(self.user["id"], "Tournament")

    @patch('game.views.cache.aget')
    async def test_get_normal_session(self, mock_cache_aget):
        mock_cache_aget.return_value = self.normal_session_data

        request = self.factory.get('/session/?mode=normal')
        view = SessionView()
        response = await view.get(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["user_id"], self.user["id"])
        self.assertEqual(data["mode"], self.normal_session_data["mode"])
        self.assertEqual(data["left_score"], self.normal_session_data["left_score"])
        self.assertEqual(data["right_score"], self.normal_session_data["right_score"])

    @patch('game.views.cache.aget')
    async def test_get_tournament_session(self, mock_cache_aget):
        mock_cache_aget.return_value = self.tournament_session_data

        request = self.factory.get('/session/?mode=tournament')
        view = SessionView()
        response = await view.get(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data["user_id"], self.user["id"])
        self.assertEqual(data["mode"], self.tournament_session_data["mode"])
        self.assertEqual(data["left_score"], self.tournament_session_data["left_score"])
        self.assertEqual(data["right_score"], self.tournament_session_data["right_score"])

    @patch('game.views.cache.set')
    async def test_post_session(self, mock_cache_set):
        players_data = {
            'players_name': ['p1', 'p2', 'p3', 'p4']
        }
        request = self.factory.post('/session/', json.dumps(players_data), content_type='application/json')
        view = SessionView()
        response = await view.post(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['message'], 'Set session success')

    @patch('game.views.cache.delete')
    async def test_delete_session(self, mock_cache_delete):
        request = self.factory.delete('/session/', json.dumps({'mode': 'normal'}), content_type='application/json')
        view = SessionView()
        response = await view.delete(request)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['message'], 'Delete session success')
