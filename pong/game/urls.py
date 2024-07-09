from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GameViewSet, TournamentViewSet

router = DefaultRouter()
router.register(r'games', GameViewSet)
router.register(r'tournaments', TournamentViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]
