# chat/consumers.py
import json
import numpy as np
import asyncio
import math

from channels.generic.websocket import AsyncWebsocketConsumer

#TODO classify paddle and ball
class Paddle:
    def __init__(self, pos, plane):
        self.positon = np.array(pos)
        self.plane = (np.array(plane), 50)

class Ball:
    def __init__(self):
        self.position = np.array([0.0, 0.0, 0.0]) #공위치  #@
        self.vector = np.array([0.0, 1.0, 2.0]) #공이 움직이는 방향
        self.rotation = np.array([0.0, 0.0, 0.0]) #공의 회전벡터
        self.angular_vector = np.array([0.0, 0.0, 0.0])

class Cube:
    def __init__(self):
        self.planes = [(np.array([1, 0, 0]), 10), (np.array([-1, 0, 0]), 10), (np.array([0, 1, 0]), 10), (np.array([0, -1, 0]), 10)]

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        self.game_task = None
        self.key_input = None

    async def disconnect(self, close_code):
        if self.game_task:
            self.game_task.cancel()
        #TODO db 작업 및 세션 정리
        # await self.save_game_state()
        # await self.cleanup_resources()

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        event = text_data_json["event"]
        if event == "start":
            self.init_game()
            self.start_game()
        elif event == "key_input":
            self.key_input = text_data_json.get("key_input")

    async def game_loop(self):
        try:
            while True:
                if self.key_input:
                    # 키 입력 처리
                    self.process_key_input(self.key_input)
                    self.key_input = None

                result = self.update()
                await self.send(text_data=json.dumps({"game": result}))
                await asyncio.sleep(0.033)
        except asyncio.CancelledError:
            pass

    def start_game(self):
        self.game_task = asyncio.create_task(self.game_loop())

    def process_key_input(self, key):
        """input key에 따른 처리 로직"""
        if key == "W":
            pass
        elif key == "A":
            pass
        elif key == "S":
            pass
        elif key == "D":
            pass
        elif key == "ArrowUp":
            pass
        elif key == "ArrowDown":
            pass
        elif key == "ArrowLeft":
            pass
        elif key == "ArrowRight":
            pass

    def init_game(self):
        self.ball_pos = np.array([0.0, 0.0, 0.0]) #공위치  #@
        self.ball_vec = np.array([0.0, 1.0, 2.0]) #공이 움직이는 방향
        self.ball_rot = np.array([0.0, 0.0, 0.0]) #공의 회전벡터
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        # self.flag = True # 공이 날라가는 방향
        self.panel1_pos = np.array([0.0, 0.0, 50.0]) #panel1의 초기위치 #@
        self.panel2_pos = np.array([0.0, 0.0, -50.0]) #panel2의 초기위치 #@

        # 골대쪽 벽면말고 사이드에 있는 4개의 plane들을 의미하며 각각([법선벡터], 원점으로부터의 거리)를 가지고 있다.
        self.planes = [(np.array([1, 0, 0]), 10), (np.array([-1, 0, 0]), 10), (np.array([0, 1, 0]), 10), (np.array([0, -1, 0]), 10)]

        # player1은 panel1을 조작, player2가 panel2를 조작
        # panel이 위치한 평면
        self.panel1_plane = (np.array([0, 0, -1]), 50) #(법선벡터, 원점과의 거리)
        self.panel2_plane = (np.array([0, 0, 1]), 50) #(법선벡터, 원점과의 거리)

        # self.panel1 = Paddle([0.0, 0.0, 50.0], [0, 0, -1])
        # self.panel2 = Paddle([0.0, 0.0, -50.0], [0, 0, 1])

    async def update(self):
        # user가 입력한 키값 소켓으로 받기
        steps = 10
        for i in range(steps):
            movement = np.copy(self.ball_vec) * (0.4 / steps)
            # self.ball_rot[0] += self.angular_vec[0]
            # self.ball_rot[1] += self.angular_vec[1]
            # self.ball_rot[2] += self.angular_vec[2]
            self.ball_pos += movement

            collisionPlane = self.collision_with_side()
            if collisionPlane:
                self.updateVector(collisionPlane)
                break

            self.collisionWithGoalArea()
        # self.updatePanel()
        return ({
            "ball":self.ball_pos.tolist(),
            "panel1": self.panel1_pos.tolist(),
            "panel2":self.panel2_pos.tolist()
            })

    # 벽4가지를 순회하며 어느 벽과 충돌했는지 판별하고 부딪힌 벽을 반환
    def collision_with_side(self):
        for plane in self.planes:
            collisionPoint = self.get_collision_point_with_plane(plane)
            if isinstance(collisionPoint, np.ndarray) != False:
                self.ball_pos = collisionPoint
                self.ball_pos += (plane[0] * 2) # 현재 공의 좌표에 평면의 법선벡터 * 2를 해서 더해준다

                return plane
    
        return None

    # 평면과 점 사이의 거리, 인자로 부딪힌 평면을 받고, 그 평면과 구의 중심사이의 거리를 계산한다
    def plane_distance_to_point(self, plane):
        #plane은 ((x, y, z), (원점으로부터의 거리)) -> 법선벡터, 원점으로부터의 거리로 구현
        ballX, ballY, ballZ = self.ball_pos #공의 좌표
        a, b, c = plane[0] #법선벡터
        d = plane[1] #중심으로부터의 거리
        # print(f"법선 벡터: {a}, {b}, {c}, {d}")
        # print(f"현재 평면: {plane[0]}")
        # print(f"공의 좌표: {ballX}, {ballY}, {ballZ}")
        # print("거리: ", abs((ballX * a) + (ballY * b) + (ballZ * c) + d) / math.sqrt((a**2) + (b**2) + (c**2)))

        return abs(ballX * a + ballY * b + ballZ * c + d) / math.sqrt(a**2 + b**2 + c**2)

