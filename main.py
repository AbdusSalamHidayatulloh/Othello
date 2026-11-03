import pygame
import random
import io
import csv
import os
import time
from queue import Queue
from threading import Thread
from contextlib import redirect_stdout
from statistics import mean
from tutorial_data import TutorialData

# =====================================================
# UTILITY FUNCTIONS
# =====================================================

def directions(row, col, minRow=0, minCol=0, maxRow=7, maxCol=7):
    """Return the neighbouring cells (up to 8) that are inside the board."""
    validDirections = []
    # Cells above
    if row != minRow: validDirections.append((row - 1, col))
    # Top-left
    if row != minRow and col != minCol: validDirections.append((row - 1, col - 1))
    # Top-right
    if row != minRow and col != maxCol: validDirections.append((row - 1, col + 1))
    # Cells below
    if row != maxRow: validDirections.append((row + 1, col))
    # Bottom-Left
    if row != maxRow and col != minCol: validDirections.append((row + 1, col - 1))
    # Bottom-Right
    if row != maxRow and col != maxCol: validDirections.append((row + 1, col + 1))
    # Cells left and right
    # Left
    if col != minCol: validDirections.append((row, col - 1))
    # Right
    if col != maxCol: validDirections.append((row, col + 1))
    return validDirections


def loadImages(path, size):
    """Load an image file and scale it to the given size."""
    
    # Load the assets needed and optimizes the loaded picture for displaying
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.scale(img, size)


def loadSpriteSheet(sheet, col, row, newSize, size):
    """Cut one tile out of a sprite sheet and scale it.
    sheet   = the full sprite sheet image
    col,row = which tile (counted in tiles, not pixels)
    newSize = final size on screen
    size    = size of one tile inside the sheet (32x32)
    """
    # Create empty surface (initialization)
    image = pygame.Surface(size).convert_alpha()
    # Extract the sprite using blit
    image.blit(sheet, (0, 0), (col * size[0], row * size[1], size[0], size[1]))
    # Resize the blit extracted data for the board
    image = pygame.transform.scale(image, newSize)
    # Set the pixels matching black transparency
    image.set_colorkey('Black')
    return image


# =====================================================
# BUTTON CLASS (used by menu, difficulty and game over screens)
# =====================================================

class Button:
    # Initialize the structure for the button in the UI
    def __init__(self, text, center, size=(300, 60)):
        self.text = text
        self.rect = pygame.Rect(0, 0, size[0], size[1])
        self.rect.center = center                      # place the button by its centre

    # Drawing the button
    def draw(self, window, font, mousePos):
        # Slightly lighter colour when the mouse hovers over the button
        hovering = self.rect.collidepoint(mousePos)
        # Change color if hovering
        color = (130, 90, 45) if hovering else (90, 60, 30)
        # Draw a rectangular for the button BG and border size
        pygame.draw.rect(window, color, self.rect, border_radius=8)
        # Draw the border
        pygame.draw.rect(window, (230, 200, 150), self.rect, 3, border_radius=8)  # border
        # The label for the text of the button
        label = font.render(self.text, True, 'White')
        window.blit(label, label.get_rect(center=self.rect.center))

    # Event listener
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

    # Init the rules so the algorithm doesn't pick a random 
    def __init__(self, rules):
        self.rules = rules

    # Step  3
    def simulateMove(self, gridLogic, move, player):
        # row and col of the candidate move
        row, col = move
        # Find opponent disc that will be flipped
        toFlip = self.rules.swappableTiles(row, col, gridLogic, player)
        # Duplicate the current board state
        newGrid = [rowGrid[:] for rowGrid in gridLogic]
        # Place the player's disc (algorithm)
        newGrid[row][col] = player
        # Find the opponent disc on the board
        for(rowSelected, columnSelected) in toFlip:
            newGrid[rowSelected][columnSelected] = player
        # Return for the simulated board & numbers of flipped disc by the algorithm
        return newGrid, len(toFlip)

    # Step 4
    def cornerScore(self, grid, player):
        # player = CPU, -player = lawan (user)
        # Looped for every corners in the game, if algorithm gots it, add 1, if player got it, add 1, if not 0
        cpuCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == player)
        userCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == -player)
        return cpuCorner - userCorner

    def mobilityScore(self, grid, player):
        # player = CPU, -player = lawan (user)
        # Find all movement the algorithm have
        cpuMobility = len(self.rules.findAvailMoves(grid, player))
        # Find all movement the player have
        userMobility = len(self.rules.findAvailMoves(grid, -player))
        return cpuMobility - userMobility

    def heuristicScore(self, grid, flipCount, player):
        # The heuristic score for each of them (C(s), M(s) & F(s))
        C = self.cornerScore(grid, player)
        M = self.mobilityScore(grid, player)
        F = flipCount
        return self.WC * C + self.WM * M + self.WF * F

    # From previous step, make a move
    # Update will be done when it exits the 
    def getMove(self, gridLogic, player):
        # Find all available move the algorithm can do
        moves = self.rules.findAvailMoves(gridLogic, player)
        # Debug
        print(f'Existing moves: {moves}')
        # If there's no move, skip it
        if not moves:
            return None
        
        # Saving score for move comparison
        scored = []
        # Repeate all available movement till it's
        for move in moves:
            # Simulate a new grid and try the make a move and count
            # how many disk is turned
            newGrid, flipCount = self.simulateMove(gridLogic, move, player)
            # Calculating the heuristic score
            h = self.heuristicScore(newGrid, flipCount, player)
            # List of movement & heuristic score it had
            print("Move", move, "-> Score", h)
            # Adding the move and the score in the variable
            scored.append((h, move))
            
        # Step 5
        # Return the best moves made after calculating
        bestHeuristicScore = max(h for h, _ in scored)
        bestMoves = [m for h, m in scored if h == bestHeuristicScore]
        print("Best score: ", bestHeuristicScore, "Move taken: ", bestMoves)
        # Use the bestMoves as the next best move (use random incase 2 move have the same h score)
        # Step 6
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

    # Creates a copy of the board   
    def _simulate(self, board, move, player):
        """Create a *copy* of the board after a legal move."""
        # row and col for the candidate move
        row, col = move
        # Make a new board
        new_board = [line[:] for line in board]
        # 
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

    # Evaluate
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
# PRACTICE COACH (uses the same Alpha-Beta algorithm at depth 6)
# =====================================================

