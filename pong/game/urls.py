from django.urls import path
from . import game, views


urlpatterns = [
    path("game", game.GameView.as_view(), name="game"),
    path("tournament", game.TournamentView.as_view(), name="tournament"),
    path("<str:room_name>/", views.room, name="room"),
]
