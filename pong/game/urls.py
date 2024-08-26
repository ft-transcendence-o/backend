from django.urls import path, re_path
from .consumers import GameConsumer
from .views import (
    GameView,
    TournamentView,
    SessionView,
)


# BASEURL + /api/game-management/
urlpatterns = [
    path("game", GameView.as_view(), name="game"),
    path("tournament", TournamentView.as_view(), name="tournament"),
    path("session", SessionView.as_view(), name="session"),
]

# BASEURL + /api/pong-game/
websocket_urlpatterns = [
    path("pong-game/<str:mode>/<int:userid>", GameConsumer.as_asgi(), name="pong_game"),
]
