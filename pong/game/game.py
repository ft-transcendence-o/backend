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
    required_fields = ['player1Nick', 'player2Nick', 'player1Score', 'player2Score', 'mode']
    for field in required_fields:
        if field not in data:
            errors[field] = f"{field} is required."
    if data.get('mode') != mode:
        errors['mode'] = f"Game mode must be '{mode}'"
    return errors

class GameView(View):
    @login_required
    async def get(self, request, decoded_jwt):
        user_id = decoded_jwt.get("user_id")
        page_number = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('size', 10))

        count_games = sync_to_async(Game.objects.filter(user_id=user_id).count)
        total_games = await count_games()

        start = (page_number - 1) * page_size
        end = start + page_size
        games = await sync_to_async(list)(Game.objects.filter(user_id=user_id).order_by('-created_at')[start:end])

        response_data = []
        for game in games:
            game_data = {
                'id': game.id,
                'player1Nick': game.player1_nick,
                'player2Nick': game.player2_nick,
                'player1Score': game.player1_score,
                'player2Score': game.player2_score,
                'mode': game.mode,
                'tournament_id': game.tournament_id,
                'created_at': game.created_at.isoformat()
            }
            response_data.append(game_data)

        total_pages = (total_games + page_size - 1) // page_size
        has_next = page_number < total_pages
        has_previous = page_number > 1

        return JsonResponse({
            "games": response_data,
            "page": {
                "current": page_number,
                "has_next": has_next,
                "has_previous": has_previous,
                "total_pages": total_pages,
                "total_items": total_games,
            }
        }, safe=False)

    @login_required
    async def post(self, request, decoded_jwt):
        user_id = decoded_jwt.get("user_id")
        try:
            data = json.loads(request.body)
            game = await sync_to_async(Game.objects.create)(
                user_id=user_id,
                player1_nick=data['player1Nick'],
                player2_nick=data['player2Nick'],
                player1_score=data['player1Score'],
                player2_score=data['player2Score'],
                mode=data['mode']
            )
            return JsonResponse({"status": "Game created successfully", "id": game.id}, status=201)
        except KeyError as e:
            return JsonResponse({"error": f"Missing required field: {str(e)}"}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

class TournamentView(View):
    @login_required
    async def post(self, request, decoded_jwt):
        user_id = decoded_jwt.get("user_id")
        try:
            data = json.loads(request.body)
            tournament_errors = {}
            for i in range(1, 4):
                game_key = f'game{i}'
                if game_key not in data:
                    tournament_errors[game_key] = f"{game_key} is required."
                else:
                    game_errors = validate_game(data[game_key], 'TOURNAMENT')
                    if game_errors:
                        tournament_errors[game_key] = game_errors

            if tournament_errors:
                return JsonResponse({"errors": tournament_errors}, status=400)

            tournament = await sync_to_async(Tournament.objects.create)(user_id=user_id)
            for i in range(1, 4):
                game_key = f'game{i}'
                game_data = data[game_key]
                game = await sync_to_async(Game.objects.create)(
                    user_id=user_id,
                    tournament_id=tournament.id,
                    player1_nick=game_data['player1Nick'],
                    player2_nick=game_data['player2Nick'],
                    player1_score=game_data['player1Score'],
                    player2_score=game_data['player2Score'],
                    mode=game_data['mode'])
                setattr(tournament, game_key, game)
            await sync_to_async(tournament.save)()
            return JsonResponse({"status": "Tournament created successfully", "id": tournament.id}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f'error: {str(e)}')
            return JsonResponse({"error": str(e)}, status=400)
