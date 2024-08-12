from django.urls import path, re_path
from . import game, views, consumers


urlpatterns = [
    path("game", game.GameView.as_view(), name="game"),
    path("tournament", game.TournamentView.as_view(), name="tournament"),
]

websocket_urlpatterns = [
    path("pong-game/<str:mode>", consumers.GameConsumer.as_asgi(), name="pong_game"),
]

# urlpatterns += websocket_urlpatterns