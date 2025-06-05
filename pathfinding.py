import pygame
import math
from queue import PriorityQueue
import random
import time

pygame.init()


WIDTH = 700
HEIGHT = 750
ROWS = 50
WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("Path Hunter - Race Against A*!")

CLOCK = pygame.time.Clock()
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREY = (100, 100, 100)
GREEN = (0, 255, 0)  # A* open
RED = (255, 0, 0)    # A* closed
BLUE = (0, 0, 255)   # Start/End outline
YELLOW = (255, 255, 0)  # A* path
DARK_GREY = (30, 30, 30)  # Border
PURPLE = (147, 0, 211)  # Player
ORANGE = (255, 165, 0)  # Player path
LIGHT_BLUE = (135, 206, 235)  # Buttons
BEIGE = (245, 245, 220)  # Parchment background
GRASS_GREEN = (154, 205, 50)  # Ground
TREE_GREEN = (34, 139, 34)  # Barriers (trees)
BROWN = (139, 69, 19)  # Grid lines (paths)

GAP = WIDTH // ROWS
GRID_OFFSET_X = 0
GRID_OFFSET_Y = 0

# UI Settings
BUTTON_COLOR = LIGHT_BLUE
BUTTON_HOVER_COLOR = BLUE
BUTTON_TEXT_COLOR = BLACK
BUTTON_HEIGHT = 40
BUTTON_WIDTH = 200
BUTTON_MARGIN = 10


FONT = pygame.font.SysFont("arial", 20)
TITLE_FONT = pygame.font.SysFont("arial", 36)

try:
    CLICK_SOUND = pygame.mixer.Sound("click.wav")
except:
    CLICK_SOUND = None

PLAYER_SPEED = 5
ASTAR_ANIMATION_SPEED = 0.05  # Seconds per A* step
GAME_STATES = {
    'MENU': 0,
    'PLAYING': 1,
    'GAME_OVER': 2,
    'VICTORY': 3,
    'RUNNING_ASTAR': 4
}

