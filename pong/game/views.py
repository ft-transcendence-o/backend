from rest_framework import mixins, viewsets, status
from rest_framework.response import Response
from .models import Game, Tournament
from .serializers import GameSerializer, TournamentSerializer
import logging

logger = logging.getLogger(__name__)

class GameViewSet(mixins.ListModelMixin,
                  mixins.CreateModelMixin,
                  viewsets.GenericViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"games": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "200 OK"}, status=status.HTTP_200_OK)
        logger.error('This is an error message')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TournamentViewSet(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        viewsets.GenericViewSet):
    queryset = Tournament.objects.all()
    serializer_class = TournamentSerializer

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({"tournaments": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request):
        print('Request Data: ', request.data)
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            tournament = serializer.save()
            return Response({"status": "200 OK"}, status=status.HTTP_200_OK)
        print("Serializer errors:", serializer.errors)  # 유효성 검사 오류 출력
        logger.error('This is an error message')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
