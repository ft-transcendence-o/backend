from .utils import get_default_session_data
from .ponggame import NormalPongGame, TournamentPongGame
from django.core.cache import cache
from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio


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
        if self.game.state != "ended":
            await self.save_game_state()

    async def save_game_state(self):
        await sync_to_async(cache.set)(
            f"session_data_{self.mode}_{self.user_id}", self.session_data, 500
        )

    async def receive(self, text_data):
        if text_data == "start":
            self.start_game()
        elif text_data == "pause":
            self.pause = True
        elif text_data == "resume":
            self.pause = False
        else:
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
        default_data = get_default_session_data(self.user_id, self.mode)
        session_data = await cache.aget(f"session_data_{self.mode}_{self.user_id}", default_data)
        return session_data
