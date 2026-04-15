import random
import pygame

from ball import Ball
from circle_ring import CircleRing
from particles import ParticleSystem
from config import Config
from game_state import GameState
from upgrade_tree import UPGRADES, PRESTIGE_UPGRADES
from achievements import ACHIEVEMENTS, check_achievements
from ui.tab_bar import TabBar
from ui.shop_view import ShopView
from ui.tree_view import TreeView
from ui.game_view import GameView
from ui.prestige_view import PrestigeView
from ui.achievements_view import AchievementsView
from ui.notification import NotificationSystem
from powerup import PowerUpSystem
from ui.settings_view import SettingsView
from ui.floating_text import FloatingTextSystem

from constants import GAME_W, GAME_H, WINDOW_W, WINDOW_H, PANEL_W, FPS, BG_COLOR

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


def _notify_achievements(newly_unlocked: list,
                          notifications: NotificationSystem) -> None:
    """Dodaje powiadomienia dla nowo odblokowanych osiągnięć."""
    for ach in newly_unlocked:
        if ach.reward_coins > 0:
            notifications.add(
                f"Osiagniecie: {ach.name}! +{ach.reward_coins:.0f} monet",
                color=(255, 220, 80),
            )
        else:
            notifications.add(
                f"Osiagniecie: {ach.name}!",
                color=(255, 220, 80),
            )
        if ach.reward_crystals > 0:
            notifications.add(
                f"+{ach.reward_crystals} krysztalow",
                color=(150, 220, 255),
            )


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
    rings: list[CircleRing] = [CircleRing(config, (GAME_W, GAME_H), hp=state.get_ring_hp())]
    balls: list[Ball] = _make_balls(cx, cy, config, 1)
    floating_texts = FloatingTextSystem()
    game_won: bool = False

    tab_bar = TabBar(GAME_W, 0, PANEL_W, WINDOW_H)
    shop_view = ShopView(PANEL_AREA, state, UPGRADES)
    tree_view = TreeView(PANEL_AREA, state, UPGRADES)
    game_view = GameView(GAME_AREA)
    prestige_view = PrestigeView(PANEL_AREA, state, PRESTIGE_UPGRADES)
    achievements_view = AchievementsView(PANEL_AREA, state, ACHIEVEMENTS)
    notifications = NotificationSystem()
    powerup_system = PowerUpSystem()
    settings_view = SettingsView(PANEL_AREA)

    def do_prestige() -> None:
        """Callback wywoływany po kliknięciu przycisku PRESTIGE."""
        nonlocal rings, balls, particles, game_won, floating_texts
        if state.prestige():
            config.apply_upgrades(state)
            rings = [CircleRing(config, (GAME_W, GAME_H), hp=state.get_ring_hp())]
            # Piłka startowa + dodatkowe z ulepszenia prestige_extra_ball
            balls = [Ball(cx, cy, config)]
            for i in range(state.prestige_extra_ball):
                balls.append(Ball(cx + 20 * (i + 1), cy, config))
            particles = ParticleSystem()
            floating_texts = FloatingTextSystem()
            game_won = False
            notifications.add("PRESTIGE! Nowa runda rozpoczeta.",
                              color=(255, 150, 50), lifetime=4.0)
            # Sprawdź osiągnięcia prestige
            newly_unlocked = check_achievements(state)
            _notify_achievements(newly_unlocked, notifications)

    def _apply_powerup_to_game(kind: str) -> None:
        """Stosuje natychmiastowy efekt power-upa na grę."""
        nonlocal rings, balls

        if kind == "gold":
            # Oznacz aktywny okrąg jako złoty — x7 monet przy zniszczeniu
            alive = [r for r in rings if r.alive]
            if alive:
                alive[-1].gold_multiplier = 7.0
                notifications.add("ZLOTY x7! Zniszcz aktywny okrag!", (255, 200, 40))

        elif kind == "bomb":
            # Zniszcz drugi okrąg od końca (obok aktywnego)
            alive = [r for r in rings if r.alive]
            if len(alive) >= 2:
                target = alive[-2]
                target.destroy()
                gold_mult = getattr(target, "gold_multiplier", 1.0)
                coins = state.on_ring_destroyed(gold_multiplier=gold_mult)
                particles.explode_ring(target.cx, target.cy,
                                       target.radius, target.color)
                notifications.add(f"BOMBA! +{coins:.0f} monet", (220, 80, 60))
            else:
                notifications.add("Bomba - brak celu!", (220, 80, 60))

        elif kind == "ice":
            # Efekt spowolnienia obsługiwany przez powerup_system.ice_active
            notifications.add("ICE! Okregi spowolnione!", (80, 180, 255))

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
                    # Nowa runda — zachowuje monety, ulepszenia i falę
                    config.apply_upgrades(state)
                    rings = [CircleRing(config, (GAME_W, GAME_H), hp=state.get_ring_hp())]
                    balls = _make_balls(cx, cy, config,
                                       state.upgrade_multi_ball + 1)
                    particles = ParticleSystem()
                    floating_texts = FloatingTextSystem()
                    game_won = False
                    powerup_system = PowerUpSystem()
                if event.key == pygame.K_F5:
                    # Pełny reset — wszystko od zera
                    print("Pelny reset!")
                    state = GameState()
                    config.apply_upgrades(state)
                    rings = [CircleRing(config, (GAME_W, GAME_H), hp=state.get_ring_hp())]
                    balls = _make_balls(cx, cy, config, 1)
                    particles = ParticleSystem()
                    floating_texts = FloatingTextSystem()
                    shop_view.state = state
                    tree_view.state = state
                    prestige_view.state = state
                    achievements_view.state = state
                    game_won = False
                    powerup_system = PowerUpSystem()

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
                    # Sprawdź osiągnięcia po zakupie
                    newly_unlocked = check_achievements(state)
                    _notify_achievements(newly_unlocked, notifications)

            elif tab_bar.active == 3:
                prestige_view.handle_event(event, do_prestige)

            elif tab_bar.active == 4:
                achievements_view.handle_event(event)

            elif tab_bar.active == 5:
                settings_view.handle_event(event, config)

        # ----------------------------------------------------------------
        # Logika gry (zawsze w tle, niezależnie od aktywnej zakładki)
        # ----------------------------------------------------------------
        if not game_won:
            # Aktualizuj power-upy
            powerup_system.update(dt, config, state)

            for ball in balls:
                ball.update(dt)

            # Wylot poza ekran = wygrana
            for ball in balls:
                margin = ball.radius
                if (ball.x < -margin or ball.x > GAME_W + margin or
                        ball.y < -margin or ball.y > GAME_H + margin):
                    game_won = True
                    break

            # Spawn nowego okręgu gdy lista jest pusta
            if not rings:
                hp = state.get_ring_hp()
                rings.append(CircleRing(config, (GAME_W, GAME_H), hp=hp))

            # Aktualizuj okręgi — ice spowalnia zmniejszanie
            ice_mult = 0.05 if powerup_system.ice_active else 1.0
            for ring in rings:
                ring.update(dt, speed_multiplier=ice_mult)

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
                            # Okrąg zniszczony — ustal przyczynę
                            gold_mult = getattr(ring, "gold_multiplier", 1.0)
                            coins = state.on_ring_destroyed(gold_multiplier=gold_mult)
                            particles.explode_ring(ring.cx, ring.cy,
                                                   ring.radius, ring.color)
                            if not collided:
                                # Piłka trafiła w dziurę
                                notifications.add(
                                    f"Dziura! +{coins:.0f} monet",
                                    color=(255, 220, 50))
                            else:
                                # Okrąg starty przez odbicia
                                notifications.add(
                                    f"Zniszczony! +{coins:.0f} monet",
                                    color=(100, 200, 255))
                            wave_up = state.check_wave_progress()
                            if wave_up:
                                config.apply_upgrades(state)
                                for b in balls:
                                    b.radius = config.ball_radius
                            # Floating text — zdobyte monety w miejscu okręgu
                            floating_texts.add(
                                ring.cx, ring.cy,
                                f"+{coins:.0f}",
                                color=(255, 220, 50),
                                lifetime=1.2,
                            )
                            # Sprawdź osiągnięcia po zniszczeniu okręgu i awansie fali
                            newly_unlocked = check_achievements(state)
                            _notify_achievements(newly_unlocked, notifications)
                        if collided:
                            # Floating text — obrażenia w miejscu uderzenia
                            floating_texts.add(
                                ball.x + random.randint(-10, 10),
                                ball.y + random.randint(-15, -5),
                                f"-{config.ball_damage}",
                                color=(255, 180, 80),
                                lifetime=0.7,
                            )
                            state.on_bounce()
                            break

            # Kolizje piłka ↔ power-upy
            for ball in balls:
                for kind in powerup_system.check_collisions(ball):
                    powerup_system.apply_effect(kind)
                    _apply_powerup_to_game(kind)

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
            ball.draw(screen, dt)

        # Pływające napisy (obrażenia, monety)
        floating_texts.update(dt)
        floating_texts.draw(screen, font)

        # Power-upy na planszy + HUD aktywnych efektów
        powerup_system.draw(screen, font)
        powerup_system.draw_active_effects_hud(screen, font)

        # HUD gry
        game_view.draw_hud(screen, font, state)

        # Powiadomienia (nad obszarem gry)
        notifications.update(dt)
        notifications.draw(screen, font)

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
        elif tab_bar.active == 3:
            prestige_view.rect = content_rect
            prestige_view.draw(screen, font)
        elif tab_bar.active == 4:
            achievements_view.rect = content_rect
            achievements_view.draw(screen, font)
        elif tab_bar.active == 5:
            settings_view.rect = content_rect
            settings_view.draw(screen, font, config)
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
