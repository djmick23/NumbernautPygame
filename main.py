"""Pygame version of Numbernaut."""

from __future__ import annotations

import random
from pathlib import Path

import pygame


WIDTH = 100
HEIGHT = 160
CANVAS_SCALE = 6
WINDOW_SIZE = (600, 960)
FPS = 60
ASSET_DIR = Path(__file__).parent / "assets"
BACKGROUND = (13, 13, 13)
TEXT_COLOR = (217, 217, 217)
HIGHLIGHT_COLOR = (247, 199, 86)


def load_image(name: str) -> pygame.Surface:
    return pygame.image.load(ASSET_DIR / name).convert_alpha()


def sprite_frames(sheet: pygame.Surface, columns: int, rows: int) -> list[pygame.Surface]:
    frame_width = sheet.get_width() // columns
    frame_height = sheet.get_height() // rows
    frames = []
    for row in range(rows):
        for column in range(columns):
            rect = pygame.Rect(
                column * frame_width, row * frame_height, frame_width, frame_height
            )
            frames.append(sheet.subsurface(rect).copy())
    return frames


class Player:
    def __init__(self) -> None:
        self.x = 50.0
        self.y = 80.0
        self.vx = 0.0
        self.vy = 0.0
        self.number = 5
        self.max_gravity = 100.0
        self.facing_right = True
        self.stretch = (1.0, 1.0)

    def update(self, delta: float, horizontal: int) -> None:
        self.vy = min(self.vy + 120.0 * delta, self.max_gravity)
        self.max_gravity += delta * 2.0
        self.vx += (horizontal * 90.0 - self.vx) * 8.0 * delta
        self.x = min(100.0, max(0.0, self.x + self.vx * delta))
        self.y += self.vy * delta
        if self.vx > 0:
            self.facing_right = True
        elif self.vx < 0:
            self.facing_right = False
        self.stretch = (
            self.stretch[0] + (1.0 - self.stretch[0]) * min(1.0, 5.0 * delta),
            self.stretch[1] + (1.0 - self.stretch[1]) * min(1.0, 5.0 * delta),
        )

    def jump(self) -> None:
        self.vy = -60.0
        if self.max_gravity > 105.0:
            self.max_gravity -= 2.0
        self.number = min(5, self.number + 1)
        self.stretch = (1.4, 0.6)

    def hurt(self) -> None:
        self.vy = -30.0
        if self.max_gravity > 105.0:
            self.max_gravity -= 3.0
        self.number = max(0, self.number - 1)

class Cloud:
    def __init__(self, x: int, y: int, number: int) -> None:
        self.x = float(x)
        self.y = float(y)
        self.number = number


