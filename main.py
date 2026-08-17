"""
Chess — full app with:
  - Menu (Play vs AI / Host LAN game / Join LAN game)
  - Selectable AI difficulty
  - Dark-themed UI with vector piece art (no external images needed)
  - LAN multiplayer for two real players on two devices
  - Post-game move-by-move analysis

Run with:  python3 main.py
"""

import sys
import threading
import pygame

from chess_engine.board import Board
from chess_engine.ai import ChessAI, DIFFICULTIES
from chess_engine.analysis import analyze_game, summarize
from network import NetworkSession, get_local_ip, DEFAULT_PORT
from ui.piece_art import build_piece_surfaces
from ui.text_input import TextInput

# ------------------------------------------------------------------ #
# Layout / dark theme
# ------------------------------------------------------------------ #
BOARD_SIZE = 640
SQ = BOARD_SIZE // 8
PANEL_WIDTH = 300
WIDTH = BOARD_SIZE + PANEL_WIDTH
HEIGHT = 680
FPS = 60

BG = (18, 19, 24)
PANEL_BG = (24, 25, 31)
LIGHT_SQ = (96, 104, 124)
DARK_SQ = (40, 43, 56)
SELECTED = (240, 199, 90)
LEGAL_DOT = (110, 225, 195)
LAST_MOVE = (90, 130, 190)
CHECK_COLOR = (222, 70, 70)
TEXT = (230, 230, 236)
SUBTEXT = (150, 152, 165)
ACCENT = (110, 170, 220)
BUTTON_BG = (52, 88, 110)
BUTTON_HOVER = (68, 112, 138)
BUTTON_TEXT = (240, 240, 244)
DANGER_BG = (110, 55, 60)
DANGER_HOVER = (140, 70, 78)


class Button:
    def __init__(self, rect, text, font, danger=False):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.font = font
        self.danger = danger
        self.enabled = True

    def draw(self, screen, mouse_pos):
        if not self.enabled:
            color = (45, 46, 52)
            text_color = (100, 100, 108)
        else:
            hovered = self.rect.collidepoint(mouse_pos)
            if self.danger:
                color = DANGER_HOVER if hovered else DANGER_BG
            else:
                color = BUTTON_HOVER if hovered else BUTTON_BG
            text_color = BUTTON_TEXT
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        label = self.font.render(self.text, True, text_color)
        screen.blit(label, label.get_rect(center=self.rect.center))

    def clicked(self, pos):
        return self.enabled and self.rect.collidepoint(pos)


class ToggleButton(Button):
    def __init__(self, rect, text, font, selected=False):
        super().__init__(rect, text, font)
        self.selected = selected

    def draw(self, screen, mouse_pos):
        hovered = self.rect.collidepoint(mouse_pos)
        if self.selected:
            color = ACCENT
            text_color = (15, 20, 25)
        else:
            color = BUTTON_HOVER if hovered else BUTTON_BG
            text_color = BUTTON_TEXT
        pygame.draw.rect(screen, color, self.rect, border_radius=8)
        label = self.font.render(self.text, True, text_color)
        screen.blit(label, label.get_rect(center=self.rect.center))


