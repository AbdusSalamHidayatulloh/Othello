import pygame

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
    image = pygame.Surface(size).convert_alpha()               # empty surface for one tile
    image.blit(sheet, (0, 0), (col * size[0], row * size[1], size[0], size[1]))  # copy the tile
    image = pygame.transform.scale(image, newSize)             # scale up
    image.set_colorkey('Black')                                # black becomes transparent
    return image


# =====================================================
# MAIN GAME CLASS
# =====================================================

class Othello:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((1100, 800))
        pygame.display.set_caption('Othello')

        # Player values used in the logic grid: 1 = white, -1 = black, 0 = empty
        self.player1 = 1
        self.player2 = -1
        self.currentPlayer = 1          # white starts

        self.rows = 8
        self.columns = 8

        # The Grid handles the board, tokens, rules and animation
        self.grid = Grid(self.rows, self.columns, (80, 80), self)
        self.RUN = True

    def run(self):
        """Main game loop: input -> update -> draw, repeated forever."""
        while self.RUN:
            self.input()
            self.update()
            self.draw()

    def input(self):
        """Handle window close and mouse clicks."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.RUN = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                # Right click: print the logic board in the terminal (for debugging)
                if event.button == 3:
                    self.grid.printGameLogicBoard()

                # Left click: try to play a move
                if event.button == 1:
                    mouseX, mouseY = pygame.mouse.get_pos()
                    # Convert pixel position to board cell.
                    # The board starts at pixel (80, 80) and each cell is 80x80.
                    col = (mouseX - 80) // 80
                    row = (mouseY - 80) // 80

                    # Real legal moves for the current player
                    validCells = self.grid.findAvailMoves(self.grid.gridLogic, self.currentPlayer)

                    if (row, col) in validCells:
                        self.playMove(row, col)

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

        # 5. Next player's turn
        self.currentPlayer *= -1

    def update(self):
        """Reserved for future game logic (score, game over, AI, ...)."""
        pass

    def draw(self):
        """Clear the screen, draw the board, show it."""
        self.screen.fill((0, 0, 0))
        self.grid.drawGrid(self.screen)
        pygame.display.update()


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

        # tokens: dictionary {(row, col): Token} -> what gets drawn on screen
        self.tokens = {}
        # gridLogic: 8x8 list of 0 / 1 / -1 -> what the rules use
        self.gridLogic = self.regenGrid(self.y, self.x)

        # While True, the white "available move" markers are hidden
        self.animating = False

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

    # ---------- Drawing ----------

    def drawGrid(self, window):
        """Draw background, all tokens, and markers showing the legal moves."""
        window.blit(self.gridBg, (0, 0))

        for token in self.tokens.values():
            token.draw(window)

        # Don't show move markers while the flip animation is playing
        if not self.animating:
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
            # If we left the board without finding our own token, currentLine is ignored
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
            pygame.time.delay(100)                    # milliseconds per frame (raise to slow down)

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