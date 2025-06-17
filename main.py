import pygame
import random
import os

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 800, 600
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
FPS = 60
FRUIT_SCALE = (64, 64)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Fruit Ninja")
clock = pygame.time.Clock()
font = pygame.font.SysFont("comicsansms", 36)

background_img = pygame.image.load("assets/backgroundingame.png")
menu_img = pygame.image.load("assets/backgroundmenu.png")

pygame.mixer.music.load("assets/background_musicc.mp3")
pygame.mixer.music.set_volume(0.4)
pygame.mixer.music.play(-1)

slice_sound = pygame.mixer.Sound("assets/slice.mp3")
combo_sound = pygame.mixer.Sound("assets/combo.wav")
bomb_fuse_sound = pygame.mixer.Sound("assets/bomb-fuse.wav")
bomb_explode_sound = pygame.mixer.Sound("assets/bomb-explode.mp3")
combo_sounds = [pygame.mixer.Sound(f"assets/combo-{i}.wav") for i in range(1, 9)]

bomb_img = pygame.transform.scale(pygame.image.load("assets/bomb.png").convert_alpha(), FRUIT_SCALE)
fruit_types_raw = ["apple", "banana", "watermelon", "orange", "pineapple", "coconut"]
fruit_images = {}
for f in fruit_types_raw:
    whole = f"assets/{f}.png"
    half1 = f"assets/{f}_half_1.png"
    half2 = f"assets/{f}_half_2.png"
    if os.path.exists(whole) and os.path.exists(half1) and os.path.exists(half2):
        fruit_images[f] = {
            "whole": pygame.transform.scale(pygame.image.load(whole).convert_alpha(), FRUIT_SCALE),
            "halves": [
                pygame.transform.scale(pygame.image.load(half1).convert_alpha(), FRUIT_SCALE),
                pygame.transform.scale(pygame.image.load(half2).convert_alpha(), FRUIT_SCALE)
            ]
        }
    else:
        print(f"[WARNING] Missing asset(s) for {f}")
fruit_types = list(fruit_images.keys())

MENU, PLAYING, GAME_OVER = 0, 1, 2
state = MENU

SPAWN_EVENT = pygame.USEREVENT + 1
pygame.time.set_timer(SPAWN_EVENT, 800)
score, combo, combo_timer = 0, 0, 0
COMBO_RESET_TIME = 1000
MAX_TRAIL_LENGTH = 10
fruit_list, particles, mouse_trail = [], [], []

def spawn_fruit():
    if not fruit_types:
        return
    fruit_type = random.choice(fruit_types)
    img = fruit_images[fruit_type]["whole"]
    rect = img.get_rect()
    max_x = max(0, WIDTH - rect.width)
    rect.x = random.randint(0, max_x)
    rect.y = HEIGHT
    is_bomb = random.random() < min(0.05 + combo * 0.02, 0.5)
    fruit_list.append({
        "rect": rect,
        "dy": -random.uniform(20.0, 24.0),
        "is_bomb": is_bomb,
        "sliced": False,
        "slice_timer": 0,
        "type": fruit_type,
        "fuse_played": False
    })

button_start_img = pygame.transform.scale(pygame.image.load("assets/startgame.png").convert_alpha(), (300, 200))
button_quit_img = pygame.transform.scale(pygame.image.load("assets/quitgame.png").convert_alpha(), (300, 200))

def draw_button(rect, text, hover=False):
    if text == "START GAME":
        image = button_start_img.copy()
    elif text == "QUIT":
        image = button_quit_img.copy()
    else:
        image = button_start_img.copy()
    if hover:
        image.set_alpha(255)
    else:
        image.set_alpha(200)
    screen.blit(image, rect.topleft)

