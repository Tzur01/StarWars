#!/usr/bin/env python3
import curses
import random
import time
import os
import json
from math import floor, sin, cos

class GameObject:
    def __init__(self, x, y, char, direction=1):
        self.x = int(x)  # Integer position for stable movement
        self.y = int(y)  # Integer position for stable movement
        # For subpixel movements, track fractional position separately 
        self.float_x = float(x)
        self.float_y = float(y)
        self.char = char
        self.direction = direction
        self.width = len(char)
        self.height = 1
    
    def move(self, dx, dy):
        # Update the floating-point positions first
        self.float_x += dx
        self.float_y += dy
        # Then update the integer positions
        self.x = int(self.float_x)
        self.y = int(self.float_y)
    
    def get_position(self):
        # Always return integer positions for rendering and collision detection
        return (self.x, self.y)
    
    def collides_with(self, other, margin=0):
        """Simple collision detection - just check if positions overlap"""
        x1, y1 = self.get_position()
        x2, y2 = other.get_position()
        
        # Check for overlap, considering the width of both objects
        # Add margin to make collision detection more forgiving
        horizontal_overlap = (x1 < x2 + other.width + margin and
                             x2 < x1 + self.width + margin)
        vertical_overlap = abs(y1 - y2) <= margin
        return horizontal_overlap and vertical_overlap

class Projectile(GameObject):
    def __init__(self, x, y, direction=1, is_rapid=False):
        # Different appearance for rapid fire projectiles
        if is_rapid:
            try:
                char = "⇒" if direction > 0 else "⇐"
                # Test if character can be displayed
                str(char)
            except:
                char = ">>" if direction > 0 else "<<"  # Fallback
        else:
            char = "->" if direction > 0 else "<"
            
        super().__init__(x, y, char, direction)
        self.speed = 1.5 * direction if is_rapid else 1 * direction  # Rapid projectiles are faster
        self.is_rapid = is_rapid
    
    def update(self):
        self.move(self.speed, 0)

class PowerUp(GameObject):
    def __init__(self, x, y, type_id):
        # Different power-up types with more distinct visual characters
        types = {
            0: "⊕",  # Shield - circle with plus
            1: "↯",  # Fast fire - lightning bolt
            2: "★",  # Invincibility - star
            3: "♥",  # Extra life
        }
        
        # Fallback characters if terminal doesn't support special characters
        fallback_types = {
            0: "S",  # Shield
            1: "F",  # Fast fire
            2: "I",  # Invincibility
            3: "L",  # Extra life
        }
        
        # Try to use special characters, fall back to simple ones if not available
        try:
            char = types.get(type_id, "P")
            # Test if the character can be printed
            str(char)
        except:
            char = fallback_types.get(type_id, "P")
            
        self.type_id = type_id
        
        super().__init__(x, y, char)
        self.speed = -1  # Simple integer speed
        self.pulse_counter = 0  # For visual pulsing effect
    
    def update(self):
        self.move(self.speed, 0)

