import random
import time

import pygame

from ball import Ball
from ring_field import RingField
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

from constants import PANEL_W, FPS, BG_COLOR
from save_manager import save_game, load_game, delete_save
from timestep import FixedTimestep
from formatting import short_number
from audio import Audio, ring_tension
from music import Music


def update_dimensions(screen: pygame.Surface) -> tuple[int, int, int, int]:
    current_game_w = screen.get_width() - PANEL_W
    current_game_h = screen.get_height()
    cx = current_game_w // 2
    cy = current_game_h // 2
    return current_game_w, current_game_h, cx, cy


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
                          notifications: NotificationSystem,
                          audio: Audio | None = None) -> None:
    """Dodaje powiadomienia dla nowo odblokowanych osiągnięć."""
    if newly_unlocked and audio is not None:
        audio.achievement()
    for ach in newly_unlocked:
        if ach.reward_coins > 0:
            notifications.add(
                f"Osiagniecie: {ach.name}! +{short_number(ach.reward_coins)} monet",
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
    screen = pygame.display.set_mode((700, 520), pygame.RESIZABLE)
    pygame.display.set_caption("bouncybox idle")
    clock = pygame.time.Clock()

    # Czcionki — tworzone raz, SysFont jest kosztowny na klatkę
    font = pygame.font.SysFont("segoeui", 13)
    crush_font = pygame.font.SysFont("segoeui", 40, bold=True)

    config = Config()
    state = load_game() or GameState()
    config.apply_upgrades(state)
    audio = Audio(volume=config.sound_volume)
    music = Music(volume=config.music_volume)   # wymaga miksera z Audio
    # Zegar do dławienia dźwięku odbić — liczony w czasie rzeczywistym
    game_time: float = 0.0

    # Naliczenie za czas poza grą — powiadomienie dodajemy niżej, gdy
    # system powiadomień już istnieje.
    away_seconds, offline_coins = state.claim_offline(time.time())

    current_game_w, current_game_h, cx, cy = update_dimensions(screen)
    old_cx, old_cy = cx, cy

    particles = ParticleSystem()
    field = RingField(config, (current_game_w, current_game_h),
                      hp=state.get_ring_hp(), wave=state.wave)
    balls: list[Ball] = _make_balls(cx, cy, config, 1)
    floating_texts = FloatingTextSystem()
    # Krótka przerwa po zduszeniu — gracz ma zobaczyć, co się stało,
    # zanim gra ruszy dalej sama.
    CRUSH_PAUSE = 2.0
    crush_pause: float = 0.0

    tab_bar = TabBar(PANEL_W)
    shop_view = ShopView(state, UPGRADES)
    tree_view = TreeView(state, UPGRADES)
    game_view = GameView()
    prestige_view = PrestigeView(state, PRESTIGE_UPGRADES)
    achievements_view = AchievementsView(state, ACHIEVEMENTS)
    notifications = NotificationSystem()
    if offline_coins > 0:
        notifications.add(
            f"Nieobecnosc {away_seconds / 3600:.1f}h — "
            f"zarobiles {short_number(offline_coins)} monet",
            color=(150, 220, 255), lifetime=8.0)
    powerup_system = PowerUpSystem()
    settings_view = SettingsView()
    autosave_timer: float = 0.0
    AUTOSAVE_INTERVAL = 30.0

    def do_prestige() -> None:
        """Callback wywoływany po kliknięciu przycisku PRESTIGE."""
        nonlocal balls, particles, floating_texts
        if state.prestige():
            config.apply_upgrades(state)
            field.clear(hp=state.get_ring_hp(), wave=state.wave)
            # Piłka startowa + dodatkowe z ulepszenia prestige_extra_ball
            balls = [Ball(cx, cy, config)]
            for i in range(state.prestige_extra_ball):
                balls.append(Ball(cx + 20 * (i + 1), cy, config))
            particles = ParticleSystem()
            floating_texts = FloatingTextSystem()
            notifications.add("PRESTIGE! Nowa runda rozpoczeta.",
                              color=(255, 150, 50), lifetime=4.0)
            # Sprawdź osiągnięcia prestige
            newly_unlocked = check_achievements(state)
            _notify_achievements(newly_unlocked, notifications, audio)

    def _apply_powerup_to_game(kind: str) -> None:
        """Stosuje natychmiastowy efekt power-upa na grę."""
        nonlocal balls

        if kind == "gold":
            # Oznacz aktywny okrąg jako złoty — x7 monet przy zniszczeniu.
            # Aktywny = najbardziej wewnętrzny, bo tylko w ten piłka trafia.
            active = field.innermost()
            if active is not None:
                active.gold_multiplier = 7.0
                notifications.add("ZLOTY x7! Zniszcz aktywny okrag!", (255, 200, 40))

        elif kind == "bomb":
            # Zniszcz okrąg tuż za aktywnym — skraca kolejkę czekających warstw
            alive = field.alive()
            if len(alive) >= 2:
                target = alive[1]
                target.destroy()
                gold_mult = getattr(target, "gold_multiplier", 1.0)
                coins = state.on_ring_destroyed(
                    gold_multiplier=gold_mult,
                    type_multiplier=target.type.coin_multiplier)
                particles.explode_ring(target.cx, target.cy,
                                       target.radius, target.color)
                notifications.add(f"BOMBA! +{short_number(coins)} monet", (220, 80, 60))
            else:
                notifications.add("Bomba - brak celu!", (220, 80, 60))

        elif kind == "ice":
            # Efekt spowolnienia obsługiwany przez powerup_system.ice_active
            notifications.add("ICE! Okregi spowolnione!", (80, 180, 255))

    running = True
    physics = FixedTimestep()
    while running:
        # frame_dt — czas rzeczywisty klatki (liczniki UI, autozapis)
        # dt       — stały krok fizyki (symulacja)
        frame_dt = clock.tick(FPS) / 1000.0
        dt = physics.step
        game_time += frame_dt

        # Muzyka idzie za napięciem najbardziej wewnętrznego okręgu —
        # ta sama informacja co wysokość odbić, ale w dłuższej skali czasu.
        inner_ring = field.innermost()
        tension = ring_tension(inner_ring.radius, config.ring_min_radius,
                               config.ring_start_radius) if inner_ring else 0.0
        music.update(frame_dt, state.wave, tension)

        autosave_timer += frame_dt
        if autosave_timer >= AUTOSAVE_INTERVAL:
            autosave_timer = 0.0
            if save_game(state):
                notifications.add("Gra zapisana.", color=(100, 200, 100), lifetime=1.5)
            else:
                notifications.add("Blad zapisu!", color=(220, 80, 80), lifetime=4.0)

        # ----------------------------------------------------------------
        # Zdarzenia
        # ----------------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_game(state)
                running = False

            if event.type == pygame.VIDEORESIZE:
                current_game_w, current_game_h, cx, cy = update_dimensions(screen)
                
                # Przenieś okręgi i powerupy do nowego środka
                field.recenter((current_game_w, current_game_h))

                for ball in balls:
                    ball.x = ball.x + cx - old_cx
                    ball.y = ball.y + cy - old_cy

                powerup_system = PowerUpSystem()  # reset powerupów — nowe pozycje

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_game(state)
                    running = False
                if event.key == pygame.K_r:
                    # Nowa runda — zachowuje monety, ulepszenia i falę
                    config.apply_upgrades(state)
                    field.clear(hp=state.get_ring_hp(), wave=state.wave)
                    balls = _make_balls(cx, cy, config,
                                       state.upgrade_multi_ball + 1)
                    particles = ParticleSystem()
                    floating_texts = FloatingTextSystem()
                    powerup_system = PowerUpSystem()
                if event.key == pygame.K_F5:
                    if save_game(state):
                        notifications.add("Zapisano!", color=(100, 200, 100), lifetime=1.5)
                    else:
                        notifications.add("Blad zapisu!", color=(220, 80, 80), lifetime=4.0)
                if event.key == pygame.K_F6:
                    delete_save()
                    state = GameState()
                    config.apply_upgrades(state)
                    field.clear(hp=state.get_ring_hp(), wave=state.wave)
                    balls = _make_balls(cx, cy, config, 1)
                    particles = ParticleSystem()
                    floating_texts = FloatingTextSystem()
                    shop_view.state = state
                    tree_view.state = state
                    prestige_view.state = state
                    achievements_view.state = state
                    powerup_system = PowerUpSystem()
                    notifications.add("Reset! Nowa gra.", color=(220, 80, 80), lifetime=2.0)

            tab_bar.handle_event(event, current_game_w)

            if tab_bar.active == 1:
                # Sklep — śledź zmiany stanu po zdarzeniu
                prev_hash = str(state.__dict__)
                shop_view.handle_event(event, current_game_w, current_game_h)
                if str(state.__dict__) != prev_hash:
                    audio.purchase()
                    config.apply_upgrades(state)
                    # Aktualizuj radius już istniejących piłek
                    for b in balls:
                        b.radius = config.ball_radius
                    # Dospawnuj piłki jeśli multi_ball wzrósł
                    balls = _sync_balls(balls, cx, cy, config, state)
                    # Sprawdź osiągnięcia po zakupie
                    newly_unlocked = check_achievements(state)
                    _notify_achievements(newly_unlocked, notifications, audio)

            elif tab_bar.active == 3:
                prestige_view.handle_event(event, do_prestige, current_game_w, current_game_h)

            elif tab_bar.active == 4:
                achievements_view.handle_event(event, current_game_w, current_game_h)

            elif tab_bar.active == 5:
                settings_view.handle_event(event, config, current_game_w, current_game_h)
                # Suwaki sterują wejściami pól pochodnych — przeliczamy od
                # razu, żeby zmiana była widoczna bez czekania na zakup
                # albo awans fali.
                config.apply_upgrades(state)
                audio.volume = config.sound_volume
                music.volume = config.music_volume

        # ----------------------------------------------------------------
        # Logika gry (zawsze w tle, niezależnie od aktywnej zakładki)
        # ----------------------------------------------------------------
        if crush_pause > 0.0:
            crush_pause = max(0.0, crush_pause - frame_dt)

        # steps() wołamy zawsze, żeby opróżnić akumulator — inaczej po
        # przerwie gra nadrabiałaby zaległość z pauzy.
        for _ in range(physics.steps(frame_dt)):
            if crush_pause > 0.0:
                break

            # Aktualizuj power-upy
            powerup_system.update(dt, config, state, cx, cy)

            for ball in balls:
                ball.update(dt)

            # Piłka, która przeleciała przez dziurę ostatniego okręgu, wylatuje
            # poza planszę. Wraca do środka zamiast zamrażać grę — w grze idle
            # pętla ma się kręcić bez udziału gracza.
            for ball in balls:
                margin = ball.radius
                if (ball.x < -margin or ball.x > current_game_w + margin or
                        ball.y < -margin or ball.y > current_game_h + margin):
                    ball.reset(cx, cy)
                    notifications.add("Pilka uciekla - wraca do srodka.",
                                      color=(180, 180, 220), lifetime=2.0)

            # Pole okręgów — zwężanie, spawn i sprzątanie; ice spowalnia zwężanie
            ice_mult = 0.05 if powerup_system.ice_active else 1.0
            field.update(dt, hp=state.get_ring_hp(), wave=state.wave,
                         speed_multiplier=ice_mult)

            # Stos docisnął piłkę — kara i restart planszy
            if field.is_crushed():
                inner = field.innermost()
                if inner is not None:
                    particles.explode_ring(inner.cx, inner.cy,
                                           inner.radius, (220, 80, 60))
                state.on_crushed()
                config.apply_upgrades(state)
                field.clear(hp=state.get_ring_hp(), wave=state.wave)
                balls = _make_balls(cx, cy, config, state.upgrade_multi_ball + 1)
                floating_texts = FloatingTextSystem()
                crush_pause = CRUSH_PAUSE
                audio.crush()
                notifications.add(f"ZDUSZONY! Spadek na fale {state.wave}",
                                  color=(220, 80, 60), lifetime=3.0)
                break

            # Kolizje piłka ↔ okrąg, od najbardziej wewnętrznego
            for ball in balls:
                for ring in field.alive():
                    if ring.alive:
                        was_alive = ring.alive
                        hp_before = ring.hp
                        collided = ring.check_collision(ball)
                        # check_collision zwraca False i przy braku kolizji,
                        # i przy przelocie przez dziurę — odróżnia je dopiero
                        # spadek HP bez odbicia.
                        if collided:
                            audio.bounce(ring.radius, config.ring_min_radius,
                                         config.ring_start_radius, now=game_time)
                        elif ring.hp < hp_before:
                            audio.hole_hit()
                        if was_alive and not ring.alive:
                            audio.ring_destroyed()
                            # Okrąg zniszczony — ustal przyczynę
                            gold_mult = getattr(ring, "gold_multiplier", 1.0)
                            coins = state.on_ring_destroyed(
                                gold_multiplier=gold_mult,
                                type_multiplier=ring.type.coin_multiplier)
                            particles.explode_ring(ring.cx, ring.cy,
                                                   ring.radius, ring.color)
                            if not collided:
                                # Piłka trafiła w dziurę
                                notifications.add(
                                    f"Dziura! +{short_number(coins)} monet",
                                    color=(255, 220, 50))
                            else:
                                # Okrąg starty przez odbicia
                                notifications.add(
                                    f"Zniszczony! +{short_number(coins)} monet",
                                    color=(100, 200, 255))
                            wave_up = state.check_wave_progress()
                            if wave_up:
                                config.apply_upgrades(state)
                                for b in balls:
                                    b.radius = config.ball_radius
                            # Floating text — zdobyte monety w miejscu okręgu
                            floating_texts.add(
                                ring.cx, ring.cy,
                                f"+{short_number(coins)}",
                                color=(255, 220, 50),
                                lifetime=1.2,
                            )
                            # Sprawdź osiągnięcia po zniszczeniu okręgu i awansie fali
                            newly_unlocked = check_achievements(state)
                            _notify_achievements(newly_unlocked, notifications, audio)
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
                    audio.powerup()
                    _apply_powerup_to_game(kind)

            particles.update(dt)

            # Auto-kolektor — pasywne monety co sekundę
            if state.upgrade_auto_collector > 0:
                state.add_coins(state.wave * 2.0 * dt)

        # ----------------------------------------------------------------
        # Rysowanie
        # ----------------------------------------------------------------
        screen.fill(BG_COLOR)

        # Obszar gry
        for ring in field.rings:
            ring.draw(screen, font)
        particles.draw(screen)
        for ball in balls:
            ball.draw(screen, frame_dt)

        # Pływające napisy (obrażenia, monety)
        floating_texts.update(frame_dt)
        floating_texts.draw(screen, font)

        # Power-upy na planszy + HUD aktywnych efektów
        powerup_system.draw(screen, font)
        powerup_system.draw_active_effects_hud(screen, font, current_game_w)

        # HUD gry
        game_view.draw_hud(screen, font, state, current_game_w, current_game_h)

        # Powiadomienia (nad obszarem gry)
        notifications.update(frame_dt)
        notifications.draw(screen, font)

        # Separator między grą a panelem
        pygame.draw.line(screen, (40, 40, 55), (current_game_w, 0), (current_game_w, current_game_h), 2)

        # Pasek zakładek
        tab_bar.draw(screen, font, current_game_w, current_game_h)

        # Aktywny widok w panelu (pod zakładkami)
        if tab_bar.active == 1:
            shop_view.draw(screen, font, current_game_w, current_game_h)
        elif tab_bar.active == 2:
            tree_view.draw(screen, font, current_game_w, current_game_h)
        elif tab_bar.active == 3:
            prestige_view.draw(screen, font, current_game_w, current_game_h)
        elif tab_bar.active == 4:
            achievements_view.draw(screen, font, current_game_w, current_game_h)
        elif tab_bar.active == 5:
            settings_view.draw(screen, font, config, current_game_w, current_game_h)
        # Zakładka 0 (Gra) — tylko HUD, nic dodatkowego w panelu

        # Nakładka po zduszeniu — gra wraca sama, bez udziału gracza
        if crush_pause > 0.0:
            txt = crush_font.render("ZDUSZONY", True, (220, 80, 60))
            screen.blit(txt, txt.get_rect(center=(cx, cy)))
            sub = font.render(f"Fala {state.wave} — gra wraca za "
                              f"{crush_pause:.0f} s", True, (180, 150, 150))
            screen.blit(sub, sub.get_rect(center=(cx, cy + 40)))

        old_cx = cx
        old_cy = cy
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
