import pygame

from ball import Ball
from circle_ring import CircleRing
from particles import ParticleSystem
from config import Config
from game_state import GameState
from upgrade_tree import UPGRADES
from ui.tab_bar import TabBar
from ui.shop_view import ShopView
from ui.tree_view import TreeView
from ui.game_view import GameView

WINDOW_W: int = 700
WINDOW_H: int = 520
GAME_W:   int = 520
GAME_H:   int = 520
PANEL_W:  int = WINDOW_W - GAME_W   # 180px

FPS: int = 60
BG_COLOR: tuple[int, int, int] = (18, 18, 24)

GAME_AREA:  pygame.Rect = pygame.Rect(0, 0, GAME_W, GAME_H)
PANEL_AREA: pygame.Rect = pygame.Rect(GAME_W, 0, PANEL_W, WINDOW_H)


def _make_balls(cx: float, cy: float, config: Config, count: int) -> list[Ball]:
    """Tworzy listę piłek z lekko różnymi prędkościami startowymi."""
    balls: list[Ball] = []
    for i in range(count):
        b = Ball(cx, cy, config)
        # Każda kolejna piłka ma nieco inny kąt startowy (±15°)
        if i > 0:
            import math
            angle_offset = math.radians((i - count // 2) * 15)
            speed = math.sqrt(b.vx ** 2 + b.vy ** 2)
            angle = math.atan2(b.vy, b.vx) + angle_offset
            b.vx = math.cos(angle) * speed
            b.vy = math.sin(angle) * speed
        balls.append(b)
    return balls


def _sync_balls(balls: list[Ball], cx: float, cy: float,
                config: Config, state: GameState) -> list[Ball]:
    """Zapewnia właściwą liczbę piłek na podstawie stanu upgradeów."""
    target = state.upgrade_multi_ball + 1   # 0->1, 1->2, 2->3
    while len(balls) < target:
        balls.extend(_make_balls(cx, cy, config, 1))
    # Nie usuwamy nadmiarowych piłek — niech same wylecą
    return balls


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("bouncybox idle")
    clock = pygame.time.Clock()

    # Czcionka podstawowa UI
    font = pygame.font.SysFont("segoeui", 13)

    config = Config()
    state = GameState()
    config.apply_upgrades(state)

    cx = GAME_W // 2
    cy = GAME_H // 2

    particles = ParticleSystem()
    rings: list[CircleRing] = [CircleRing(config, (GAME_W, GAME_H))]
    balls: list[Ball] = _make_balls(cx, cy, config, 1)
    spawn_timer: float = 0.0
    game_won: bool = False

    tab_bar = TabBar(GAME_W, 0, PANEL_W, WINDOW_H)
    shop_view = ShopView(PANEL_AREA, state, UPGRADES)
    tree_view = TreeView(PANEL_AREA, state, UPGRADES)
    game_view = GameView(GAME_AREA)

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        # ----------------------------------------------------------------
        # Zdarzenia
        # ----------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    # Restart gry
                    state = GameState()
                    config.apply_upgrades(state)
                    rings = [CircleRing(config, (GAME_W, GAME_H))]
                    balls = _make_balls(cx, cy, config, 1)
                    particles = ParticleSystem()
                    shop_view.state = state
                    tree_view.state = state
                    spawn_timer = 0.0
                    game_won = False

            tab_bar.handle_event(event)

            if tab_bar.active == 1:
                # Sklep — śledź zmiany stanu po zdarzeniu
                prev_hash = str(state.__dict__)
                shop_view.handle_event(event)
                if str(state.__dict__) != prev_hash:
                    config.apply_upgrades(state)
                    # Aktualizuj radius już istniejących piłek
                    for b in balls:
                        b.radius = config.ball_radius
                    # Dospawnuj piłki jeśli multi_ball wzrósł
                    balls = _sync_balls(balls, cx, cy, config, state)

        # ----------------------------------------------------------------
        # Logika gry (zawsze w tle, niezależnie od aktywnej zakładki)
        # ----------------------------------------------------------------
        if not game_won:
            for ball in balls:
                ball.update(dt)

            # Wylot poza ekran = wygrana
            for ball in balls:
                margin = ball.radius
                if (ball.x < -margin or ball.x > GAME_W + margin or
                        ball.y < -margin or ball.y > GAME_H + margin):
                    game_won = True
                    break

            # Spawn nowych okręgów
            spawn_timer += dt
            if spawn_timer >= config.ring_spawn_interval:
                rings.append(CircleRing(config, (GAME_W, GAME_H)))
                spawn_timer = 0.0

            # Aktualizuj okręgi
            for ring in rings:
                ring.update(dt)

            # Minimalny odstęp między okręgami (zapobiega nakładaniu)
            alive_rings = sorted([r for r in rings if r.alive], key=lambda r: r.radius)
            min_r = max((b.radius for b in balls), default=8) * 3
            for ring in alive_rings:
                if ring.radius < min_r:
                    ring.radius = min_r
                min_r = ring.radius + 35

            # Kolizje piłka ↔ okrąg
            for ball in balls:
                for ring in reversed(rings):
                    if ring.alive:
                        was_alive = ring.alive
                        collided = ring.check_collision(ball)
                        if was_alive and not ring.alive:
                            # Okrąg zniszczony
                            state.on_ring_destroyed()
                            particles.explode_ring(ring.cx, ring.cy,
                                                   ring.radius, ring.color)
                            wave_up = state.check_wave_progress()
                            if wave_up:
                                config.apply_upgrades(state)
                                for b in balls:
                                    b.radius = config.ball_radius
                        if collided:
                            state.on_bounce()
                            break

            # Usuń całkowicie przezroczyste okręgi
            rings = [r for r in rings if not r.is_faded()]
            particles.update(dt)

            # Auto-kolektor — pasywne monety co sekundę
            if state.upgrade_auto_collector > 0:
                state.add_coins(state.wave * 2.0 * dt)

        # ----------------------------------------------------------------
        # Rysowanie
        # ----------------------------------------------------------------
        screen.fill(BG_COLOR)

        # Obszar gry
        for ring in rings:
            ring.draw(screen)
        particles.draw(screen)
        for ball in balls:
            ball.draw(screen)

        # HUD gry
        game_view.draw_hud(screen, font, state)

        # Separator między grą a panelem
        pygame.draw.line(screen, (40, 40, 55), (GAME_W, 0), (GAME_W, WINDOW_H), 2)

        # Pasek zakładek
        tab_bar.draw(screen, font)

        # Aktywny widok w panelu (pod zakładkami)
        tabs_h = len(tab_bar.TABS) * tab_bar.tab_height
        content_rect = pygame.Rect(GAME_W, tabs_h, PANEL_W, WINDOW_H - tabs_h)

        if tab_bar.active == 1:
            shop_view.rect = content_rect
            shop_view.draw(screen, font)
        elif tab_bar.active == 2:
            tree_view.rect = content_rect
            tree_view.draw(screen, font)
        # Zakładka 0 (Gra) — tylko HUD, nic dodatkowego w panelu

        # Ekran wygranej
        if game_won:
            win_font = pygame.font.SysFont("segoeui", 52, bold=True)
            txt = win_font.render("Win!", True, (255, 220, 80))
            screen.blit(txt, txt.get_rect(center=(GAME_W // 2, GAME_H // 2)))
            sub = font.render("R \u2014 zagraj ponownie", True, (180, 180, 200))
            screen.blit(sub, sub.get_rect(center=(GAME_W // 2, GAME_H // 2 + 50)))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