start_btn_rect = button_start_img.get_rect(center=(WIDTH//2, 300))
quit_btn_rect = button_quit_img.get_rect(center=(WIDTH//2, 420))

def draw_menu():
    screen.blit(menu_img, (0, 0))
    mx, my = pygame.mouse.get_pos()
    hover_start = start_btn_rect.collidepoint(mx, my)
    hover_quit = quit_btn_rect.collidepoint(mx, my)

    draw_button(start_btn_rect, "START GAME", hover_start)
    draw_button(quit_btn_rect, "QUIT", hover_quit)

def draw_game():
    screen.blit(background_img, (0, 0))
    for fruit in fruit_list:
        x, y = fruit["rect"].x, fruit["rect"].y
        if fruit["is_bomb"]:
            screen.blit(bomb_img, (x, y))
        elif fruit["sliced"]:
            screen.blit(fruit_images[fruit["type"]]["halves"][0], (x - 10, y))
            screen.blit(fruit_images[fruit["type"]]["halves"][1], (x + 10, y))
        else:
            screen.blit(fruit_images[fruit["type"]]["whole"], (x, y))
    for i in range(len(mouse_trail) - 1):
        pygame.draw.line(screen, WHITE, mouse_trail[i], mouse_trail[i + 1], 3)
    for p in particles:
        pygame.draw.circle(screen, (255, 0, 0), (int(p["x"]), int(p["y"])), p["radius"])
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))
    if combo > 1:
        combo_text = font.render(f"Combo x{combo}", True, (255, 255, 0))
        screen.blit(combo_text, (WIDTH - combo_text.get_width() - 20, 10))

def draw_game_over():
    screen.fill(BLACK)
    game_over_text = font.render("GAME OVER", True, WHITE)
    screen.blit(game_over_text, (WIDTH//2 - game_over_text.get_width()//2, 120))

    final_score = font.render(f"Final Score: {score}", True, WHITE)
    screen.blit(final_score, (WIDTH//2 - final_score.get_width()//2, 200))

    high_score = max(score, load_high_score())
    high_score_text = font.render(f"High Score: {high_score}", True, WHITE)
    screen.blit(high_score_text, (WIDTH//2 - high_score_text.get_width()//2, 250))

    combo_text = font.render(f"Combo: x{combo}", True, (255, 255, 0))
    screen.blit(combo_text, (WIDTH//2 - combo_text.get_width()//2, 300))
    
    restart_text = font.render("Press SPACE to Restart", True, WHITE)
    screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, 400))

def update_game():
    global combo, combo_timer, state
    for fruit in fruit_list[:]:
        if fruit["is_bomb"] and not fruit["fuse_played"]:
            bomb_fuse_sound.play(-1)
            fruit["fuse_played"] = True
        fruit["dy"] += 0.6
        fruit["rect"].y += int(fruit["dy"])
        if fruit["rect"].y > HEIGHT or (fruit["sliced"] and pygame.time.get_ticks() - fruit["slice_timer"] > 300):
            if fruit["is_bomb"] and fruit["fuse_played"]:
                bomb_fuse_sound.stop()
            fruit_list.remove(fruit)
    for p in particles[:]:
        p["x"] += p["dx"]
        p["y"] += p["dy"]
        p["radius"] -= 0.3
        if p["radius"] <= 0:
            particles.remove(p)
    if pygame.time.get_ticks() - combo_timer > COMBO_RESET_TIME:
        combo = 0

def handle_slice():
    global score, combo, combo_timer, state
    if len(mouse_trail) < 2:
        return
    for fruit in fruit_list:
        if fruit["sliced"]:
            continue
        for i in range(len(mouse_trail) - 1):
            if fruit["rect"].clipline(mouse_trail[i], mouse_trail[i+1]):
                fruit["sliced"] = True
                fruit["slice_timer"] = pygame.time.get_ticks()
                if fruit["is_bomb"]:
                    bomb_fuse_sound.stop()
                    bomb_explode_sound.play()
                    pygame.mixer.music.stop()
                    pygame.mixer.music.load("assets/gameover.mp3")
                    pygame.mixer.music.play()
                    save_high_score(score)
                    state = GAME_OVER
                    return
                slice_sound.play()
                if combo >= 1:
                    combo_sounds[min(combo - 1, 7)].play()
                score += 1 + combo
                combo += 1
                combo_timer = pygame.time.get_ticks()
                spawn_particles(fruit["rect"].center)
                break

def spawn_particles(pos):
    for _ in range(10):
        particles.append({"x": pos[0], "y": pos[1], "dx": random.uniform(-2, 2), "dy": random.uniform(-2, 2), "radius": random.randint(3, 6)})

def load_high_score():
    try:
        with open("highscore.txt", "r") as file:
            return int(file.read())
    except:
        return 0

def save_high_score(new_score):
    if new_score > load_high_score():
        with open("highscore.txt", "w") as file:
            file.write(str(new_score))

# Game loop
running = True
while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]

    for event in pygame.event.get():
        if state == MENU and event.type == pygame.MOUSEBUTTONDOWN:
            if start_btn_rect.collidepoint(event.pos):
                fruit_list.clear()
                particles.clear()
                score = combo = 0
                pygame.mixer.music.load("assets/background_musicc.mp3")
                pygame.mixer.music.play(-1)
                save_high_score(score)
                state = PLAYING
            elif quit_btn_rect.collidepoint(event.pos):
                running = False
        if event.type == pygame.QUIT:
            running = False
        elif event.type == SPAWN_EVENT and state == PLAYING:
            spawn_fruit()
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            if state in [MENU, GAME_OVER]:
                fruit_list.clear()
                particles.clear()
                score = combo = 0
                state = PLAYING

    if state == MENU:
        draw_menu()
    elif state == PLAYING:
        if mouse_pressed:
            mouse_trail.append(mouse_pos)
            if len(mouse_trail) > MAX_TRAIL_LENGTH:
                mouse_trail.pop(0)
            handle_slice()
        else:
            mouse_trail.clear()
        update_game()
        draw_game()
    elif state == GAME_OVER:
        draw_game_over()

    pygame.display.flip()

pygame.quit()
