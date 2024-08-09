# chat/consumers.py
import json
import numpy as np
import asyncio
import math

from channels.generic.websocket import AsyncWebsocketConsumer


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.game_task = None
        self.key_input = None
        self.game = PongGame()

    async def disconnect(self, close_code):
        if self.game_task:
            self.game_task.cancel()
        #TODO db 작업 및 세션 정리
        # await self.save_game_state()
        # await self.cleanup_resources()

    async def receive(self, text_data):
        if text_data == "start":
            self.game.init_game()
            self.start_game()
        else:
            self.key_input = json.loads(text_data)

    async def game_loop(self):
        try:
            while True:
                if self.key_input:
                    self.game.process_key_input(self.key_input)
                    self.key_input = None
                self.game.move_panels()
                result = self.game.update()
                await self.send(text_data=json.dumps({"game": result}))
                await asyncio.sleep(0.006)
        except asyncio.CancelledError:
            print("CancelledError")

    def start_game(self):
        self.game_task = asyncio.create_task(self.game_loop())


KEY_MAPPING = {
    "KeyW": 0, "KeyA": 1, "KeyS": 2, "KeyD": 3,
    "ArrowUp": 4, "ArrowDown": 6, "ArrowLeft": 5, "ArrowRight": 7
}

class PongGame:
    def __init__(self):
        self.ball_pos = np.array([0.0, 0.0, 0.0]) #공위치
        self.ball_vec = np.array([0.0, 0.0, 1.0]) #공이 움직이는 방향
        self.ball_rot = np.array([0.0, 0.0, 0.0]) #공의 회전벡터
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        self.panel1_pos = np.array([0.0, 0.0, 50.0]) #panel1의 초기위치
        self.panel2_pos = np.array([0.0, 0.0, -50.0]) #panel2의 초기위치
        # self.flag = True # 공이 날라가는 방향

        # 키입력값 [W, A, S, D, UP, Left, Down, Right]
        self.key_state = [False, False, False, False, False, False, False, False]

        # 골대쪽 벽면말고 사이드에 있는 4개의 plane들을 의미하며 각각([법선벡터], 원점으로부터의 거리)를 가지고 있다.
        self.planes = [(np.array([1, 0, 0]), 10), (np.array([-1, 0, 0]), 10), (np.array([0, 1, 0]), 10), (np.array([0, -1, 0]), 10)]

        # panel이 위치한 평면
        self.panel1_plane = (np.array([0, 0, -1]), 50) #(법선벡터, 원점과의 거리)
        self.panel2_plane = (np.array([0, 0, 1]), 50)
        self.player1_score = 0
        self.player2_score = 0

    def init_game(self):
        self.ball_pos = np.array([0.0, 0.0, 0.0]) #공위치
        self.ball_vec = np.array([0.0, 0.0, 1.0]) #공이 움직이는 방향
        self.ball_rot = np.array([0.0, 0.0, 0.0]) #공의 회전벡터
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        self.panel1_pos = np.array([0.0, 0.0, 50.0]) #panel1의 초기위치
        self.panel2_pos = np.array([0.0, 0.0, -50.0]) #panel2의 초기위치

    def process_key_input(self, key_input):
        for k, v in key_input.items():
            if k in KEY_MAPPING:
                self.key_state[KEY_MAPPING[k]] = v

    def move_panels(self):
        ball_speed = 0.2
        if self.key_state[0]:
            self.panel1_pos[1] += ball_speed
        elif self.key_state[2]:
            self.panel1_pos[1] -= ball_speed
        if self.key_state[1]:
            self.panel1_pos[0] -= ball_speed
        elif self.key_state[3]:
            self.panel1_pos[0] += ball_speed
        if self.key_state[4]:
            self.panel2_pos[1] += ball_speed
        elif self.key_state[6]:
            self.panel2_pos[1] -= ball_speed
        if self.key_state[5]:
            self.panel2_pos[0] += ball_speed
        elif self.key_state[7]:
            self.panel2_pos[0] -= ball_speed


    def update(self):
        steps = 10
        for i in range(steps):
            movement = np.copy(self.ball_vec) * (0.4 / steps)
            self.ball_pos += movement

            collision_plane = self.check_collision_with_sides()
            if collision_plane:
                self.update_ball_vector(collision_plane)
                break
            self.check_collision_with_goal_area()

        # is this tuple?
        return ({
            "ball": self.ball_pos.tolist(),
            "panel1": self.panel1_pos.tolist(),
            "panel2": self.panel2_pos.tolist(),
        })

    # 벽4가지를 순회하며 어느 벽과 충돌했는지 판별하고 부딪힌 벽을 반환
    def check_collision_with_sides(self):
        for plane in self.planes:
            collision_point = self.get_collision_point_with_plane(plane)
            if isinstance(collision_point, np.ndarray):
                self.ball_pos = collision_point
                self.ball_pos += (plane[0] * 2) # 현재 공의 좌표에 평면의 법선벡터 * 2를 해서 더해준다
                return plane
        return None

    # 구가 평면과 부딪힌 좌표
    def get_collision_point_with_plane(self, plane):
        distance_to_plane = self.plane_distance_to_point(plane)
        if abs(distance_to_plane) <= 2:
            return self.ball_pos - (plane[0] * distance_to_plane)
        return None

    # 평면과 점 사이의 거리, 인자로 부딪힌 평면을 받고, 그 평면과 구의 중심사이의 거리를 계산한다
    def plane_distance_to_point(self, plane):
        # plane은 ((x, y, z), (원점으로부터의 거리)) -> 법선벡터, 원점으로부터의 거리로 구현
        a, b, c = plane[0] # 법선벡터
        d = plane[1] # 중심으로부터의 거리
        return abs(self.ball_pos[0] * a + self.ball_pos[1] * b + self.ball_pos[2] * c + d) / math.sqrt(a**2 + b**2 + c**2)

    # 공 벡터 업데이트함수
    def update_ball_vector(self, collision_plane):
        dot_product = np.dot(self.ball_vec, collision_plane[0])
        reflection = collision_plane[0] * dot_product * 2
        self.ball_vec = self.ball_vec - reflection

    # panel이 위치한 평면과 충돌시
    def check_collision_with_goal_area(self):
        if self.ball_pos[2] >= 48: # z좌표가 48이상인경우 #player1쪽 벽과 충돌한경우
            if self.is_ball_in_panel(self.panel1_pos): # x,y 좌표 판정
                self.handle_panel_collision(self.panel1_plane) # panel1과 충돌한경우
            else:
                self.player2_win() # panel1이 위치한 면에 충돌한경우
        elif self.ball_pos[2] <= -48:
            if self.is_ball_in_panel(self.panel2_pos):
                self.handle_panel_collision(self.panel2_plane) # panel2와 충돌한 경우
            else:
                self.player1_win()

    # 공 중심의 x, y좌표가 panel안에 위치하는지 확인하는 함수
    def is_ball_in_panel(self, panel_pos):
        if abs(self.ball_pos[0] - panel_pos[0]) > 4:
            return False
        elif abs(self.ball_pos[1] - panel_pos[1]) > 4:
            return False
        return True

    # 판넬과 공이 충돌한 경우
    def handle_panel_collision(self, panel_plane):
        # 충돌지점 계산
        collision_point = self.get_collision_point_with_plane(panel_plane)
        # 충돌후 공의 좌표를 보정
        self.ball_pos = collision_point + panel_plane[0] * 2
        self.update_ball_vector(panel_plane)

    def player1_win(self):
        self.ball_vec = np.array([0.0, 0.0, 1.0])
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        self.ball_pos = np.array([0.0, 0.0, 0.0])
        self.player1_score += 1
        result = {
            "score": [self.player1_score, self.player2_score],
        }
        # asyncio.create_task(self.send(text_data=json.dumps({"score": result})))

    def player2_win(self):
        self.ball_vec = np.array([0.0, 0.0, 1.0])
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        self.ball_pos = np.array([0.0, 0.0, 0.0])
        self.player2_score += 1
        result = {
            "score": [self.player1_score, self.player2_score],
        }
        # asyncio.create_task(self.send(text_data=json.dumps({"score": result})))