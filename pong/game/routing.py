from django.urls import re_path

from . import consumers

# TODO: urls에 합쳐지나?
websocket_urlpatterns = [
    re_path(r"ws/game/(?P<mode>\w+)", consumers.GameConsumer.as_asgi()),
]
