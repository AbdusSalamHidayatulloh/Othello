import pygame
import random
import io
import csv
import os
import time
from contextlib import redirect_stdout
from statistics import mean

# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def directions(row, col, minRow=0, minCol=0, maxRow=7, maxCol=7):
    """Return the neighbouring cells (up to 8) that are inside the board."""
    validDirections = []
    # Cells above
    if row != minRow: validDirections.append((row - 1, col))
    if row != minRow and col != minCol: validDirections.append((row - 1, col - 1))
    if row != minRow and col != maxCol: validDirections.append((row - 1, col + 1))
    # Cells below
    if row != maxRow: validDirections.append((row + 1, col))
    if row != maxRow and col != minCol: validDirections.append((row + 1, col - 1))
    if row != maxRow and col != maxCol: validDirections.append((row + 1, col + 1))
    # Cells left and right
    if col != minCol: validDirections.append((row, col - 1))
    if col != maxCol: validDirections.append((row, col + 1))
    return validDirections


def loadImages(path, size):
    """Load an image file and scale it to the given size."""
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(img, size)


def loadSpriteSheet(sheet, col, row, newSize, size):
    """Cut one tile out of a sprite sheet and scale it.
    sheet   = the full sprite sheet image
    col,row = which tile (counted in tiles, not pixels)
    newSize = final size on screen
    size    = size of one tile inside the sheet (32x32)
    """
    image = pygame.Surface(size).convert_alpha()
    image.blit(sheet, (0, 0), (col * size[0], row * size[1], size[0], size[1]))
    image = pygame.transform.scale(image, newSize)
    image.set_colorkey('Black')
    return image


# =====================================================
# BUTTON CLASS (used by menu, difficulty and game over screens)
# =====================================================

class Button:
    def __init__(self, text, center, size=(300, 60)):
        self.text = text
        self.rect = pygame.Rect(0, 0, size[0], size[1])
        self.rect.center = center                      # place the button by its centre

    def draw(self, window, font, mousePos):
        # Slightly lighter colour when the mouse hovers over the button
        hovering = self.rect.collidepoint(mousePos)
        color = (130, 90, 45) if hovering else (90, 60, 30)
        pygame.draw.rect(window, color, self.rect, border_radius=8)
        pygame.draw.rect(window, (230, 200, 150), self.rect, 3, border_radius=8)  # border
        label = font.render(self.text, True, 'White')
        window.blit(label, label.get_rect(center=self.rect.center))

    def isClicked(self, mousePos):
        return self.rect.collidepoint(mousePos)


# =====================================================
# AI AGENTS
# =====================================================
# Both agents have the same interface so the game can use either one:
#   getMove(gridLogic, player) -> (row, col) or None
# `rules` is the Grid object, so the agents can reuse:
#   rules.findAvailMoves(grid, player)   -> list of legal (row, col)
#   rules.swappableTiles(row, col, grid, player) -> tokens that would flip

class GBFSAgent:
    """Easy difficulty: Greedy Best-First Search."""

    # Corners location on the board for corner advantage
    CORNERS = [(0,0), (0,7), (7,0), (7,7)]

    # Weight for the priority on what should be took into factor
    WC, WM, WF= 25, 5, 2

    def __init__(self, rules):
        self.rules = rules

    # Step 
    def simulateMove(self, gridLogic, move, player):
        row, col = move
        toFlip = self.rules.swappableTiles(row, col, gridLogic, player)
        newGrid = [rowGrid[:] for rowGrid in gridLogic]
        newGrid[row][col] = player
        for(rowSelected, columnSelected) in toFlip:
            newGrid[rowSelected][columnSelected] = player
        return newGrid, len(toFlip)

    # Step 4
    def cornerScore(self, grid, player):
        # player = CPU, -player = lawan (user)
        cpuCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == player)
        userCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == -player)
        return cpuCorner - userCorner

    def mobilityScore(self, grid, player):
        # player = CPU, -player = lawan (user)
        cpuMobility = len(self.rules.findAvailMoves(grid, player))
        userMobility = len(self.rules.findAvailMoves(grid, -player))
        return cpuMobility - userMobility

    def heuristicScore(self, grid, flipCount, player):
        C = self.cornerScore(grid, player)
        M = self.mobilityScore(grid, player)
        F = flipCount
        return self.WC * C + self.WM * M + self.WF * F

    # From previous step, make a move
    # Update will be done when it exits the 
    def getMove(self, gridLogic, player):
        moves = self.rules.findAvailMoves(gridLogic, player)
        print(f'Existing moves: {moves}')
        if not moves:
            return None

        scored = []
        for move in moves:
            newGrid, flipCount = self.simulateMove(gridLogic, move, player)
            h = self.heuristicScore(newGrid, flipCount, player)
            scored.append((h, move))

        bestHeuristicScore = max(h for h, _ in scored)
        bestMoves = [m for h, m in scored if h == bestHeuristicScore]
        return random.choice(bestMoves)


