# chat/consumers.py
import json
import numpy as np

from channels.generic.websocket import WebsocketConsumer

class GameConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        print(message)

        self.send(text_data=json.dumps({"message": message}))


class PongGame:


    def __init__(self):
        self.ball_pos = np.array([0, 0, 2])
        self.ball_rot = np.array([0, 0, 0])
        self.angular_vec = np.array([0, 0, 0])
        self.flag = True
        self.panel1_vec = np.array([0, 0, 0])
        self.panel2_vec = np.array([0, 0, 0])
        self.panel1_pos = np.array([0, 0, 50])
        self.panel2_pos = np.array([0, 0, -50])

        # plane1 = [(법선벡터), (면의 중심좌표)]
        self._planes = [
            [(1, 0, 0), (10, 0, 0)]
            [(-1, 0, 0), (-10, 0, 0)]
            [(0, 1, 0), (0, 10, 0)]
            [(0, -1, 0), (0, -10, 0)]
        ]

    def update(self):
        steps = 10
        for i in range(steps):
            movement = np.copy(self.ball_pos) * (0.4 / steps)
            self.ball_rot[0] += self.angular_vec[0]
            self.ball_rot[1] += self.angular_vec[1]
            self.ball_rot[2] += self.angular_vec[2]

            collisionPlane = self.collisionWithSide()