class Player(GameObject):
    # Ship appearance for different levels
    SHIP_LEVELS = {
        0: "{-+==+-}",    # Basic ship
        1: "<-=:::=->",   # Level 1 upgrade
        2: "{+-=^=-+}>",   # Level 2 upgrade
        3: ">[=X=]>"   # Level 3 upgrade
    }
    
    def __init__(self, x, y):
        self.level = 0  # Start at level 0
        super().__init__(x, y, self.SHIP_LEVELS[0])
        self.speed = 1  # Integer speed for predictable movement
        self.score = 0
        self.lives = 1  # Player starts with 1 life
        self.projectiles = []
        self.last_shot_time = 0
        
        # Enhanced power-up states
        self.has_shield = False
        self.rapid_fire = False
        self.invincible = False
        self.shield_active_until = 0
        self.rapid_fire_until = 0
        self.invincible_until = 0
        self.power_up_duration = 4.0   # Much shorter power-up duration for extreme challenge
        
        # Rapid fire properties
        self.normal_cooldown = 0.3     # Normal fire rate cooldown
        self.rapid_cooldown = 0.1      # Rapid fire cooldown (3x faster)
        self.projectile_char = "-->"     # Normal projectile appearance
        self.rapid_projectile_char = "-=>" # Rapid fire projectile appearance
        
        # For upgrade messages
        self.upgrade_message = ""
        self.upgrade_time = 0
        self.upgrade_display_duration = 3.0
        
        # Invincibility effect
        self.invincible_flash = False
        self.invincible_flash_rate = 0.1  # Flash rate in seconds
        self.last_flash_time = 0
    
    def shoot(self, current_time):
        # Limit shooting rate using the enhanced cooldown properties
        cooldown = self.rapid_cooldown if self.rapid_fire else self.normal_cooldown
        
        if current_time - self.last_shot_time > cooldown:
            x, y = self.get_position()
            
            # Create projectile with appropriate appearance based on rapid fire state
            projectile = Projectile(x + self.width, y, 1, self.rapid_fire)
            self.projectiles.append(projectile)
            
            # Level 2+ ships shoot additional projectiles
            if self.level >= 2:
                # Add diagonal shots for higher level ships
                if y > 1:  # Don't shoot up if too close to top
                    up_projectile = Projectile(x + self.width, y - 1, 1, self.rapid_fire)
                    self.projectiles.append(up_projectile)
                if y < curses.LINES - 2:  # Don't shoot down if too close to bottom
                    down_projectile = Projectile(x + self.width, y + 1, 1, self.rapid_fire)
                    self.projectiles.append(down_projectile)
            
            self.last_shot_time = current_time
            return True
        return False
    
    def update_projectiles(self, max_x):
        # Move projectiles and remove ones that go off-screen
        for projectile in self.projectiles[:]:
            projectile.update()
            x, _ = projectile.get_position()
            if x < 0 or x > max_x:
                if projectile in self.projectiles:
                    self.projectiles.remove(projectile)
                    
    def update_power_ups(self, current_time):
        # Check if power-ups have expired
        if current_time > self.shield_active_until:
            self.has_shield = False
        if current_time > self.rapid_fire_until:
            self.rapid_fire = False
        if current_time > self.invincible_until:
            self.invincible = False
            
    def check_upgrade(self, current_time):
        """Check if player should be upgraded based on score"""
        old_level = self.level
        
        # Check for level upgrades
        if self.score >= 300 and self.level < 3:
            self.level = 3
        elif self.score >= 200 and self.level < 2:
            self.level = 2
        elif self.score >= 100 and self.level < 1:
            self.level = 1
            
        # If upgraded, update appearance and show message
        if self.level > old_level:
            self.char = self.SHIP_LEVELS[self.level]
            self.width = len(self.char)
            self.upgrade_message = f"SHIP UPGRADED! LEVEL {self.level+1}"
            self.upgrade_time = current_time
            return True
        return False

class EnemyType:
    """Class to define different enemy types and their properties"""
    BASIC = 0
    ZIGZAG = 1
    HUNTER = 2
    
    @staticmethod
    def get_appearance(enemy_type):
        appearances = {
            EnemyType.BASIC: "<<=+=>>",
            EnemyType.ZIGZAG: "-=+::+=-",
            EnemyType.HUNTER: "<+==+<",
        }
        return appearances.get(enemy_type, "<==<")
    
    @staticmethod
    def get_base_speed(enemy_type):
        """Get the base speed for an enemy type, before difficulty multiplier"""
        speeds = {
            EnemyType.BASIC: 1.0,    # Base speed for basic enemies
            EnemyType.ZIGZAG: 1.2,   # Base speed for zigzag enemies
            EnemyType.HUNTER: 0.9,   # Base speed for hunter enemies
        }
        return speeds.get(enemy_type, 1.0)
        
    @staticmethod
    def get_max_speed(enemy_type):
        """Get the maximum speed for an enemy type at highest difficulty"""
        speeds = {
            EnemyType.BASIC: 3.0,    # Max speed for basic enemies
            EnemyType.ZIGZAG: 3.5,   # Max speed for zigzag enemies
            EnemyType.HUNTER: 3.2,   # Max speed for hunter enemies
        }
        return speeds.get(enemy_type, 3.0)
    
    @staticmethod
    def get_points(enemy_type):
        points = {
            EnemyType.BASIC: 10,
            EnemyType.ZIGZAG: 15,
            EnemyType.HUNTER: 20,
        }
        return points.get(enemy_type, 10)