class AlphaBetaAgent:
    """Hard difficulty: Minimax with Alpha-Beta Pruning.

    Board values: 1 = white, -1 = black, 0 = empty.
    This agent can play either colour, but the game's default AI is black (-1).
    It never modifies the live board during its search.
    """

    # Used ONLY to search promising moves first (move ordering).
    # This can improve the number of alpha-beta cutoffs.
    POSITION_WEIGHTS = (
        (120, -20,  20,   5,   5,  20, -20, 120),
        (-20, -40,  -5,  -5,  -5,  -5, -40, -20),
        ( 20,  -5,  15,   3,   3,  15,  -5,  20),
        (  5,  -5,   3,   3,   3,   3,  -5,   5),
        (  5,  -5,   3,   3,   3,   3,  -5,   5),
        ( 20,  -5,  15,   3,   3,  15,  -5,  20),
        (-20, -40,  -5,  -5,  -5,  -5, -40, -20),
        (120, -20,  20,   5,   5,  20, -20, 120),
    )
    CORNERS = ((0, 0), (0, 7), (7, 0), (7, 7))

    def __init__(self, rules, depth=4):
        self.rules = rules
        self.depth = depth
        self.nodesExplored = 0
        self.leavesEvaluated = 0
        self.pruningCount = 0
        self.executionTime = 0.0
        self.lastScore = None

    def _simulate(self, board, move, player):
        """Create a *copy* of the board after a legal move."""
        row, col = move
        new_board = [line[:] for line in board]
        flips = self.rules.swappableTiles(row, col, new_board, player)
        new_board[row][col] = player
        for r, c in flips:
            new_board[r][c] = player
        return new_board

    def _ordered_moves(self, moves):
        """Explore corners and generally strong squares earlier."""
        return sorted(
            moves,
            key=lambda move: self.POSITION_WEIGHTS[move[0]][move[1]],
            reverse=True,
        )

    def _evaluate(self, board, ai_player):
        """Evaluate a position from the perspective of the AI.

        Matches the three terms of the proposal's linear weighted heuristic:
        corner control, mobility and disc difference.
        """
        self.leavesEvaluated += 1
        human = -ai_player
        ai_moves = self.rules.findAvailMoves(board, ai_player)
        human_moves = self.rules.findAvailMoves(board, human)
        disc_difference = sum(cell * ai_player for line in board for cell in line)

        # When neither side has legal moves, the game has ended.
        # Wins/losses should outweigh ordinary positional heuristics.
        if not ai_moves and not human_moves:
            if disc_difference > 0:
                return 100000 + disc_difference
            if disc_difference < 0:
                return -100000 + disc_difference
            return 0

        corner_difference = sum(board[r][c] * ai_player for r, c in self.CORNERS)
        mobility_difference = len(ai_moves) - len(human_moves)
        return 100 * corner_difference + 10 * mobility_difference + disc_difference

    def _minimax(self, board, current_player, ai_player, depth, alpha, beta):
        """Return the best score assuming both players make optimal moves."""
        self.nodesExplored += 1

        if depth == 0:
            return self._evaluate(board, ai_player)

        moves = self.rules.findAvailMoves(board, current_player)
        if not moves:
            # Othello rule: a player must PASS when no legal move exists.
            opponent_moves = self.rules.findAvailMoves(board, -current_player)
            if not opponent_moves:
                return self._evaluate(board, ai_player)  # game is over
            # A pass doesn't place a disc, so it doesn't consume a search ply.
            return self._minimax(board, -current_player, ai_player, depth, alpha, beta)

        if current_player == ai_player:  # MAX
            best = float('-inf')
            for move in self._ordered_moves(moves):
                next_board = self._simulate(board, move, current_player)
                score = self._minimax(next_board, -current_player, ai_player, depth - 1, alpha, beta)
                best = max(best, score)
                alpha = max(alpha, best)
                if alpha >= beta:
                    self.pruningCount += 1
                    break
            return best

        # MIN: assume the opponent chooses the most damaging reply.
        best = float('inf')
        for move in self._ordered_moves(moves):
            next_board = self._simulate(board, move, current_player)
            score = self._minimax(next_board, -current_player, ai_player, depth - 1, alpha, beta)
            best = min(best, score)
            beta = min(beta, best)
            if alpha >= beta:
                self.pruningCount += 1
                break
        return best

    def getMove(self, gridLogic, player):
        """Return the best legal (row, col), or None when the AI must pass."""
        from time import perf_counter

        started = perf_counter()
        self.nodesExplored = 1  # include the root position
        self.leavesEvaluated = 0
        self.pruningCount = 0
        self.lastScore = None

        moves = self.rules.findAvailMoves(gridLogic, player)
        if not moves:
            self.executionTime = perf_counter() - started
            return None

        best_move = None
        best_score = float('-inf')
        alpha, beta = float('-inf'), float('inf')

        for move in self._ordered_moves(moves):
            next_board = self._simulate(gridLogic, move, player)
            score = self._minimax(next_board, -player, player, self.depth - 1, alpha, beta)
            if score > best_score:
                best_score = score
                best_move = move
            alpha = max(alpha, best_score)

        self.executionTime = perf_counter() - started
        self.lastScore = best_score
        print(
            f'[Alpha-Beta] move={best_move} | depth={self.depth} | '
            f'score={best_score} | time={self.executionTime:.3f}s | '
            f'nodes={self.nodesExplored} | evaluated={self.leavesEvaluated} | '
            f'cutoffs={self.pruningCount}'
        )
        return best_move


# =====================================================
# BENCHMARK RUNNER (Alpha-Beta vs GBFS, tanpa animasi)
# =====================================================

