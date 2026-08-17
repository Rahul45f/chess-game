import pygame


class TextInput:
    def __init__(self, rect, font, placeholder="", initial="", allowed=None, max_len=32):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = initial
        self.placeholder = placeholder
        self.active = False
        self.allowed = allowed  # set of allowed chars, or None for any printable
        self.max_len = max_len
        self._cursor_visible = True
        self._cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_TAB):
                pass
            else:
                ch = event.unicode
                if ch and len(self.text) < self.max_len:
                    if self.allowed is None or ch in self.allowed:
                        self.text += ch

    def update(self, dt):
        self._cursor_timer += dt
        if self._cursor_timer > 500:
            self._cursor_timer = 0
            self._cursor_visible = not self._cursor_visible

    def draw(self, screen):
        bg = (48, 50, 60) if self.active else (38, 40, 48)
        border = (110, 170, 200) if self.active else (70, 72, 82)
        pygame.draw.rect(screen, bg, self.rect, border_radius=6)
        pygame.draw.rect(screen, border, self.rect, width=2, border_radius=6)

        if self.text:
            label = self.font.render(self.text, True, (235, 235, 240))
        else:
            label = self.font.render(self.placeholder, True, (120, 120, 130))
        screen.blit(label, (self.rect.x + 10, self.rect.centery - label.get_height() // 2))

        if self.active and self._cursor_visible and self.text:
            text_w = self.font.size(self.text)[0]
            cx = self.rect.x + 10 + text_w + 2
            pygame.draw.line(screen, (235, 235, 240),
                              (cx, self.rect.y + 8), (cx, self.rect.bottom - 8), width=2)
