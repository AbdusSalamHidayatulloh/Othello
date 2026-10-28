from statistics import mean

from main import Grid, BenchmarkRunner   # main.py tidak menjalankan game saat di-import

# ================== PENGATURAN ==================
GAMES = 100            # 50 game Alpha-Beta jalan duluan + 50 game GBFS jalan duluan
DEPTHS = [2, 3, 4]     # tiap depth diuji terpisah, lalu dibandingkan di tabel akhir
BAR_WIDTH = 30         # lebar progress bar di console
# Tes cepat dulu: GAMES = 4, DEPTHS = [2]
# =================================================


class HeadlessRules:
    """Meminjam fungsi aturan dari Grid supaya tidak perlu membuka window pygame."""
    findValidCells = Grid.findValidCells
    swappableTiles = Grid.swappableTiles
    findAvailMoves = Grid.findAvailMoves
    countTokens = Grid.countTokens


def progressLine(runner):
    """Satu baris progress untuk game yang sedang berjalan."""
    p = max(0.0, min(1.0, runner.gameProgress()))
    filled = int(BAR_WIDTH * p)
    bar = '#' * filled + '-' * (BAR_WIDTH - filled)
    who = 'AB' if runner.abFirst else 'GBFS'
    return (f'Game {runner.gameIndex + 1:>3}/{runner.totalGames} | [{bar}] {p * 100:3.0f}% | '
            f'{runner.discCount():>2}/64 discs | putih: {who}')


def runDepth(depth):
    """Jalankan satu rangkaian benchmark untuk satu depth, lalu return runner-nya."""
    runner = BenchmarkRunner(HeadlessRules(), GAMES, depth)
    print(f'\n===== Alpha-Beta depth {depth} vs GBFS | {GAMES} game =====')

    shown = 0
    lastDiscs = -1
    while not runner.finished:
        runner.step()

        if runner.gameIndex > shown:               # satu game baru selesai -> cetak hasilnya
            g = runner.games[-1]
            print(f'\rGame {g["game"]:>3}/{GAMES} | AB jalan {"duluan" if g["abFirst"] else "kedua "} | '
                  f'AB {g["abDiscs"]:>2} - {g["gbDiscs"]:>2} GBFS | {g["winner"]}'.ljust(100))
            shown = runner.gameIndex
            lastDiscs = -1
        elif not runner.finished and runner.discCount() != lastDiscs:
            lastDiscs = runner.discCount()         # update progress hanya saat papan berubah
            print('\r' + progressLine(runner), end='', flush=True)

    print()
    for line in runner.summaryLines():
        print(line)
    gamesFile, movesFile = runner.saveCsv()
    print(f'CSV disimpan: {gamesFile}, {movesFile}')
    return runner


def printComparisonTable(runners):
    """Satu tabel berisi semua depth, siap disalin ke proposal."""
    print('\n' + '=' * 100)
    print('TABEL PERBANDINGAN (Alpha-Beta vs GBFS)')
    print('=' * 100)
    print(f'{"Depth":<6}{"AB win%":>9}{"GBFS win%":>11}{"Draw%":>8}{"Avg margin":>12}'
          f'{"AB ms/move":>12}{"GBFS ms/move":>14}{"AB nodes":>10}{"AB cutoff":>11}')
    print('-' * 100)

    for r in runners:
        n = len(r.games)
        ab = sum(g['winner'] == 'AlphaBeta' for g in r.games)
        gb = sum(g['winner'] == 'GBFS' for g in r.games)
        draw = n - ab - gb
        margin = mean(abs(g['abDiscs'] - g['gbDiscs']) for g in r.games)

        abTime = mean(m[1] * 1000 for m in r.moves if m[0] == 'AlphaBeta')
        gbTime = mean(m[1] * 1000 for m in r.moves if m[0] == 'GBFS')
        abNodes = mean(m[2] for m in r.moves if m[0] == 'AlphaBeta')
        abCuts = mean(m[3] for m in r.moves if m[0] == 'AlphaBeta')

        print(f'{r.depth:<6}{ab / n * 100:>8.1f}%{gb / n * 100:>10.1f}%{draw / n * 100:>7.1f}%'
              f'{margin:>12.2f}{abTime:>12.2f}{gbTime:>14.2f}{abNodes:>10.1f}{abCuts:>11.1f}')
    print('=' * 100)


if __name__ == '__main__':
    results = [runDepth(d) for d in DEPTHS]
    printComparisonTable(results)