class BenchmarkRunner:
    """Menjalankan game AlphaBeta vs GBFS satu langkah per panggilan step().
    Dipakai oleh menu Benchmark di main.py DAN oleh benchmark.py.
    `rules` = objek apa pun yang punya findAvailMoves, swappableTiles, countTokens
    (Grid asli atau HeadlessRules di benchmark.py)."""

    RESULT_DIR = 'benchmark_result'     # nama folder tempat file CSV disimpan

    def __init__(self, rules, totalGames, depth):
        self.rules = rules
        self.totalGames = totalGames
        self.depth = depth
        self.gameIndex = 0              # jumlah game yang sudah selesai
        self.games = []                 # hasil per game
        self.moves = []                 # data per langkah: (algoritma, detik, node, cutoff)
        self.finished = False
        self.startGame()

    def startGame(self):
        # Selang-seling siapa yang jalan duluan (putih) supaya seimbang
        self.abFirst = (self.gameIndex % 2 == 0)
        ab = ('AlphaBeta', AlphaBetaAgent(self.rules, self.depth))
        gb = ('GBFS', GBFSAgent(self.rules))
        self.agents = {1: ab, -1: gb} if self.abFirst else {1: gb, -1: ab}

        # Papan awal (terpisah dari papan game yang asli)
        self.board = [[0] * 8 for _ in range(8)]
        self.board[3][3] = self.board[4][4] = 1
        self.board[3][4] = self.board[4][3] = -1
        self.player = 1

    def discCount(self):
        """Jumlah cakram di papan game yang sedang berjalan (4 - 64)."""
        white, black = self.rules.countTokens(self.board)
        return white + black

    def gameProgress(self):
        """Progress game yang sedang berjalan: 0.0 (4 cakram awal) sampai 1.0 (papan penuh)."""
        return (self.discCount() - 4) / 60

    def step(self):
        """Mainkan satu langkah (atau pass / akhiri game)."""
        rules, board = self.rules, self.board
        moves = rules.findAvailMoves(board, self.player)

        if not moves:
            if not rules.findAvailMoves(board, -self.player):
                self.endGame()                      # kedua pemain tidak bisa jalan
            else:
                self.player = -self.player          # pass
            return

        name, agent = self.agents[self.player]
        start = time.perf_counter()
        with redirect_stdout(io.StringIO()):        # sembunyikan print bawaan agent
            move = agent.getMove(board, self.player)
        elapsed = time.perf_counter() - start

        if name == 'AlphaBeta':
            nodes, cutoffs = agent.nodesExplored, agent.pruningCount
        else:
            nodes, cutoffs = len(moves), 0          # GBFS: node = jumlah kandidat yang dievaluasi
        self.moves.append((name, elapsed, nodes, cutoffs))

        row, col = move
        flips = rules.swappableTiles(row, col, board, self.player)
        board[row][col] = self.player
        for r, c in flips:
            board[r][c] = self.player
        self.player = -self.player

    def endGame(self):
        white, black = self.rules.countTokens(self.board)
        abDiscs, gbDiscs = (white, black) if self.abFirst else (black, white)
        if abDiscs > gbDiscs:   winner = 'AlphaBeta'
        elif gbDiscs > abDiscs: winner = 'GBFS'
        else:                   winner = 'Draw'

        self.games.append({'game': self.gameIndex + 1, 'abFirst': self.abFirst,
                           'abDiscs': abDiscs, 'gbDiscs': gbDiscs, 'winner': winner})
        self.gameIndex += 1

        if self.gameIndex >= self.totalGames:
            self.finished = True
        else:
            self.startGame()

    def summaryLines(self):
        """Ringkasan untuk 4 metrik di proposal (dipakai untuk layar dan console)."""
        n = len(self.games)
        abWins = sum(g['winner'] == 'AlphaBeta' for g in self.games)
        gbWins = sum(g['winner'] == 'GBFS' for g in self.games)
        draws = n - abWins - gbWins

        lines = [
            f'Alpha-Beta (depth {self.depth}) vs GBFS | {n} games',
            f'Win rate   : AB {abWins} ({abWins / n * 100:.1f}%) | '
            f'GBFS {gbWins} ({gbWins / n * 100:.1f}%) | Draw {draws} ({draws / n * 100:.1f}%)',
        ]
        for label, flag in (('AB first ', True), ('AB second', False)):
            sub = [g for g in self.games if g['abFirst'] == flag]
            if sub:
                w = sum(g['winner'] == 'AlphaBeta' for g in sub)
                lines.append(f'{label}  : AB won {w}/{len(sub)}')

        margins = [abs(g['abDiscs'] - g['gbDiscs']) for g in self.games]
        signed = [g['abDiscs'] - g['gbDiscs'] for g in self.games]
        lines.append(f'Avg margin : {mean(margins):.2f} discs (winner - loser)')
        lines.append(f'Avg AB-GBFS: {mean(signed):+.2f} discs')

        times = {k: [m[1] * 1000 for m in self.moves if m[0] == k] for k in ('AlphaBeta', 'GBFS')}
        nodes = {k: [m[2] for m in self.moves if m[0] == k] for k in ('AlphaBeta', 'GBFS')}
        cuts = [m[3] for m in self.moves if m[0] == 'AlphaBeta']
        lines.append(f'Time/move  : AB {mean(times["AlphaBeta"]):.2f} ms (max {max(times["AlphaBeta"]):.1f}) | '
                     f'GBFS {mean(times["GBFS"]):.2f} ms (max {max(times["GBFS"]):.1f})')
        lines.append(f'Nodes/move : AB {mean(nodes["AlphaBeta"]):.1f} (max {max(nodes["AlphaBeta"])}) | '
                     f'GBFS {mean(nodes["GBFS"]):.1f} (max {max(nodes["GBFS"])})')
        lines.append(f'AB cutoffs : {mean(cuts):.1f} per move')
        return lines

    @classmethod
    def ensureResultDir(cls):
        """Buat folder hasil kalau belum ada, lalu return path-nya.
        Folder ada di sebelah main.py (bukan di working directory),
        jadi lokasinya selalu sama walau game dijalankan dari folder lain."""
        baseDir = os.path.dirname(os.path.abspath(__file__))
        folder = os.path.join(baseDir, cls.RESULT_DIR)
        os.makedirs(folder, exist_ok=True)      # tidak error kalau folder sudah ada
        return folder

    def saveCsv(self):
        folder = self.ensureResultDir()         # dibuat otomatis kalau belum ada / terhapus

        gamesFile = os.path.join(folder, f'hasil_games_depth{self.depth}.csv')
        movesFile = os.path.join(folder, f'hasil_moves_depth{self.depth}.csv')

        with open(gamesFile, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=self.games[0].keys())
            w.writeheader()
            w.writerows(self.games)
        with open(movesFile, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['algoritma', 'waktu_detik', 'node', 'cutoff'])
            w.writerows(self.moves)
        return gamesFile, movesFile


# =====================================================
# MAIN GAME CLASS
# =====================================================

