from abc import *
from game.models import Tournament, Game
from asgiref.sync import sync_to_async
from django.core.cache import cache
import numpy as np
import math


KEY_MAPPING = {
    "KeyW": 0,
    "KeyA": 1,
    "KeyS": 2,
    "KeyD": 3,
    "ArrowUp": 4,
    "ArrowDown": 6,
    "ArrowLeft": 5,
    "ArrowRight": 7,
}

# TODO: Need fix in prod
GAME_END_SCORE = 3


class PongGame(metaclass=ABCMeta):
    @abstractmethod
    async def set_game_ended(self, winner):
        """
        TournamentGame, NormalGame 모드로 구분된 게임이 종료되었을 떄
        데이터를 처리하는 방식이 상이함
        """
        pass

    def __init__(self, send_callback, session_data):
        self.send_callback = send_callback
        self.ball_pos = np.array([0.0, 0.0, 0.0])  # 공위치
        self.ball_vec = np.array([0.0, 0.0, 1.0])  # 공이 움직이는 방향
        self.ball_rot = np.array([0.0, 0.0, 0.0])  # 공의 회전벡터
        self.panel1_pos = np.array([0.0, 0.0, 50.0])  # panel1의 초기위치
        self.panel2_pos = np.array([0.0, 0.0, -50.0])  # panel2의 초기위치

        # 키입력값 [W, A, S, D, UP, Left, Down, Right]
        self.key_state = [False, False, False, False, False, False, False, False]

        # 골대쪽 벽면말고 사이드에 있는 4개의 plane들을 의미하며 각각([법선벡터], 원점으로부터의 거리)를 가지고 있다.
        self.planes = [
            (np.array([1, 0, 0]), 10),
            (np.array([-1, 0, 0]), 10),
            (np.array([0, 1, 0]), 10),
            (np.array([0, -1, 0]), 10),
        ]

        # panel이 위치한 평면
        self.panel1_plane = (np.array([0, 0, -1]), 50)  # (법선벡터, 원점과의 거리)
        self.panel2_plane = (np.array([0, 0, 1]), 50)
        self.state = "playing"
        self.winner = None
        self.session_data = session_data
        self.game_mode = session_data.get("game_mode", "normal")
        self.player1_score = session_data.get("left_score")
        self.player2_score = session_data.get("right_score")

    def init_game(self):
        self.ball_pos = np.array([0.0, 0.0, 0.0])  # 공위치
        self.ball_vec = np.array([0.0, 0.0, 1.0])  # 공이 움직이는 방향
        self.ball_rot = np.array([0.0, 0.0, 0.0])  # 공의 회전벡터
        self.panel1_pos = np.array([0.0, 0.0, 50.0])  # panel1의 초기위치
        self.panel2_pos = np.array([0.0, 0.0, -50.0])  # panel2의 초기위치

    def process_key_input(self, key_input):
        for k, v in key_input.items():
            if k in KEY_MAPPING:
                self.key_state[KEY_MAPPING[k]] = v

    def move_panels(self):
        ball_speed = 0.2
        if self.key_state[0]:
            self.panel1_pos[1] = self.clamp_panel_pos(self.panel1_pos[1] + ball_speed)
        elif self.key_state[2]:
            self.panel1_pos[1] = self.clamp_panel_pos(self.panel1_pos[1] - ball_speed)
        if self.key_state[1]:
            self.panel1_pos[0] = self.clamp_panel_pos(self.panel1_pos[0] - ball_speed)
        elif self.key_state[3]:
            self.panel1_pos[0] = self.clamp_panel_pos(self.panel1_pos[0] + ball_speed)
        if self.key_state[4]:
            self.panel2_pos[1] = self.clamp_panel_pos(self.panel2_pos[1] + ball_speed)
        elif self.key_state[6]:
            self.panel2_pos[1] = self.clamp_panel_pos(self.panel2_pos[1] - ball_speed)
        if self.key_state[5]:
            self.panel2_pos[0] = self.clamp_panel_pos(self.panel2_pos[0] + ball_speed)
        elif self.key_state[7]:
            self.panel2_pos[0] = self.clamp_panel_pos(self.panel2_pos[0] - ball_speed)

    def clamp_panel_pos(self, pos):
        if abs(pos) > 7:
            if pos < -7:
                return -7
            elif pos > 7:
                return 7
        return pos

    async def update(self):
        steps = 10
        for i in range(steps):
            movement = np.copy(self.ball_vec) * (0.4 / steps)
            self.ball_pos += movement

            collision_plane = self.check_collision_with_sides()
            if collision_plane:
                self.update_ball_vector(collision_plane)
                break
            await self.check_collision_with_goal_area()

        await self.send_callback(
            {
                "type": "state",
                "ball_pos": self.ball_pos.tolist(),
                "panel1": self.panel1_pos.tolist(),
                "panel2": self.panel2_pos.tolist(),
                "ball_rot": self.ball_rot.tolist(),
            }
        )

    # 벽4가지를 순회하며 어느 벽과 충돌했는지 판별하고 부딪힌 벽을 반환
    def check_collision_with_sides(self):
        for plane in self.planes:
            collision_point = self.get_collision_point_with_plane(plane)
            if isinstance(collision_point, np.ndarray):
                self.ball_pos = collision_point
                # 현재 공의 좌표에 평면의 법선벡터 * 2를 해서 더해준다
                self.ball_pos += plane[0] * 2
                return plane
        return None

    # 구가 평면과 부딪힌 좌표
    def get_collision_point_with_plane(self, plane):
        distance_to_plane = self.plane_distance_to_point(plane)
        if abs(distance_to_plane) <= 2:
            self.ball_rot -= plane[0] * 0.01
            return self.ball_pos - (plane[0] * distance_to_plane)
        return None

    # 평면과 점 사이의 거리, 인자로 부딪힌 평면을 받고, 그 평면과 구의 중심사이의 거리를 계산한다
    def plane_distance_to_point(self, plane):
        # plane은 ((x, y, z), (원점으로부터의 거리)) -> 법선벡터, 원점으로부터의 거리로 구현
        a, b, c = plane[0]  # 법선벡터
        d = plane[1]  # 중심으로부터의 거리
        return abs(
            self.ball_pos[0] * a + self.ball_pos[1] * b + self.ball_pos[2] * c + d
        ) / math.sqrt(a**2 + b**2 + c**2)

    # panel이 위치한 평면과 충돌시
    async def check_collision_with_goal_area(self):
        if self.ball_pos[2] >= 48:  # z좌표가 48이상인경우 #player1쪽 벽과 충돌한경우
            if self.is_ball_in_panel(self.panel1_pos):  # x,y 좌표 판정
                self.handle_panel_collision(
                    self.panel1_plane, self.panel1_pos
                )  # panel1과 충돌한경우
            else:
                await self.player_win("left")  # panel1이 위치한 면에 충돌한경우
        elif self.ball_pos[2] <= -48:
            if self.is_ball_in_panel(self.panel2_pos):
                self.handle_panel_collision(
                    self.panel2_plane, self.panel2_pos
                )  # panel2와 충돌한 경우
            else:
                await self.player_win("right")

    # 공 중심의 x, y좌표가 panel안에 위치하는지 확인하는 함수
    def is_ball_in_panel(self, panel_pos):
        if abs(self.ball_pos[0] - panel_pos[0]) > 4:
            return False
        elif abs(self.ball_pos[1] - panel_pos[1]) > 4:
            return False
        return True

    # 판넬과 공이 충돌한 경우
    def handle_panel_collision(self, panel_plane, panel_pos):
        # 충돌지점 계산
        collision_point = self.get_collision_point_with_plane(panel_plane)
        # 충돌후 공의 좌표를 보정
        self.ball_pos = collision_point + panel_plane[0] * 2
        self.update_vector_by_panel(panel_plane, panel_pos)

    # 공 벡터 업데이트함수
    def update_ball_vector(self, collision_plane):
        dot_product = np.dot(self.ball_vec, collision_plane[0])
        reflection = collision_plane[0] * dot_product * 2
        self.ball_vec = self.ball_vec - reflection

    # 판넬과 공이 충돌한경우 ball_vec에 보정
    def update_vector_by_panel(self, panel_plane, panel_pos):
        self.update_ball_vector(panel_plane)
        self.update_ball_rotation(panel_plane)
        self.ball_vec[0] = (2 - (panel_pos[0] - self.ball_pos[0])) / 24
        self.ball_vec[1] = (2 - (panel_pos[1] - self.ball_pos[1])) / 24
        self.ball_vec[2] += panel_plane[0][2] * 0.04

    def update_ball_rotation(self, panel_plane):
        # 구름 마찰력을 계산
        F = -self.ball_rot

        # 마찰력이 회전을 감속시키는 방향으로 작용하도록 설정
        friction_torque = -self.ball_rot / np.linalg.norm(self.ball_rot) * F

        # 관성 모멘트 (구의 경우)
        mass = 4  # 공의 질량
        radius = 2  # 공의 반지름
        inertia = (2 / 5) * 4 * 4

        # 각가속도 계산
        angular_acceleration = friction_torque / inertia

        # 회전 속도 업데이트
        self.ball_rot += angular_acceleration * 0.1  # delta_time은 시간 간격

        # 감쇠 항을 추가하여 미세한 감속 효과 부여
        self.ball_rot *= 0.5

    def reset_ball(self):
        self.ball_vec = np.array([0.0, 0.0, 1.0])
        self.angular_vec = np.array([0.0, 0.0, 0.0])
        self.ball_pos = np.array([0.0, 0.0, 0.0])

    async def player_win(self, player):
        self.reset_ball()
        if player == "left":
            self.player1_score += 1
            self.session_data["left_score"] += 1
            if self.player1_score >= GAME_END_SCORE:
                await self.set_game_ended()
        elif player == "right":
            self.player2_score += 1
            self.session_data["right_score"] += 1
            if self.player2_score >= GAME_END_SCORE:
                await self.set_game_ended()

        await self.send_score_callback()

    async def send_score_callback(self):
        await self.send_callback(
            {
                "type": "score",
                "left_score": self.player1_score,
                "right_score": self.player2_score,
            }
        )