# 구가 평면과 부딪힌 좌표
    def get_collision_point_with_plane(self, plane):
        distance_to_plane = self.plane_distance_to_point(plane)

        if abs(distance_to_plane) <= 2:
            collisionPoint = self.ball_pos - (plane[0] * distance_to_plane)
            return collisionPoint
        return None

    # 벡터 업데이트함수
    def updateVector(self, collisionPlane):
        previousVec = self.ball_vec
        dotProduct = np.dot(self.ball_vec, collisionPlane[0])
        reflection = collisionPlane[0] * dotProduct * 2
        # angularComponent = np.cross(self.angular_vec, collisionPlane[0] * 2)
        # self.ball_vec = self.ball_vec - reflection + angularComponent
        #updateAngularVector()
        self.ball_vec = self.ball_vec - reflection


    # panel이 위치한 평면과 충돌시
    def collisionWithGoalArea(self):
        if self.ball_pos[2] >= 48: #z좌표가 48이상인경우 #player1쪽 벽과 충돌한경우
            # Q: 인자값의 부재
            if self.checkBallInPanel(self.panel1_pos): # x,y 좌표 판정
                self.collisionInPanel(self.panel1_plane) # panel1과 충돌한경우
            else:
                self.player2Win() # panel1이 위치한 면에 충돌한경우
        elif self.ball_pos[2] <= -48:
            # Q: 인자값의 부재
            if self.checkBallInPanel(self.panel2_pos):
                self.collisionInPanel(self.panel2_plane) # panel2와 충돌한 경우
            else:
                self.plane1Win()


    # player2가 이긴경우
    def player2Win(self):
        self.ball_vec = np.array([0, 0, 0])
        self.angular_vec = np.array([0, 0, 0.1])
    
    # player1이 이긴경우
    def player1Win(self):
        self.ball_vec = np.array([0, 0, 0])
        self.angular_vec = np.array([0, 0, 0.1])

    # 공 중심의 x, y좌표가 panel안에 위치하는지 확인하는 함수
    # panel은 panel의 위치좌표를 의미한다
    def checkBallInPanel(self, panel_pos):
        if abs(self.ball_pos[0] - panel_pos[0]) > 4:
            return False
        elif abs(self.ball_pos[1] - panel_pos[1]) > 4:
            return False
        return True

    # 판넬과 공이 충돌한 경우
    def collisionInPanel(self, panelPlane):
        # self.flag = false # 공의 방향을 재설정한다

        #충돌지점 계산
        collisionPoint = self.get_collision_point_with_plane(panelPlane)

        # 충돌후 공의 좌표를 보정
        self.ball_pos = collisionPoint + panelPlane[0] * 2

        # angularVec = panelPlane[0] * 0.01
        self.updateVector(panelPlane)
        #updateVectorByPanel()

