import pygame
import random

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
# AI AGENTS (EMPTY FOR NOW - GROUP MEMBERS WILL FILL THESE IN)
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
        userCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == player)
        cpuCorner = sum(1 for (row, column) in self.CORNERS if grid[row][column] == -player)
        return cpuCorner - userCorner

    def mobilityScore(self, grid, player):
        userMobility = len(self.rules.findAvailMoves(grid, player))
        cpuMobility = len(self.rules.findAvailMoves(grid, -player))
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
    """Hard difficulty: Minimax with Alpha-Beta Pruning."""
    def __init__(self, rules, depth=4):
        self.rules = rules
        self.depth = depth

    def getMove(self, gridLogic, player):
        # TODO: implement Alpha-Beta Pruning
        # Placeholder so the game is playable: pick a random legal move.
        moves = self.rules.findAvailMoves(gridLogic, player)
        return random.choice(moves) if moves else None


# =====================================================
# MAIN GAME CLASS
# =====================================================

class Othello:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1100, 800))
        pygame.display.set_caption('Othello')
        self.clock = pygame.time.Clock()

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
        # state: 'menu' | 'difficulty' | 'playing' | 'gameover'
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
            '1v1':  Button('1 vs 1',        (cx, 380)),
            'ai':   Button('1 vs Computer', (cx, 470)),
            'quit': Button('Quit',          (cx, 560)),
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
            else:
                self.message = f'{skipped} has no moves, turn skipped'
        else:
            self.message = ''

    def playerName(self, player):
        return 'White' if player == 1 else 'Black'

    # ---------- Input ----------

    def input(self):
        """Handle window close and mouse clicks for every screen."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.RUN = False

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
                        self.clickBoard(event.pos)
                    elif self.state == 'gameover':
                        self.clickGameOver(event.pos)

    def clickMenu(self, pos):
        if self.menuButtons['1v1'].isClicked(pos):
            self.startGame('1v1')
        elif self.menuButtons['ai'].isClicked(pos):
            self.state = 'difficulty'
        elif self.menuButtons['quit'].isClicked(pos):
            self.RUN = False

    def clickDifficulty(self, pos):
        if self.difficultyButtons['easy'].isClicked(pos):
            self.startGame('ai', 'easy')
        elif self.difficultyButtons['hard'].isClicked(pos):
            self.startGame('ai', 'hard')
        elif self.difficultyButtons['back'].isClicked(pos):
            self.state = 'menu'

    def clickGameOver(self, pos):
        if self.gameOverButtons['retry'].isClicked(pos):
            self.startGame(self.mode, self.difficulty)   # same settings as before
        elif self.gameOverButtons['menu'].isClicked(pos):
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

    # ---------- Playing a move ----------

    def playMove(self, row, col):
        """Place a token, flip the captured tokens (with animation), switch turn."""
        grid = self.grid

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

        # 5. Next player's turn (also handles skipped turns and game over)
        self.nextTurn()
        self.lastMoveTime = pygame.time.get_ticks()

    # ---------- Update ----------

    def update(self):
        """Runs every frame. Used here to let the computer play its turn."""
        if self.state == 'playing' and self.mode == 'ai' and self.currentPlayer == self.aiPlayer:
            # Wait 600 ms so the computer's move doesn't happen instantly
            if pygame.time.get_ticks() - self.lastMoveTime >= 600:
                move = self.agent.getMove(self.grid.gridLogic, self.aiPlayer)
                if move is not None:
                    self.playMove(move[0], move[1])

    # ---------- Drawing ----------

    def draw(self):
        """Clear the screen, draw whichever screen is active, show it."""
        mousePos = pygame.mouse.get_pos()

        if self.state == 'menu':
            self.drawMenu(mousePos)
        elif self.state == 'difficulty':
            self.drawDifficulty(mousePos)
        else:
            # 'playing' and 'gameover' both show the board
            self.screen.fill((0, 0, 0))
            self.grid.drawGrid(self.screen)
            self.drawScorePanel()
            if self.state == 'gameover':
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
            self.screen.blit(self.smallFont.render(self.message, True, (255, 200, 100)), (815, 600))

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