class TournamentPongGame(PongGame):
    async def set_game_ended(self):
        self.update_match_result(self.session_data)
        # 마지막 경기가 끝나면 DB에 저장
        if self.session_data["current_match"] >= 3:
            self.state = "ended"
            await self.save_tournament_results(self.session_data)
        await self.send_callback({"type": "game_end"})

    def update_match_result(self, data):
        current_match = data["matches"][data["current_match"]]
        player1_index, player2_index = current_match
        match_result = {
            "player1_nick": data["players_name"][player1_index],
            "player2_nick": data["players_name"][player2_index],
            "player1_score": self.player1_score,
            "player2_score": self.player2_score,
        }
        data["match_results"].append(match_result)
        data["left_score"] = 0
        data["right_score"] = 0

        # 승자 결정
        winner_index = player1_index if self.player1_score > self.player2_score else player2_index
        data["win_history"].append(winner_index)

        data["current_match"] += 1

        # 두 번째 경기가 끝나면 결승전 참가자 결정
        if data["current_match"] == 2:
            data["matches"][2][0] = data["win_history"][0]
            data["matches"][2][1] = data["win_history"][1]
        cache.set(f"session_data_tournament_{self.session_data['user_id']}", data, 500)

    async def save_tournament_results(self, data):
        user_id = data["user_id"]
        tournament = await sync_to_async(Tournament.objects.create)(user_id=user_id)
        for i, match in enumerate(data["match_results"]):
            game_key = f"game{i + 1}"
            game = await sync_to_async(Game.objects.create)(
                user_id=user_id,
                tournament_id=tournament.id,
                player1_nick=match["player1_nick"],
                player2_nick=match["player2_nick"],
                player1_score=match["player1_score"],
                player2_score=match["player2_score"],
                mode="Tournament",
            )
            setattr(tournament, game_key, game)
        await sync_to_async(tournament.save)()


class NormalPongGame(PongGame):
    async def set_game_ended(self):
        self.state = "ended"
        await self.save_game_result(self.session_data)
        cache.delete(f"session_data_normal_{self.session_data['user_id']}")
        await self.send_callback({"type": "game_end"})

    async def save_game_result(self, data):
        await sync_to_async(Game.objects.create)(
            user_id=data["user_id"],
            player1_nick=data["players_name"][0],
            player2_nick=data["players_name"][1],
            player1_score=data["left_score"],
            player2_score=data["right_score"],
            mode="1on1",
        )
