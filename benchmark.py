from statistics import mean

from main import Grid, BenchmarkRunner   # main.py tidak menjalankan game saat di-import

# Data awalan,
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

# Membuat sebuah progress bar untuk benchmark
def progressLine(runner):
    """Satu baris progress untuk game yang sedang berjalan."""
    # Kalkulasi progress game
    p = max(0.0, min(1.0, runner.gameProgress()))
    # Menghitung seberapa banyak bagian yang terisi pada bar
    filled = int(BAR_WIDTH * p)
    # Bar dalam bentuk plainteks
    bar = '#' * filled + '-' * (BAR_WIDTH - filled)
    # Menentukkan siapa yang duluan antara AB atau GBFS
    who = 'AB' if runner.abFirst else 'GBFS'
    return (f'Game {runner.gameIndex + 1:>3}/{runner.totalGames} | [{bar}] {p * 100:3.0f}% | '
            f'{runner.discCount():>2}/64 discs | putih: {who}')

# Menjalankan  keseluruhan benchmark untuk depth Alpha-Beta
def runDepth(depth):
    """Jalankan satu rangkaian benchmark untuk satu depth, lalu return runner-nya."""
    runner = BenchmarkRunner(HeadlessRules(), GAMES, depth)
    print(f'\n===== Alpha-Beta depth {depth} vs GBFS | {GAMES} game =====')

    # Inisiasi data
    shown = 0
    lastDiscs = -1
    # Jalankan looping untuk benchmark sampai game selesai
    while not runner.finished:
        runner.step()

        # Apabila satu game sesi selesai, masuk ke kode
        if runner.gameIndex > shown:               # satu game baru selesai -> cetak hasilnya
            # Ambil data terakhir
            g = runner.games[-1]
            # Print datanya
            print(f'\rGame {g["game"]:>3}/{GAMES} | AB jalan {"duluan" if g["abFirst"] else "kedua "} | '
                  f'AB {g["abDiscs"]:>2} - {g["gbDiscs"]:>2} GBFS | {g["winner"]}'.ljust(100))
            # Shown akan menjadi tracking jumlah game
            shown = runner.gameIndex
            # Menghitung jumlah disc yang terpasang
            lastDiscs = -1
        # Apabila permainan belum selesai dan discnya tidak sama dengan permainan sebelumnya
        elif not runner.finished and runner.discCount() != lastDiscs:
            # last discs akan diupdate menjadi jumlah disk terbaru
            lastDiscs = runner.discCount()         # update progress hanya saat papan berubah
            # Update progressbarnya
            print('\r' + progressLine(runner), end='', flush=True)

    # Menampilkan hasil akhirnya
    print()
    # Looping untuk setiap hasil benchmark yang ada
    for line in runner.summaryLines():
        print(line)
    # Simpan datanya
    gamesFile, movesFile = runner.saveCsv()
    print(f'CSV disimpan: {gamesFile}, {movesFile}')
    return runner

# Menampilkan hasil pertimbangan (apabila sudah selesai)
def printComparisonTable(runners):
    """Satu tabel berisi semua depth, siap disalin ke proposal."""
    print('\n' + '=' * 100)
    print('TABEL PERBANDINGAN (Alpha-Beta vs GBFS)')
    print('=' * 100)
    # Menampilkan summary dari benchmark (sama dengan UI di main.py)
    print(f'{"Depth":<6}{"AB win%":>9}{"GBFS win%":>11}{"Draw%":>8}{"Avg margin":>12}'
          f'{"AB ms/move":>12}{"GBFS ms/move":>14}{"AB nodes":>10}{"AB cutoff":>11}')
    print('-' * 100)

    # Untuk setiap permainan yang ada, masukkan datanya ke variabel yang ada
    for r in runners:
        # Jumlah game
        n = len(r.games)
        # Jumlah AB menang
        ab = sum(g['winner'] == 'AlphaBeta' for g in r.games)
        # Jumlah GBFS menang
        gb = sum(g['winner'] == 'GBFS' for g in r.games)
        # Jumlah serinya
        draw = n - ab - gb
        # Margin diantara 3 algoritma
        margin = mean(abs(g['abDiscs'] - g['gbDiscs']) for g in r.games)

        # Waktu AB berpikir
        abTime = mean(m[1] * 1000 for m in r.moves if m[0] == 'AlphaBeta')
        # Waktu GBFS berpikir
        gbTime = mean(m[1] * 1000 for m in r.moves if m[0] == 'GBFS')
        # Jumlah node AB
        abNodes = mean(m[2] for m in r.moves if m[0] == 'AlphaBeta')
        # Jumlah pruning AB
        abCuts = mean(m[3] for m in r.moves if m[0] == 'AlphaBeta')

        # Data statistik akan diprint satu satu selama game berjalan
        print(f'{r.depth:<6}{ab / n * 100:>8.1f}%{gb / n * 100:>10.1f}%{draw / n * 100:>7.1f}%'
              f'{margin:>12.2f}{abTime:>12.2f}{gbTime:>14.2f}{abNodes:>10.1f}{abCuts:>11.1f}')
    print('=' * 100)

# Mengecek apabila file ini dijalankan
if __name__ == '__main__':
    # Jika dirun, jalankan semua depths
    results = [runDepth(d) for d in DEPTHS]
    # Print hasilnya
    printComparisonTable(results)