class Enemy(GameObject):
    def __init__(self, x, y, enemy_type=EnemyType.BASIC, difficulty_multiplier=1.0):
        self.enemy_type = enemy_type
        char = EnemyType.get_appearance(enemy_type)
        super().__init__(x, y, char, -1)
        
        # Basic properties
        base_speed = EnemyType.get_base_speed(enemy_type)
        max_speed = EnemyType.get_max_speed(enemy_type)
        
        # Scale speed based on difficulty, between base and max
        self.base_speed = base_speed + (max_speed - base_speed) * difficulty_multiplier
        self.speed = self.base_speed * self.direction
        
        # Store difficulty multiplier for movement pattern intensity
        self.difficulty_multiplier = difficulty_multiplier
        
        # For zigzag movement
        self.zigzag_counter = 0
        self.zigzag_interval = 5
        self.zigzag_direction = 1  # 1 for down, -1 for up
        self.zigzag_accumulator = 0.0  # Accumulate fractional movements
        
        # For hunter movement
        self.hunt_interval = 10  # Update target every 10 frames
        self.hunt_counter = 0
        self.target_y = None
        self.hunter_accumulator = 0.0  # Accumulate fractional movements for hunter
    
    def update(self, player_position=None):
        # Base horizontal movement for all enemy types
        self.move(self.speed, 0)
        
        # Additional movements based on enemy type
        if self.enemy_type == EnemyType.ZIGZAG:
            # Movement pattern scales with difficulty
            self.zigzag_counter += 1
            if self.zigzag_counter >= self.zigzag_interval:
                # Change zigzag direction 
                self.zigzag_counter = 0
                self.zigzag_direction *= -1
                # Randomize the zigzag interval - more unpredictable at higher difficulty
                min_interval = max(5 - int(3 * self.difficulty_multiplier), 2)
                max_interval = max(10 - int(5 * self.difficulty_multiplier), 5)
                self.zigzag_interval = random.randint(min_interval, max_interval)
            
            # Vertical movement scales with difficulty
            base_zigzag_speed = 0.5
            max_zigzag_speed = 2.0
            zigzag_speed = base_zigzag_speed + (max_zigzag_speed - base_zigzag_speed) * self.difficulty_multiplier
            self.zigzag_accumulator += zigzag_speed * self.zigzag_direction
        elif self.enemy_type == EnemyType.HUNTER and player_position:
            # Hunter enemies periodically adjust their vertical position to move toward the player
            player_x, player_y = player_position
            
            # Hunter enemies more aggressively track the player's position
            self.hunt_counter += 1
            if self.hunt_counter >= self.hunt_interval or self.target_y is None:
                self.hunt_counter = 0
                # Much more frequent targeting updates for relentless pursuit
                self.hunt_interval = random.randint(3, 5)  # Extremely responsive tracking
                self.target_y = player_y
            
            # Move toward target y-position
            if self.target_y is not None:
                current_y = self.float_y  # Use floating-point position for calculation
                if abs(current_y - self.target_y) > 0.2:  # More precise targeting
                    # Hunter tracking speed scales with difficulty
                    base_tracking_speed = 0.8
                    max_tracking_speed = 2.5
                    tracking_speed = base_tracking_speed + (max_tracking_speed - base_tracking_speed) * self.difficulty_multiplier
                    dy = tracking_speed if current_y < self.target_y else -tracking_speed
                    self.hunter_accumulator += dy
                    
                    # Apply movement when accumulation reaches +/- 1
                    move_amount = int(self.hunter_accumulator)
                    if move_amount != 0:
                        self.move(0, move_amount)
                        # Subtract the applied movement
                        self.hunter_accumulator -= move_amount