class Player:
    def __init__(self, start_node):
        self.current_node = start_node
        self.path = [start_node]
        self.score = 0
        self.moves = 0
        self.start_time = time.time()
        self.pos = [start_node.x + GRID_OFFSET_X + GAP // 2, start_node.y + GRID_OFFSET_Y + GAP // 2]
        self.target_pos = self.pos.copy()
        self.moving = False

    def move_to(self, new_node):
        if new_node in self.current_node.neighbors and not self.moving:
            self.current_node = new_node
            self.path.append(new_node)
            self.moves += 1
            self.target_pos = [new_node.x + GRID_OFFSET_X + GAP // 2, new_node.y + GRID_OFFSET_Y + GAP // 2]
            self.moving = True
            return True
        return False

    def update(self):
        if self.moving:
            dx = self.target_pos[0] - self.pos[0]
            dy = self.target_pos[1] - self.pos[1]
            dist = math.sqrt(dx**2 + dy**2) 
            if dist > 1:
                speed = PLAYER_SPEED
                self.pos[0] += dx / dist * speed
                self.pos[1] += dy / dist * speed
            else:
                self.pos = self.target_pos.copy()
                self.moving = False

    def draw(self, win):
        # Draw player's path (dashed orange lines)
        if len(self.path) > 1:
            for i in range(len(self.path) - 1):
                start_pos = (self.path[i].x + GRID_OFFSET_X + GAP // 2,
                             self.path[i].y + GRID_OFFSET_Y + GAP // 2)
                end_pos = (self.path[i + 1].x + GRID_OFFSET_X + GAP // 2,
                           self.path[i + 1].y + GRID_OFFSET_Y + GAP // 2)
                pygame.draw.line(win, ORANGE, start_pos, end_pos, 3)
        # Draw player (purple circle)
        pygame.draw.circle(win, PURPLE, (int(self.pos[0]), int(self.pos[1])), GAP // 2 - 5)

class Node:
    def __init__(self, row, col, width, total_rows):
        self.row = row
        self.col = col
        self.x = col * width
        self.y = row * width
        self.color = GRASS_GREEN
        self.neighbors = []
        self.width = width
        self.total_rows = total_rows
        self.g = float("inf")
        self.h = 0
        self.f = 0
        self.alpha = 255
        self.fade_alpha = 0
        self.fade_speed = 20

    def get_pos(self):
        return self.row, self.col

    def is_closed(self): return self.color == RED
    def is_open(self): return self.color == GREEN
    def is_barrier(self): return self.color == TREE_GREEN
    def is_start(self): return self.color == BLUE
    def is_end(self): return self.color == BLUE

    def reset(self): self.color = GRASS_GREEN; self.g = float("inf"); self.h = 0; self.f = 0; self.alpha = 255; self.fade_alpha = 0
    def make_start(self): self.color = BLUE
    def make_closed(self): self.color = RED; self.fade_alpha = 0
    def make_open(self): self.color = GREEN; self.fade_alpha = 0
    def make_barrier(self): self.color = TREE_GREEN
    def make_end(self): self.color = BLUE
    def make_path(self): self.color = YELLOW; self.fade_alpha = 0

    def update(self):
        if self.fade_alpha < self.alpha:
            self.fade_alpha += self.fade_speed
            if self.fade_alpha > self.alpha:
                self.fade_alpha = self.alpha

    def draw(self, win):
        self.update()
        # Draw base grass texture
        pygame.draw.rect(win, GRASS_GREEN, (self.x + GRID_OFFSET_X, self.y + GRID_OFFSET_Y, self.width, self.width))
        # Add noise for texture
        for i in range(3):
            rx = random.randint(self.x + GRID_OFFSET_X, self.x + GRID_OFFSET_X + self.width - 1)
            ry = random.randint(self.y + GRID_OFFSET_Y, self.y + GRID_OFFSET_Y + self.width - 1)
            pygame.draw.circle(win, (GRASS_GREEN[0] - 20, GRASS_GREEN[1] - 20, GRASS_GREEN[2]), (rx, ry), 2)
        # Draw node state
        if self.is_barrier():
            pygame.draw.circle(win, TREE_GREEN, (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + self.width // 2), self.width // 2 - 2)
        elif self.is_start():
            # Draw house icon
            pygame.draw.rect(win, BROWN, (self.x + GRID_OFFSET_X + 4, self.y + GRID_OFFSET_Y + self.width // 2, self.width - 8, self.width // 2 - 4))
            pygame.draw.polygon(win, DARK_GREY, [
                (self.x + GRID_OFFSET_X, self.y + GRID_OFFSET_Y + self.width // 2),
                (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + 4),
                (self.x + GRID_OFFSET_X + self.width, self.y + GRID_OFFSET_Y + self.width // 2)
            ])
        elif self.is_end():
            # Draw flag icon
            pygame.draw.line(win, DARK_GREY, (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + 4),
                             (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + self.width - 4), 3)
            pygame.draw.polygon(win, RED, [
                (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + 4),
                (self.x + GRID_OFFSET_X + self.width - 4, self.y + GRID_OFFSET_Y + 4),
                (self.x + GRID_OFFSET_X + self.width // 2, self.y + GRID_OFFSET_Y + self.width // 3)
            ])
        elif self.color in [GREEN, RED, YELLOW]:
            color = (*self.color[:3], int(self.fade_alpha))
            pygame.draw.rect(win, color, (self.x + GRID_OFFSET_X + 2, self.y + GRID_OFFSET_Y + 2, self.width - 4, self.width - 4))

    def update_neighbors(self, grid):
        self.neighbors = []
        for dr, dc in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            r, c = self.row + dr, self.col + dc
            if 0 <= r < self.total_rows and 0 <= c < self.total_rows and not grid[r][c].is_barrier():
                self.neighbors.append(grid[r][c])

def h(p1, p2):
    x1, y1 = p1
    x2, y2 = p2
    return abs(x1 - x2) + abs(y1 - y2)

class AStar:
    def __init__(self, grid, start, end):
        self.grid = grid
        self.start = start
        self.end = end
        self.count = 0
        self.open_set = PriorityQueue()
        self.open_set.put((0, self.count, start))
        self.came_from = {}
        self.start.g = 0
        self.start.f = h(start.get_pos(), end.get_pos())
        self.open_set_hash = {start}
        self.visited_count = 0
        self.path_length = 0
        self.done = False
        self.last_update = time.time()
        self.path = []

    def step(self):
        if self.done or self.open_set.empty():
            self.done = True
            return

        current_time = time.time()
        if current_time - self.last_update < ASTAR_ANIMATION_SPEED:
            return

        self.last_update = current_time
        current = self.open_set.get()[2]
        self.open_set_hash.remove(current)

        if current == self.end:
            self.path = self.reconstruct_path()
            self.done = True
            self.path_length = len(self.path)
            return

        for neighbor in current.neighbors:
            temp_g = current.g + 1
            if temp_g < neighbor.g:
                self.came_from[neighbor] = current
                neighbor.g = temp_g
                neighbor.h = h(neighbor.get_pos(), self.end.get_pos())
                neighbor.f = neighbor.g + neighbor.h
                if neighbor not in self.open_set_hash:
                    self.count += 1
                    self.open_set.put((neighbor.f, self.count, neighbor))
                    self.open_set_hash.add(neighbor)
                    neighbor.make_open()
                    neighbor.alpha = 128

        if current != self.start:
            current.make_closed()
            current.alpha = 128
            self.visited_count += 1

    def reconstruct_path(self):
        path = []
        current = self.end
        while current in self.came_from:
            path.append(current)
            current = self.came_from[current]
        path.reverse()
        for node in path:
            node.make_path()
            node.alpha = 255
        return path

def make_grid(rows, width):
    grid = []
    gap = width // rows
    for i in range(rows):
        grid.append([Node(i, j, gap, rows) for j in range(rows)])
    for row in grid:
        for node in row:
            if random.random() < 0.3:
                node.make_barrier()
    return grid

def draw_grid_lines(win, rows, width):
    gap = width // rows
    for i in range(rows + 1):
        pygame.draw.line(win, BROWN, (GRID_OFFSET_X, GRID_OFFSET_Y + i * gap), (GRID_OFFSET_X + width, GRID_OFFSET_Y + i * gap), 1)
        pygame.draw.line(win, BROWN, (GRID_OFFSET_X + i * gap, GRID_OFFSET_Y), (GRID_OFFSET_X + i * gap, GRID_OFFSET_Y + width), 1)

class Button:
    def __init__(self, x, y, width, height, text):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.is_hovered = False
        self.scale = 1.0
        self.target_scale = 1.0
        self.scale_speed = 0.1

    def update(self):
        if self.is_hovered and self.scale < 1.05:
            self.scale += self.scale_speed
        elif not self.is_hovered and self.scale > 1.0:
            self.scale -= self.scale_speed

    def draw(self, win):
        self.update()
        scaled_width = int(self.rect.width * self.scale)
        scaled_height = int(self.rect.height * self.scale)
        scaled_rect = pygame.Rect(
            self.rect.centerx - scaled_width // 2,
            self.rect.centery - scaled_height // 2,
            scaled_width,
            scaled_height
        )
        color = BUTTON_HOVER_COLOR if self.is_hovered else BUTTON_COLOR
        pygame.draw.rect(win, color, scaled_rect, border_radius=5)
        pygame.draw.rect(win, DARK_GREY, scaled_rect, 2, border_radius=5)
        text_surface = FONT.render(self.text, True, BUTTON_TEXT_COLOR)
        text_rect = text_surface.get_rect(center=scaled_rect.center)
        win.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.is_hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.is_hovered:
                if CLICK_SOUND:
                    CLICK_SOUND.play()
                return True
        return False

class UI:
    def __init__(self):
        self.buttons = {}
        self._create_buttons()

    def _create_buttons(self):
        self.buttons['menu'] = [
            Button(WIDTH//2 - BUTTON_WIDTH//2, HEIGHT//2, BUTTON_WIDTH, BUTTON_HEIGHT, "Start Game"),
            Button(WIDTH//2 - BUTTON_WIDTH//2, HEIGHT//2 + BUTTON_HEIGHT + BUTTON_MARGIN, BUTTON_WIDTH, BUTTON_HEIGHT, "Quit")
        ]
        self.buttons['game'] = [
            Button(WIDTH - BUTTON_WIDTH - 10, HEIGHT - BUTTON_HEIGHT - 10, BUTTON_WIDTH, BUTTON_HEIGHT, "Reset"),
            Button(10, HEIGHT - BUTTON_HEIGHT - 10, BUTTON_WIDTH, BUTTON_HEIGHT, "Run A*")
        ]
        self.buttons['end'] = [
            Button(WIDTH//2 - BUTTON_WIDTH//2, HEIGHT//2 + 100, BUTTON_WIDTH, BUTTON_HEIGHT, "Play Again"),
            Button(WIDTH//2 - BUTTON_WIDTH//2, HEIGHT//2 + BUTTON_HEIGHT + BUTTON_MARGIN + 100, BUTTON_WIDTH, BUTTON_HEIGHT, "Main Menu")
        ]

def draw_menu(win, ui):
    win.fill(BEIGE)
    pygame.draw.rect(win, DARK_GREY, (0, 0, WIDTH, HEIGHT), 5)  # Border
    title = TITLE_FONT.render("Path Hunter", True, BLACK)
    subtitle = FONT.render("Race Against A* Pathfinding!", True, BLACK)
    win.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
    win.blit(subtitle, (WIDTH//2 - subtitle.get_width()//2, HEIGHT//3 + 50))
    for button in ui.buttons['menu']:
        button.draw(win)

def draw_game_ui(win, game_state, player, astar, message, ui):
    pygame.draw.rect(win, LIGHT_BLUE, (0, HEIGHT - 50, WIDTH, 50))
    pygame.draw.line(win, DARK_GREY, (0, HEIGHT - 50), (WIDTH, HEIGHT - 50), 2)
    status = message
    if game_state == GAME_STATES['PLAYING'] and player:
        status = f"Moves: {player.moves} | Time: {int(time.time() - player.start_time)}s"
    elif game_state == GAME_STATES['RUNNING_ASTAR'] and astar:
        status = f"Running A*: Visited={astar.visited_count}"
    text = FONT.render(status, True, BLACK)
    win.blit(text, (10, HEIGHT - 35))
    for button in ui.buttons['game']:
        button.draw(win)

def draw_game_over(win, player, optimal_path_length, ui):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill(BEIGE)
    overlay.set_alpha(230)
    win.blit(overlay, (0, 0))
    text = TITLE_FONT.render("Game Over!", True, BLACK)
    subtext = FONT.render("No valid path exists!", True, BLACK)
    win.blit(text, (WIDTH//2 - text.get_width()//2, HEIGHT//3))
    win.blit(subtext, (WIDTH//2 - subtext.get_width()//2, HEIGHT//3 + 50))
    for button in ui.buttons['end']:
        button.draw(win)

def draw_victory(win, player, optimal_path_length, ui):
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.fill(BEIGE)
    overlay.set_alpha(230)
    win.blit(overlay, (0, 0))
    title = TITLE_FONT.render("Victory!", True, BLACK)
    score_text = FONT.render(f"Score: {player.score}", True, BLACK)
    moves_text = FONT.render(f"Your moves: {player.moves} | Optimal: {optimal_path_length}", True, BLACK)
    time_text = FONT.render(f"Time: {int(time.time() - player.start_time)}s", True, BLACK)
    win.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3))
    win.blit(score_text, (WIDTH//2 - score_text.get_width()//2, HEIGHT//3 + 50))
    win.blit(moves_text, (WIDTH//2 - moves_text.get_width()//2, HEIGHT//3 + 80))
    win.blit(time_text, (WIDTH//2 - time_text.get_width()//2, HEIGHT//3 + 110))
    for button in ui.buttons['end']:
        button.draw(win)

def render(win, game_state, grid, player, astar, ui, message, optimal_path_length):
    win.fill(BEIGE)  # Parchment background
    pygame.draw.rect(win, DARK_GREY, (0, 0, WIDTH, HEIGHT), 5)  # Border
    if game_state != GAME_STATES['MENU']:
        for row in grid:
            for node in row:
                node.draw(win)
        draw_grid_lines(win, ROWS, WIDTH)
        pygame.draw.rect(win, DARK_GREY, (GRID_OFFSET_X, GRID_OFFSET_Y, WIDTH, WIDTH), 3)
        if player:
            player.draw(win)
        draw_game_ui(win, game_state, player, astar, message, ui)
        if game_state == GAME_STATES['GAME_OVER']:
            draw_game_over(win, player, optimal_path_length, ui)
        elif game_state == GAME_STATES['VICTORY']:
            draw_victory(win, player, optimal_path_length, ui)
    else:
        draw_menu(win, ui)
    pygame.display.flip()

def get_clicked_pos(pos, rows, width):
    gap = width // rows
    x, y = pos
    row = (y - GRID_OFFSET_Y) // gap
    col = (x - GRID_OFFSET_X) // gap
    return row, col

def calculate_score(player_moves, optimal_path_length, time_taken):
    if optimal_path_length == 0:
        return 0
    efficiency = min(optimal_path_length / player_moves, 1.0)
    time_bonus = max(100 - time_taken, 10)
    return int(100 * efficiency * (time_bonus / 100))

def main(win, width):
    grid = make_grid(ROWS, width)
    start = None
    end = None
    player = None
    astar = None
    game_state = GAME_STATES['MENU']
    optimal_path_length = 0
    run = True
    ui = UI()
    message = ""
    last_click = 0
    click_delay = 0.2

    while run:
        CLOCK.tick(FPS)
        if player:
            player.update()
        if astar and game_state == GAME_STATES['RUNNING_ASTAR']:
            astar.step()
            if astar.done:
                optimal_path_length = astar.path_length
                if optimal_path_length > 0:
                    message = f"A* Done: Visited={astar.visited_count}, Path={optimal_path_length}"
                else:
                    message = "No Path Found"
                    game_state = GAME_STATES['GAME_OVER']
        render(win, game_state, grid, player, astar, ui, message, optimal_path_length)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            if game_state == GAME_STATES['MENU']:
                for i, button in enumerate(ui.buttons['menu']):
                    if button.handle_event(event):
                        if i == 0:
                            game_state = GAME_STATES['PLAYING']
                            message = "Select Start Point"
                        elif i == 1:
                            run = False

            elif game_state == GAME_STATES['PLAYING']:
                for i, button in enumerate(ui.buttons['game']):
                    if button.handle_event(event):
                        if i == 0:  # Reset
                            grid = make_grid(ROWS, width)
                            start = None
                            end = None
                            player = None
                            astar = None
                            message = "Select Start Point"
                        elif i == 1 and start and end:  # Run A*
                            game_state = GAME_STATES['RUNNING_ASTAR']
                            astar = AStar(grid, start, end)

                if event.type == pygame.MOUSEBUTTONDOWN and time.time() - last_click > click_delay:
                    last_click = time.time()
                    pos = event.pos
                    row, col = get_clicked_pos(pos, ROWS, width)
                    if 0 <= row < ROWS and 0 <= col < ROWS:
                        node = grid[row][col]
                        if not start and node != end:
                            start = node
                            start.make_start()
                            player = Player(start)
                            message = "Select End Point"
                        elif not end and node != start:
                            end = node
                            end.make_end()
                            for row in grid:
                                for spot in row:
                                    spot.update_neighbors(grid)
                            message = "Use Arrow Keys to Move!"
                        elif node != end and node != start:
                            node.make_barrier()

                if event.type == pygame.KEYDOWN and player and end:
                    row, col = player.current_node.get_pos()
                    moved = False
                    if event.key == pygame.K_LEFT and col > 0:
                        moved = player.move_to(grid[row][col-1])
                    elif event.key == pygame.K_RIGHT and col < ROWS-1:
                        moved = player.move_to(grid[row][col+1])
                    elif event.key == pygame.K_UP and row > 0:
                        moved = player.move_to(grid[row-1][col])
                    elif event.key == pygame.K_DOWN and row < ROWS-1:
                        moved = player.move_to(grid[row+1][col])
                    if moved and player.current_node == end:
                        astar = AStar(grid, start, end)
                        game_state = GAME_STATES['RUNNING_ASTAR']

            elif game_state in [GAME_STATES['VICTORY'], GAME_STATES['GAME_OVER']]:
                for i, button in enumerate(ui.buttons['end']):
                    if button.handle_event(event):
                        if i == 0:  # Play Again
                            grid = make_grid(ROWS, width)
                            start = None
                            end = None
                            player = None
                            astar = None
                            game_state = GAME_STATES['PLAYING']
                            message = "Select Start Point"
                        elif i == 1:  # Main Menu
                            game_state = GAME_STATES['MENU']

        if game_state == GAME_STATES['RUNNING_ASTAR'] and astar and astar.done and astar.path_length > 0:
            player.score = calculate_score(player.moves, astar.path_length, time.time() - player.start_time)
            game_state = GAME_STATES['VICTORY']

    pygame.quit()

if __name__ == "__main__":
    main(WIN, WIDTH)