import pygame
import random
import copy
import json
import time
import sys
from datetime import datetime
from collections import deque

# -------------------------------------------------------------------------
# SYSTEM CONFIGURATION
# -------------------------------------------------------------------------
# Increase recursion depth to handle complex backtracking sequences
# required for difficult puzzle generation and solving.
sys.setrecursionlimit(2500)


# =========================================================================
# MODULE 1: CSP SOLVER (Constraint Satisfaction Problem)
# Uses AC-3 (Arc Consistency) + MRV (Minimum Remaining Values)
# =========================================================================
class CSPSolver:
    """
    Solves Sudoku using Constraint Satisfaction Problem techniques.
    It reduces the search space using AC-3 before attempting to solve.
    """

    def __init__(self, board):
        # Create a deep copy of the board to avoid modifying the original game state
        self.board = [row[:] for row in board]
        self.domains = self.initialize_domains()
        self.constraints = self.build_constraints()

    def initialize_domains(self):
        """
        Initializes the domain of possible values for each cell.
        - Empty cells (0) start with domains {1, 2, ..., 9}.
        - Filled cells start with a domain containing only their specific value.
        """
        domains = []
        for i in range(9):
            row = []
            for j in range(9):
                if self.board[i][j] == 0:
                    # Unknown cell: can be any number 1-9
                    row.append(set(range(1, 10)))
                else:
                    # Known cell: domain is restricted to the current value
                    row.append({self.board[i][j]})
            domains.append(row)
        return domains

    def build_constraints(self):
        """
        Builds the binary constraints for the Sudoku graph.
        A constraint exists between two cells if they cannot contain the same value.
        """
        constraints = []

        # 1. Row constraints: Every cell in a row interacts with every other cell in that row
        for i in range(9):
            for j in range(9):
                for k in range(j + 1, 9):
                    constraints.append(((i, j), (i, k)))

        # 2. Column constraints: Every cell in a column interacts with others in that column
        for j in range(9):
            for i in range(9):
                for k in range(i + 1, 9):
                    constraints.append(((i, j), (k, j)))

        # 3. Subgrid (3x3 Box) constraints
        for box_row in range(3):
            for box_col in range(3):
                # Collect all coordinates in the current 3x3 box
                cells = []
                for i in range(3):
                    for j in range(3):
                        cells.append((box_row * 3 + i, box_col * 3 + j))

                # Create constraints between all pairs in the box
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        constraints.append((cells[i], cells[j]))

        return constraints

    def ac3(self):
        """
        The AC-3 Algorithm (Arc Consistency Algorithm #3).
        Iteratively removes impossible values from domains based on constraints.
        Returns False if a domain becomes empty (unsolvable), True otherwise.
        """
        queue = deque(self.constraints)

        while queue:
            cell1, cell2 = queue.popleft()

            # If removing values from cell1's domain impacts consistency
            if self.revise(cell1, cell2):

                # If a domain becomes empty, no solution is possible
                if len(self.domains[cell1[0]][cell1[1]]) == 0:
                    return False

                # If the domain of cell1 changed, we must re-check its neighbors
                for constraint in self.constraints:
                    if constraint[1] == cell1 and constraint[0] != cell2:
                        queue.append(constraint)
        return True

    def revise(self, cell1, cell2):
        """
        Helper for AC-3. Removes values from cell1's domain that do not
        satisfy constraints with cell2.
        """
        r1, c1 = cell1
        r2, c2 = cell2
        revised = False
        to_remove = []

        # Check every value x in cell1's domain
        for val in self.domains[r1][c1]:
            satisfied = False

            # Is there any value y in cell2's domain such that x != y?
            for val2 in self.domains[r2][c2]:
                if val != val2:
                    satisfied = True
                    break

            # If no value in cell2 supports val in cell1, mark val for removal
            if not satisfied:
                to_remove.append(val)
                revised = True

        # Remove invalid values
        for val in to_remove:
            self.domains[r1][c1].discard(val)

        return revised

    def select_unassigned_variable(self):
        """
        MRV Heuristic: Selects the empty cell with the fewest remaining legal values.
        Tie-breaking is done using the Degree Heuristic (most constraints on remaining variables).
        """
        min_domain = 10
        candidates = []

        # Find cells with the smallest domain size
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0:
                    domain_size = len(self.domains[i][j])
                    if domain_size < min_domain:
                        min_domain = domain_size
                        candidates = [(i, j)]
                    elif domain_size == min_domain:
                        candidates.append((i, j))

        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Tie-breaker: Degree Heuristic
        max_degree = -1
        best_cell = candidates[0]

        for cell in candidates:
            degree = self.count_constraints(cell)
            if degree > max_degree:
                max_degree = degree
                best_cell = cell

        return best_cell

    def count_constraints(self, cell):
        """Counts how many unassigned neighbors a specific cell has."""
        count = 0
        for constraint in self.constraints:
            if cell in constraint:
                other = constraint[0] if constraint[1] == cell else constraint[1]
                if self.board[other[0]][other[1]] == 0:
                    count += 1
        return count

    def forward_check(self, row, col, value):
        """
        Updates domains of neighboring cells after assigning a value.
        Returns False if any neighbor's domain becomes empty.
        """
        # Create a snapshot of domains to restore if this path fails
        # Deep copy sets manually to ensure safety during recursion
        saved_domains = [[set(s) for s in row] for row in self.domains]

        # 1. Update Row Neighbors
        for j in range(9):
            if j != col:
                self.domains[row][j].discard(value)
                if len(self.domains[row][j]) == 0 and self.board[row][j] == 0:
                    self.domains = saved_domains
                    return False

        # 2. Update Column Neighbors
        for i in range(9):
            if i != row:
                self.domains[i][col].discard(value)
                if len(self.domains[i][col]) == 0 and self.board[i][col] == 0:
                    self.domains = saved_domains
                    return False

        # 3. Update Subgrid Neighbors
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if i != row or j != col:
                    self.domains[i][j].discard(value)
                    if len(self.domains[i][j]) == 0 and self.board[i][j] == 0:
                        self.domains = saved_domains
                        return False

        return True

    def solve(self):
        """
        Main recursive solver function combining AC-3 and Forward Checking.
        """
        # Step 1: Prune search space initially
        if not self.ac3():
            return False

        # Step 2: Auto-fill Single Candidates (Naked Singles)
        progress = True
        while progress:
            progress = False
            for i in range(9):
                for j in range(9):
                    if self.board[i][j] == 0 and len(self.domains[i][j]) == 1:
                        value = list(self.domains[i][j])[0]
                        self.board[i][j] = value
                        progress = True
                        if not self.forward_check(i, j, value):
                            return False

        # Step 3: Select next variable (MRV)
        cell = self.select_unassigned_variable()
        if cell is None:
            return True  # Board is full, solved!

        row, col = cell

        # Step 4: Try values in the domain
        for value in list(self.domains[row][col]):
            # Save state
            saved_board = [row[:] for row in self.board]
            saved_domains = [[set(s) for s in row] for row in self.domains]

            self.board[row][col] = value

            # Check constraints forward
            if self.forward_check(row, col, value):
                # Recursive call
                if self.solve():
                    return True

            # Backtrack: Restore state
            self.board = saved_board
            self.domains = saved_domains

        return False


