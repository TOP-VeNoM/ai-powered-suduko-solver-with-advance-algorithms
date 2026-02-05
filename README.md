# AI-Powered Sudoku Solver & Generator

This project is a comprehensive Sudoku application developed in Python as part of my Artificial Intelligence course. The goal was to implement multiple AI algorithms for puzzle solving and generation, then build an intuitive graphical interface using Pygame.

The system features intelligent puzzle solving, generation, and an educational gameplay experience with advanced AI assistance.

## Project Features

### AI Algorithms
- **CSP Solver with AC-3** - Constraint Satisfaction Problem solver using Arc Consistency Algorithm #3
- **MRV Heuristic** - Minimum Remaining Values with degree heuristic tie-breaking
- **Forward Checking** - Early conflict detection during solving
- **Backtracking Solver** - Solution validation and counting
- **Genetic Puzzle Generator** - Difficulty-based puzzle creation
- **Minimax Warning System** - Move validation and logic error detection

### System Features
- **Intelligent Hint System** - Context-aware hints using CSP analysis
- **Real-time Conflict Detection** - Visual highlighting of rule violations
- **Multiple Difficulty Levels** - Easy, Medium, Hard, Expert
- **Score Tracking** - Time-based scoring with penalty/reward system
- **Undo/Redo Functionality** - Track and revert moves
- **Puzzle Creator Mode** - Build and validate custom puzzles
- **Solution Validation** - Check puzzle uniqueness and solvability
- **Game History Management** - View and track performance statistics

## Technologies Used

- **Python 3.8+**
  
### Core Python Libraries
- **`random`** - Random number generation and shuffling
- **`copy`** - Deep copying for state management during backtracking
- **`json`** - Data persistence for game history
- **`time`** - Game timer and performance tracking
- **`sys`** - System configuration and recursion management
- **`datetime`** - Timestamp generation for game records
- **`collections.deque`** - Efficient queue for AC-3 algorithm implementation

### External Library
- **`pygame`** - Complete GUI framework for game interface and interaction

## Learning Objectives

This project helped me practice and understand:
- Constraint Satisfaction Problems (CSP) and arc consistency
- Search algorithms and heuristic optimization
- Recursive backtracking with pruning techniques
- Game AI implementation and state management
- GUI development with Pygame and event-driven programming
- Modular software architecture and data persistence

---

## Contributors
- Abdullah Majeed
- Syed Turrab Haider
- Syed Yousaf Rasheed

---