class StarWarsGame:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.setup_curses()
        self.init_game()
        
    def get_difficulty_multiplier(self, current_time):
        """
        Calculate difficulty multiplier based on gameplay time and score
        Returns a value between 0.0 (easiest) and 1.0 (hardest)
        """
        # Time-based difficulty scaling (reaches 60% difficulty after 3 minutes)
        time_played = current_time - self.start_time
        
        # Very gentle curve that increases more rapidly after 60 seconds
        if time_played < 60:
            # First 60 seconds: very gentle increase (max 20%)
            time_factor = min(time_played / 300.0, 0.2)
        else:
            # After 60 seconds: standard increase up to 60%
            time_factor = 0.2 + min((time_played - 60) / 180.0, 0.4)
        
        # Score-based difficulty scaling (reaches 40% difficulty at 300 points)
        # Use a gentler curve for score-based difficulty
        if self.player.score < 100:
            score_factor = self.player.score / 500.0  # Very gradual increase
        else:
            score_factor = 0.2 + min((self.player.score - 100) / 500.0, 0.2)
        
        # Combined difficulty factor (capped at 1.0)
        difficulty = min(time_factor + score_factor, 1.0)
        
        # Smoothing function for the very early game (first 30 seconds)
        if time_played < 30:
            difficulty *= (time_played / 30.0) * 0.7  # Even gentler start
            
        # Apply logarithmic smoothing to make the curve more natural
        # This makes difficulty increases feel more gradual
        import math
        if difficulty > 0:
            difficulty = math.log(1 + 9 * difficulty) / math.log(10)
            
        # For display purposes
        self.current_difficulty = difficulty
        
        return difficulty
    
    def setup_curses(self):
        # Set up curses
        curses.curs_set(0)  # Hide cursor
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)
        self.stdscr.timeout(0)  # Non-blocking input
        
        # Try to set up colors if available
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)     # Player
            curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)       # Enemies
            curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)    # Projectiles
            curses.init_pair(4, curses.COLOR_CYAN, curses.COLOR_BLACK)      # Stars
            curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)   # Power-ups
            curses.init_pair(6, curses.COLOR_BLUE, curses.COLOR_BLACK)      # Shield
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLACK)     # Text
            curses.init_pair(8, curses.COLOR_RED, curses.COLOR_WHITE)       # Warning
            curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_YELLOW)    # Highlight
    
    def init_game(self):
        # Get screen dimensions
        self.height, self.width = self.stdscr.getmaxyx()
        
        # Initialize game state
        self.running = True
        self.game_over = False
        self.frame_time = 1/15  # Lower frame rate for stability
        self.current_difficulty = 0.0  # For displaying the current difficulty
        
        # Create player spaceship
        player_x = 5
        player_y = self.height // 2
        self.player = Player(player_x, player_y)
        
        # Initialize enemies
        self.enemies = []
        self.last_enemy_spawn = 0
        
        # Spawn rate parameters that scale with difficulty
        self.initial_enemy_spawn_rate = 3.0  # Starting spawn rate (even easier)
        self.min_enemy_spawn_rate = 0.3      # Final spawn rate at max difficulty (slightly easier)
        self.enemy_spawn_rate = self.initial_enemy_spawn_rate
        
        # Enemy type spawn thresholds - more gradual introduction
        self.zigzag_enemy_score_threshold = 50   # Start spawning zigzag enemies a bit later
        self.hunter_enemy_score_threshold = 120  # Start spawning hunter enemies later
        
        self.power_ups = []
        self.last_power_up_spawn = 0
        
        # Power-up spawn rate parameters that scale with difficulty
        self.initial_power_up_spawn_rate = 8.0   # Starting power-up rate (more frequent)
        self.max_power_up_spawn_rate = 25.0      # Maximum power-up spawn interval (slightly more frequent)
        self.power_up_spawn_rate = self.initial_power_up_spawn_rate
        
        # Initialize game time for consistent timing after reset
        self.start_time = time.time()
        
        # Simple stars for background (fewer than before)
        self.stars = []
        for _ in range(15):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            char = "*"
            self.stars.append(GameObject(x, y, char))
    

    def spawn_enemy(self):
        """Spawn a new enemy if under the limit, with type based on score"""
        if len(self.enemies) < 15:  # Maximum number of enemies on screen at once
            # Spawn position
            x = self.width - 10
            y = random.randint(2, self.height - 3)  # Keep away from borders
            
            # Get current difficulty multiplier
            current_time = time.time()
            difficulty = self.get_difficulty_multiplier(current_time)
            
            # Determine enemy type based on score and difficulty
            enemy_type = EnemyType.BASIC  # Default enemy type
            
            # More gradual enemy type introduction based on difficulty
            # Hunter enemies appear more gradually
            hunter_chance_threshold = self.hunter_enemy_score_threshold * (1.0 - difficulty * 0.3)
            if self.player.score >= hunter_chance_threshold:
                # Hunter chance scales with difficulty (10-40%)
                hunter_chance = 0.1 + (difficulty * 0.3)
                if random.random() < hunter_chance:
                    enemy_type = EnemyType.HUNTER
            
            # Zigzag enemies appear more gradually
            zigzag_chance_threshold = self.zigzag_enemy_score_threshold * (1.0 - difficulty * 0.3)
            if enemy_type == EnemyType.BASIC and self.player.score >= zigzag_chance_threshold:
                # Zigzag chance scales with difficulty (20-60%)
                zigzag_chance = 0.2 + (difficulty * 0.4)
                if random.random() < zigzag_chance:
                    enemy_type = EnemyType.ZIGZAG
            
            # Create the enemy with the chosen type and current difficulty
            self.enemies.append(Enemy(x, y, enemy_type, difficulty))
    
    def spawn_power_up(self):
        """Spawn a random power-up"""
        if len(self.power_ups) < 2:  # Limit number of power-ups on screen
            x = self.width - 5
            y = random.randint(2, self.height - 3)
            
            # Simplified power-up types
            power_up_type = random.randint(0, 2)  # 0=Shield, 1=Fast fire, 2=Invincibility
            
            # Create the power-up
            try:
                new_power_up = PowerUp(x, y, power_up_type)
                self.power_ups.append(new_power_up)
            except Exception as e:
                print(f"Error creating power-up: {e}")
    
    def handle_input(self, current_time):
        key = self.stdscr.getch()
        
        if self.game_over:
            # Game over - check for restart
            if key == ord('r'):
                self.reset_game()
                return
            elif key == ord('q') or key == 27:  # 'q' or ESC to quit
                self.running = False
                return
        else:
            # Normal gameplay input handling
            if key == curses.KEY_UP:
                self.player.move(0, -self.player.speed)
            elif key == curses.KEY_DOWN:
                self.player.move(0, self.player.speed)
            elif key == curses.KEY_LEFT:
                self.player.move(-self.player.speed, 0)
            elif key == curses.KEY_RIGHT:
                self.player.move(self.player.speed, 0)
            elif key == ord(' '):  # Spacebar to shoot
                self.player.shoot(current_time)
            elif key == ord('q') or key == 27:  # 'q' or ESC to quit
                self.running = False
                
        # Ensure player stays within bounds
        px, py = self.player.get_position()
        if px < 0:
            self.player.x = 0
        elif px + self.player.width >= self.width:
            self.player.x = self.width - self.player.width - 1
        
        if py < 0:
            self.player.y = 0
        elif py + self.player.height >= self.height:
            self.player.y = self.height - self.player.height - 1
    
    def update(self, current_time):
        # Update player power-up states
        self.player.update_power_ups(current_time)
        
        # Get current difficulty multiplier
        difficulty = self.get_difficulty_multiplier(current_time)
        
        # Calculate enemy spawn rate based on difficulty
        self.enemy_spawn_rate = self.initial_enemy_spawn_rate - (
            (self.initial_enemy_spawn_rate - self.min_enemy_spawn_rate) * difficulty
        )
        
        # Calculate power-up spawn rate based on difficulty (less frequent at higher difficulty)
        self.power_up_spawn_rate = self.initial_power_up_spawn_rate + (
            (self.max_power_up_spawn_rate - self.initial_power_up_spawn_rate) * difficulty
        )
        
        # Spawn enemies at calculated rate
        if current_time - self.last_enemy_spawn > self.enemy_spawn_rate:
            self.spawn_enemy()
            self.last_enemy_spawn = current_time
            
        # Spawn power-ups occasionally
        if current_time - self.last_power_up_spawn > self.power_up_spawn_rate:
            self.spawn_power_up()
            self.last_power_up_spawn = current_time
            
        # Update player projectiles
        self.player.update_projectiles(self.width)
        
        # Check for ship upgrades based on score
        self.player.check_upgrade(current_time)
        
        # Update power-ups
        for power_up in self.power_ups[:]:
            try:
                power_up.update()
                
                # Remove power-ups that move off-screen
                px, py = power_up.get_position()
                if px < 0 or px > self.width or py < 0 or py > self.height:
                    if power_up in self.power_ups:
                        self.power_ups.remove(power_up)
                    continue
            except Exception as e:
                print(f"Power-up update error: {e}")
                # Try to safely remove problematic power-up
                try:
                    if power_up in self.power_ups:
                        self.power_ups.remove(power_up)
                except:
                    pass
                continue
                
            # Check collision between player and power-up
            # Use a consistent margin for better power-up collection
            try:
                # Check for collision with power-up (increased margin)
                if power_up.collides_with(self.player, margin=3):
                    # Apply power-up effect based on type
                    if power_up.type_id == 0:  # Shield
                        self.player.has_shield = True
                        self.player.shield_active_until = current_time + self.player.power_up_duration
                        feedback_msg = "SHIELD ACTIVATED!"
                    elif power_up.type_id == 1:  # Fast fire
                        self.player.rapid_fire = True
                        self.player.rapid_fire_until = current_time + self.player.power_up_duration
                        feedback_msg = "RAPID FIRE ACTIVATED!"
                    elif power_up.type_id == 2:  # Invincibility
                        self.player.invincible = True
                        self.player.invincible_until = current_time + self.player.power_up_duration
                        feedback_msg = "INVINCIBILITY ACTIVATED!"
                    else:
                        feedback_msg = "POWER-UP COLLECTED!"
                    
                    # Show feedback message
                    self.player.upgrade_message = feedback_msg
                    self.player.upgrade_time = current_time
                    
                    # Remove the power-up
                    if power_up in self.power_ups:
                        self.power_ups.remove(power_up)
                    
                    # Give bonus points for collecting power-up
                    self.player.score += 5
            except Exception as e:
                # In case of any errors, safely remove the problematic power-up
                print(f"Error in power-up processing: {e}")
                try:
                    if power_up in self.power_ups:
                        self.power_ups.remove(power_up)
                except:
                    pass  # Ensure we don't crash if power-up can't be removed
        
        # Update enemies
        for enemy in self.enemies[:]:
            # Pass player position to enemy update (for hunter enemies)
            player_position = self.player.get_position()
            enemy.update(player_position)
            
            # Remove enemies that move off-screen
            ex, ey = enemy.get_position()
            if ex + enemy.width < 0 or ex > self.width or ey < 0 or ey > self.height:
                self.enemies.remove(enemy)
                continue
            
            # Check collision between player and enemy
            try:
                if enemy.collides_with(self.player):
                    # Handle collision based on player status
                    if self.player.invincible:
                        # Invincible players destroy enemies on contact without increasing score
                        try:
                            if enemy in self.enemies:
                                self.enemies.remove(enemy)
                                # NO score increase for collisions - fixed bug
                            else:
                                # Enemy already removed
                                continue
                        except ValueError:
                            # Enemy might have been removed by another collision check
                            pass
                    # Check if player has a shield
                    elif self.player.has_shield:
                        # Shield absorbs the hit then deactivates
                        self.player.has_shield = False
                        # Show shield deactivation message
                        self.player.upgrade_message = "SHIELD DEACTIVATED!"
                        self.player.upgrade_time = current_time
                        try:
                            if enemy in self.enemies:
                                self.enemies.remove(enemy)
                                # NO score increase for collisions - fixed bug
                            else:
                                # Enemy already removed
                                continue
                        except ValueError:
                            pass
                    else:
                        # No protection - game over immediately
                        self.game_over = True
                        # Game over triggered by collision
                        # Exit the update function immediately to prevent any further processing
                        return
            except Exception as e:
                print(f"Error in player-enemy collision detection: {e}")
            
            # Check collision between projectiles and enemies
            for projectile in self.player.projectiles[:]:
                try:
                    if enemy.collides_with(projectile):
                        # Safely remove enemy
                        try:
                            if enemy in self.enemies:
                                self.enemies.remove(enemy)
                            else:
                                continue  # Enemy already removed
                        except ValueError:
                            continue  # Enemy was removed elsewhere
                            
                        # Safely remove projectile
                        try:
                            if projectile in self.player.projectiles:
                                self.player.projectiles.remove(projectile)
                        except:
                            pass  # Ensure we don't crash if projectile was already removed
                            
                        # Award points based on enemy type
                        self.player.score += EnemyType.get_points(enemy.enemy_type)
                        break
                except Exception as e:
                    # Handle any errors in collision detection
                    print(f"Projectile collision error: {e}")
                    pass
    
    def render(self):
        # Draw score and difficulty level
        score_text = f"Score: {self.player.score}"
        self.stdscr.addstr(0, 0, score_text)
        
        # Show difficulty percentage (if in debug mode)
        # difficulty_text = f"Difficulty: {int(self.current_difficulty * 100)}%"
        # self.stdscr.addstr(0, self.width - len(difficulty_text) - 1, difficulty_text)
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(4))
        for star in self.stars:
            x, y = star.get_position()
            if 0 <= x < self.width and 0 <= y < self.height:
                self.stdscr.addstr(int(y), int(x), star.char)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(4))
        
        # Draw player
        px, py = self.player.get_position()
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(int(py), int(px), self.player.char)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(1))
        
        # Draw player projectiles
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(3))
        for projectile in self.player.projectiles:
            px, py = projectile.get_position()
            if 0 <= px < self.width and 0 <= py < self.height:
                self.stdscr.addstr(int(py), int(px), projectile.char)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(3))
        
        # Draw enemies
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(2))
        for enemy in self.enemies:
            ex, ey = enemy.get_position()
            if 0 <= ex < self.width and 0 <= ey < self.height:
                self.stdscr.addstr(int(ey), int(ex), enemy.char)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(2))
        
        # Draw power-ups
        if curses.has_colors():
            self.stdscr.attron(curses.color_pair(5))
        for power_up in self.power_ups:
            px, py = power_up.get_position()
            if 0 <= px < self.width and 0 <= py < self.height:
                self.stdscr.addstr(int(py), int(px), power_up.char)
        if curses.has_colors():
            self.stdscr.attroff(curses.color_pair(5))
        
        # Draw player shield if active
        current_time = time.time()
        if self.player.has_shield:
            if curses.has_colors():
                self.stdscr.attron(curses.color_pair(6))
            px, py = self.player.get_position()
            shield_char = "[" + " " * (self.player.width-2) + "]"
            self.stdscr.addstr(int(py), int(px-1), shield_char)
            if curses.has_colors():
                self.stdscr.attroff(curses.color_pair(6))
                
        # Draw score
        score_text = f"Score: {self.player.score}"
        self.stdscr.addstr(0, 0, score_text)
        
        # Show power-up status
        current_time = time.time()
        status_y = 1
        if current_time < self.player.shield_active_until:
            self.stdscr.addstr(status_y, 0, f"Shield: {int(self.player.shield_active_until - current_time)}s")
            status_y += 1
        if current_time < self.player.rapid_fire_until:
            self.stdscr.addstr(status_y, 0, f"Rapid Fire: {int(self.player.rapid_fire_until - current_time)}s")
            status_y += 1
        if current_time < self.player.invincible_until:
            self.stdscr.addstr(status_y, 0, f"Invincible: {int(self.player.invincible_until - current_time)}s")
            status_y += 1
            
        # Show upgrade message if there is one (simplified)
        if self.player.upgrade_message and current_time - self.player.upgrade_time < self.player.upgrade_display_duration:
            # Choose a color based on message type
            color_pair = 1  # Default green
            if "SHIELD" in self.player.upgrade_message:
                color_pair = 6  # Blue for shield
            elif "FIRE" in self.player.upgrade_message:
                color_pair = 3  # Yellow for rapid fire
            elif "INVINCIBILITY" in self.player.upgrade_message:
                color_pair = 2  # Red for invincibility
                
            if curses.has_colors():
                self.stdscr.attron(curses.color_pair(color_pair) | curses.A_BOLD)
                
            msg = self.player.upgrade_message
            x = self.width // 2 - len(msg) // 2
            y = self.height - 4
            
            # Draw message
            self.stdscr.addstr(y, x, msg)
                
            if curses.has_colors():
                self.stdscr.attroff(curses.color_pair(color_pair) | curses.A_BOLD)
            
        # Show ship level indicator
        level_text = f"Ship Level: {self.player.level + 1}"
        self.stdscr.addstr(status_y, 0, level_text)
        
        # Draw upgrade info
        if self.player.level < 3:
            next_upgrade = (100, 200, 300)[self.player.level]
            points_needed = next_upgrade - self.player.score
            if points_needed > 0:
                upgrade_text = f"Points to next upgrade: {points_needed}"
                self.stdscr.addstr(status_y + 1, 0, upgrade_text)
        
        # Draw game over message if needed
        if self.game_over:
            game_over_text = "GAME OVER - Final Score: " + str(self.player.score)
            x = self.width // 2 - len(game_over_text) // 2
            y = self.height // 2 - 1
            self.stdscr.addstr(y, x, game_over_text, curses.A_BOLD)
            
            restart_text = "Press 'r' to play again, 'q' to quit"
            x = self.width // 2 - len(restart_text) // 2
            self.stdscr.addstr(y + 2, x, restart_text, curses.A_BOLD)
        
        self.stdscr.refresh()
    
    
    def reset_game(self):
        """Reset the game state to start a new game"""
        # Clear the screen
        self.stdscr.clear()
            
        # Get screen dimensions again in case of resize
        self.height, self.width = self.stdscr.getmaxyx()
        
        # Reset game state
        self.game_over = False
        
        # Reset player
        player_x = 5
        player_y = self.height // 2
        self.player = Player(player_x, player_y)
        
        # Clear enemies and power-ups
        self.enemies = []
        self.power_ups = []
        
        # Reset timers
        current_time = time.time()
        self.last_enemy_spawn = current_time
        self.last_power_up_spawn = current_time
        self.start_time = current_time
        
        # Reset stars
        self.stars = []
        for _ in range(30):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            char = random.choice(['*', '.', '+'])
            self.stars.append(GameObject(x, y, char))
    
    def run(self):
        """Main game loop"""
        last_time = time.time()
        
        try:
            # Main game loop
            while self.running:
                current_time = time.time()
                
                # Check if terminal size has changed
                new_height, new_width = self.stdscr.getmaxyx()
                if new_height != self.height or new_width != self.width:
                    self.height, self.width = new_height, new_width
                    self.stdscr.clear()
                    self.stdscr.refresh()
                
                # Handle user input
                self.handle_input(current_time)
                
                # Update game state if not game over
                if not self.game_over:
                    self.update(current_time)
                    # Check if game_over flag was set during update
                    # (No action needed as we're not saving high scores)
                
                # Clear screen before rendering
                self.stdscr.clear()
                
                # Render the game
                self.render()
                
                # Control frame rate
                sleep_time = self.frame_time - (time.time() - current_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
                last_time = current_time
        except Exception as e:
            # Handle any unexpected errors
            self.cleanup()
            print(f"Game loop error: {e}")
    
    def cleanup(self):
        curses.nocbreak()
        self.stdscr.keypad(False)
        curses.echo()
        curses.endwin()


def display_title_screen(stdscr):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    title = [

        r"  / ___|| |_ __ _ _ _\ \      / /_ _ _ __ ___",
        r" \___ \| __/ _` | '__\ \ /\ / / _` | '__/ __| ",
        r"___) | || (_| | |   \ V  V / (_| | |  \__ \ ",
        r"|____/ \__\__,_|_|    \_/\_/ \__,_|_|  |___/",
        "",
        "             A TERMINAL SPACE ADVENTURE",
        "",
        "                 Press ENTER to start",
        "                  Press 'q' to quit",
    ]
    
    y_offset = (height - len(title)) // 2
    
    for i, line in enumerate(title):
        if y_offset + i < height:
            x_offset = (width - len(line)) // 2
            stdscr.addstr(y_offset + i, x_offset, line, curses.A_BOLD)
    
    stdscr.refresh()
    
    # Wait for player to press Enter or q
    while True:
        key = stdscr.getch()
        if key == 10 or key == 13:  # Enter key
            return True
        if key == ord('q'):
            return False


def display_instructions(stdscr):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    
    instructions = [
        "HOW TO PLAY",
        "",
        "Arrow keys: Move your spaceship",
        "Spacebar: Fire weapons",
        "q or ESC: Quit the game",
        "",
        "Power-ups:",
        "S - Shield (protects from one hit)",
        "F - Rapid Fire (shoot faster)",
        "I - Invincibility (temporarily immune to enemies)",
        "U - Ship Upgrade (instantly level up your ship)",
        "",
        "Ship Upgrades:",
        "Level 1 (100 pts): Dual firing (front and back)",
        "Level 2 (200 pts): Triple firing (adds diagonal shots)",
        "Level 3 (300 pts): Ultimate ship (increased firepower)",
        "",
        "Destroy enemy ships to earn points!",
        "Avoid collisions with enemy ships!",
        "",
        "Press ENTER to continue"
    ]
    
    y_offset = (height - len(instructions)) // 2
    
    for i, line in enumerate(instructions):
        if y_offset + i < height:
            x_offset = (width - len(line)) // 2
            stdscr.addstr(y_offset + i, x_offset, line)
    
    stdscr.refresh()
    
    # Wait for player to press Enter
    while True:
        key = stdscr.getch()
        if key == 10 or key == 13:  # Enter key
            return


def main(stdscr):
    # Initial setup
    curses.curs_set(0)  # Hide cursor
    stdscr.timeout(0)   # Non-blocking input
    
    # Display title screen
    if not display_title_screen(stdscr):
        return
    
    # Display game instructions
    display_instructions(stdscr)
    
    # Set up proper terminal modes
    stdscr.nodelay(True)  # Non-blocking input
    curses.cbreak()
    curses.noecho()
    stdscr.keypad(True)
    
    try:
        # Initialize and run the game
        game = StarWarsGame(stdscr)
        game.run()
    except Exception as e:
        # Handle any unexpected errors
        curses.endwin()
        print(f"Game crashed: {e}")
    finally:
        # Clean up curses settings
        game.cleanup() if 'game' in locals() else curses.endwin()


if __name__ == "__main__":
    # Use the curses wrapper to properly initialize and clean up the terminal
    curses.wrapper(main)