class Othello:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1100, 800))
        pygame.display.set_caption('Othello')
        self.clock = pygame.time.Clock()

        # Buat folder benchmark_result otomatis saat game dibuka (kalau belum ada)
        BenchmarkRunner.ensureResultDir()

        # Fonts
        self.titleFont = pygame.font.Font(None, 110)
        self.bigFont = pygame.font.Font(None, 64)
        self.font = pygame.font.Font(None, 40)
        self.smallFont = pygame.font.Font(None, 30)

        # Player values used in the logic grid: 1 = white, -1 = black, 0 = empty
        self.player1 = 1
        self.player2 = -1
        self.currentPlayer = 1          # white starts

        self.rows = 8
        self.columns = 8

        # The Grid handles the board, tokens, rules and animation
        self.grid = Grid(self.rows, self.columns, (80, 80), self)

        # Small token icons for the score panel
        self.iconWhite = pygame.transform.scale(self.grid.whitetoken, (50, 50))
        self.iconBlack = pygame.transform.scale(self.grid.blacktoken, (50, 50))

        # ---- Game state ----
        # state: 'menu' | 'difficulty' | 'playing' | 'paused' | 'gameover'
        #        | 'benchmark' | 'benchrun' | 'benchresult'
        self.state = 'menu'
        self.mode = None                # '1v1' or 'ai'
        self.difficulty = None          # 'easy' (GBFS) or 'hard' (Alpha-Beta)
        self.agent = None               # the AI object (only in 'ai' mode)
        self.aiPlayer = -1              # the computer plays black, the human plays white
        self.lastMoveTime = 0           # used to add a short pause before the AI moves
        self.message = ''               # info text (e.g. "Black has no moves")

        # ---- Buttons for each screen ----
        cx = 550                        # horizontal centre of the window
        self.menuButtons = {
            '1v1':       Button('1 vs 1',        (cx, 380)),
            'ai':        Button('1 vs Computer', (cx, 470)),
            'benchmark': Button('Benchmark',     (cx, 560)),
            'quit':      Button('Quit',          (cx, 650)),
        }
        self.difficultyButtons = {
            'easy': Button('Easy (GBFS)',        (cx, 380)),
            'hard': Button('Hard (Alpha-Beta)',  (cx, 470)),
            'back': Button('Back',               (cx, 560)),
        }
        self.gameOverButtons = {
            'retry': Button('Retry',     (cx, 450)),
            'menu':  Button('Main Menu', (cx, 530)),
        }
        # Tombol Pause di panel kanan saat bermain, dan menu pause-nya
        self.pauseButton = Button('Pause', (950, 730), (240, 60))
        self.pauseButtons = {
            'resume':  Button('Resume',    (cx, 380)),
            'restart': Button('Restart',   (cx, 460)),
            'menu':    Button('Main Menu', (cx, 540)),
        }

        # ---- Benchmark ----
        self.benchDepth = 3
        self.benchGames = 100
        self.depthOptions = [2, 3, 4]
        self.gameOptions = [4, 10, 50, 100]     # 4 = tes cepat
        self.benchmark = None                   # BenchmarkRunner yang sedang jalan
        self.benchLines = []                    # teks hasil untuk layar result

        self.benchButtons = {
            'depth': Button(f'Depth: {self.benchDepth}',  (cx, 340)),
            'games': Button(f'Games: {self.benchGames}',  (cx, 420)),
            'start': Button('Start',                      (cx, 530)),
            'back':  Button('Back',                       (cx, 610)),
        }
        self.benchRunButtons = {'cancel': Button('Cancel', (950, 700), (240, 60))}
        self.benchResultButtons = {'back': Button('Main Menu', (cx, 700))}

        self.RUN = True

    # ---------- Main loop ----------

    def run(self):
        """Main game loop: input -> update -> draw, repeated forever."""
        while self.RUN:
            self.input()
            self.update()
            self.draw()
            self.clock.tick(60)         # limit to 60 FPS

    # ---------- Starting / ending a game ----------

    def startGame(self, mode, difficulty=None):
        """Reset the board and begin a new game with the given settings."""
        self.mode = mode
        self.difficulty = difficulty
        self.grid.reset()
        self.currentPlayer = 1
        self.message = ''
        self.lastMoveTime = pygame.time.get_ticks()

        if mode == 'ai':
            if difficulty == 'easy':
                self.agent = GBFSAgent(self.grid)
            else:
                self.agent = AlphaBetaAgent(self.grid)
        else:
            self.agent = None

        self.state = 'playing'

    def nextTurn(self):
        """Switch player. Skip a player who has no moves. End the game if nobody can move."""
        grid = self.grid
        self.currentPlayer *= -1

        if not grid.findAvailMoves(grid.gridLogic, self.currentPlayer):
            skipped = self.playerName(self.currentPlayer)
            self.currentPlayer *= -1                    # give the turn back

            if not grid.findAvailMoves(grid.gridLogic, self.currentPlayer):
                self.state = 'gameover'                 # neither player can move
                white, black = grid.countTokens(grid.gridLogic)
                print(f'[Game Over] White {white} - {black} Black')
            else:
                self.message = f'{skipped} has no moves, turn skipped'
                print(f'[Skip] {self.message}')
        else:
            self.message = ''

    def playerName(self, player):
        return 'White' if player == 1 else 'Black'

    def logMove(self, player, row, col, flipped, white, black):
        """Print the chosen move, the flipped tokens and the new score to the console."""
        colLetter = 'ABCDEFGH'[col]                  # same A-H labels as printGameLogicBoard
        who = self.playerName(player)
        if self.mode == 'ai' and player == self.aiPlayer:
            who += ' (Computer)'
        print(f'[Move] {who} -> {colLetter}{row} (row={row}, col={col}) | flipped {len(flipped)}: {flipped}')
        print(f'[Score] White {white} - {black} Black')

    # ---------- Input ----------

    def input(self):
        """Handle window close and mouse clicks for every screen."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.RUN = False

            # ESC: pause / resume saat bermain
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == 'playing':
                    self.pauseGame()
                elif self.state == 'paused':
                    self.resumeGame()

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Right click: print the logic board in the terminal (for debugging)
                if event.button == 3 and self.state == 'playing':
                    self.grid.printGameLogicBoard()

                if event.button == 1:
                    if self.state == 'menu':
                        self.clickMenu(event.pos)
                    elif self.state == 'difficulty':
                        self.clickDifficulty(event.pos)
                    elif self.state == 'playing':
                        # Tombol Pause dicek dulu supaya tetap bisa diklik saat giliran komputer
                        if self.pauseButton.isClicked(event.pos):
                            self.pauseGame()
                        else:
                            self.clickBoard(event.pos)
                    elif self.state == 'paused':
                        self.clickPause(event.pos)
                    elif self.state == 'gameover':
                        self.clickGameOver(event.pos)
                    elif self.state == 'benchmark':
                        self.clickBenchmark(event.pos)
                    elif self.state == 'benchrun':
                        self.clickBenchRun(event.pos)
                    elif self.state == 'benchresult':
                        self.clickBenchResult(event.pos)

    def clickMenu(self, pos):
        if self.menuButtons['1v1'].isClicked(pos):
            self.startGame('1v1')
        elif self.menuButtons['ai'].isClicked(pos):
            self.state = 'difficulty'
        elif self.menuButtons['benchmark'].isClicked(pos):
            self.state = 'benchmark'
        elif self.menuButtons['quit'].isClicked(pos):
            self.RUN = False

    def clickDifficulty(self, pos):
        if self.difficultyButtons['easy'].isClicked(pos):
            self.startGame('ai', 'easy')
        elif self.difficultyButtons['hard'].isClicked(pos):
            self.startGame('ai', 'hard')
        elif self.difficultyButtons['back'].isClicked(pos):
            self.state = 'menu'

    def pauseGame(self):
        self.state = 'paused'

    def resumeGame(self):
        self.state = 'playing'
        self.lastMoveTime = pygame.time.get_ticks()     # komputer menunggu lagi 600 ms setelah resume

    def clickPause(self, pos):
        if self.pauseButtons['resume'].isClicked(pos):
            self.resumeGame()
        elif self.pauseButtons['restart'].isClicked(pos):
            self.startGame(self.mode, self.difficulty)   # mulai ulang dengan pengaturan yang sama
        elif self.pauseButtons['menu'].isClicked(pos):
            self.state = 'menu'

    def clickGameOver(self, pos):
        if self.gameOverButtons['retry'].isClicked(pos):
            self.startGame(self.mode, self.difficulty)   # same settings as before
        elif self.gameOverButtons['menu'].isClicked(pos):
            self.state = 'menu'

    def clickBenchmark(self, pos):
        b = self.benchButtons
        if b['depth'].isClicked(pos):
            # Klik untuk ganti depth (2 -> 3 -> 4 -> 2 ...)
            i = (self.depthOptions.index(self.benchDepth) + 1) % len(self.depthOptions)
            self.benchDepth = self.depthOptions[i]
            b['depth'].text = f'Depth: {self.benchDepth}'
        elif b['games'].isClicked(pos):
            # Klik untuk ganti jumlah game (4 -> 10 -> 50 -> 100 -> 4 ...)
            i = (self.gameOptions.index(self.benchGames) + 1) % len(self.gameOptions)
            self.benchGames = self.gameOptions[i]
            b['games'].text = f'Games: {self.benchGames}'
        elif b['start'].isClicked(pos):
            self.benchmark = BenchmarkRunner(self.grid, self.benchGames, self.benchDepth)
            self.state = 'benchrun'
        elif b['back'].isClicked(pos):
            self.state = 'menu'

    def clickBenchRun(self, pos):
        if self.benchRunButtons['cancel'].isClicked(pos):
            self.benchmark = None
            self.state = 'menu'

    def clickBenchResult(self, pos):
        if self.benchResultButtons['back'].isClicked(pos):
            self.state = 'menu'

    def clickBoard(self, pos):
        """Left click on the board: try to play a move."""
        # Ignore clicks while it is the computer's turn
        if self.mode == 'ai' and self.currentPlayer == self.aiPlayer:
            return

        # Convert pixel position to board cell (board starts at (80, 80), cells are 80x80)
        col = (pos[0] - 80) // 80
        row = (pos[1] - 80) // 80

        validCells = self.grid.findAvailMoves(self.grid.gridLogic, self.currentPlayer)
        if (row, col) in validCells:
            self.playMove(row, col)
        else:
            print(f'[Invalid] Click at row={row}, col={col} is not a legal move')

    # ---------- Playing a move ----------

    def playMove(self, row, col):
        """Place a token, flip the captured tokens (with animation), switch turn."""
        grid = self.grid
        mover = self.currentPlayer                   # remember who moved, because nextTurn() switches it

        # 1. Find which tokens will flip BEFORE placing the new token
        toFlip = grid.swappableTiles(row, col, grid.gridLogic, self.currentPlayer)

        # 2. Place the new token
        grid.insertToken(grid.gridLogic, self.currentPlayer, row, col)

        # 3. Animate the flip (all flipped tokens at the same time)
        grid.animateTransitions(toFlip, self.currentPlayer)

        # 4. Update the logic grid and the Token objects to the new colour
        for (r, c) in toFlip:
            grid.gridLogic[r][c] *= -1
            grid.tokens[(r, c)].player *= -1

        # 5. Print the result to the console
        white, black = grid.countTokens(grid.gridLogic)
        self.logMove(mover, row, col, toFlip, white, black)

        # 6. Next player's turn (also handles skipped turns and game over)
        self.nextTurn()
        self.lastMoveTime = pygame.time.get_ticks()

    # ---------- Update ----------

    def update(self):
        """Runs every frame: computer's turn, and the benchmark when it is running."""
        if self.state == 'playing' and self.mode == 'ai' and self.currentPlayer == self.aiPlayer:
            # Wait 600 ms so the computer's move doesn't happen instantly
            if pygame.time.get_ticks() - self.lastMoveTime >= 600:
                move = self.agent.getMove(self.grid.gridLogic, self.aiPlayer)
                if move is not None:
                    self.playMove(move[0], move[1])

        elif self.state == 'benchrun':
            # Mainkan langkah benchmark sebanyak mungkin dalam ~30 ms, lalu gambar ulang layar
            start = pygame.time.get_ticks()
            while not self.benchmark.finished and pygame.time.get_ticks() - start < 30:
                self.benchmark.step()

            if self.benchmark.finished:
                self.benchLines = self.benchmark.summaryLines()
                gamesFile, movesFile = self.benchmark.saveCsv()
                # Tampilkan folder + nama file saja (bukan path lengkap) supaya muat di layar
                self.benchLines.append(
                    f'CSV: {BenchmarkRunner.RESULT_DIR}/{os.path.basename(gamesFile)}, '
                    f'{os.path.basename(movesFile)}'
                )
                for line in self.benchLines:        # cetak juga ke console
                    print(line)
                print(f'Path lengkap: {os.path.dirname(gamesFile)}')
                print()
                self.state = 'benchresult'

    # ---------- Drawing ----------

    def draw(self):
        """Clear the screen, draw whichever screen is active, show it."""
        mousePos = pygame.mouse.get_pos()

        if self.state == 'menu':
            self.drawMenu(mousePos)
        elif self.state == 'difficulty':
            self.drawDifficulty(mousePos)
        elif self.state == 'benchmark':
            self.drawBenchmark(mousePos)
        elif self.state == 'benchrun':
            self.drawBenchRun(mousePos)
        elif self.state == 'benchresult':
            self.drawBenchResult(mousePos)
        else:
            # 'playing', 'paused' and 'gameover' all show the board
            self.screen.fill((0, 0, 0))
            self.grid.drawGrid(self.screen)
            self.drawScorePanel()
            if self.state == 'paused':
                self.drawPause(mousePos)
            elif self.state == 'gameover':
                self.drawGameOver(mousePos)

        pygame.display.update()

    def drawCentered(self, text, font, y, color='White'):
        """Draw text horizontally centred at height y."""
        label = font.render(text, True, color)
        self.screen.blit(label, label.get_rect(center=(550, y)))

    def drawMenu(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('OTHELLO', self.titleFont, 220, (230, 200, 150))
        for button in self.menuButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawDifficulty(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Choose Difficulty', self.bigFont, 250, (230, 200, 150))
        for button in self.difficultyButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawBenchmark(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Benchmark', self.bigFont, 200, (230, 200, 150))
        self.drawCentered('Alpha-Beta vs GBFS (tanpa animasi)', self.smallFont, 260)
        for button in self.benchButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawBenchRun(self, mousePos):
        bm = self.benchmark
        done, total = bm.gameIndex, bm.totalGames

        # Papan game benchmark yang sedang berjalan (tanpa animasi flip)
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.grid.gridBg, (0, 0))
        for r in range(8):
            for c in range(8):
                if bm.board[r][c] != 0:
                    img = self.grid.whitetoken if bm.board[r][c] == 1 else self.grid.blacktoken
                    self.screen.blit(img, (80 + c * 80, 80 + r * 80))

        # Panel kanan
        white, black = self.grid.countTokens(bm.board)
        pygame.draw.rect(self.screen, (35, 25, 15), (800, 0, 300, 800))
        pygame.draw.line(self.screen, (230, 200, 150), (800, 0), (800, 800), 3)

        self.screen.blit(self.smallFont.render(f'Benchmark: Depth {bm.depth}', True, (230, 200, 150)), (830, 65))
        self.screen.blit(self.font.render(f'Game {min(done + 1, total)} / {total}', True, 'White'), (830, 110))
        pygame.draw.rect(self.screen, (230, 200, 150), (830, 150, 240, 20), 3)
        pygame.draw.rect(self.screen, (130, 90, 45), (833, 153, int(234 * done / total), 14))

        whiteName = 'Alpha-Beta' if bm.abFirst else 'GBFS'
        blackName = 'GBFS' if bm.abFirst else 'Alpha-Beta'
        self.screen.blit(self.smallFont.render(f'White: {whiteName}', True, 'White'), (830, 200))
        self.screen.blit(self.iconWhite, (830, 240))
        self.screen.blit(self.bigFont.render(f'{white}', True, 'White'), (910, 248))
        self.screen.blit(self.smallFont.render(f'Black: {blackName}', True, 'White'), (830, 310))
        self.screen.blit(self.iconBlack, (830, 350))
        self.screen.blit(self.bigFont.render(f'{black}', True, 'White'), (910, 358))

        # Progress game yang sedang berjalan (jumlah cakram di papan: 4 -> 64)
        gameProgress = max(0.0, min(1.0, bm.gameProgress()))
        self.screen.blit(self.smallFont.render(f'Current game: {int(gameProgress * 100)}%', True, 'White'), (830, 440))
        pygame.draw.rect(self.screen, (230, 200, 150), (830, 470, 240, 20), 3)
        pygame.draw.rect(self.screen, (90, 150, 90), (833, 473, int(234 * gameProgress), 14))

        abWins = sum(g['winner'] == 'AlphaBeta' for g in bm.games)
        gbWins = sum(g['winner'] == 'GBFS' for g in bm.games)
        self.screen.blit(self.smallFont.render('So far', True, (230, 200, 150)), (830, 540))
        self.screen.blit(self.smallFont.render(f'Alpha-Beta: {abWins}', True, 'White'), (830, 575))
        self.screen.blit(self.smallFont.render(f'GBFS: {gbWins}', True, 'White'), (830, 610))

        for button in self.benchRunButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawBenchResult(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Benchmark Result', self.bigFont, 90, (230, 200, 150))
        for i, line in enumerate(self.benchLines):
            label = self.smallFont.render(line, True, 'White')
            self.screen.blit(label, (100, 170 + i * 42))
        for button in self.benchResultButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawScorePanel(self):
        """Right side panel (x = 800 to 1100): mode, current turn, and token counts."""
        white, black = self.grid.countTokens(self.grid.gridLogic)

        # Panel background
        pygame.draw.rect(self.screen, (35, 25, 15), (800, 0, 300, 800))
        pygame.draw.line(self.screen, (230, 200, 150), (800, 0), (800, 800), 3)

        # Mode text
        if self.mode == '1v1':
            modeText = '1 vs 1'
        else:
            modeText = 'Computer: ' + ('Easy' if self.difficulty == 'easy' else 'Hard')
        self.screen.blit(self.font.render(modeText, True, (230, 200, 150)), (830, 90))

        # Score
        self.screen.blit(self.font.render('SCORE', True, 'White'), (830, 200))
        self.screen.blit(self.iconWhite, (830, 250))
        self.screen.blit(self.bigFont.render(f'{white}', True, 'White'), (910, 258))
        self.screen.blit(self.iconBlack, (830, 330))
        self.screen.blit(self.bigFont.render(f'{black}', True, 'White'), (910, 338))

        # Whose turn is it?
        if self.state == 'playing':
            self.screen.blit(self.font.render('Turn:', True, 'White'), (830, 450))
            icon = self.iconWhite if self.currentPlayer == 1 else self.iconBlack
            self.screen.blit(icon, (910, 438))
            if self.mode == 'ai' and self.currentPlayer == self.aiPlayer:
                self.screen.blit(self.smallFont.render('Computer thinking...', True, 'White'), (830, 510))

        # Info message (e.g. skipped turn)
        if self.message:
            for i, part in enumerate(self.message.split(', ')):    # 2 baris supaya muat di panel
                self.screen.blit(self.smallFont.render(part, True, (255, 200, 100)), (815, 600 + i * 30))

        # Tombol Pause (hanya saat bermain; saat paused/gameover tombol lain yang tampil)
        if self.state == 'playing':
            self.pauseButton.draw(self.screen, self.font, pygame.mouse.get_pos())

    def drawPause(self, mousePos):
        """Dark overlay + 'PAUSED' + Resume / Restart / Main Menu buttons."""
        overlay = pygame.Surface((1100, 800), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        self.drawCentered('PAUSED', self.titleFont, 230, (230, 200, 150))
        for button in self.pauseButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawGameOver(self, mousePos):
        """Dark overlay + result text + Retry / Main Menu buttons."""
        white, black = self.grid.countTokens(self.grid.gridLogic)

        # Semi-transparent dark layer over the whole window
        overlay = pygame.Surface((1100, 800), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))

        if white > black:
            result = 'White wins!'
        elif black > white:
            result = 'Black wins!'
        else:
            result = "It's a draw!"

        self.drawCentered('GAME OVER', self.titleFont, 220, (230, 200, 150))
        self.drawCentered(result, self.bigFont, 310)
        self.drawCentered(f'White {white}  -  {black} Black', self.font, 370)
        for button in self.gameOverButtons.values():
            button.draw(self.screen, self.font, mousePos)


# =====================================================
# GRID CLASS (board visuals + game rules)
# =====================================================

class Grid:
    def __init__(self, rows, columns, size, main):
        self.GAME = main          # reference back to the Othello object
        self.y = rows
        self.x = columns
        self.size = size          # size of one cell in pixels, e.g. (80, 80)

        # Token images
        self.whitetoken = loadImages('assets/WhiteToken.png', size)
        self.blacktoken = loadImages('assets/BlackToken.png', size)
        # Flip animation frames (3 frames each)
        self.transitionWhiteToBlack = [loadImages(f'assets/BlackToWhite{i}.png', self.size) for i in range(1, 4)]
        self.transitionBlackToWhite = [loadImages(f'assets/WhiteToBlack{i}.png', self.size) for i in range(1, 4)]

        # Wood background tiles, then the full board background image
        self.bg = self.loadBackGroundImages()
        self.gridBg = self.createbgimg()

        # While True, the white "available move" markers are hidden
        self.animating = False

        # tokens: dictionary {(row, col): Token} -> what gets drawn on screen
        self.tokens = {}
        # gridLogic: 8x8 list of 0 / 1 / -1 -> what the rules use
        self.gridLogic = self.regenGrid(self.y, self.x)

    # ---------- Background ----------

    def loadBackGroundImages(self):
        """Cut every tile out of the wood sprite sheet and name it like 'A0', 'B1', ..."""
        alpha = 'ABCDEFGHI'
        spriteSheet = pygame.image.load('assets/wood.png').convert_alpha()
        imageDict = {}
        for i in range(3):          # sprite sheet rows
            for j in range(7):      # sprite sheet columns
                imageDict[alpha[j] + str(i)] = loadSpriteSheet(spriteSheet, j, i, self.size, (32, 32))
        return imageDict

    def createbgimg(self):
        """Build one big background image: a 10x10 layout (8x8 board + border)."""
        gridBg = [
            ['C0', 'D0', 'D0', 'D0', 'D0', 'D0', 'D0', 'D0', 'D0', 'E0'],  # top border
            ['C1', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'E1'],  # board rows
            ['C1', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'E1'],  # A/B alternate
            ['C1', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'E1'],  # like a chessboard
            ['C1', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'E1'],
            ['C1', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'E1'],
            ['C1', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'E1'],
            ['C1', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'E1'],
            ['C1', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'B0', 'A0', 'E1'],
            ['C2', 'D2', 'D2', 'D2', 'D2', 'D2', 'D2', 'D2', 'D2', 'E2'],  # bottom border
        ]
        image = pygame.Surface((10 * self.size[0], 10 * self.size[1]))
        for j, row in enumerate(gridBg):
            for i, name in enumerate(row):
                image.blit(self.bg[name], (i * self.size[0], j * self.size[1]))
        return image

    # ---------- Setup ----------

    def regenGrid(self, rows, columns):
        """Create an empty 8x8 logic grid and place the 4 starting tokens in the centre."""
        grid = [[0 for _ in range(columns)] for _ in range(rows)]
        self.insertToken(grid, 1, 3, 3)    # white
        self.insertToken(grid, -1, 3, 4)   # black
        self.insertToken(grid, 1, 4, 4)    # white
        self.insertToken(grid, -1, 4, 3)   # black
        return grid

    def reset(self):
        """Start a fresh board (used by Retry and when starting a new game)."""
        self.tokens = {}
        self.gridLogic = self.regenGrid(self.y, self.x)
        self.animating = False

    # ---------- Drawing ----------

    def drawGrid(self, window):
        """Draw background, all tokens, and markers showing the legal moves."""
        window.blit(self.gridBg, (0, 0))

        for token in self.tokens.values():
            token.draw(window)

        # Don't show markers during animation, game over, or the computer's turn
        humanTurn = not (self.GAME.mode == 'ai' and self.GAME.currentPlayer == self.GAME.aiPlayer)
        if not self.animating and self.GAME.state == 'playing' and humanTurn:
            availMoves = self.findAvailMoves(self.gridLogic, self.GAME.currentPlayer)
            for (row, col) in availMoves:
                # Small white square in the middle of the cell
                pygame.draw.rect(window, 'White', (80 + col * 80 + 30, 80 + row * 80 + 30, 20, 20))

    def printGameLogicBoard(self):
        """Debug helper: print the logic grid to the terminal."""
        print('  | A | B | C | D | E | F | G | H |')
        for i, row in enumerate(self.gridLogic):
            line = f'{i} |'.ljust(3, " ")
            for item in row:
                line += f"{item}".center(3, " ") + "|"
            print(line)
        print()

    # ---------- Game rules ----------

    def countTokens(self, grid):
        """Return (white, black) token counts for the given logic grid."""
        white = sum(row.count(1) for row in grid)
        black = sum(row.count(-1) for row in grid)
        return white, black

    def findValidCells(self, grid, curPlayer):
        """Quick filter: empty cells that touch at least one opponent token.
        These are only CANDIDATES; findAvailMoves checks which ones are really legal."""
        candidates = []
        for row in range(8):
            for col in range(8):
                if grid[row][col] != 0:
                    continue                          # cell is occupied
                for (r, c) in directions(row, col):
                    if grid[r][c] == -curPlayer:      # neighbour is an opponent
                        candidates.append((row, col))
                        break                         # one is enough, go to next cell
        return candidates

    def swappableTiles(self, row, col, grid, player):
        """Return all opponent tokens that would be flipped if `player`
        places a token at (row, col). Checks all 8 directions."""
        swappable = []
        for (checkRow, checkCol) in directions(row, col):
            # Step direction, e.g. (-1, 0) means "go up"
            stepRow, stepCol = checkRow - row, checkCol - col
            currentLine = []                          # opponent tokens found in this direction

            # Walk in this direction until we leave the board
            while 0 <= checkRow <= 7 and 0 <= checkCol <= 7:
                cell = grid[checkRow][checkCol]
                if cell == -player:                   # opponent: might be flipped
                    currentLine.append((checkRow, checkCol))
                elif cell == player:                  # our own token closes the line -> flip them
                    swappable.extend(currentLine)
                    break
                else:                                 # empty cell: no flip in this direction
                    break
                checkRow += stepRow
                checkCol += stepCol
        return swappable

    def findAvailMoves(self, grid, currentPlayer):
        """Return the cells where the player can legally play (flips at least 1 token)."""
        playableCells = []
        for (row, col) in self.findValidCells(grid, currentPlayer):
            if len(self.swappableTiles(row, col, grid, currentPlayer)) > 0:
                playableCells.append((row, col))
        return playableCells

    # ---------- Tokens and animation ----------

    def insertToken(self, grid, curplayer, row, col):
        """Create a Token object for drawing and write its value to the logic grid."""
        tokenImage = self.whitetoken if curplayer == 1 else self.blacktoken
        self.tokens[(row, col)] = Token(curplayer, row, col, tokenImage, self.GAME)
        grid[row][col] = curplayer

    def animateTransitions(self, cells, player):
        """Play the flip animation on all `cells` at the same time.
        `player` is the player who just moved (the colour the tokens become)."""
        if player == 1:
            frames, finalImage = self.transitionWhiteToBlack, self.whitetoken
        else:
            frames, finalImage = self.transitionBlackToWhite, self.blacktoken

        self.animating = True
        for frame in frames:                          # show frame 1, 2, 3
            for cell in cells:
                self.tokens[cell].image = frame
            self.GAME.draw()                          # show the frame on screen
            pygame.event.pump()                       # keep the window responsive
            pygame.time.delay(100)                    # milliseconds per frame

        for cell in cells:                            # finish with the final token image
            self.tokens[cell].image = finalImage
        self.animating = False


# =====================================================
# TOKEN CLASS (one piece on the board)
# =====================================================

class Token:
    def __init__(self, player, row, col, image, main):
        self.player = player                          # 1 = white, -1 = black
        self.row = row
        self.col = col
        # Pixel position: board starts at (80, 80), each cell is 80 px
        self.posX = 80 + col * 80
        self.posY = 80 + row * 80
        self.GAME = main
        self.image = image                            # current image (changes during animation)

    def draw(self, window):
        window.blit(self.image, (self.posX, self.posY))


# =====================================================
# START THE GAME
# =====================================================

if __name__ == '__main__':
    game = Othello()
    game.run()
    pygame.quit()