# =========================================================================
# MODULE 2: BACKTRACKING SOLVER
# A standard DFS solver used for validation and solution counting.
# =========================================================================
class BacktrackingSolver:
    def __init__(self, board):
        self.board = [row[:] for row in board]
        self.solutions = []

    def is_valid(self, row, col, num):
        """Checks if placing 'num' at (row, col) is valid."""
        # Check row
        if num in self.board[row]:
            return False

        # Check column
        for i in range(9):
            if self.board[i][col] == num:
                return False

        # Check 3x3 subgrid
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if self.board[i][j] == num:
                    return False

        return True

    def solve(self, count_solutions=False, max_solutions=2):
        """
        Recursive backtracking function.
        Can stop after finding one solution, or continue to count multiple solutions
        to check for puzzle uniqueness.
        """
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0:
                    for num in range(1, 10):
                        if self.is_valid(i, j, num):
                            self.board[i][j] = num

                            if self.solve(count_solutions, max_solutions):
                                if count_solutions:
                                    # Store copy of solution found
                                    self.solutions.append([row[:] for row in self.board])
                                    if len(self.solutions) >= max_solutions:
                                        return True
                                    self.board[i][j] = 0
                                else:
                                    return True

                            self.board[i][j] = 0

                    return False

        return True

    def count_solutions(self):
        """Helper to count how many solutions exist (capped at 2 for uniqueness check)."""
        self.solutions = []
        self.solve(count_solutions=True, max_solutions=2)
        return len(self.solutions)


# =========================================================================
# MODULE 3: GENETIC PUZZLE GENERATOR
# Generates a full valid board, then removes numbers to create a puzzle.
# =========================================================================
class GeneticPuzzleGenerator:
    def __init__(self, difficulty='medium'):
        self.difficulty = difficulty
        self.clue_ranges = {
            'easy': (40, 48),
            'medium': (32, 38),
            'hard': (26, 30),
            'expert': (22, 25)
        }

    def generate_complete_board(self):
        """Generates a completely filled, valid Sudoku grid."""
        board = [[0] * 9 for _ in range(9)]
        self.fill_board(board)
        return board

    def fill_board(self, board):
        """Recursively fills the board with random numbers."""
        for i in range(9):
            for j in range(9):
                if board[i][j] == 0:
                    numbers = list(range(1, 10))
                    random.shuffle(numbers)

                    for num in numbers:
                        if self.is_valid_placement(board, i, j, num):
                            board[i][j] = num
                            if self.fill_board(board):
                                return True
                            board[i][j] = 0

                    return False
        return True

    def is_valid_placement(self, board, row, col, num):
        # Check row and column
        for i in range(9):
            if board[row][i] == num or board[i][col] == num:
                return False

        # Check subgrid
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if board[i][j] == num:
                    return False

        return True

    def create_puzzle(self, solution):
        """
        Removes numbers from a complete board to create the puzzle.
        Ensures the puzzle has a unique solution.
        """
        puzzle = [row[:] for row in solution]

        # Fallback for difficulty setting
        if self.difficulty not in self.clue_ranges:
            self.difficulty = 'medium'

        min_clues, max_clues = self.clue_ranges[self.difficulty]
        target_clues = random.randint(min_clues, max_clues)

        # Create a list of all coordinates and shuffle them
        cells = [(i, j) for i in range(9) for j in range(9)]
        random.shuffle(cells)

        removed = 0
        max_attempts = 150
        attempt = 0

        for row, col in cells:
            if removed >= 81 - target_clues:
                break

            attempt += 1
            if attempt > max_attempts:
                break

            backup = puzzle[row][col]
            puzzle[row][col] = 0

            # Optimizations for higher difficulties:
            # Skip expensive validation every single time to speed up generation,
            # but validate more strictly towards the end.
            should_validate = True
            if self.difficulty in ['hard', 'expert']:
                should_validate = (removed % 2 == 0) or (81 - removed <= target_clues + 5)

            is_unique = False
            if should_validate:
                is_unique = self.has_unique_solution_fast(puzzle)
            else:
                is_unique = True  # Optimistic assumption

            if is_unique:
                removed += 1
            else:
                # If removal breaks uniqueness, put the number back
                puzzle[row][col] = backup

        # Final rigid validation to ensure 100% correctness
        if not self.has_unique_solution_fast(puzzle):
            # If broken, fill a few holes back in to recover a valid state
            empty_cells = [(i, j) for i in range(9) for j in range(9) if puzzle[i][j] == 0]
            for i, j in empty_cells[:5]:
                puzzle[i][j] = solution[i][j]

        return puzzle

    def has_unique_solution_fast(self, puzzle):
        """
        Fast uniqueness check. Returns True if the puzzle has exactly one solution.
        """
        try:
            bt_solver = BacktrackingSolver([row[:] for row in puzzle])
            count = bt_solver.count_solutions()
            return count == 1
        except:
            return False

    def generate(self):
        """Main entry point to generate a puzzle and its solution."""
        solution = self.generate_complete_board()
        puzzle = self.create_puzzle(solution)
        return puzzle, solution


# =========================================================================
# MODULE 4: INTELLIGENT HINT SYSTEM
# Provides context-aware hints using CSP analysis.
# =========================================================================
class HintSystem:
    def __init__(self, board, solution):
        self.board = board
        self.solution = solution

    def get_single_candidate_hint(self):
        """Finds a cell where only one value is logically possible."""
        solver = CSPSolver(self.board)

        # If AC-3 fails, logic is broken
        if not solver.ac3():
            return None

        for i in range(9):
            for j in range(9):
                # If domain size is 1, it's a naked single
                if self.board[i][j] == 0 and len(solver.domains[i][j]) == 1:
                    value = list(solver.domains[i][j])[0]
                    return (i, j, value, "Single Candidate: Only one possible value")

        return None

    def get_mrv_hint(self):
        """Finds the cell with the fewest possibilities (harder hint)."""
        solver = CSPSolver(self.board)
        solver.ac3()

        cell = solver.select_unassigned_variable()
        if cell:
            row, col = cell
            value = self.solution[row][col]
            return (row, col, value, "MRV Strategy: Most constrained cell")

        return None

    def get_hint(self):
        """Prioritizes simple hints over complex ones."""
        hint = self.get_single_candidate_hint()
        if hint:
            return hint
        return self.get_mrv_hint()