class PracticeCoach:
    """Derive truthful hints/explanations from the real board position.

    The depth-6 Alpha-Beta score chooses the move; the explanation describes
    directly measurable consequences of that move, not a fabricated search line.
    """

    DEPTH = 6

    def __init__(self, rules):
        self.rules = rules
        
    # Analyzing the board and player
    def analyze(self, board, player):
        # Agent will use the AlphaBeta
        agent = AlphaBetaAgent(self.rules, depth=self.DEPTH)
        # Agent will take the best move for the answer
        best_move = agent.getMove(board, player)
        # If there's none, continue
        if best_move is None:
            return None

        # Take all availabale move
        moves = self.rules.findAvailMoves(board, player)
        # Initialize options
        options = {}
        # Loop for every available move
        for move in moves:
            # The result will be simulated by the agent
            result = agent._simulate(board, move, player)
            # Summing total disc owned by the player
            own_discs = sum(v == player for row in result for v in row)
            # Summing total disc owned by the algorithm
            enemy_discs = sum(v == -player for row in result for v in row)
            # Based on the move, add the following data:
            options[move] = {
                'own_mobility': len(self.rules.findAvailMoves(result, player)),
                'enemy_mobility': len(self.rules.findAvailMoves(result, -player)),
                'enemy_corner_moves': sum(
                    m in AlphaBetaAgent.CORNERS
                    for m in self.rules.findAvailMoves(result, -player)
                ),
                'own_corners': sum(result[r][c] == player for r, c in AlphaBetaAgent.CORNERS),
                'enemy_corners': sum(result[r][c] == -player for r, c in AlphaBetaAgent.CORNERS),
                'own_discs': own_discs,
                'enemy_discs': enemy_discs,
                'flips': len(self.rules.swappableTiles(move[0], move[1], board, player)),
            }
        
        # Select a movement and take the data from the options dict.
        selected = options[best_move]
        # Retrieve aall information about every movement
        other = [v for m, v in options.items() if m != best_move]
        # Gives advice based on the the things the players have (advantage)
        if best_move in AlphaBetaAgent.CORNERS:
            hint = 'Ada sudut yang bisa kamu amankan. Perhatikan kotak-kotak di pojok papan.'
            explanation = 'Langkah ini menguasai sudut. Bidak di sudut tidak bisa dibalik oleh lawan.'
        elif selected['enemy_corner_moves'] == 0 and any(v['enemy_corner_moves'] > 0 for v in other):
            hint = 'Periksa apakah pilihan langkahmu memberi lawan jalan menuju sudut.'
            explanation = 'Langkah ini tidak memberi lawan kesempatan langsung mengambil sudut, tidak seperti beberapa alternatif.'
        elif other and selected['enemy_mobility'] < max(v['enemy_mobility'] for v in other):
            hint = 'Perhatikan jumlah langkah sah yang akan dimiliki lawan sesudah giliranmu.'
            explanation = f'Lawan memiliki {selected["enemy_mobility"]} langkah sah setelah langkah ini, lebih sedikit daripada pada beberapa alternatif.'
        elif other and selected['flips'] < max(v['flips'] for v in other):
            hint = 'Jangan hanya mengejar jumlah bidak yang dibalik. Pikirkan balasan lawan.'
            explanation = 'Langkah ini tidak membalik bidak terbanyak, tetapi mendapat nilai pencarian terbaik pada depth 6.'
        elif other and selected['own_mobility'] > min(v['own_mobility'] for v in other):
            hint = 'Coba pertahankan banyak pilihan langkah sah untuk giliran-giliran berikutnya.'
            explanation = 'Posisi setelah langkah ini mempertahankan pilihan langkahmu; Coach juga memperhitungkan balasan lawan.'
        else:
            hint = 'Bandingkan langkah yang tersedia. Perhatikan sudut, mobilitas, dan balasan lawan.'
            explanation = 'Coach memilih langkah ini berdasarkan pencarian Alpha-Beta depth 6; tidak ada satu faktor langsung yang cukup menjelaskan seluruh keputusan.'

        # Returns advice for the plater and the explanation
        return {
            'move': best_move,
            'score': agent.lastScore,
            'hint': hint,
            'explanation': explanation,
            **selected,
        }


# =====================================================
# BENCHMARK RUNNER (pilih AI Player 1 vs Player 2, tanpa animasi)
# =====================================================

