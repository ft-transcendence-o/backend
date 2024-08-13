from django.urls import path, re_path
from . import game, views, consumers


# BASEURL + /api/game-management/
urlpatterns = [
    path("game", game.GameView.as_view(), name="game"),
    path("tournament", game.TournamentView.as_view(), name="tournament"),
    path("session", game.SessionView.as_view(), name="session"),
    path("test", game.TestView.as_view(), name="test"),
]

# BASEURL + /api/pong-game/
websocket_urlpatterns = [
    path("pong-game/<str:mode>/<int:userid>", consumers.GameConsumer.as_asgi(), name="pong_game"),
]