# =========================================================================
# MODULE 5: MINIMAX MOVE WARNING SYSTEM
# Performs a look-ahead to warn players of logically fatal moves.
# =========================================================================
class MinimaxWarning:
    def __init__(self, board, solution):
        self.board = board
        self.solution = solution

    def evaluate_move(self, row, col, value):
        test_board = [row[:] for row in self.board]
        test_board[row][col] = value

        solver = CSPSolver(test_board)

        # If AC-3 returns False, this move makes the board unsolvable
        if not solver.ac3():
            return -99999
        return 0

    def warn_player(self, row, col, value):
        score = self.evaluate_move(row, col, value)
        if score < -5000:
            return True, "⚠️ Logic Error: This leads to a dead end!"
        return False, ""


# =========================================================================
# MODULE 6: LOCAL GAME HISTORY STORAGE
# Saves game statistics to a JSON file.
# =========================================================================
class GameHistory:
    def __init__(self, filename='sudoku_history.json'):
        self.filename = filename
        self.history = self.load_history()

    def load_history(self):
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_history(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.history, f, indent=2)
        except IOError:
            print("Warning: Could not save history file.")

    def add_game(self, game_data):
        game_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.history.append(game_data)
        self.save_history()


# =========================================================================
# MODULE 9: PUZZLE CREATOR & VALIDATOR
# Allows users to input custom puzzles and validate them.
# =========================================================================
class PuzzleCreator:
    def __init__(self):
        self.board = [[0] * 9 for _ in range(9)]

    def validate_puzzle(self):
        """
        Validates the user-created puzzle.
        Checks for:
        1. Immediate conflicts.
        2. Solvability (must have at least one solution).
        3. Uniqueness (must have exactly one solution).
        """
        # Step 1: Check for immediate rule violations
        for i in range(9):
            for j in range(9):
                if self.board[i][j] != 0:
                    num = self.board[i][j]
                    self.board[i][j] = 0  # Temporarily remove to check validity
                    if not self.is_valid_placement(i, j, num):
                        self.board[i][j] = num
                        return False, "Conflict detected in puzzle!"
                    self.board[i][j] = num

        # Step 2 & 3: Check solutions count
        solver = BacktrackingSolver([row[:] for row in self.board])
        count = solver.count_solutions()

        if count == 0:
            return False, "No solution exists!"
        elif count > 1:
            return False, f"Multiple ({count}) solutions exist!"

        return True, "Valid puzzle with unique solution! ✓"

    def is_valid_placement(self, row, col, num):
        # Check row
        for j in range(9):
            if self.board[row][j] == num:
                return False
        # Check column
        for i in range(9):
            if self.board[i][col] == num:
                return False
        # Check subgrid
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if self.board[i][j] == num:
                    return False
        return True

    def get_board_copy(self):
        return [row[:] for row in self.board]