class BenchmarkRunner:
    """Menjalankan game benchmark (tanpa animasi) satu langkah per panggilan step().
    Player 1 dan Player 2 bisa diisi AI apa pun ('AlphaBeta' / 'GBFS'), termasuk yang sama.
    Warna ditukar tiap game (P1 putih di game ganjil, hitam di game genap) supaya 50/50.
    Dipakai oleh menu Benchmark di main.py DAN oleh benchmark.py.
    `rules` = objek apa pun yang punya findAvailMoves, swappableTiles, countTokens
    (Grid asli atau HeadlessRules di benchmark.py).
    Tanpa algo1/algo2, defaultnya tetap AlphaBeta (P1) vs GBFS (P2)."""

    RESULT_DIR = 'benchmark_result'     # nama folder tempat file CSV disimpan
    LABELS = {'AlphaBeta': 'Alpha-Beta', 'GBFS': 'GBFS'}    # nama untuk layar
    TAGS = {'AlphaBeta': 'AB', 'GBFS': 'GBFS'}              # nama untuk file CSV

    def __init__(self, rules, totalGames, depth, algo1='AlphaBeta', algo2='GBFS', depth2=None):
        self.rules = rules
        self.totalGames = totalGames
        self.depth = depth
        self.depths = {1: depth, 2: depth if depth2 is None else depth2}   # depth AB per pemain
        self.algos = {1: algo1, 2: algo2}   # slot pemain -> nama algoritma
        self.gameIndex = 0              # jumlah game yang sudah selesai
        self.games = []                 # hasil per game
        self.moves = []                 # data per langkah: (algoritma, detik, node, cutoff, slot)
        self.finished = False
        self.startGame()

    def label(self, slot):
        return self.LABELS[self.algos[slot]]

    def shortLabel(self, slot):
        """Nama pendek untuk panel layar, mis. 'AB d3' atau 'GBFS'."""
        if self.algos[slot] == 'AlphaBeta':
            return f'AB d{self.depths[slot]}'
        return 'GBFS'

    def fullLabel(self, slot):
        if self.algos[slot] == 'AlphaBeta':
            return f'Alpha-Beta (depth {self.depths[slot]})'
        return 'GBFS'

    def makeAgent(self, slot):
        if self.algos[slot] == 'AlphaBeta':
            return AlphaBetaAgent(self.rules, self.depths[slot])
        return GBFSAgent(self.rules)

    def startGame(self):
        # Selang-seling warna: P1 putih di game ke-1, 3, 5, ... supaya seimbang
        self.p1White = (self.gameIndex % 2 == 0)
        a1 = (1, self.algos[1], self.makeAgent(1))
        a2 = (2, self.algos[2], self.makeAgent(2))
        self.agents = {1: a1, -1: a2} if self.p1White else {1: a2, -1: a1}

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
        # Mencari semua gerakan yang dapat dilakukan oleh algoritma
        moves = rules.findAvailMoves(board, self.player)

        # Apabila tidak ada gerakan yang dapat dilakukan oleh Algoritma
        if not moves:
            # Apabila lawan algoritma tidak juga dapat berjalan, akhiri game
            if not rules.findAvailMoves(board, -self.player):
                self.endGame()                      # kedua pemain tidak bisa jalan
            # Jika tidak, ganti giliran
            else:
                self.player = -self.player          # pass
            return

        # Taking which algorithm first
        slot, name, agent = self.agents[self.player]
        # Starting the game
        start = time.perf_counter()
        # Hiding the output made by the algorithm
        with redirect_stdout(io.StringIO()):        # sembunyikan print bawaan agent
            # Do movement based on the player
            move = agent.getMove(board, self.player)
        # Time elapsed for the game
        elapsed = time.perf_counter() - start

        # Ig alforithm is Alpha-Beta
        if name == 'AlphaBeta':
            # Take the explored nodes and the count of pruning done
            nodes, cutoffs = agent.nodesExplored, agent.pruningCount
        # If it's not Alpha-Beta, GBFS is choosen and just take the amount of nodes
        else:
            nodes, cutoffs = len(moves), 0          # GBFS: node = jumlah kandidat yang dievaluasi
        # Move done is appended
        self.moves.append((name, elapsed, nodes, cutoffs, slot))

        # Selecting a row and col as a candidate movement
        row, col = move
        # Find all enemy discs that will be flipped if the current algorithm places it at that specific place
        flips = rules.swappableTiles(row, col, board, self.player)
        # Places a new disc on row and col from the current player
        board[row][col] = self.player
        # Loop for every disc that's flipped
        for r, c in flips:
            board[r][c] = self.player
        # Change player
        self.player = -self.player

    # Ending the game if there's no movement
    def endGame(self):
        # Count the disc it have
        white, black = self.rules.countTokens(self.board)
        # Identifying whose side has the color white and black (Alpha Beta is black and GBFS is white)
        # if AB is first then AlphaBeta is black and GBFS is white
        p1Discs, p2Discs = (white, black) if self.p1White else (black, white)
        # Winning condition
        if p1Discs > p2Discs:   winner = 'P1'
        elif p2Discs > p1Discs: winner = 'P2'
        else:                   winner = 'Draw'

        # Append the game result
        self.games.append({'game': self.gameIndex + 1, 'p1White': self.p1White,
                           'p1Discs': p1Discs, 'p2Discs': p2Discs, 'winner': winner})
        self.gameIndex += 1

        # If the index is more than the total games needed, end
        if self.gameIndex >= self.totalGames:
            self.finished = True
        # If not, start a new game
        else:
            self.startGame()

    # Summary from the all of the games that have been done
    def summaryLines(self):
        """Ringkasan 4 metrik di proposal, per sisi (P1 / P2), untuk layar dan console."""
        # Untuk benchmark, n adalah jumlah permainan
        n = len(self.games)
        # Totalkan jumlah menang dari algoritma 1 & algoritma 2
        p1Wins = sum(g['winner'] == 'P1' for g in self.games)
        p2Wins = sum(g['winner'] == 'P2' for g in self.games)
        # Number of games that have ended in a tie
        draws = n - p1Wins - p2Wins

        # Lines for the summary 
        lines = [
            f'P1 {self.fullLabel(1)} vs P2 {self.fullLabel(2)} | {n} games',
            f'Win rate   : P1 {p1Wins} ({p1Wins / n * 100:.1f}%) | '
            f'P2 {p2Wins} ({p2Wins / n * 100:.1f}%) | Draw {draws} ({draws / n * 100:.1f}%)',
        ]
        # Compare Algorithm 1 first & second position (determines if Algorithm 1 plays as the one who moves first and last)
        for label, who, flag in (('P1 as White', 'P1', True), ('P1 as Black', 'P1', False),
                                 ('P2 as White', 'P2', False), ('P2 as Black', 'P2', True)):
            # Collects the current flag of the game (Collects the data of the game if Algorithm 1 is the one who moves first and last)
            sub = [g for g in self.games if g['p1White'] == flag]
            # If there's any games contained, do the code
            if sub:
                # Counts how many wind one by Algorithm 1
                w = sum(g['winner'] == who for g in sub)
                # Adds the result to the summary 
                lines.append(f'{label} : {who} won {w}/{len(sub)}')

        # Calculate margins of disc between the winner and loser
        margins = [abs(g['p1Discs'] - g['p2Discs']) for g in self.games]
        # Same thing but keeps the positive and negative difference (raw data)
        signed = [g['p1Discs'] - g['p2Discs'] for g in self.games]
        # Adds average result to the summary
        lines.append(f'Avg margin : {mean(margins):.2f} discs (winner - loser)')
        lines.append(f'Avg P1-P2  : {mean(signed):+.2f} discs')

        # Collect benchmark data
        def vals(slot, idx, scale=1):
            # Creates a temporart list and returns with selected data (idx)
            return [m[idx] * scale for m in self.moves if m[4] == slot]

        # Collect the tiime execution for each algorithm
        def timeText(slot):
            # In this case, slot are the one who's the current plater, the data is 1 (execution time) and scale it to miliseconds (*1000) 
            v = vals(slot, 1, 1000)
            # Return it in a form of string
            return f'{mean(v):.2f} ms (max {max(v):.1f})' if v else '-'

        # Collect the data of the nodes
        def nodeText(slot):
            # The data is 2 (nodes explored)
            v = vals(slot, 2)
            return f'{mean(v):.1f} (max {max(v)})' if v else '-'

        def cutText(slot):
            # If alforithm choosed is not alpha beta, return -
            if self.algos[slot] != 'AlphaBeta':
                return '-'
            # The data is 3 (Pruning of the branch)
            v = vals(slot, 3)
            # Return in form of string
            return f'{mean(v):.1f}' if v else '-'

        # Save the data
        lines.append(f'Time/move  : P1 {timeText(1)} | P2 {timeText(2)}')
        lines.append(f'Nodes/move : P1 {nodeText(1)} | P2 {nodeText(2)}')
        lines.append(f'Cutoffs    : P1 {cutText(1)} | P2 {cutText(2)} per move')
        return lines

    def summaryRows(self):
        """Ringkasan dalam bentuk tabel (metrik, P1, P2) untuk file CSV."""
        n = len(self.games)
        p1Wins = sum(g['winner'] == 'P1' for g in self.games)
        p2Wins = sum(g['winner'] == 'P2' for g in self.games)
        draws = n - p1Wins - p2Wins
        signed = [g['p1Discs'] - g['p2Discs'] for g in self.games]
        margins = [abs(x) for x in signed]

        def vals(slot, idx, scale=1):
            return [m[idx] * scale for m in self.moves if m[4] == slot]

        def stat(slot, idx, scale, fn, nd):
            v = vals(slot, idx, scale)
            return round(fn(v), nd) if v else '-'

        rows = [
            ['metrik', 'P1', 'P2'],
            ['algoritma', self.fullLabel(1), self.fullLabel(2)],
            ['total_game', n, n],
            ['menang', p1Wins, p2Wins],
            ['seri', draws, draws],
            ['win_rate_persen', round(p1Wins / n * 100, 1), round(p2Wins / n * 100, 1)],
        ]
        for color, p1Plays in (('putih', True), ('hitam', False)):
            g1 = [g for g in self.games if g['p1White'] == p1Plays]     # game di mana P1 pakai warna ini
            g2 = [g for g in self.games if g['p1White'] != p1Plays]     # game di mana P2 pakai warna ini
            rows.append([f'game_sebagai_{color}', len(g1), len(g2)])
            rows.append([f'menang_sebagai_{color}',
                         sum(g['winner'] == 'P1' for g in g1),
                         sum(g['winner'] == 'P2' for g in g2)])
        rows += [
            ['rata_selisih_disc_sendiri_minus_lawan', round(mean(signed), 2), round(-mean(signed), 2)],
            ['rata_selisih_disc_pemenang_minus_kalah', round(mean(margins), 2), round(mean(margins), 2)],
            ['waktu_per_langkah_ms_rata', stat(1, 1, 1000, mean, 3), stat(2, 1, 1000, mean, 3)],
            ['waktu_per_langkah_ms_max', stat(1, 1, 1000, max, 3), stat(2, 1, 1000, max, 3)],
            ['node_per_langkah_rata', stat(1, 2, 1, mean, 1), stat(2, 2, 1, mean, 1)],
            ['node_per_langkah_max', stat(1, 2, 1, max, 0), stat(2, 2, 1, max, 0)],
        ]
        cut = [stat(slot, 3, 1, mean, 1) if self.algos[slot] == 'AlphaBeta' else '-' for slot in (1, 2)]
        rows.append(['cutoff_per_langkah_rata', cut[0], cut[1]])
        return rows

    @classmethod
    def ensureResultDir(cls):
        """Buat folder hasil kalau belum ada, lalu return path-nya.
        Folder ada di sebelah main.py (bukan di working directory),
        jadi lokasinya selalu sama walau game dijalankan dari folder lain."""
        # Take the absolute path to the folder
        baseDir = os.path.dirname(os.path.abspath(__file__))
        # Make a new folder on that path
        folder = os.path.join(baseDir, cls.RESULT_DIR)
        # Make sure the folder is there
        os.makedirs(folder, exist_ok=True)      # tidak error kalau folder sudah ada
        return folder

    # Saving the benchmark in a form of a .CSV file
    def saveCsv(self):
        # Ensure folder exist
        folder = self.ensureResultDir()         # dibuat otomatis kalau belum ada / terhapus

        def tagOf(slot):
            algo = self.algos[slot]
            return self.TAGS[algo] + (str(self.depths[slot]) if algo == 'AlphaBeta' else '')
        stamp = time.strftime('%Y%m%d_%H%M%S')      # supaya file lama tidak tertimpa
        tag = f'{tagOf(1)}-vs-{tagOf(2)}_{stamp}'   # mis. AB3-vs-GBFS_20261103_153045
        gamesFile = os.path.join(folder, f'hasil_games_{tag}.csv')
        movesFile = os.path.join(folder, f'hasil_moves_{tag}.csv')
        self.summaryFile = os.path.join(folder, f'hasil_summary_{tag}.csv')

        # Menuliskan isi dari .csv file untuk game dan gerakannya
        with open(gamesFile, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=self.games[0].keys())
            w.writeheader()
            w.writerows(self.games)
        with open(movesFile, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['algoritma', 'waktu_detik', 'node', 'cutoff', 'pemain'])
            w.writerows(self.moves)
        with open(self.summaryFile, 'w', newline='') as f:
            csv.writer(f).writerows(self.summaryRows())
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
        self.coachFont = pygame.font.Font(None, 25)

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
        # state: 'menu' | 'playmode' | 'difficulty' | 'playing' | 'paused' | 'gameover'
        #        | 'benchmark' | 'benchrun' | 'benchresult'
        self.state = 'menu'
        self.mode = None                # '1v1' or 'ai'
        self.playStyle = 'normal'        # 'normal' or 'practice' (AI matches only)
        self.difficulty = None          # 'easy' (GBFS) or 'hard' (Alpha-Beta)
        self.agent = None               # the AI object (only in 'ai' mode)
        self.aiPlayer = -1              # the computer plays black, the human plays white
        self.lastMoveTime = 0           # used to add a short pause before the AI moves
        self.message = ''               # info text (e.g. "Black has no moves")

        # Practice Coach: search runs in a daemon thread so Pygame can draw
        # "Analyzing..." and still accept input during a depth-6 search.
        self.coachResultQueue = Queue()
        self.coachWorker = None
        self.coachGeneration = 0         # prevents old results appearing in a new turn/game
        self.coachCacheKey = None
        self.coachCache = None
        self.coachView = None            # None | 'hint' | 'answer'
        self.coachRequest = None         # latest requested view while searching
        self.coachError = ''

        # ---- Buttons for each screen ----
        cx = 550                        # horizontal centre of the window
        self.menuButtons = {
            # Baris atas (2 tombol)
            '1v1':       Button('1 vs 1',        (cx - 175, 420)),
            'ai':        Button('1 vs Computer', (cx + 175, 420)),
            # Baris bawah (3 tombol)
            'tut':       Button('How to Play',   (cx - 350, 510)),
            'benchmark': Button('Benchmark',     (cx,       510)),
            'quit':      Button('Quit',          (cx + 350, 510)),
        }
        self.playModeButtons = {
            'normal':   Button('Normal Mode',   (cx, 380)),
            'practice': Button('Practice Mode', (cx, 470)),
            'back':     Button('Back',          (cx, 560)),
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
        self.coachButtons = {
            'hint': Button('Get Hint', (950, 223), (240, 52)),
            'answer': Button('Show Answer', (950, 285), (240, 52)),
        }
        self.pauseButtons = {
            'resume':  Button('Resume',    (cx, 380)),
            'restart': Button('Restart',   (cx, 460)),
            'menu':    Button('Main Menu', (cx, 540)),
        }

        # ---- Benchmark ----
        self.benchDepth1 = 3                    # depth AB untuk Player 1
        self.benchDepth2 = 3                    # depth AB untuk Player 2
        self.benchGames = 100
        self.depthOptions = [2, 3, 4]
        self.gameOptions = [4, 10, 50, 100]     # 4 = tes cepat
        self.algoOptions = ['AlphaBeta', 'GBFS']
        self.benchAlgo1 = 'AlphaBeta'           # AI Player 1
        self.benchAlgo2 = 'GBFS'                # AI Player 2
        self.benchmark = None                   # BenchmarkRunner yang sedang jalan
        self.benchLines = []                    # teks hasil untuk layar result

        labels = BenchmarkRunner.LABELS
        self.benchButtons = {
            'p1':     Button(f'P1: {labels[self.benchAlgo1]}', (cx - 250, 330)),
            'p2':     Button(f'P2: {labels[self.benchAlgo2]}', (cx + 250, 330)),
            'depth1': Button(f'Depth: {self.benchDepth1}',     (cx - 250, 410)),   # hanya muncul kalau P1 = AB
            'depth2': Button(f'Depth: {self.benchDepth2}',     (cx + 250, 410)),   # hanya muncul kalau P2 = AB
            'games':  Button(f'Games: {self.benchGames}',      (cx, 520)),
            'start':  Button('Start',                          (cx, 600)),
            'back':   Button('Back',                           (cx, 680)),
        }
        self.benchRunButtons = {'cancel': Button('Cancel', (950, 700), (240, 60))}
        self.benchResultButtons = {'back': Button('Main Menu', (cx, 700))}

        self.RUN = True

        self.tutorialStep = 0
        self.tutorialDone = False
        self.tutorialButton = {
            'next': Button('Next', (950, 600), (180, 50)),
            'menu': Button('Menu', (950, 660), (180, 50)),
        }

    # ---------- Main loop ----------

    def run(self):
        """Main game loop: input -> update -> draw, repeated forever."""
        while self.RUN:
            self.input()
            self.update()
            self.draw()
            self.clock.tick(60)         # limit to 60 FPS

    # ---------- Starting / ending a game ----------

    def startGame(self, mode, difficulty=None, playStyle='normal'):
        """Reset the board and begin a new game with the given settings."""
        self.mode = mode
        self.playStyle = playStyle if mode == 'ai' else 'normal'
        self.difficulty = difficulty
        self.resetCoach()
        self.grid.reset()
        self.currentPlayer = 1
        self.message = ''
        self.lastMoveTime = pygame.time.get_ticks()
        
        # If player 1 vs AI, then picked based on what they choose
        if mode == 'ai':
            if difficulty == 'easy':
                self.agent = GBFSAgent(self.grid)
            else:
                self.agent = AlphaBetaAgent(self.grid, depth=4)
        else:
            self.agent = None

        self.state = 'playing'

    # ---------- Practice Coach ----------
    def resetCoach(self):
        """Invalidate hints after every move, restart or new game."""
        self.coachGeneration += 1
        self.coachCacheKey = None
        self.coachCache = None
        self.coachView = None
        self.coachRequest = None
        self.coachError = ''

    def isPracticeTurn(self):
        return (self.state == 'playing' and self.mode == 'ai'
                and self.playStyle == 'practice'
                and self.currentPlayer != self.aiPlayer)

    def coachKey(self):
        return (self.coachGeneration, self.currentPlayer,
                tuple(tuple(row) for row in self.grid.gridLogic))

    def requestCoach(self, view):
        """Request a hint/answer; never block the UI on Alpha-Beta search."""
        if not self.isPracticeTurn():
            return
        key = self.coachKey()
        self.coachError = ''
        if self.coachCache is not None and self.coachCacheKey == key:
            self.coachView = view
            self.coachRequest = None
            return
        self.coachView = None
        self.coachRequest = view
        self.startCoachWorker()

    def startCoachWorker(self):
        if self.coachRequest is None or not self.isPracticeTurn():
            return
        if self.coachWorker is not None and self.coachWorker.is_alive():
            return                # one search at a time, no thread pile-up

        key = self.coachKey()
        snapshot = [row[:] for row in self.grid.gridLogic]
        player = self.currentPlayer
        result_queue = self.coachResultQueue
        rules = self.grid

        def work():
            try:
                result = PracticeCoach(rules).analyze(snapshot, player)
                result_queue.put((key, result, ''))
            except Exception as exc:
                result_queue.put((key, None, str(exc)))

        self.coachWorker = Thread(target=work, daemon=True, name='OthelloPracticeCoach')
        self.coachWorker.start()

    def updateCoach(self):
        """Consume completed results on the main thread, ignoring stale boards."""
        while not self.coachResultQueue.empty():
            key, result, error = self.coachResultQueue.get_nowait()
            if (self.isPracticeTurn() and self.coachRequest is not None
                    and key == self.coachKey()):
                self.coachError = error or ''
                self.coachCacheKey = key
                self.coachCache = result
                self.coachView = self.coachRequest if result is not None else None
                self.coachRequest = None

        # If the position changed while searching, any old result was ignored.
        # The most recent request is processed as soon as the worker is idle.
        if self.coachRequest is not None:
            self.startCoachWorker()

    @staticmethod
    def moveLabel(move):
        return f'{"ABCDEFGH"[move[1]]}{move[0]}'

    def drawWrappedText(self, content, x, y, maxWidth, color='White', maxY=690):
        """Render a short paragraph inside the narrow (300 px) coach panel."""
        if self.message:
            maxY = min(maxY, 653)  # leave room for a pass/skip notification
        for paragraph in content.split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = f'{line} {word}'.strip()
                if line and self.coachFont.size(candidate)[0] > maxWidth:
                    if y + 26 > maxY:
                        return y
                    self.screen.blit(self.coachFont.render(line, True, color), (x, y))
                    y += 26
                    line = word
                else:
                    line = candidate
            if line:
                if y + 26 > maxY:
                    return y
                self.screen.blit(self.coachFont.render(line, True, color), (x, y))
                y += 26
        return y

    def drawPracticePanel(self):
        """Score, hint and answer share the existing right-hand game panel."""
        mouse = pygame.mouse.get_pos()
        white, black = self.grid.countTokens(self.grid.gridLogic)
        pygame.draw.rect(self.screen, (35, 25, 15), (800, 0, 300, 800))
        pygame.draw.line(self.screen, (230, 200, 150), (800, 0), (800, 800), 3)
        self.screen.blit(self.font.render('PRACTICE', True, (230, 200, 150)), (825, 35))
        diff = 'Easy (GBFS)' if self.difficulty == 'easy' else 'Hard (AB 4)'
        self.screen.blit(self.smallFont.render(diff, True, 'White'), (825, 78))
        self.screen.blit(self.smallFont.render(f'White: {white}  |  Black: {black}', True, 'White'), (825, 114))
        turn = 'Your turn (White)' if self.currentPlayer == 1 else 'Computer turn'
        self.screen.blit(self.coachFont.render(turn, True, (230, 200, 150)), (825, 150))

        if self.state == 'playing':
            for button in self.coachButtons.values():
                button.draw(self.screen, self.smallFont, mouse)

        self.screen.blit(self.smallFont.render('COACH - AB DEPTH 6', True, (230, 200, 150)), (825, 330))
        y = 369
        if self.coachError:
            y = self.drawWrappedText('Coach error: ' + self.coachError, 825, y, 250, (255, 170, 120))
        elif self.coachRequest is not None:
            y = self.drawWrappedText('Analyzing position... You can still play.', 825, y, 250)
        elif self.coachView == 'hint' and self.coachCache is not None:
            y = self.drawWrappedText('HINT:', 825, y, 250, (230, 200, 150))
            y = self.drawWrappedText(self.coachCache['hint'], 825, y + 4, 250)
            y = self.drawWrappedText('Use Show Answer to reveal the best move.', 825, y + 14, 250, (190, 180, 160))
        elif self.coachView == 'answer' and self.coachCache is not None:
            data = self.coachCache
            y = self.drawWrappedText(
                f'BEST: {self.moveLabel(data["move"])} | Score {data["score"]:+d}',
                825, y, 250, (240, 208, 100))
            y = self.drawWrappedText('Stats: You / Computer', 825, y + 4, 250, (190, 180, 160))
            y = self.drawWrappedText(
                f'Flipped: {data["flips"]} | Corners: {data["own_corners"]}/{data["enemy_corners"]}',
                825, y, 250)
            y = self.drawWrappedText(
                f'Moves: {data["own_mobility"]}/{data["enemy_mobility"]} | Discs: {data["own_discs"]}/{data["enemy_discs"]}',
                825, y, 250)
            y = self.drawWrappedText('EXPLANATION:', 825, y + 13, 250, (230, 200, 150))
            y = self.drawWrappedText(data['explanation'], 825, y + 5, 250)
        elif self.currentPlayer != 1 and self.state == 'playing':
            y = self.drawWrappedText('Wait for the computer to move.', 825, y, 250)
        else:
            y = self.drawWrappedText(
                'Get Hint: strategic advice without a square. Show Answer: best move and explanation.',
                825, y, 250)

        if self.message:
            self.drawWrappedText(self.message, 825, 663, 250, (255, 200, 100), maxY=719)
        if self.state == 'playing':
            self.pauseButton.draw(self.screen, self.font, mouse)

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

    # ---------- Loading Tutorial Steps ----------
    
    def loadTutorialStep(self):
        # Take the steps on tutorialdata
        step = TutorialData.TUTORIAL_STEPS[self.tutorialStep]
        # Check if the board is available
        if step['board'] is not None:
            # If it's available, load the board for tutorial
            self.grid.loadBoardForTutorial(step['board'])
        # Take players value for determining who'se next (in this context)
        # just changing player's token appearance
        self.currentPlayer = step.get('player', 1)
        # The mode it uses is the 1v1
        self.mode = '1v1'
        # Assumed the tutorial is still on-going
        self.tutorialDone = False
        self.state = 'tut'
        
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
                    elif self.state == 'playmode':
                        self.clickPlayMode(event.pos)
                    elif self.state == 'difficulty':
                        self.clickDifficulty(event.pos)
                    elif self.state == 'playing':
                        # Tombol Pause dicek dulu supaya tetap bisa diklik saat giliran komputer
                        if self.pauseButton.isClicked(event.pos):
                            self.pauseGame()
                        elif self.isPracticeTurn() and self.coachButtons['hint'].isClicked(event.pos):
                            self.requestCoach('hint')
                        elif self.isPracticeTurn() and self.coachButtons['answer'].isClicked(event.pos):
                            self.requestCoach('answer')
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
                    elif self.state == 'tut':
                        self.clickTutorial(event.pos)
                    elif self.state == 'benchresult':
                        self.clickBenchResult(event.pos)

    def clickMenu(self, pos):
        if self.menuButtons['1v1'].isClicked(pos):
            self.startGame('1v1')
        elif self.menuButtons['ai'].isClicked(pos):
            self.state = 'playmode'
        elif self.menuButtons['benchmark'].isClicked(pos):
            self.state = 'benchmark'
        elif self.menuButtons['tut'].isClicked(pos):
            self.grid.reset()
            self.tutorialStep = 0
            self.loadTutorialStep()
        elif self.menuButtons['quit'].isClicked(pos):
            self.RUN = False

    def clickPlayMode(self, pos):
        if self.playModeButtons['normal'].isClicked(pos):
            self.playStyle = 'normal'
            self.state = 'difficulty'
        elif self.playModeButtons['practice'].isClicked(pos):
            self.playStyle = 'practice'
            self.state = 'difficulty'
        elif self.playModeButtons['back'].isClicked(pos):
            self.state = 'menu'

    def clickDifficulty(self, pos):
        if self.difficultyButtons['easy'].isClicked(pos):
            self.startGame('ai', 'easy', self.playStyle)
        elif self.difficultyButtons['hard'].isClicked(pos):
            self.startGame('ai', 'hard', self.playStyle)
        elif self.difficultyButtons['back'].isClicked(pos):
            self.state = 'playmode'

    def pauseGame(self):
        self.state = 'paused'

    def resumeGame(self):
        self.state = 'playing'
        self.lastMoveTime = pygame.time.get_ticks()     # komputer menunggu lagi 600 ms setelah resume

    def clickPause(self, pos):
        if self.pauseButtons['resume'].isClicked(pos):
            self.resumeGame()
        elif self.pauseButtons['restart'].isClicked(pos):
            self.startGame(self.mode, self.difficulty, self.playStyle)   # pengaturan yang sama
        elif self.pauseButtons['menu'].isClicked(pos):
            self.state = 'menu'

    def clickGameOver(self, pos):
        if self.gameOverButtons['retry'].isClicked(pos):
            self.startGame(self.mode, self.difficulty, self.playStyle)   # same settings as before
        elif self.gameOverButtons['menu'].isClicked(pos):
            self.state = 'menu'

    def benchButtonVisible(self, name):
        """Tombol depth hanya tampil untuk pemain yang memakai Alpha-Beta."""
        if name == 'depth1':
            return self.benchAlgo1 == 'AlphaBeta'
        if name == 'depth2':
            return self.benchAlgo2 == 'AlphaBeta'
        return True

    def clickBenchmark(self, pos):
        b = self.benchButtons
        labels = BenchmarkRunner.LABELS
        if b['p1'].isClicked(pos):
            # Klik untuk ganti AI Player 1 (AlphaBeta <-> GBFS)
            i = (self.algoOptions.index(self.benchAlgo1) + 1) % len(self.algoOptions)
            self.benchAlgo1 = self.algoOptions[i]
            b['p1'].text = f'P1: {labels[self.benchAlgo1]}'
        elif b['p2'].isClicked(pos):
            # Klik untuk ganti AI Player 2 (AlphaBeta <-> GBFS)
            i = (self.algoOptions.index(self.benchAlgo2) + 1) % len(self.algoOptions)
            self.benchAlgo2 = self.algoOptions[i]
            b['p2'].text = f'P2: {labels[self.benchAlgo2]}'
        elif self.benchButtonVisible('depth1') and b['depth1'].isClicked(pos):
            # Klik untuk ganti depth Player 1 (2 -> 3 -> 4 -> 2 ...)
            i = (self.depthOptions.index(self.benchDepth1) + 1) % len(self.depthOptions)
            self.benchDepth1 = self.depthOptions[i]
            b['depth1'].text = f'Depth: {self.benchDepth1}'
        elif self.benchButtonVisible('depth2') and b['depth2'].isClicked(pos):
            # Klik untuk ganti depth Player 2
            i = (self.depthOptions.index(self.benchDepth2) + 1) % len(self.depthOptions)
            self.benchDepth2 = self.depthOptions[i]
            b['depth2'].text = f'Depth: {self.benchDepth2}'
        elif b['games'].isClicked(pos):
            # Klik untuk ganti jumlah game (4 -> 10 -> 50 -> 100 -> 4 ...)
            i = (self.gameOptions.index(self.benchGames) + 1) % len(self.gameOptions)
            self.benchGames = self.gameOptions[i]
            b['games'].text = f'Games: {self.benchGames}'
        elif b['start'].isClicked(pos):
            self.benchmark = BenchmarkRunner(self.grid, self.benchGames, self.benchDepth1,
                                             self.benchAlgo1, self.benchAlgo2, self.benchDepth2)
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

    def clickTutorial(self, pos):
        step = TutorialData.TUTORIAL_STEPS[self.tutorialStep]
        
        if self.tutorialButton['menu'].isClicked(pos):
            self.state = 'menu'
            return
        
        if step['goal'] == 'next' or self.tutorialDone:
            if self.tutorialButton['next'].isClicked(pos):
                self.advanceTutorial()
        
        else:
            col, row = (pos[0] - 80) // 80, (pos[1] - 80)//80
            if(row, col) == step['target']:
                self.playTutorialMove(row, col)
    
    # For the logic on the game's tutorial
    def playTutorialMove(self, row, col):
        # Make a grid
        grid = self.grid
        # Stores the coordinate of all enemy disc needs to be flipped
        toFlip = grid.swappableTiles(row, col, grid.gridLogic, self.currentPlayer)
        # Insert the player's disc based on the current player
        grid.insertToken(grid.gridLogic, self.currentPlayer, row, col)
        # Animating for the disc flip
        grid.animateTransitions(toFlip, self.currentPlayer)
        # Loop based on the numbers of coordinates of opponent discs needs to flipped 
        for(r, c) in toFlip:
            # Update the logical board
            grid.gridLogic[r][c] *= -1
            # Update the visual disc
            grid.tokens[(r, c)].player *= -1
        # After that, it's done
        self.tutorialDone = True
        
    # For moving to the next part of the tutorial
    def advanceTutorial(self):
        # Every call goes to the next step
        self.tutorialStep += 1
        # If the tutorial is done, return to the menu
        if self.tutorialStep >= len(TutorialData.TUTORIAL_STEPS):
            self.state = 'menu'
        # If the tutorial is not done, continue
        else:
            self.loadTutorialStep()
                
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
        self.resetCoach()       # the previous hint/answer no longer applies
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
        """Runs every frame: computer's turn, benchmark and coach results."""
        self.updateCoach()
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
                self.benchLines.append(f'Hasil Game: {BenchmarkRunner.RESULT_DIR}/{os.path.basename(gamesFile)}')
                self.benchLines.append(f'Hasil Moves: {BenchmarkRunner.RESULT_DIR}/{os.path.basename(movesFile)}')
                self.benchLines.append(f'Kesimpulan Game: {BenchmarkRunner.RESULT_DIR}/{os.path.basename(self.benchmark.summaryFile)}')
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
        elif self.state == 'playmode':
            self.drawPlayMode(mousePos)
        elif self.state == 'difficulty':
            self.drawDifficulty(mousePos)
        elif self.state == 'benchmark':
            self.drawBenchmark(mousePos)
        elif self.state == 'benchrun':
            self.drawBenchRun(mousePos)
        elif self.state == 'benchresult':
            self.drawBenchResult(mousePos)
        elif self.state == 'tut':
            self.screen.fill((0, 0, 0))
            self.grid.drawGrid(self.screen)
            self.drawTutorialPanel()
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
        
    def drawTutorialPanel(self):
        # Get the cursor position
        mousePos = pygame.mouse.get_pos()
        # Take the tutorial steps that's needed
        step = TutorialData.TUTORIAL_STEPS[self.tutorialStep]
        pygame.draw.rect(self.screen, (35, 25, 15), (800, 0, 300, 800))
        pygame.draw.line(self.screen, (230, 200, 150), (800,0), (800, 800), 2)
        self.screen.blit(self.font.render(
            f'Step {self.tutorialStep + 1}/{len(TutorialData.TUTORIAL_STEPS)}', True, (230, 200, 150)
        ), (830, 60))
        
        # Loop for every text that's available
        for i, line in enumerate(step['text']):
            # Print the text in the UI (the tutorial text)
            self.screen.blit(self.smallFont.render(line, True, 'White'), (815, 130 + i * 36))
            
        # Check if the next button should appear ot not (if not, then the tutorial ends)
        if step['goal'] == 'next' or self.tutorialDone:
            # Draw the next button if not end and the tutorial still have steps
            self.tutorialButton['next'].draw(self.screen, self.font, mousePos)
        # Draw the button that directs back to the menu
        self.tutorialButton['menu'].draw(self.screen, self.font, mousePos)

    def drawCentered(self, text, font, y, color='White'):
        """Draw text horizontally centred at height y."""
        label = font.render(text, True, color)
        self.screen.blit(label, label.get_rect(center=(550, y)))

    def drawMenu(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('OTHELLO', self.titleFont, 220, (230, 200, 150))
        for button in self.menuButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawPlayMode(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Choose Mode', self.bigFont, 250, (230, 200, 150))
        for button in self.playModeButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawDifficulty(self, mousePos):
        self.screen.fill((35, 25, 15))
        style = 'Practice' if self.playStyle == 'practice' else 'Normal'
        self.drawCentered(f'{style}: Choose Difficulty', self.bigFont, 250, (230, 200, 150))
        for button in self.difficultyButtons.values():
            button.draw(self.screen, self.font, mousePos)

    def drawBenchmark(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Benchmark', self.bigFont, 200, (230, 200, 150))
        self.drawCentered('Warna bergantian tiap game (tanpa animasi)', self.smallFont, 260)
        for name, button in self.benchButtons.items():
            if self.benchButtonVisible(name):
                button.draw(self.screen, self.font, mousePos)

    def drawBenchRun(self, mousePos):
        # Get benchmark information on the total game and the current index of the game
        bm = self.benchmark
        done, total = bm.gameIndex, bm.totalGames

        # Papan game benchmark yang sedang berjalan (tanpa animasi flip)
        
        # Clear the screens to clear previous drawing
        self.screen.fill((0, 0, 0))
        # Draw the bg background
        self.screen.blit(self.grid.gridBg, (0, 0))
        # loop for each row
        for r in range(8):
            # loop for each column
            for c in range(8):
                # If that specific part of the board is not empty
                if bm.board[r][c] != 0:
                    # Placing the token based on the player
                    img = self.grid.whitetoken if bm.board[r][c] == 1 else self.grid.blacktoken
                    # Draws the token that's placed there
                    self.screen.blit(img, (80 + c * 80, 80 + r * 80))

        # Panel kanan
        white, black = self.grid.countTokens(bm.board)
        pygame.draw.rect(self.screen, (35, 25, 15), (800, 0, 300, 800))
        pygame.draw.line(self.screen, (230, 200, 150), (800, 0), (800, 800), 3)

        self.screen.blit(self.smallFont.render('Benchmark', True, (230, 200, 150)), (830, 65))
        self.screen.blit(self.font.render(f'Game {min(done + 1, total)} / {total}', True, 'White'), (830, 110))
        pygame.draw.rect(self.screen, (230, 200, 150), (830, 150, 240, 20), 3)
        pygame.draw.rect(self.screen, (130, 90, 45), (833, 153, int(234 * done / total), 14))

        whiteName = f'P1 {bm.shortLabel(1)}' if bm.p1White else f'P2 {bm.shortLabel(2)}'
        blackName = f'P2 {bm.shortLabel(2)}' if bm.p1White else f'P1 {bm.shortLabel(1)}'
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

        p1Wins = sum(g['winner'] == 'P1' for g in bm.games)
        p2Wins = sum(g['winner'] == 'P2' for g in bm.games)
        self.screen.blit(self.smallFont.render('So far', True, (230, 200, 150)), (830, 540))
        self.screen.blit(self.smallFont.render(f'P1 {bm.shortLabel(1)}: {p1Wins}', True, 'White'), (830, 575))
        self.screen.blit(self.smallFont.render(f'P2 {bm.shortLabel(2)}: {p2Wins}', True, 'White'), (830, 610))

        # Loop through every available button in the benchmark
        for button in self.benchRunButtons.values():
            # Draw the button
            button.draw(self.screen, self.font, mousePos)

    def drawBenchResult(self, mousePos):
        self.screen.fill((35, 25, 15))
        self.drawCentered('Benchmark Result', self.bigFont, 90, (230, 200, 150))
        # Loop for each lines that will be displayed on the result
        for i, line in enumerate(self.benchLines):
            label = self.smallFont.render(line, True, 'White')
            self.screen.blit(label, (100, 160 + i * 36))
        # Loop through every available button in the benchmark
        for button in self.benchResultButtons.values():
            # Draw the buttons
            button.draw(self.screen, self.font, mousePos)

    def drawScorePanel(self):
        """Right side panel (x = 800 to 1100): mode, current turn, and token counts."""
        if self.mode == 'ai' and self.playStyle == 'practice':
            self.drawPracticePanel()
            return
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

    # Loading the background image for the game board
    def loadBackGroundImages(self):
        """Cut every tile out of the wood sprite sheet and name it like 'A0', 'B1', ..."""
        alpha = 'ABCDEFGHI'
        # Load the sprite image for the baackground
        spriteSheet = pygame.image.load('assets/wood.png').convert_alpha()
        # Initialize the variable to store the sprite 
        imageDict = {}
        # looping for the wood.png sprite
        for i in range(3):          # sprite sheet rows
            for j in range(7):      # sprite sheet columns
                # Create dictionary based on the board name "C0","B0","B0" and etc then 
                # extract the image based on col j & row i and store the image
                imageDict[alpha[j] + str(i)] = loadSpriteSheet(spriteSheet, j, i, self.size, (32, 32))
        return imageDict

    # Creating the background image to the game
    def createbgimg(self):
        """Build one big background image: a 10x10 layout (8x8 board + border)."""
        # grid for the game
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
        # Create an empty surface for the board to be made
        image = pygame.Surface((10 * self.size[0], 10 * self.size[1]))
        # outer loop for the bg where j is index and row is the data
        for j, row in enumerate(gridBg):
            # inner loop where the i is index and the name for the to;e
            for i, name in enumerate(row):
                # Add the image onto the empty surface
                image.blit(self.bg[name], (i * self.size[0], j * self.size[1]))
        return image

    # ---------- Setup ----------

    def regenGrid(self, rows, columns):
        """Create an empty 8x8 logic grid and place the 4 starting tokens in the centre."""
        # Emptying the grid
        grid = [[0 for _ in range(columns)] for _ in range(rows)]
        # Placing the initial token for playing othello
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
        # Draw the board background onto the window
        window.blit(self.gridBg, (0, 0))

        # For each tokens in the grid, draw the token
        for token in self.tokens.values():
            token.draw(window)

        # Don't show markers during animation, game over, or the computer's turn
        # Validating if it's the player turn or the algorithm
        humanTurn = not (self.GAME.mode == 'ai' and self.GAME.currentPlayer == self.GAME.aiPlayer)
        # If it's not doing any animation, game is playing and is player turn
        if not self.animating and self.GAME.state == 'playing' and humanTurn:
            # Find all available moves of the player
            availMoves = self.findAvailMoves(self.gridLogic, self.GAME.currentPlayer)
            # Loop for every available moves of the player
            for (row, col) in availMoves:
                # Small white square in the middle of the cell
                pygame.draw.rect(window, 'White', (80 + col * 80 + 30, 80 + row * 80 + 30, 20, 20))
                
        # Highlight only the currently recommended legal square in Practice.
        # If it's in practice and not doing animation
        if (self.GAME.isPracticeTurn() and not self.animating
                # and view must set to answer
                and self.GAME.coachView == 'answer'
                # the cache is not none
                and self.GAME.coachCache is not None
                # the cache must be the same as current game
                and self.GAME.coachCacheKey == self.GAME.coachKey()):
            # Take the row and col for the advised movement from the coach
            row, col = self.GAME.coachCache['move']
            # make it to be a rectangle
            pygame.draw.rect(window, (0, 255, 0),
                             (80 + col * 80 + 3, 80 + row * 80 + 3, 74, 74),
                             5, border_radius=7)

        # If it's in a tutorial and it's not done
        if self.GAME.state == 'tut' and not self.animating and not self.GAME.tutorialDone:
            # Take the steps that available
            step = TutorialData.TUTORIAL_STEPS[self.GAME.tutorialStep]
            # If the step requires for moving
            if step['goal'] == 'move':
                # Take the row and column position for the placement of the disc
                r, c = step['target']
                # Highlight it
                pygame.draw.rect(window, (225, 220, 0), (80 + c * 80 + 25, 80 + r * 80 + 25, 30, 30))

    # Debugging for the Game Logic
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

        # Checking for cells that's affected, the disc shown is the final change.
        for cell in cells:                            # finish with the final token image
            self.tokens[cell].image = finalImage
        # End the state of animation
        self.animating = False
        
    # Loading the board game for the tutorials
    def loadBoardForTutorial(self, board, window=None):
        # Empty the tokens for the tutorial
        self.tokens = {}
        # Reset the logical board, make each row and column to be an empty position
        self.gridLogic = [[0] * self.x for _ in range(self.y)]
        # Loop for each row in y
        for r in range(self.y):
            # Loop for each column in x
            for c in range(self.x):
                # If the row and column position of the board is not empty
                if board[r][c] != 0:
                    # Insert the disc.
                    self.insertToken(self.gridLogic, board[r][c], r, c)
        # stop the animation for flipping the disc
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

    # Extracting the disc image using the blit
    def draw(self, window):
        window.blit(self.image, (self.posX, self.posY))

# =====================================================
# START THE GAME
# =====================================================

if __name__ == '__main__':
    game = Othello()
    game.run()
    pygame.quit()