class App:
    STATE_MENU = "menu"
    STATE_DIFFICULTY = "difficulty"
    STATE_HOST_WAIT = "host_wait"
    STATE_JOIN = "join"
    STATE_PLAYING = "playing"
    STATE_ANALYZING = "analyzing"
    STATE_ANALYSIS = "analysis"

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Chess")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()

        self.title_font = pygame.font.SysFont("dejavusans", 42, bold=True)
        self.subtitle_font = pygame.font.SysFont("dejavusans", 18)
        self.h2_font = pygame.font.SysFont("dejavusans", 24, bold=True)
        self.text_font = pygame.font.SysFont("dejavusans", 18)
        self.small_font = pygame.font.SysFont("dejavusans", 15)
        self.button_font = pygame.font.SysFont("dejavusans", 18, bold=True)
        self.big_status_font = pygame.font.SysFont("dejavusans", 32, bold=True)
        self.mono_font = pygame.font.SysFont("dejavusansmono", 20)

        self.piece_images = build_piece_surfaces(SQ)

        self.selected_difficulty = "Medium"
        self.ip_input = TextInput((0, 0, 10, 10), self.text_font, placeholder="e.g. 192.168.1.14")

        self.state = self.STATE_MENU
        self.network = None
        self._build_menu_buttons()

    # ================================================================ #
    # MENU
    # ================================================================ #
    def _build_menu_buttons(self):
        cx = WIDTH // 2
        w, h, gap = 320, 56, 18
        top = 280
        self.menu_buttons = {
            "ai": Button((cx - w // 2, top, w, h), "Play vs AI", self.button_font),
            "host": Button((cx - w // 2, top + (h + gap), w, h), "Host LAN Game", self.button_font),
            "join": Button((cx - w // 2, top + 2 * (h + gap), w, h), "Join LAN Game", self.button_font),
        }

    def draw_menu(self, mouse_pos):
        self.screen.fill(BG)
        title = self.title_font.render("Chess", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 150)))
        subtitle = self.subtitle_font.render(
            "Play the AI, or connect two devices on the same network.", True, SUBTEXT)
        self.screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 190)))

        for button in self.menu_buttons.values():
            button.draw(self.screen, mouse_pos)

    def handle_menu_click(self, pos):
        if self.menu_buttons["ai"].clicked(pos):
            self.state = self.STATE_DIFFICULTY
            self._build_difficulty_buttons()
        elif self.menu_buttons["host"].clicked(pos):
            self.start_hosting()
        elif self.menu_buttons["join"].clicked(pos):
            self.state = self.STATE_JOIN
            self._build_join_screen()

    # ================================================================ #
    # DIFFICULTY SELECT
    # ================================================================ #
    def _build_difficulty_buttons(self):
        cx = WIDTH // 2
        names = list(DIFFICULTIES.keys())
        w, h, gap = 150, 50, 14
        total_w = len(names) * w + (len(names) - 1) * gap
        start_x = cx - total_w // 2
        y = 280
        self.difficulty_buttons = {}
        for i, name in enumerate(names):
            x = start_x + i * (w + gap)
            self.difficulty_buttons[name] = ToggleButton(
                (x, y, w, h), name, self.button_font, selected=(name == self.selected_difficulty))

        bw = 260
        self.color_choice_buttons = {
            "w": Button((cx - bw - 10, 380, bw, 54), "Start as White", self.button_font),
            "b": Button((cx + 10, 380, bw, 54), "Start as Black", self.button_font),
        }
        self.back_button = Button((30, HEIGHT - 70, 120, 44), "Back", self.button_font)

    def draw_difficulty(self, mouse_pos):
        self.screen.fill(BG)
        title = self.h2_font.render("Choose AI Difficulty", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 200)))

        depth = DIFFICULTIES[self.selected_difficulty]["depth"]
        desc = self.text_font.render(f"Search depth {depth} — higher is stronger but slower.",
                                      True, SUBTEXT)
        self.screen.blit(desc, desc.get_rect(center=(WIDTH // 2, 235)))

        for button in self.difficulty_buttons.values():
            button.draw(self.screen, mouse_pos)

        pick_label = self.text_font.render("Then choose which side to play:", True, SUBTEXT)
        self.screen.blit(pick_label, pick_label.get_rect(center=(WIDTH // 2, 350)))

        for button in self.color_choice_buttons.values():
            button.draw(self.screen, mouse_pos)

        self.back_button.draw(self.screen, mouse_pos)

    def handle_difficulty_click(self, pos):
        for name, button in self.difficulty_buttons.items():
            if button.clicked(pos):
                self.selected_difficulty = name
                for n, b in self.difficulty_buttons.items():
                    b.selected = (n == name)
                return
        if self.color_choice_buttons["w"].clicked(pos):
            self.start_ai_game("w")
        elif self.color_choice_buttons["b"].clicked(pos):
            self.start_ai_game("b")
        elif self.back_button.clicked(pos):
            self.state = self.STATE_MENU

    def start_ai_game(self, human_color):
        self.mode = "ai"
        self.ai = ChessAI(difficulty=self.selected_difficulty)
        self.human_color = human_color
        self.network = None
        self._start_game_state()
        if self.board.turn != self.human_color:
            self.trigger_ai_move()

    # ================================================================ #
    # HOST / JOIN (LAN)
    # ================================================================ #
    def start_hosting(self):
        self.network = NetworkSession()
        self.network.host(DEFAULT_PORT)
        self.local_ip = get_local_ip()
        self.state = self.STATE_HOST_WAIT
        cx = WIDTH // 2
        self.cancel_button = Button((cx - 100, 460, 200, 48), "Cancel", self.button_font, danger=True)

    def draw_host_wait(self, mouse_pos):
        self.screen.fill(BG)
        title = self.h2_font.render("Hosting LAN Game", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 180)))

        ip_text = self.mono_font.render(f"{self.local_ip}:{DEFAULT_PORT}", True, ACCENT)
        self.screen.blit(ip_text, ip_text.get_rect(center=(WIDTH // 2, 250)))
        hint = self.text_font.render("Have the other player enter this address on their device.",
                                      True, SUBTEXT)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 285)))

        if self.network.status == "listening":
            status = "Waiting for opponent to connect..."
            color = (240, 200, 90)
        elif self.network.status == "connected":
            status = "Connected! Starting game..."
            color = (120, 220, 140)
        elif self.network.status == "error":
            status = f"Error: {self.network.error_message}"
            color = CHECK_COLOR
        else:
            status = self.network.status
            color = SUBTEXT
        status_label = self.text_font.render(status, True, color)
        self.screen.blit(status_label, status_label.get_rect(center=(WIDTH // 2, 400)))

        self.cancel_button.draw(self.screen, mouse_pos)

    def handle_host_wait_click(self, pos):
        if self.cancel_button.clicked(pos):
            if self.network:
                self.network.close()
            self.network = None
            self.state = self.STATE_MENU
        elif self.network and self.network.status == "connected":
            self.begin_network_game(human_color="w")

    def _build_join_screen(self):
        cx = WIDTH // 2
        self.ip_input.rect = pygame.Rect(cx - 160, 260, 320, 46)
        allowed = set("0123456789.:")
        self.ip_input.allowed = allowed
        self.connect_button = Button((cx - 100, 330, 200, 48), "Connect", self.button_font)
        self.join_back_button = Button((30, HEIGHT - 70, 120, 44), "Back", self.button_font)
        self.join_status = ""
        self.join_status_color = SUBTEXT
        if self.network:
            self.network.close()
        self.network = None

    def draw_join(self, mouse_pos, dt):
        self.screen.fill(BG)
        title = self.h2_font.render("Join LAN Game", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, 190)))
        hint = self.text_font.render("Enter the host's IP address (ask them for it).", True, SUBTEXT)
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, 225)))

        self.ip_input.update(dt)
        self.ip_input.draw(self.screen)
        self.connect_button.draw(self.screen, mouse_pos)
        self.join_back_button.draw(self.screen, mouse_pos)

        if self.join_status:
            label = self.text_font.render(self.join_status, True, self.join_status_color)
            self.screen.blit(label, label.get_rect(center=(WIDTH // 2, 410)))

        if self.network and self.network.status == "connected":
            self.begin_network_game(human_color="b")

    def handle_join_event(self, event):
        self.ip_input.handle_event(event)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.connect_button.clicked(event.pos):
                self.attempt_join()
            elif self.join_back_button.clicked(event.pos):
                if self.network:
                    self.network.close()
                self.network = None
                self.state = self.STATE_MENU

    def attempt_join(self):
        raw = self.ip_input.text.strip()
        if not raw:
            self.join_status, self.join_status_color = "Enter an IP address first.", CHECK_COLOR
            return
        if ":" in raw:
            ip, port_str = raw.split(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = DEFAULT_PORT
        else:
            ip, port = raw, DEFAULT_PORT

        self.network = NetworkSession()
        self.network.join(ip, port)
        self.join_status, self.join_status_color = f"Connecting to {ip}:{port}...", (240, 200, 90)

    # ================================================================ #
    # GAME (shared by AI and network modes)
    # ================================================================ #
    def _start_game_state(self):
        self.board = Board()
        self.selected_sq = None
        self.legal_targets = []
        self.last_move = None
        self.game_over_text = ""
        self.ai_thinking = False
        self.ai_move_result = None
        self.pending_promotion = None
        self.flipped = getattr(self, "human_color", "w") == "b"
        self.state = self.STATE_PLAYING
        self._build_game_buttons()

    def begin_network_game(self, human_color):
        self.mode = "network"
        self.human_color = human_color
        self.ai = None
        self._start_game_state()

    def _build_game_buttons(self):
        x = BOARD_SIZE + 20
        self.game_buttons = {
            "flip": Button((x, HEIGHT - 180, 260, 42), "Flip Board", self.button_font),
            "resign": Button((x, HEIGHT - 128, 260, 42), "Resign", self.button_font, danger=True),
            "menu": Button((x, HEIGHT - 76, 260, 42), "Back to Menu", self.button_font),
        }
        if self.mode == "ai":
            self.game_buttons["undo"] = Button((x, HEIGHT - 232, 260, 42), "Undo", self.button_font)

    # ---- AI turn handling ---- #
    def trigger_ai_move(self):
        if self.board.is_game_over():
            return
        self.ai_thinking = True
        self.ai_move_result = None
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _ai_worker(self):
        self.ai_move_result = self.ai.choose_move(self.board)

    def poll_ai_result(self):
        if self.ai_thinking and self.ai_move_result is not None:
            move = self.ai_move_result
            self.board.make_move(move)
            self.last_move = move
            self.selected_sq, self.legal_targets = None, []
            self.ai_thinking = False
            self.ai_move_result = None
            self.check_game_over()

    # ---- network turn handling ---- #
    def poll_network(self):
        if not self.network:
            return
        if self.network.status == "error":
            self.game_over_text = f"Connection error: {self.network.error_message}"
            return
        if self.network.status == "closed" and not self.game_over_text:
            self.game_over_text = "Opponent disconnected."
            return

        msg = self.network.poll_incoming_move()
        if msg is None:
            return
        start, end = tuple(msg["start"]), tuple(msg["end"])
        promo = msg.get("promotion", "Q")
        legal = self.board.get_legal_moves()
        match = next((m for m in legal
                      if m.start == start and m.end == end
                      and (not m.is_pawn_promotion or m.promotion_choice == promo)), None)
        if match:
            self.board.make_move(match)
            self.last_move = match
            self.selected_sq, self.legal_targets = None, []
            self.check_game_over()

    # ---- coordinates ---- #
    def screen_to_square(self, pos):
        x, y = pos
        if x >= BOARD_SIZE or x < 0 or y < 0 or y >= BOARD_SIZE:
            return None
        col, row = x // SQ, y // SQ
        if self.flipped:
            row, col = 7 - row, 7 - col
        return int(row), int(col)

    def square_to_screen(self, r, c):
        if self.flipped:
            r, c = 7 - r, 7 - c
        return c * SQ, r * SQ

    # ---- input ---- #
    def is_my_turn(self):
        if self.board.is_game_over():
            return False
        if self.mode == "ai":
            return self.board.turn == self.human_color and not self.ai_thinking
        return self.board.turn == self.human_color

    def handle_board_click(self, pos):
        if self.pending_promotion is not None:
            self.handle_promotion_click(pos)
            return
        if not self.is_my_turn():
            return
        sq = self.screen_to_square(pos)
        if sq is None:
            return
        r, c = sq

        if self.selected_sq is None:
            piece = self.board.board[r][c]
            if piece != "--" and piece[0] == self.human_color:
                self.selected_sq = (r, c)
                self.legal_targets = [m for m in self.board.get_legal_moves() if m.start == (r, c)]
        else:
            if (r, c) == self.selected_sq:
                self.selected_sq, self.legal_targets = None, []
                return
            chosen = [m for m in self.legal_targets if m.end == (r, c)]
            if chosen:
                if any(m.is_pawn_promotion for m in chosen):
                    self.pending_promotion = (self.selected_sq, (r, c))
                else:
                    self.play_move(chosen[0])
            else:
                piece = self.board.board[r][c]
                if piece != "--" and piece[0] == self.human_color:
                    self.selected_sq = (r, c)
                    self.legal_targets = [m for m in self.board.get_legal_moves() if m.start == (r, c)]
                else:
                    self.selected_sq, self.legal_targets = None, []

    def handle_promotion_click(self, pos):
        choice = self.promotion_choice_at(pos)
        if choice is None:
            return
        start, end = self.pending_promotion
        move = next(m for m in self.board.get_legal_moves()
                    if m.start == start and m.end == end and m.promotion_choice == choice)
        self.pending_promotion = None
        self.play_move(move)

    def play_move(self, move):
        self.board.make_move(move)
        self.last_move = move
        self.selected_sq, self.legal_targets = None, []
        self.check_game_over()
        if self.network:
            self.network.send_move(move)
        elif not self.board.is_game_over() and self.board.turn != self.human_color:
            self.trigger_ai_move()

    def check_game_over(self):
        if self.board.is_game_over():
            self.game_over_text = self.board.result_string()

    def handle_undo(self):
        if self.mode != "ai" or self.ai_thinking:
            return
        if len(self.board.move_log) >= 2 and self.board.turn == self.human_color:
            self.board.undo_move()
            self.board.undo_move()
        elif self.board.move_log:
            self.board.undo_move()
        self.selected_sq, self.legal_targets = None, []
        self.last_move = self.board.move_log[-1] if self.board.move_log else None
        self.game_over_text = ""
        self.pending_promotion = None

    def handle_resign(self):
        if self.game_over_text:
            return
        resigning_color = "White" if self.human_color == "w" else "Black"
        winner = "Black" if self.human_color == "w" else "White"
        self.game_over_text = f"{resigning_color} resigned — {winner} wins"

    def handle_game_click(self, pos):
        if self.game_buttons["flip"].clicked(pos):
            self.flipped = not self.flipped
        elif self.game_buttons["resign"].clicked(pos):
            self.handle_resign()
        elif self.game_buttons["menu"].clicked(pos):
            self.return_to_menu()
        elif "undo" in self.game_buttons and self.game_buttons["undo"].clicked(pos):
            self.handle_undo()
        elif self.game_over_text and getattr(self, "analysis_button", None) and self.analysis_button.clicked(pos):
            self.start_analysis()
        else:
            self.handle_board_click(pos)

    def return_to_menu(self):
        if self.network:
            self.network.close()
            self.network = None
        self.state = self.STATE_MENU

    # ---- drawing ---- #
    def draw_game(self, mouse_pos):
        self.screen.fill(BG)
        self.draw_board()
        self.draw_panel(mouse_pos)
        self.draw_promotion_dialog()
        if self.game_over_text:
            self.draw_game_over_overlay(mouse_pos)

    def draw_board(self):
        king_check_sq = None
        if self.board.is_in_check(self.board.turn):
            king_check_sq = self.board.king_pos[self.board.turn]

        for r in range(8):
            for c in range(8):
                x, y = self.square_to_screen(r, c)
                base = LIGHT_SQ if (r + c) % 2 == 0 else DARK_SQ
                pygame.draw.rect(self.screen, base, (x, y, SQ, SQ))
                if self.last_move and (r, c) in (self.last_move.start, self.last_move.end):
                    ov = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                    ov.fill((*LAST_MOVE, 110))
                    self.screen.blit(ov, (x, y))
                if self.selected_sq == (r, c):
                    ov = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                    ov.fill((*SELECTED, 150))
                    self.screen.blit(ov, (x, y))
                if king_check_sq == (r, c):
                    ov = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
                    ov.fill((*CHECK_COLOR, 140))
                    self.screen.blit(ov, (x, y))

        for move in self.legal_targets:
            r, c = move.end
            x, y = self.square_to_screen(r, c)
            occupied = self.board.board[r][c] != "--"
            marker = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
            if occupied:
                pygame.draw.circle(marker, LEGAL_DOT, (SQ // 2, SQ // 2), SQ // 2 - 4, width=6)
            else:
                pygame.draw.circle(marker, LEGAL_DOT, (SQ // 2, SQ // 2), SQ // 7)
            self.screen.blit(marker, (x, y))

        for r in range(8):
            for c in range(8):
                piece = self.board.board[r][c]
                if piece == "--":
                    continue
                x, y = self.square_to_screen(r, c)
                self.screen.blit(self.piece_images[piece], (x, y))

        files = "abcdefgh"
        for i in range(8):
            fc = 7 - i if self.flipped else i
            label = self.small_font.render(files[fc], True, (150, 150, 158))
            self.screen.blit(label, (i * SQ + 4, BOARD_SIZE - 18))
            rr = i if self.flipped else 7 - i
            rank_label = self.small_font.render(str(rr + 1), True, (150, 150, 158))
            self.screen.blit(rank_label, (4, i * SQ + 2))

    def promotion_rects(self):
        start, end = self.pending_promotion
        r, c = end
        x, _ = self.square_to_screen(r, c)
        y = max(0, min(HEIGHT // 2 - SQ * 2, HEIGHT - SQ * 4))
        color = self.board.turn
        rects = []
        for i, p in enumerate(("Q", "R", "B", "N")):
            rects.append((pygame.Rect(x, y + i * SQ, SQ, SQ), p, color + p.lower()))
        return rects

    def promotion_choice_at(self, pos):
        for rect, choice, _ in self.promotion_rects():
            if rect.collidepoint(pos):
                return choice
        return None

    def draw_promotion_dialog(self):
        if self.pending_promotion is None:
            return
        overlay = pygame.Surface((BOARD_SIZE, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        self.screen.blit(overlay, (0, 0))
        for rect, _choice, piece_code in self.promotion_rects():
            pygame.draw.rect(self.screen, (235, 235, 240), rect)
            pygame.draw.rect(self.screen, (20, 20, 24), rect, width=2)
            img = self.piece_images[piece_code]
            self.screen.blit(img, img.get_rect(center=rect.center))

    def draw_panel(self, mouse_pos):
        pygame.draw.rect(self.screen, PANEL_BG, (BOARD_SIZE, 0, PANEL_WIDTH, HEIGHT))
        title = self.h2_font.render("Chess", True, TEXT)
        self.screen.blit(title, (BOARD_SIZE + 20, 18))

        mode_label = "vs AI" if self.mode == "ai" else "LAN Multiplayer"
        you_are = "White" if self.human_color == "w" else "Black"
        info = self.text_font.render(f"{mode_label} — You: {you_are}", True, SUBTEXT)
        self.screen.blit(info, (BOARD_SIZE + 20, 56))
        if self.mode == "ai":
            diff = self.text_font.render(f"Difficulty: {self.ai.difficulty}", True, SUBTEXT)
            self.screen.blit(diff, (BOARD_SIZE + 20, 80))

        if self.game_over_text:
            status, color = self.game_over_text, (240, 200, 90)
        elif self.mode == "ai" and self.ai_thinking:
            status, color = "AI is thinking...", (240, 200, 90)
        elif self.mode == "network" and self.network and self.network.status != "connected":
            status, color = f"Connection: {self.network.status}", (240, 150, 90)
        else:
            turn_name = "White" if self.board.turn == "w" else "Black"
            check = " (in check)" if self.board.is_in_check(self.board.turn) else ""
            status, color = f"{turn_name} to move{check}", (150, 220, 150)
        self.screen.blit(self.text_font.render(status, True, color), (BOARD_SIZE + 20, 110))

        list_top = 145
        self.screen.blit(self.small_font.render("Moves:", True, SUBTEXT), (BOARD_SIZE + 20, list_top))
        move_area = pygame.Rect(BOARD_SIZE + 20, list_top + 24, PANEL_WIDTH - 40, 230)
        pygame.draw.rect(self.screen, (30, 31, 38), move_area, border_radius=6)

        moves = self.board.move_log
        lines = []
        for i in range(0, len(moves), 2):
            num = i // 2 + 1
            w_mv = moves[i].get_notation()
            b_mv = moves[i + 1].get_notation() if i + 1 < len(moves) else ""
            lines.append(f"{num}. {w_mv}  {b_mv}")
        y = move_area.top + 8
        for line in lines[-9:]:
            self.screen.blit(self.small_font.render(line, True, TEXT), (move_area.left + 10, y))
            y += 22

        for button in self.game_buttons.values():
            button.draw(self.screen, mouse_pos)

    def draw_game_over_overlay(self, mouse_pos):
        overlay = pygame.Surface((BOARD_SIZE, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        box = pygame.Rect(BOARD_SIZE // 2 - 220, HEIGHT // 2 - 110, 440, 220)
        pygame.draw.rect(self.screen, PANEL_BG, box, border_radius=12)
        pygame.draw.rect(self.screen, ACCENT, box, width=2, border_radius=12)

        label = self.big_status_font.render(self.game_over_text, True, TEXT)
        if label.get_width() > box.width - 40:
            label = self.text_font.render(self.game_over_text, True, TEXT)
        self.screen.blit(label, label.get_rect(center=(box.centerx, box.top + 55)))

        self.analysis_button = Button((box.centerx - 130, box.top + 130, 260, 46),
                                       "View Move Analysis", self.button_font)
        self.analysis_button.draw(self.screen, mouse_pos)

    # ================================================================ #
    # ANALYSIS
    # ================================================================ #
    def start_analysis(self):
        self.analysis_progress = (0, len(self.board.move_log))
        self.analysis_records = None
        self.analysis_summary = None
        self.analysis_scroll = 0
        move_log_snapshot = list(self.board.move_log)
        self.state = self.STATE_ANALYZING
        threading.Thread(target=self._analysis_worker, args=(move_log_snapshot,), daemon=True).start()

    def _analysis_worker(self, move_log_snapshot):
        def progress(done, total):
            self.analysis_progress = (done, total)

        records = analyze_game(move_log_snapshot, depth=2, progress_callback=progress)
        self.analysis_records = records
        self.analysis_summary = summarize(records)

    def draw_analyzing(self):
        self.screen.fill(BG)
        title = self.h2_font.render("Analyzing game...", True, TEXT)
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40)))

        done, total = self.analysis_progress
        total = max(total, 1)
        bar_rect = pygame.Rect(WIDTH // 2 - 200, HEIGHT // 2, 400, 22)
        pygame.draw.rect(self.screen, (40, 42, 50), bar_rect, border_radius=10)
        fill_w = int(bar_rect.width * done / total)
        if fill_w > 0:
            pygame.draw.rect(self.screen, ACCENT, (bar_rect.x, bar_rect.y, fill_w, bar_rect.height),
                              border_radius=10)
        count_label = self.text_font.render(f"{done} / {total} moves", True, SUBTEXT)
        self.screen.blit(count_label, count_label.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 40)))

        if self.analysis_records is not None:
            self.state = self.STATE_ANALYSIS
            self._build_analysis_buttons()

    def _build_analysis_buttons(self):
        self.analysis_back_button = Button((WIDTH // 2 - 100, HEIGHT - 60, 200, 44),
                                            "Back to Menu", self.button_font)

    def draw_analysis(self, mouse_pos, wheel_delta=0):
        self.screen.fill(BG)
        title = self.h2_font.render("Game Analysis", True, TEXT)
        self.screen.blit(title, (30, 20))

        summary = self.analysis_summary
        labels_order = ["Best", "Excellent", "Good", "Inaccuracy", "Mistake", "Blunder"]
        colors = {rec["label"]: rec["color"] for rec in self.analysis_records}

        col_x = {"w": 30, "b": WIDTH - 260}
        for color_key, side_name in (("w", "White"), ("b", "Black")):
            x = col_x[color_key]
            self.screen.blit(self.text_font.render(side_name, True, TEXT), (x, 60))
            y = 88
            for lab in labels_order:
                count = summary[color_key].get(lab, 0)
                swatch_color = colors.get(lab, (150, 150, 150))
                pygame.draw.rect(self.screen, swatch_color, (x, y, 14, 14), border_radius=3)
                text = self.small_font.render(f"{lab}: {count}", True, SUBTEXT)
                self.screen.blit(text, (x + 22, y - 2))
                y += 22

        # eval graph
        graph_rect = pygame.Rect(230, 60, WIDTH - 520, 170)
        pygame.draw.rect(self.screen, (28, 29, 36), graph_rect, border_radius=8)
        evals = [rec["eval_after_white"] for rec in self.analysis_records]
        if len(evals) >= 2:
            max_abs = max(200, max(abs(e) for e in evals))
            mid_y = graph_rect.centery
            points = []
            for i, e in enumerate(evals):
                px = graph_rect.left + int(i / (len(evals) - 1) * graph_rect.width)
                py = mid_y - int((e / max_abs) * (graph_rect.height / 2 - 6))
                py = max(graph_rect.top + 3, min(graph_rect.bottom - 3, py))
                points.append((px, py))
            pygame.draw.line(self.screen, (70, 72, 82),
                              (graph_rect.left, mid_y), (graph_rect.right, mid_y), width=1)
            pygame.draw.lines(self.screen, ACCENT, False, points, width=2)
        eval_caption = self.small_font.render("Evaluation over the game (White's perspective)",
                                               True, SUBTEXT)
        self.screen.blit(eval_caption, (graph_rect.left, graph_rect.bottom + 6))

        # move list
        list_rect = pygame.Rect(30, 260, WIDTH - 60, HEIGHT - 340)
        pygame.draw.rect(self.screen, (24, 25, 31), list_rect, border_radius=8)

        row_h = 24
        max_scroll = max(0, len(self.analysis_records) * row_h - list_rect.height + 10)
        self.analysis_scroll = max(0, min(max_scroll, self.analysis_scroll - wheel_delta * 30))

        clip = self.screen.get_clip()
        self.screen.set_clip(list_rect)
        y = list_rect.top + 8 - self.analysis_scroll
        for rec in self.analysis_records:
            if list_rect.top - row_h <= y <= list_rect.bottom:
                mover = "White" if rec["mover"] == "w" else "Black"
                line = f"{rec['index'] + 1:>3}. {mover:<5} {rec['notation']:<8} {rec['label']}"
                if rec["loss_cp"] > 0:
                    line += f"  (-{rec['loss_cp']}cp)"
                label = self.small_font.render(line, True, rec["color"])
                self.screen.blit(label, (list_rect.left + 12, y))
            y += row_h
        self.screen.set_clip(clip)

        self.analysis_back_button.draw(self.screen, mouse_pos)

    def handle_analysis_click(self, pos):
        if self.analysis_back_button.clicked(pos):
            self.state = self.STATE_MENU

    # ================================================================ #
    # MAIN LOOP
    # ================================================================ #
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()
            wheel_delta = 0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEWHEEL:
                    wheel_delta = event.y
                elif self.state == self.STATE_JOIN:
                    self.handle_join_event(event)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.state == self.STATE_MENU:
                        self.handle_menu_click(event.pos)
                    elif self.state == self.STATE_DIFFICULTY:
                        self.handle_difficulty_click(event.pos)
                    elif self.state == self.STATE_HOST_WAIT:
                        self.handle_host_wait_click(event.pos)
                    elif self.state == self.STATE_PLAYING:
                        self.handle_game_click(event.pos)
                    elif self.state == self.STATE_ANALYSIS:
                        self.handle_analysis_click(event.pos)

            if self.state == self.STATE_PLAYING:
                if self.mode == "ai":
                    self.poll_ai_result()
                else:
                    self.poll_network()
                self.draw_game(mouse_pos)
            elif self.state == self.STATE_MENU:
                self.draw_menu(mouse_pos)
            elif self.state == self.STATE_DIFFICULTY:
                self.draw_difficulty(mouse_pos)
            elif self.state == self.STATE_HOST_WAIT:
                self.draw_host_wait(mouse_pos)
                if self.network and self.network.status == "connected":
                    self.begin_network_game(human_color="w")
            elif self.state == self.STATE_JOIN:
                self.draw_join(mouse_pos, dt)
            elif self.state == self.STATE_ANALYZING:
                self.draw_analyzing()
            elif self.state == self.STATE_ANALYSIS:
                self.draw_analysis(mouse_pos, wheel_delta)

            pygame.display.flip()

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    App().run()