class NumbernautGame:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("Numbernaut")
        self.window = pygame.display.set_mode(WINDOW_SIZE, pygame.RESIZABLE)
        self.canvas = pygame.Surface((WIDTH * CANVAS_SCALE, HEIGHT * CANVAS_SCALE))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(
            ASSET_DIR / "Awasete Powder.ttf", 8 * CANVAS_SCALE
        )
        self.player_frames = sprite_frames(load_image("numbernaut.png"), 2, 3)
        self.cloud_frames = sprite_frames(load_image("clouds.png"), 2, 3)
        self.stars = load_image("stars.png")
        self.scaled_stars = pygame.transform.scale(
            self.stars,
            (
                self.stars.get_width() * CANVAS_SCALE,
                self.stars.get_height() * CANVAS_SCALE,
            ),
        )
        self.scaled_cloud_frames = [
            pygame.transform.scale(frame, (16 * CANVAS_SCALE, 16 * CANVAS_SCALE))
            for frame in self.cloud_frames
        ]
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.music: pygame.mixer.Sound | None = None
        self._load_audio()
        self.state = "menu"
        self.player = Player()
        self.clouds: list[Cloud] = []
        self.score = 0
        self.next_cloud_y = 130
        self.cloud_interval = 120
        self.camera_y = 80.0
        self.elapsed = 0.0
        self.game_over_timer = 0.0
        self.game_over_sound_played = False
        self.running = True

    def _load_audio(self) -> None:
        pygame.mixer.init()
        for name in ("Jump", "Hurt", "Menu", "Over"):
            self.sounds[name.lower()] = pygame.mixer.Sound(ASSET_DIR / f"{name}.wav")
        self.music = pygame.mixer.Sound(ASSET_DIR / "Music.wav")
        self.music.set_volume(0.35)
        self.music.play(loops=-1)

    def play_sound(self, name: str) -> None:
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()

    def spawn_cloud(self, y: int) -> None:
        self.clouds.append(Cloud(random.randint(10, 90), y, random.randint(1, 5)))

    def start_game(self) -> None:
        if self.state != "menu":
            return
        self.state = "playing"
        self.elapsed = 0.0
        self.play_sound("menu")

    def reset_game(self) -> None:
        self.player = Player()
        self.clouds.clear()
        self.score = 0
        self.next_cloud_y = 130
        self.cloud_interval = 120
        self.camera_y = 80.0
        self.elapsed = 0.0
        self.game_over_timer = 0.0
        self.game_over_sound_played = False
        self.state = "menu"
        if self.music is not None:
            self.music.play(loops=-1)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.state == "menu":
                point = self.window_to_canvas(event.pos)
                if point is not None and 27 <= point[0] <= 74 and 75 <= point[1] <= 108:
                    self.start_game()

    def window_to_canvas(self, point: tuple[int, int]) -> tuple[int, int] | None:
        width, height = self.window.get_size()
        scale = min(width / WIDTH, height / HEIGHT)
        if scale <= 0:
            return None
        offset_x = (width - WIDTH * scale) / 2
        offset_y = (height - HEIGHT * scale) / 2
        x = (point[0] - offset_x) / scale
        y = (point[1] - offset_y) / scale
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            return round(x), round(y)
        return None

    def update(self, delta: float, keys: pygame.key.ScancodeWrapper) -> None:
        if self.state == "menu":
            return
        if self.state == "game_over":
            self.game_over_timer += delta
            if self.game_over_timer >= 0.5 and not self.game_over_sound_played:
                self.play_sound("over")
                if self.music is not None:
                    self.music.stop()
                self.game_over_sound_played = True
            if self.game_over_timer >= 0.75:
                self.reset_game()
            return

        self.elapsed += delta
        horizontal = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(
            keys[pygame.K_LEFT] or keys[pygame.K_a]
        )
        self.player.update(delta, horizontal)

        if self.elapsed >= 1.0:
            target_camera_y = self.player.y + 20.0
            self.camera_y += (target_camera_y - self.camera_y) * min(1.0, delta * 5.0)

        if self.player.number == 0:
            self.state = "game_over"

        for cloud in self.clouds[:]:
            player_left = self.player.x - 4
            player_top = self.player.y - 9
            cloud_left = cloud.x - 6
            cloud_top = cloud.y - 3
            if (
                player_left < cloud_left + 11
                and player_left + 8 > cloud_left
                and player_top < cloud_top + 7
                and player_top + 9 > cloud_top
            ):
                if self.player.number == cloud.number:
                    self.player.jump()
                    self.play_sound("jump")
                else:
                    self.player.hurt()
                    self.play_sound("hurt")
                self.clouds.remove(cloud)

        if self.player.y + 320 > self.next_cloud_y:
            self.spawn_cloud(self.next_cloud_y)
            self.next_cloud_y += self.cloud_interval
            if self.score < 500:
                self.cloud_interval = random.randint(30, 60)
            else:
                self.cloud_interval = random.randint(50, 80)

        self.clouds = [
            cloud for cloud in self.clouds if self.player.y - cloud.y <= 320
        ]
        self.score = int(self.player.y / 10)

    def draw(self) -> None:
        self.canvas.fill(BACKGROUND)
        star_offset = (
            round(self.camera_y * 0.5 * CANVAS_SCALE)
            % self.scaled_stars.get_height()
        )
        first_y = -star_offset
        for y in range(first_y, self.canvas.get_height(), self.scaled_stars.get_height()):
            self.canvas.blit(self.scaled_stars, (0, y))

        for cloud in self.clouds:
            screen_y = round(
                (cloud.y - self.camera_y + HEIGHT / 2) * CANVAS_SCALE
            )
            self.canvas.blit(
                self.scaled_cloud_frames[cloud.number - 1],
                (
                    round((cloud.x - 8) * CANVAS_SCALE),
                    screen_y - 8 * CANVAS_SCALE,
                ),
            )

        player_y = (
            self.player.y - self.camera_y + HEIGHT / 2 - 7
        ) * CANVAS_SCALE
        frame = self.player_frames[self.player.number]
        width = max(
            1,
            round(frame.get_width() * CANVAS_SCALE * self.player.stretch[0]),
        )
        height = max(
            1,
            round(frame.get_height() * CANVAS_SCALE * self.player.stretch[1]),
        )
        player_image = pygame.transform.scale(frame, (width, height))
        if not self.player.facing_right:
            player_image = pygame.transform.flip(player_image, True, False)
        self.canvas.blit(
            player_image,
            (
                round(self.player.x * CANVAS_SCALE - width / 2),
                round(player_y - height / 2),
            ),
        )

        score_text = self.font.render(f"SCORE: {self.score}", False, TEXT_COLOR)
        self.canvas.blit(score_text, (8 * CANVAS_SCALE, 8 * CANVAS_SCALE))

        if self.state == "menu":
            overlay = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            self.canvas.blit(overlay, (0, 0))
            self._draw_centered("NUMBERNAUT", 55, TEXT_COLOR)
            mouse_position = pygame.mouse.get_pos()
            pointer = self.window_to_canvas(mouse_position)
            hovering_play = (
                pointer is not None
                and 27 <= pointer[0] <= 74
                and 75 <= pointer[1] <= 108
            )
            play_color = HIGHLIGHT_COLOR if hovering_play else TEXT_COLOR
            self._draw_centered("PLAY", 92, play_color)
            self._draw_centered("ARROWS / A D TO MOVE", 112, TEXT_COLOR)
        elif self.state == "game_over":
            overlay = pygame.Surface(self.canvas.get_size(), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.canvas.blit(overlay, (0, 0))
            self._draw_centered("GAME OVER", 75, TEXT_COLOR)
            self._draw_centered(f"SCORE: {self.score}", 91, TEXT_COLOR)

        self._present()

    def _draw_centered(self, text: str, y: int, color: tuple[int, int, int]) -> None:
        image = self.font.render(text, False, color)
        self.canvas.blit(
            image,
            (
                WIDTH * CANVAS_SCALE // 2 - image.get_width() // 2,
                y * CANVAS_SCALE,
            ),
        )

    def _present(self) -> None:
        width, height = self.window.get_size()
        scale = min(width / WIDTH, height / HEIGHT)
        output_size = (
            max(1, round(WIDTH * scale)),
            max(1, round(HEIGHT * scale)),
        )
        output = pygame.transform.scale(self.canvas, output_size)
        self.window.fill((0, 0, 0))
        self.window.blit(
            output,
            ((width - output_size[0]) // 2, (height - output_size[1]) // 2),
        )
        pygame.display.flip()

    def run(self) -> None:
        while self.running:
            delta = min(self.clock.tick(FPS) / 1000.0, 0.05)
            for event in pygame.event.get():
                self.handle_event(event)
            self.update(delta, pygame.key.get_pressed())
            self.draw()
        pygame.quit()


if __name__ == "__main__":
    NumbernautGame().run()
