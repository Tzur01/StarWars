# Star Wars Terminal Game

A fast-paced space shooter game that runs entirely in your terminal. Fly your spaceship, shoot down enemies, collect power-ups, and survive as long as possible in this ASCII-art space adventure!



## Features

- Terminal-based gameplay with colorful ASCII graphics
- Multiple enemy types with unique movement patterns:
  - Basic enemies that fly straight
  - Zigzag enemies that move in patterns
  - Hunter enemies that track your movement
- Progressive difficulty system that increases challenge over time
- Power-up system with multiple effects
- Ship upgrade system based on score
- Collision detection and game-over mechanics
- Smooth animations despite terminal limitations

## Installation

1. Clone this repository:
   ```
   [git clone https://github.com/Tzur01/starwars_game.git](https://github.com/Tzur01/StarWars.git)
   cd starwars_game
   ```

2. No additional dependencies required! The game uses only Python's built-in libraries.

## How to Play

Run the game with Python 3:
```
python3 main.py
```

### Controls
- **Arrow keys**: Move your spaceship
- **Spacebar**: Fire weapons
- **Q or ESC**: Quit the game
- **R**: Restart after game over

## Game Mechanics

### Power-ups

The game features various power-ups that give temporary advantages:

- **⊕ Shield (S)**: Absorbs one enemy collision before deactivating
- **↯ Rapid Fire (F)**: Increases fire rate for a limited time
- **★ Invincibility (I)**: Makes you temporarily immune to enemy ships

Power-ups last for a limited time (shown by a countdown timer).

### Ship Upgrades

Your ship automatically upgrades as your score increases:

- **Level 1** (100 points): Improved ship design
- **Level 2** (200 points): Triple-shot capability (forward and diagonal)
- **Level 3** (300 points): Ultimate ship with maximum firepower

### Progressive Difficulty

The game features a sophisticated difficulty scaling system:

- **Early Game** (first 30 seconds): Very gentle difficulty for new players
- **Mid Game** (30-60 seconds): Gradually increasing challenge
- **Late Game** (after 60 seconds): Full difficulty with maximum enemy speed and spawn rates

Difficulty affects:
- Enemy movement speed
- Enemy spawn rate
- Type of enemies that appear
- Power-up frequency
- Enemy movement patterns

The difficulty is calculated based on both playtime and score, ensuring a balanced challenge regardless of player skill level.

## Game Objective

Survive as long as possible while scoring points by destroying enemy ships. The game ends when an enemy ship collides with your ship without protection.

## Development

This game was developed as a terminal-based space shooter using Python's curses library. Feel free to modify and expand upon the game!

## License

MIT License - Feel free to use, modify, and distribute this code.