# =========================================================================
# MODULE 7 & 8: PYGAME GUI + GAME LOGIC
# The main application class handling the loop, rendering, and inputs.
# =========================================================================
class SudokuGame:
    def __init__(self):
        pygame.init()
        self.WINDOW_WIDTH = 800
        self.WINDOW_HEIGHT = 650

        # Scroll variables
        self.scroll_offset = 0
        self.max_scroll = 0
        self.content_height = 700

        self.screen = pygame.display.set_mode((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
        pygame.display.set_caption("AI-Powered Sudoku")

        # Color Palette
        self.BG_COLOR = (245, 247, 250)
        self.GRID_BG = (255, 255, 255)
        self.BLACK = (30, 30, 30)
        self.GRAY = (180, 190, 200)
        self.PRIMARY = (79, 70, 229)
        self.PRIMARY_LIGHT = (129, 140, 248)
        self.PRIMARY_DARK = (55, 48, 163)
        self.SUCCESS = (34, 197, 94)
        self.SUCCESS_LIGHT = (134, 239, 172)
        self.ERROR = (239, 68, 68)
        self.ERROR_LIGHT = (254, 202, 202)
        self.WARNING = (251, 191, 36)
        self.SELECTION = (224, 231, 255)
        self.SELECTION_BORDER = (129, 140, 248)
        self.TEXT_GRAY = (100, 116, 139)
        self.SUBGRID_LINE = (203, 213, 225)
        self.CONFLICT_HIGHLIGHT = (255, 100, 100)
        self.CONFLICT_BORDER = (200, 50, 50)

        # Grid positioning
        self.GRID_SIZE = 450
        self.CELL_SIZE = self.GRID_SIZE // 9
        self.GRID_X = 30
        self.GRID_Y = 80

        # Fonts
        self.font_title = pygame.font.Font(None, 48)
        self.font_large = pygame.font.Font(None, 42)
        self.font_medium = pygame.font.Font(None, 32)
        self.font_small = pygame.font.Font(None, 22)
        self.font_tiny = pygame.font.Font(None, 18)

        # Game State Variables
        self.difficulty = 'medium'
        self.board = None
        self.solution = None
        self.initial_board = None
        self.selected = None
        self.mistakes = 0
        self.max_mistakes = 3
        self.hints_used = 0
        self.max_hints = 5
        self.score = 0
        self.game_over = False
        self.game_won = False
        self.timer_start = None
        self.elapsed_time = 0
        self.move_history = []

        # UI Message Timers
        self.hint_message = ""
        self.hint_timer = 0
        self.warning_message = ""
        self.warning_timer = 0

        # Creator Mode Variables
        self.creator_mode = False
        self.creator = PuzzleCreator()
        self.validation_message = ""
        self.validation_timer = 0

        # Systems
        self.conflicts = set()
        self.history = GameHistory()

        # Key Mapping for Numpad support
        self.key_mapping = {
            pygame.K_1: 1, pygame.K_2: 2, pygame.K_3: 3, pygame.K_4: 4, pygame.K_5: 5,
            pygame.K_6: 6, pygame.K_7: 7, pygame.K_8: 8, pygame.K_9: 9,
            pygame.K_KP1: 1, pygame.K_KP2: 2, pygame.K_KP3: 3, pygame.K_KP4: 4, pygame.K_KP5: 5,
            pygame.K_KP6: 6, pygame.K_KP7: 7, pygame.K_KP8: 8, pygame.K_KP9: 9
        }

        # Menu State
        self.show_menu = True
        self.show_history = False

        # Initialize (don't generate puzzle until menu selection)
        self.board = [[0] * 9 for _ in range(9)]
        self.solution = [[0] * 9 for _ in range(9)]
        self.initial_board = [[0] * 9 for _ in range(9)]

    def generate_new_puzzle(self):
        """Generates a fresh puzzle in a separate thread (simulated) and resets state."""
        self.screen.fill(self.BG_COLOR)
        text = self.font_large.render(f"Generating {self.difficulty} puzzle...", True, self.PRIMARY)
        self.screen.blit(text, text.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2)))
        pygame.display.flip()

        generator = GeneticPuzzleGenerator(self.difficulty)
        self.board, self.solution = generator.generate()
        self.initial_board = [row[:] for row in self.board]

        # Reset game stats
        self.selected = None
        self.mistakes = 0
        self.hints_used = 0
        self.score = 0
        self.game_over = False
        self.game_won = False
        self.timer_start = time.time()
        self.elapsed_time = 0
        self.move_history = []
        self.hint_message = ""
        self.warning_message = ""
        self.conflicts = set()
        self.creator_mode = False
        self.show_menu = False
        self.show_history = False

    def calculate_content_height(self):
        return self.GRID_Y + self.GRID_SIZE + 200

    def handle_scroll(self, y_offset):
        self.scroll_offset -= y_offset * 30
        self.scroll_offset = max(0, min(self.scroll_offset, self.max_scroll))

    def is_safe_move(self, row, col, num):
        """Checks if a move is valid within the current board state."""
        # Check Row
        for j in range(9):
            if j != col and self.board[row][j] == num:
                return False
        # Check Column
        for i in range(9):
            if i != row and self.board[i][col] == num:
                return False
        # Check Subgrid
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if (i != row or j != col) and self.board[i][j] == num:
                    return False
        return True

    def get_conflicts(self, row, col):
        """Identifies conflicting cells for a specific position."""
        conflicts = set()
        if self.board[row][col] == 0:
            return conflicts
        num = self.board[row][col]

        # Row conflicts
        for j in range(9):
            if j != col and self.board[row][j] == num:
                conflicts.add((row, j))

        # Column conflicts
        for i in range(9):
            if i != row and self.board[i][col] == num:
                conflicts.add((i, col))

        # Box conflicts
        box_row, box_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(box_row, box_row + 3):
            for j in range(box_col, box_col + 3):
                if (i != row or j != col) and self.board[i][j] == num:
                    conflicts.add((i, j))
        return conflicts

    def update_all_conflicts(self):
        """Refreshes the global set of all conflicting cells on the board."""
        self.conflicts = set()
        for i in range(9):
            for j in range(9):
                if self.board[i][j] != 0 and not self.is_safe_move(i, j, self.board[i][j]):
                    self.conflicts.add((i, j))
                    self.conflicts.update(self.get_conflicts(i, j))

    def toggle_creator_mode(self):
        """Switches between Play Mode and Puzzle Creator Mode."""
        self.creator_mode = not self.creator_mode
        if self.creator_mode:
            self.creator.board = [[0] * 9 for _ in range(9)]
            self.board = self.creator.board
            self.initial_board = [[0] * 9 for _ in range(9)]
            self.selected = None
            self.validation_message = "Creator Mode: Build your puzzle!"
            self.validation_timer = 120
            self.conflicts = set()
            self.show_menu = False
            self.show_history = False
        else:
            self.generate_new_puzzle()

    def validate_created_puzzle(self):
        """Validates the user's custom puzzle and starts the game if valid."""
        is_valid, message = self.creator.validate_puzzle()
        self.validation_message = message
        self.validation_timer = 180

        if is_valid:
            solver = BacktrackingSolver([row[:] for row in self.creator.board])
            solver.solve()
            self.solution = solver.board
            self.board = self.creator.get_board_copy()
            self.initial_board = self.creator.get_board_copy()

            # Start game with custom puzzle
            self.creator_mode = False
            self.mistakes = 0
            self.hints_used = 0
            self.score = 0
            self.game_over = False
            self.game_won = False
            self.timer_start = time.time()
            self.conflicts = set()

    def draw_rounded_rect(self, surface, color, rect, radius=10):
        """Utility to draw a rectangle with rounded corners."""
        x, y, width, height = rect
        pygame.draw.rect(surface, color, (x + radius, y, width - 2 * radius, height))
        pygame.draw.rect(surface, color, (x, y + radius, width, height - 2 * radius))
        pygame.draw.circle(surface, color, (x + radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + width - radius, y + radius), radius)
        pygame.draw.circle(surface, color, (x + radius, y + height - radius), radius)
        pygame.draw.circle(surface, color, (x + width - radius, y + height - radius), radius)

    def draw_button(self, text, x, y, width, height, color, text_color, hover=False):
        """Draws a clickable button with a shadow effect."""
        shadow_offset = 2
        # Draw shadow
        self.draw_rounded_rect(self.screen, (0, 0, 0, 30),
                               (x + shadow_offset, y + shadow_offset, width, height), 8)
        # Draw button body
        self.draw_rounded_rect(self.screen, color, (x, y, width, height), 8)

        text_surface = self.font_small.render(text, True, text_color)
        text_rect = text_surface.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surface, text_rect)
        return pygame.Rect(x, y, width, height)

    def draw_stat_card(self, label, value, x, y, width, icon=""):
        """Draws a statistic display card (Time, Score)."""
        height = 50
        self.draw_rounded_rect(self.screen, self.GRID_BG, (x, y, width, height), 8)
        label_text = self.font_tiny.render(label, True, self.TEXT_GRAY)
        self.screen.blit(label_text, (x + 12, y + 10))
        value_text = self.font_medium.render(str(value), True, self.BLACK)
        self.screen.blit(value_text, (x + 12, y + 24))

    def draw_menu(self):
        """Draws the main menu screen."""
        self.screen.fill(self.BG_COLOR)

        # Title with shadow effect
        title = self.font_title.render("SUDOKU AI", True, self.PRIMARY_DARK)
        shadow = self.font_title.render("SUDOKU AI", True, (200, 200, 210))
        title_rect = title.get_rect(center=(self.WINDOW_WIDTH // 2, 120))
        self.screen.blit(shadow, (title_rect.x + 3, title_rect.y + 3))
        self.screen.blit(title, title_rect)

        subtitle = self.font_small.render("Powered by CSP & Backtracking Algorithms", True, self.TEXT_GRAY)
        self.screen.blit(subtitle, subtitle.get_rect(center=(self.WINDOW_WIDTH // 2, 170)))

        # Menu buttons
        menu_x = (self.WINDOW_WIDTH - 400) // 2
        menu_y = 240
        button_height = 70
        button_spacing = 20

        menu_buttons = [
            ("🎮 New Game", self.PRIMARY, "Start a fresh puzzle"),
            ("🎨 Create Puzzle", self.SUCCESS, "Design your own challenge"),
            ("📊 Score History", self.WARNING, "View past performances"),
            ("❌ Exit", self.ERROR, "Close application")
        ]

        for i, (text, color, subtitle_text) in enumerate(menu_buttons):
            y = menu_y + i * (button_height + button_spacing)

            # Button shadow
            self.draw_rounded_rect(self.screen, (0, 0, 0, 30),
                                   (menu_x + 4, y + 4, 400, button_height), 12)
            # Button
            self.draw_rounded_rect(self.screen, color, (menu_x, y, 400, button_height), 12)

            # Button text
            text_surf = self.font_medium.render(text, True, (255, 255, 255))
            text_rect = text_surf.get_rect(center=(menu_x + 200, y + 22))
            self.screen.blit(text_surf, text_rect)

            # Subtitle
            sub_surf = self.font_tiny.render(subtitle_text, True, (255, 255, 255, 180))
            sub_rect = sub_surf.get_rect(center=(menu_x + 200, y + 48))
            self.screen.blit(sub_surf, sub_rect)

        # Footer
        footer = self.font_tiny.render("© 2025 Sudoku AI", True, self.TEXT_GRAY)
        self.screen.blit(footer, footer.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT - 30)))

    def draw_history(self):
        """Draws the score history screen."""
        self.screen.fill(self.BG_COLOR)

        # Header
        title = self.font_title.render("Score History", True, self.PRIMARY_DARK)
        self.screen.blit(title, title.get_rect(center=(self.WINDOW_WIDTH // 2, 50)))

        # Back button
        back_btn = self.draw_button("← Back to Menu", 30, 20, 150, 40, self.PRIMARY, (255, 255, 255))

        # Get history data
        history = self.history.history[-10:]  # Show last 10 games

        if not history:
            no_data = self.font_medium.render("No games played yet!", True, self.TEXT_GRAY)
            self.screen.blit(no_data, no_data.get_rect(center=(self.WINDOW_WIDTH // 2, self.WINDOW_HEIGHT // 2)))
        else:
            # Table header
            header_y = 120
            self.draw_rounded_rect(self.screen, self.PRIMARY, (40, header_y, 720, 40), 8)
            headers = ["Date", "Difficulty", "Time", "Score", "Status"]
            x_positions = [60, 220, 360, 490, 600]

            for i, header in enumerate(headers):
                h_text = self.font_small.render(header, True, (255, 255, 255))
                self.screen.blit(h_text, (x_positions[i], header_y + 12))

            # Table rows
            row_y = header_y + 50
            for game in reversed(history):
                # Alternate row colors
                row_color = self.GRID_BG if history.index(game) % 2 == 0 else (248, 250, 252)
                self.draw_rounded_rect(self.screen, row_color, (40, row_y, 720, 45), 6)

                # Date
                date_str = game.get('timestamp', 'N/A')[:10]
                date_text = self.font_tiny.render(date_str, True, self.BLACK)
                self.screen.blit(date_text, (x_positions[0], row_y + 15))

                # Difficulty
                diff_text = self.font_tiny.render(game.get('difficulty', 'N/A').upper(), True, self.PRIMARY)
                self.screen.blit(diff_text, (x_positions[1], row_y + 15))

                # Time
                time_sec = game.get('time', 0)
                time_str = f"{time_sec // 60:02d}:{time_sec % 60:02d}"
                time_text = self.font_tiny.render(time_str, True, self.BLACK)
                self.screen.blit(time_text, (x_positions[2], row_y + 15))

                # Score
                score_text = self.font_tiny.render(str(game.get('score', 0)), True, self.SUCCESS)
                self.screen.blit(score_text, (x_positions[3], row_y + 15))

                # Status
                completed = game.get('completed', False)
                status_str = "✓ Won" if completed else "✗ Lost"
                status_color = self.SUCCESS if completed else self.ERROR
                status_text = self.font_tiny.render(status_str, True, status_color)
                self.screen.blit(status_text, (x_positions[4], row_y + 15))

                row_y += 50

                # Stop if we run out of screen space
                if row_y > self.WINDOW_HEIGHT - 100:
                    break

            # Statistics summary
            total_games = len(self.history.history)
            completed_games = sum(1 for g in self.history.history if g.get('completed', False))
            win_rate = (completed_games / total_games * 100) if total_games > 0 else 0

            stats_y = self.WINDOW_HEIGHT - 80
            self.draw_rounded_rect(self.screen, self.PRIMARY_LIGHT, (40, stats_y, 720, 50), 8)

            stats_str = f"Total Games: {total_games}  |  Wins: {completed_games}  |  Win Rate: {win_rate:.1f}%"
            stats_text = self.font_small.render(stats_str, True, (255, 255, 255))
            self.screen.blit(stats_text, stats_text.get_rect(center=(self.WINDOW_WIDTH // 2, stats_y + 25)))

    def draw_grid(self):
        """Draws the main Sudoku grid lines."""
        shadow_offset = 4
        # Grid shadow
        self.draw_rounded_rect(self.screen, (200, 200, 200, 50),
                               (self.GRID_X + shadow_offset, self.GRID_Y + shadow_offset,
                                self.GRID_SIZE, self.GRID_SIZE), 12)
        # Grid background
        self.draw_rounded_rect(self.screen, self.GRID_BG,
                               (self.GRID_X, self.GRID_Y, self.GRID_SIZE, self.GRID_SIZE), 12)

        for i in range(10):
            thickness = 3 if i % 3 == 0 else 1
            color = self.BLACK if i % 3 == 0 else self.SUBGRID_LINE

            # Horizontal line
            pygame.draw.line(self.screen, color,
                             (self.GRID_X, self.GRID_Y + i * self.CELL_SIZE),
                             (self.GRID_X + self.GRID_SIZE, self.GRID_Y + i * self.CELL_SIZE), thickness)

            # Vertical line
            pygame.draw.line(self.screen, color,
                             (self.GRID_X + i * self.CELL_SIZE, self.GRID_Y),
                             (self.GRID_X + i * self.CELL_SIZE, self.GRID_Y + self.GRID_SIZE), thickness)

    def draw_conflict_highlights(self):
        """Highlights cells that are part of a conflict (Red)."""
        for (row, col) in self.conflicts:
            x = self.GRID_X + col * self.CELL_SIZE
            y = self.GRID_Y + row * self.CELL_SIZE
            conflict_surf = pygame.Surface((self.CELL_SIZE - 4, self.CELL_SIZE - 4))
            conflict_surf.set_alpha(80)
            conflict_surf.fill(self.CONFLICT_HIGHLIGHT)
            self.screen.blit(conflict_surf, (x + 2, y + 2))
            pygame.draw.rect(self.screen, self.CONFLICT_BORDER,
                             (x + 2, y + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4), 2)

    def draw_numbers(self):
        """Renders the numbers inside the grid."""
        for i in range(9):
            for j in range(9):
                if self.board[i][j] != 0:
                    x = self.GRID_X + j * self.CELL_SIZE + self.CELL_SIZE // 2
                    y = self.GRID_Y + i * self.CELL_SIZE + self.CELL_SIZE // 2

                    if self.initial_board[i][j] != 0:
                        color = self.BLACK  # Original numbers
                    else:
                        # User entered numbers (Red if invalid, Blue if valid)
                        color = self.ERROR if (i, j) in self.conflicts else self.PRIMARY

                    text = self.font_large.render(str(self.board[i][j]), True, color)
                    text_rect = text.get_rect(center=(x, y))
                    self.screen.blit(text, text_rect)

    def draw_selection(self):
        """Highlights the currently selected cell."""
        if self.selected:
            row, col = self.selected
            x = self.GRID_X + col * self.CELL_SIZE
            y = self.GRID_Y + row * self.CELL_SIZE

            # Cross-hair effect
            highlight_surf = pygame.Surface((self.CELL_SIZE, self.CELL_SIZE))
            highlight_surf.set_alpha(30)
            highlight_surf.fill(self.PRIMARY_LIGHT)
            for i in range(9):
                self.screen.blit(highlight_surf, (self.GRID_X + i * self.CELL_SIZE, y))
                self.screen.blit(highlight_surf, (x, self.GRID_Y + i * self.CELL_SIZE))

            # Selected cell border
            pygame.draw.rect(self.screen, self.SELECTION,
                             (x + 2, y + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4))
            pygame.draw.rect(self.screen, self.SELECTION_BORDER,
                             (x + 2, y + 2, self.CELL_SIZE - 4, self.CELL_SIZE - 4), 3)

    def draw_ui(self):
        """Draws the right-hand control panel."""
        title = self.font_title.render("AI Sudoku", True, self.PRIMARY_DARK)
        title_rect = title.get_rect(center=(self.WINDOW_WIDTH // 2, 35))
        self.screen.blit(title, title_rect)
        # Back to Menu button (top-left)
        self.draw_button("← Menu", 20, 20, 100, 35, self.TEXT_GRAY, (255, 255, 255))
        panel_x = self.GRID_X + self.GRID_SIZE + 20
        panel_width = 260

        # Update timer
        if self.timer_start and not self.game_over and not self.game_won and not self.creator_mode:
            self.elapsed_time = int(time.time() - self.timer_start)

        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Draw Stats
        self.draw_stat_card("TIME", time_str, panel_x, 90, 120)
        self.draw_stat_card("SCORE", str(self.score), panel_x + 130, 90, 120)

        # Draw Mistakes indicator
        mistakes_y = 155
        self.draw_rounded_rect(self.screen, self.GRID_BG, (panel_x, mistakes_y, panel_width, 50), 8)
        self.screen.blit(self.font_tiny.render("MISTAKES", True, self.TEXT_GRAY), (panel_x + 12, mistakes_y + 10))
        for i in range(self.max_mistakes):
            color = self.ERROR if i < self.mistakes else self.GRAY
            filled = 0 if i < self.mistakes else 2
            pygame.draw.circle(self.screen, color, (panel_x + 15 + i * 30, mistakes_y + 32), 8, filled)

        # Draw Hints indicator
        hints_y = 220
        self.draw_rounded_rect(self.screen, self.GRID_BG, (panel_x, hints_y, panel_width, 50), 8)
        self.screen.blit(self.font_tiny.render("HINTS", True, self.TEXT_GRAY), (panel_x + 12, hints_y + 10))
        for i in range(self.max_hints):
            color = self.SUCCESS if i < (self.max_hints - self.hints_used) else self.GRAY
            filled = 0 if i < (self.max_hints - self.hints_used) else 2
            pygame.draw.circle(self.screen, color, (panel_x + 15 + i * 25, hints_y + 32), 7, filled)

        # Draw Mode/Difficulty Badge
        diff_y = 285
        badge_color = self.SUCCESS if self.creator_mode else self.PRIMARY_LIGHT
        self.draw_rounded_rect(self.screen, badge_color, (panel_x, diff_y, panel_width, 40), 8)
        txt = "MODE: CREATOR" if self.creator_mode else f"LEVEL: {self.difficulty.upper()}"
        d_text = self.font_small.render(txt, True, (255, 255, 255))
        self.screen.blit(d_text, d_text.get_rect(center=(panel_x + panel_width // 2, diff_y + 20)))

        # Draw Buttons
        button_y = 340
        button_height = 45
        button_spacing = 12

        if self.creator_mode:
            buttons = [("✏️ Exit Creator", self.SUCCESS), ("✓ Validate Puzzle", self.WARNING)]
        else:
            buttons = [
                ("🎮 New Game", self.PRIMARY),
                ("💡 Hint", self.SUCCESS),
                ("🔍 Solve", self.WARNING),
                ("↩️ Undo", self.TEXT_GRAY),
                ("🎨 Create Puzzle", self.PRIMARY)
            ]

        for i, (text, color) in enumerate(buttons):
            y = button_y + i * (button_height + button_spacing)
            self.draw_button(text, panel_x, y, panel_width, button_height, color, (255, 255, 255))

        # Draw Difficulty Selector (Only in Play Mode)
        if not self.creator_mode:
            diff_selector_y = button_y + len(buttons) * (button_height + button_spacing) + 20
            self.screen.blit(self.font_tiny.render("DIFFICULTY", True, self.TEXT_GRAY), (panel_x, diff_selector_y - 20))
            diffs = ['easy', 'medium', 'hard', 'expert']
            for i, diff in enumerate(diffs):
                bx = panel_x + (i % 2) * ((panel_width - 9) // 2 + 3)
                by = diff_selector_y + (i // 2) * (43)
                col = self.PRIMARY if diff == self.difficulty else self.GRID_BG
                txt_col = (255, 255, 255) if diff == self.difficulty else self.TEXT_GRAY
                self.draw_rounded_rect(self.screen, col, (bx, by, (panel_width - 9) // 2, 35), 6)
                t_surf = self.font_tiny.render(diff.upper(), True, txt_col)
                self.screen.blit(t_surf, t_surf.get_rect(center=(bx + (panel_width - 9) // 4, by + 17)))

        # Draw Notifications (Messages fade out via timer)
        msg_y = self.GRID_Y + self.GRID_SIZE + 15

        if self.hint_message and self.hint_timer > 0:
            self.draw_rounded_rect(self.screen, self.SUCCESS_LIGHT, (self.GRID_X, msg_y, 450, 35), 8)
            t = self.font_small.render(self.hint_message, True, self.SUCCESS)
            self.screen.blit(t, t.get_rect(center=(self.GRID_X + 225, msg_y + 17)))
            self.hint_timer -= 1
            msg_y += 45

        if self.warning_message and self.warning_timer > 0:
            self.draw_rounded_rect(self.screen, self.ERROR_LIGHT, (self.GRID_X, msg_y, 450, 35), 8)
            t = self.font_small.render(self.warning_message, True, self.ERROR)
            self.screen.blit(t, t.get_rect(center=(self.GRID_X + 225, msg_y + 17)))
            self.warning_timer -= 1
            msg_y += 45

        if self.validation_message and self.validation_timer > 0:
            msg_color = self.SUCCESS_LIGHT if "✓" in self.validation_message else self.ERROR_LIGHT
            text_color = self.SUCCESS if "✓" in self.validation_message else self.ERROR
            self.draw_rounded_rect(self.screen, msg_color, (self.GRID_X, msg_y, 450, 35), 8)
            t = self.font_small.render(self.validation_message, True, text_color)
            self.screen.blit(t, t.get_rect(center=(self.GRID_X + 225, msg_y + 17)))
            self.validation_timer -= 1

    def handle_menu_click(self, pos):
        """Handles clicks on the main menu."""
        x, y = pos
        menu_x = (self.WINDOW_WIDTH - 400) // 2
        menu_y = 240
        button_height = 70
        button_spacing = 20

        # Check which button was clicked
        for i in range(4):
            btn_y = menu_y + i * (button_height + button_spacing)
            if menu_x <= x <= menu_x + 400 and btn_y <= y <= btn_y + button_height:
                if i == 0:  # New Game
                    self.generate_new_puzzle()
                elif i == 1:  # Create Puzzle
                    self.toggle_creator_mode()
                elif i == 2:  # Score History
                    self.show_history = True
                    self.show_menu = False
                elif i == 3:  # Exit
                    return True  # Signal to quit
                break
        return False

    def handle_history_click(self, pos):
        """Handles clicks on the history screen."""
        x, y = pos
        # Back button
        if 30 <= x <= 180 and 20 <= y <= 60:
            self.show_history = False
            self.show_menu = True

    def handle_click(self, pos):
        """Processes mouse clicks for grid selection and UI buttons."""
        x, y = pos
        y += self.scroll_offset
        # Check Back to Menu button (adjust for scroll)
        if 20 <= x <= 120 and 20 <= y <= 55:
            self.show_menu = True
            self.show_history = False
            return
        # Check Grid Click
        if (self.GRID_X <= x <= self.GRID_X + self.GRID_SIZE and
                self.GRID_Y <= y <= self.GRID_Y + self.GRID_SIZE):
            col = (x - self.GRID_X) // self.CELL_SIZE
            row = (y - self.GRID_Y) // self.CELL_SIZE
            self.selected = (row, col)
            return

        # Check UI Button Clicks
        panel_x = self.GRID_X + self.GRID_SIZE + 20
        panel_width = 260
        button_y = 340
        button_height = 45
        button_spacing = 12

        if self.creator_mode:
            # Creator Mode Buttons
            if panel_x <= x <= panel_x + panel_width and button_y <= y <= button_y + button_height:
                self.toggle_creator_mode()
                return
            validate_y = button_y + button_height + button_spacing
            if panel_x <= x <= panel_x + panel_width and validate_y <= y <= validate_y + button_height:
                self.validate_created_puzzle()
                return
        else:
            # Play Mode Buttons
            buttons = [self.generate_new_puzzle, self.give_hint, self.solve_puzzle,
                       self.undo_move, self.toggle_creator_mode]
            for i, action in enumerate(buttons):
                btn_y = button_y + i * (button_height + button_spacing)
                if panel_x <= x <= panel_x + panel_width and btn_y <= y <= btn_y + button_height:
                    action()
                    return

            # Difficulty Selectors
            diff_selector_y = button_y + len(buttons) * (button_height + button_spacing) + 20
            diffs = ['easy', 'medium', 'hard', 'expert']
            for i, diff in enumerate(diffs):
                bx = panel_x + (i % 2) * ((panel_width - 9) // 2 + 3)
                by = diff_selector_y + (i // 2) * (43)
                if bx <= x <= bx + ((panel_width - 9) // 2) and by <= y <= by + 35:
                    self.difficulty = diff
                    self.generate_new_puzzle()
                    return

    def handle_key(self, key):
        """Processes keyboard input for number entry and navigation."""
        if self.game_over or self.game_won:
            if key == pygame.K_SPACE:
                self.generate_new_puzzle()
            return

        if self.selected:
            row, col = self.selected

            # Standard Numbers + Numpad
            num = self.key_mapping.get(key)

            if self.creator_mode:
                if key in [pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_0]:
                    self.creator.board[row][col] = 0
                    self.update_all_conflicts()
                elif num is not None:
                    self.creator.board[row][col] = num
                    self.update_all_conflicts()
            else:
                if key in [pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_0]:
                    # Only allow deleting user-placed numbers
                    if self.initial_board[row][col] == 0:
                        self.board[row][col] = 0
                        self.update_all_conflicts()
                elif num is not None:
                    self.make_move(row, col, num)

            # Arrow Key Navigation
            if key == pygame.K_UP and row > 0:
                self.selected = (row - 1, col)
            elif key == pygame.K_DOWN and row < 8:
                self.selected = (row + 1, col)
            elif key == pygame.K_LEFT and col > 0:
                self.selected = (row, col - 1)
            elif key == pygame.K_RIGHT and col < 8:
                self.selected = (row, col + 1)

    def make_move(self, row, col, num):
        """Attempts to place a number on the board."""
        if self.initial_board[row][col] != 0:
            return

        # Optimization: Only check "Minimax" warning if move is valid locally.
        if self.is_safe_move(row, col, num):
            warning_system = MinimaxWarning(self.board, self.solution)
            is_bad, message = warning_system.warn_player(row, col, num)
            if is_bad:
                self.warning_message = message
                self.warning_timer = 120

        # Record move for undo history
        old_value = self.board[row][col]
        self.move_history.append((row, col, old_value))

        self.board[row][col] = num
        self.update_all_conflicts()

        # Check against solution
        if num == self.solution[row][col]:
            self.hint_message = ""
            self.score += 5
            if self.check_win():
                self.game_won = True
                self.score += 1000
                self.save_game_history(completed=True)
        else:
            self.mistakes += 1
            self.score -= 5
            self.hint_message = "⚠️ Conflict!"
            self.hint_timer = 60
            if self.mistakes >= self.max_mistakes:
                self.game_over = True
                self.save_game_history(completed=False)

    def check_win(self):
        """Checks if the board is completely filled with no conflicts."""
        for i in range(9):
            for j in range(9):
                if self.board[i][j] == 0 or not self.is_safe_move(i, j, self.board[i][j]):
                    return False
        return True

    def give_hint(self):
        """Provides a hint to the user."""
        if self.hints_used >= self.max_hints:
            self.hint_message = "No hints left!"
            self.hint_timer = 120
            return

        hint = HintSystem(self.board, self.solution).get_hint()
        if hint:
            r, c, v, m = hint
            self.board[r][c] = v
            self.hints_used += 1
            self.score -= 3
            self.hint_message = m
            self.hint_timer = 180
            self.selected = (r, c)
            self.update_all_conflicts()
            if self.check_win():
                self.game_won = True
                self.save_game_history(True)

    def solve_puzzle(self):
        """Instantly solves the puzzle using the stored solution."""
        self.board = [row[:] for row in self.solution]
        self.game_won = True
        self.update_all_conflicts()
        self.save_game_history(completed=True)

    def undo_move(self):
        """Reverts the last move made by the user."""
        if not self.move_history:
            self.hint_message = "Nothing to undo"
            self.hint_timer = 60
            return

        r, c, old_val = self.move_history.pop()
        current_val = self.board[r][c]

        # Adjust score based on whether the undone move was a mistake
        if current_val != 0:
            if not self.is_safe_move(r, c, current_val):
                self.mistakes = max(0, self.mistakes - 1)
                self.score += 5
            else:
                self.score -= 5

        self.board[r][c] = old_val
        self.hint_message = "Move undone"
        self.hint_timer = 60
        self.selected = (r, c)
        self.update_all_conflicts()

    def save_game_history(self, completed):
        data = {
            'difficulty': self.difficulty,
            'completed': completed,
            'time': self.elapsed_time,
            'score': self.score,
            'mistakes': self.mistakes,
            'hints': self.hints_used
        }
        self.history.add_game(data)

    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        running = True

        while running:
            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if self.show_menu:
                        if self.handle_menu_click(event.pos):
                            running = False
                    elif self.show_history:
                        self.handle_history_click(event.pos)
                    elif not self.game_over and not self.game_won:
                        self.handle_click(event.pos)
                elif event.type == pygame.MOUSEWHEEL:
                    if not self.show_menu and not self.show_history:
                        self.handle_scroll(event.y)
                elif event.type == pygame.KEYDOWN:
                    if not self.show_menu and not self.show_history:
                        self.handle_key(event.key)

            # Scroll Calculation
            self.content_height = self.calculate_content_height()
            self.max_scroll = max(0, self.content_height - self.WINDOW_HEIGHT)

            # Check what to render
            if self.show_menu:
                self.draw_menu()
            elif self.show_history:
                self.draw_history()
            else:
                # Drawing on scrollable surface
                scroll_surface = pygame.Surface((self.WINDOW_WIDTH, self.content_height))
                scroll_surface.fill(self.BG_COLOR)

                original_screen = self.screen
                self.screen = scroll_surface

                # Draw game elements
                self.draw_grid()
                self.draw_conflict_highlights()
                self.draw_selection()
                self.draw_numbers()
                self.draw_ui()

                # Blit scroll surface to main window
                self.screen = original_screen
                self.screen.fill(self.BG_COLOR)
                self.screen.blit(scroll_surface, (0, -self.scroll_offset))

                # Game Over / Win Overlay
                if self.game_over or self.game_won:
                    overlay = pygame.Surface((self.WINDOW_WIDTH, self.WINDOW_HEIGHT))
                    overlay.set_alpha(200)
                    overlay.fill((20, 20, 30))
                    self.screen.blit(overlay, (0, 0))

                    mx, my = (self.WINDOW_WIDTH - 400) // 2, (self.WINDOW_HEIGHT - 280) // 2
                    self.draw_rounded_rect(self.screen, self.GRID_BG, (mx, my, 400, 280), 16)

                    t_str = "🎉 Victory!" if self.game_won else "Game Over"
                    c_str = self.SUCCESS if self.game_won else self.ERROR
                    t = self.font_title.render(t_str, True, c_str)
                    self.screen.blit(t, t.get_rect(center=(self.WINDOW_WIDTH // 2, my + 50)))

                    s_txt = f"Score: {self.score}" if self.game_won else "Too many mistakes!"
                    s = self.font_medium.render(s_txt, True, self.PRIMARY if self.game_won else self.TEXT_GRAY)
                    self.screen.blit(s, s.get_rect(center=(self.WINDOW_WIDTH // 2, my + 110)))

                    r = self.font_small.render("Press SPACE for New Game", True, self.PRIMARY)
                    self.screen.blit(r, r.get_rect(center=(self.WINDOW_WIDTH // 2, my + 210)))

            pygame.display.flip()
            clock.tick(60)

        pygame.quit()


if __name__ == "__main__":
    game = SudokuGame()
    game.run()