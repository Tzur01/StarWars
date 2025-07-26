import curses
import time
import random

class GameObject:
    def __init__(self, x, y, char, color_pair):
        self.x = x
        self.y = y
        self.char = char
        self.color_pair = color_pair

    def draw(self, stdscr):
        try:
            stdscr.attron(curses.color_pair(self.color_pair))
            stdscr.addstr(int(self.y), int(self.x), self.char)
            stdscr.attroff(curses.color_pair(self.color_pair))
        except curses.error:
            pass

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

def draw_border(stdscr):
    height, width = stdscr.getmaxyx()
    usable_width = max(4, width - 2)
    stdscr.attron(curses.color_pair(7))
    try:
        border_line = "+" + "-" * usable_width + "+"
        stdscr.addstr(0, 0, border_line[:width - 1])
        for y in range(1, height - 1):
            if width >= 2:
                stdscr.addstr(y, 0, "|")
                stdscr.addstr(y, min(width - 1, usable_width + 1), "|")
        stdscr.addstr(height - 1, 0, border_line[:width - 1])
    except curses.error:
        pass
    stdscr.attroff(curses.color_pair(7))

def explode_animation(stdscr, x, y):
    explosions = [" BOOM! ", " * * * ", "  ***  ", "   *   "]
    for frame in explosions:
        try:
            stdscr.clear()
            stdscr.addstr(int(y), max(0, int(x - len(frame)//2)), frame, curses.A_BOLD | curses.color_pair(2))
            stdscr.refresh()
            time.sleep(0.2)
        except curses.error:
            pass

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(30)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)

    height, width = stdscr.getmaxyx()
    if height < 10 or width < 30:
        stdscr.clear()
        stdscr.addstr(0, 0, "Please resize your terminal to at least 30x10")
        stdscr.refresh()
        time.sleep(3)
        return

    player = GameObject(5, height // 2, "<=>", 1)
    projectiles = []
    stars = [GameObject(random.randint(0, width - 1), random.randint(1, height - 2), "*", 4) for _ in range(15)]
    enemies = []
    powerups = []
    score = 0
    last_shot = 0
    shoot_cooldown = 0.2
    last_enemy_spawn = 0
    last_powerup_spawn = 0
    game_over = False

    while True:
        now = time.time()
        stdscr.erase()
        draw_border(stdscr)

        for star in stars:
            star.move(-0.2, 0)
            if star.x < 1:
                star.x = width - 2
                star.y = random.randint(1, height - 2)
            star.draw(stdscr)

        player.draw(stdscr)

        for p in projectiles[:]:
            p.move(1, 0)
            if p.x >= width - 1:
                projectiles.remove(p)
            else:
                p.draw(stdscr)

        if now - last_enemy_spawn > 1.5:
            y = random.randint(1, height - 2)
            enemies.append(GameObject(width - 4, y, "*[==]*", 2))
            last_enemy_spawn = now

        if now - last_powerup_spawn > 6:
            y = random.randint(1, height - 2)
            powerups.append(GameObject(width - 4, y, "P", 5))
            last_powerup_spawn = now

        for enemy in enemies[:]:
            enemy.move(-0.5, 0)
            if enemy.x < 1:
                enemies.remove(enemy)
            else:
                enemy.draw(stdscr)
                if int(enemy.y) == int(player.y) and enemy.x <= player.x + 3:
                    explode_animation(stdscr, player.x + 1, player.y)
                    game_over = True

        for powerup in powerups[:]:
            powerup.move(-0.3, 0)
            if powerup.x < 1:
                powerups.remove(powerup)
            else:
                powerup.draw(stdscr)
                if int(powerup.y) == int(player.y) and powerup.x <= player.x + 3:
                    score += 10
                    powerups.remove(powerup)

        for p in projectiles[:]:
            for e in enemies[:]:
                if abs(int(p.y) - int(e.y)) <= 0 and abs(int(p.x) - int(e.x)) <= 1:
                    if p in projectiles:
                        projectiles.remove(p)
                    if e in enemies:
                        enemies.remove(e)
                    score += 5

        key = stdscr.getch()
        if key == curses.KEY_UP and player.y > 1:
            player.move(0, -1)
        elif key == curses.KEY_DOWN and player.y < height - 2:
            player.move(0, 1)
        elif key == ord(' '):
            if now - last_shot > shoot_cooldown:
                projectiles.append(GameObject(player.x + 3, player.y, "-", 3))
                last_shot = now
        elif key == ord('q'):
            break

        stdscr.addstr(0, 2, f"Score: {score}")

        stdscr.refresh()
        time.sleep(1 / 30)

        if game_over:
            stdscr.nodelay(False)
            stdscr.addstr(height // 2, max(0, width // 2 - 5), "GAME OVER", curses.A_BOLD)
            stdscr.addstr(height // 2 + 1, max(0, width // 2 - 10), "Press any key to exit...")
            stdscr.refresh()
            stdscr.getch()
            break

if __name__ == "__main__":
    curses.wrapper(main)
