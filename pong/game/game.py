from asgiref.sync import sync_to_async
from django.http import JsonResponse
from django.core.cache import cache
from authentication.decorators import login_required
from .models import Game, Tournament
from django.views import View
import json
import logging

logger = logging.getLogger(__name__)


def validate_game(data, mode):
    errors = {}
    required_fields = ["player1Nick", "player2Nick", "player1Score", "player2Score", "mode"]
    for field in required_fields:
        if field not in data:
            errors[field] = f"{field} is required."
    if data.get("mode") != mode:
        errors["mode"] = f"Game mode must be '{mode}'"
    return errors


class GameView(View):
    @login_required
    async def get(self, request, decoded_jwt):
        user_id = decoded_jwt.get("user_id")
        page_number = int(request.GET.get("page", 1))
        page_size = int(request.GET.get("size", 10))

        count_games = sync_to_async(Game.objects.filter(user_id=user_id).count)
        total_games = await count_games()

        start = (page_number - 1) * page_size
        end = start + page_size
        games = await sync_to_async(list)(
            Game.objects.filter(user_id=user_id).order_by("-created_at")[start:end]
        )

        response_data = []
        for game in games:
            game_data = {
                "id": game.id,
                "player1Nick": game.player1_nick,
                "player2Nick": game.player2_nick,
                "player1Score": game.player1_score,
                "player2Score": game.player2_score,
                "mode": game.mode,
                "tournament_id": game.tournament_id,
                "created_at": game.created_at.isoformat(),
            }
            response_data.append(game_data)

        total_pages = (total_games + page_size - 1) // page_size
        has_next = page_number < total_pages
        has_previous = page_number > 1

        return JsonResponse(
            {
                "games": response_data,
                "page": {
                    "current": page_number,
                    "has_next": has_next,
                    "has_previous": has_previous,
                    "total_pages": total_pages,
                    "total_items": total_games,
                },
            },
            safe=False,
        )

    @login_required
    async def post(self, request, decoded_jwt):
        user_id = decoded_jwt.get("user_id")
        try:
            data = json.loads(request.body)
            game = await sync_to_async(Game.objects.create)(
                user_id=user_id,
                player1_nick=data["player1Nick"],
                player2_nick=data["player2Nick"],
                player1_score=data["player1Score"],
                player2_score=data["player2Score"],
                mode=data["mode"],
            )
            return JsonResponse({"status": "Game created successfully", "id": game.id}, status=201)
        except KeyError as e:
            return JsonResponse({"error": f"Missing required field: {str(e)}"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


# DEPRECATED!
class TournamentView(View):
    @login_required
    async def get(self, request, decoded_jwt):
        """
        대진표에서 필요한 정보들을 반환
        
        :cookie jwt: 인증을 위한 JWT
        """
        session_data = request.session.get("game_info_t", {})
        data = {
            "players_name": session_data.get("players_name", ['player1', 'player2', 'player3', 'player4']),
            "win_history": session_data.get("win_history", []),
            "game_round": session_data.get("game_round", 1),
        }
        return JsonResponse(data)

    @login_required
    async def post(self, request, decoded_jwt):
        """
        토너먼트 유저 이름을 받아온다
        
        :cookie jwt: 인증을 위한 JWT
        :body players_name: 4명의 유저 이름을 담은 리스트
        """
        try:
            body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        
        players_name = body.get("players_name", ['player1', 'player2', 'player3', 'player4'])
        session_data = await cache.aget(f"session_data_{user_id}", {})
        return JsonResponse({"message": "success set players name"})

class SessionView(View):
    @login_required
    async def get(self, request, decoded_jwt):
        """
        세션 정보 반환
        
        :cookie jwt: 인증을 위한 JWT
        """
        user_id = decoded_jwt.get("user_id")
        mode = request.GET.get("mode")
        if mode != "tournament":
            mode = "normal"
        session_data = await cache.aget(f"session_data_{mode}_{user_id}", {})
        data = {
            "user_id": user_id,
            "players_name": session_data.get("players_name", ['player1', 'player2', 'player3', 'player4']),
            "win_history": session_data.get("win_history", []),
            "game_round": session_data.get("game_round", 1),
        }
        return JsonResponse(data)

    @login_required
    async def post(self, request, decoded_jwt):
        """
        tournament 플레이어 이름을 cache에 저장한 뒤
        불러와서 사용
        
        :body players_name: 사용자 이름 리스트
        :cookie jwt: 인증을 위한 JWT
        """
        try:
            body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        user_id = decoded_jwt.get("user_id")
        players_name = body.get("players_name", ['player1', 'player2', 'player3', 'player4'])
        data = {
            "user_id": user_id,
            "players_name": players_name,
            "win_history": [],
            "game_round": 1
        }
        cache.set(f"session_data_tournament_{user_id}", data, 500)
        return JsonResponse({"message": "Set session success"})


class TestView(View):
    @login_required
    async def post(self, request, decoded_jwt):
        """
        tournament 플레이어 이름을 cache에 저장한 뒤
        불러와서 사용
        
        :body players_name: 사용자 이름 리스트
        :cookie jwt: 인증을 위한 JWT
        """
        try:
            body = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        user_id = decoded_jwt.get("user_id")
        players_name = body.get("players_name", ['player1', 'player2', 'player3', 'player4'])
        win_history = body.get("win_history", [])
        game_round = body.get("game_round", 1)
        left_score = body.get("left_score", 0)
        right_score = body.get("right_score", 0)
        data = {
            "players_name": players_name,
            "win_history": [],
            "game_round": 1,
            "left_score": 0,
            "right_score": 0,
        }
        cache.set(f"session_data_tournament_{user_id}", data, 500)
        return JsonResponse({"message": "Set tournament session success"})