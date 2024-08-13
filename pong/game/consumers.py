# chat/consumers.py
import json
import asyncio

from .ponggame import NormalPongGame, TournamentPongGame
from django.core.cache import cache
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.game_task = None
        self.key_input = None
        self.pause = False
        self.mode = "tournament"
        if self.scope["url_route"]["kwargs"]["mode"] != "tournament":
            self.mode = "normal"
        self.user_id = self.scope["url_route"]["kwargs"]["userid"]
        self.session_data = await self.get_session_data()
        if self.mode == "tournament":
            self.game = TournamentPongGame(self.send_callback, self.session_data)
        else:
            self.game = NormalPongGame(self.send_callback, self.session_data)

    async def disconnect(self, close_code):
        if self.game_task:
            self.game_task.cancel()
        # TODO db 작업 및 세션 정리
        await self.save_game_state()
        # await self.cleanup_resources()

    async def save_game_state(self):
        await sync_to_async(cache.set)(
            f"session_data_{self.mode}_{self.user_id}", self.session_data, 500
        )

    async def receive(self, text_data):
        if text_data == "start":
            # self.game.init_game()
            self.start_game()
        elif text_data == "pause":
            self.pause = True
        elif text_data == "resume":
            self.pause = False
        else:
            # TODO: MODIFY FLOW
            # self.game.proccess_key_input(text_data)
            self.key_input = json.loads(text_data)

    async def send_callback(self, data):
        await self.send(text_data=json.dumps(data))

    async def game_loop(self):
        try:
            while True:
                while self.pause:
                    await asyncio.sleep(0.1)
                if self.key_input:
                    self.game.process_key_input(self.key_input)
                    self.key_input = None
                self.game.move_panels()
                await self.game.update()
                await asyncio.sleep(0.006)
        except asyncio.CancelledError:
            print("CancelledError")

    def start_game(self):
        self.game_task = asyncio.create_task(self.game_loop())

    async def get_session_data(self):
        session_data = await cache.aget(f"session_data_{self.mode}_{self.user_id}", {})
        context = {
            "players_name": session_data.get(
                "players_name", ["player1", "player2", "player3", "player4"]
            ),
            "win_history": session_data.get("win_history", []),
            "game_round": session_data.get("round", 1),
            "left_score": session_data.get("left_score", 0),
            "right_score": session_data.get("right_score", 0),
        }
        return context

    # DEPRECATED
    def get_players_name(self):
        name_list = self.session_data["players_name"]
        game_round = self.session_data["game_round"]
        if game_round == 1:
            return name_list[0], name_list[1]
        if game_round == 2:
            return name_list[2], name_list[3]
        if game_round == 3:
            return self.session_data["win_history"]
        return "player1", "player2"
