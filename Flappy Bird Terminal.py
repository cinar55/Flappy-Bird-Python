"""
Flappy Bird - Terminal Edition (No curses, pure ANSI)
Works on Python 3.14+ Windows with no extra installs.
Controls: SPACE / ENTER = flap  |  Q / ESC = quit
"""

import sys
import os
import random
import time
import threading

# ── enable ANSI on Windows ─────────────────────────────────
if sys.platform == "win32":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# ── ANSI helpers ───────────────────────────────────────────
def ansi(*codes):
    return "\033[" + ";".join(str(c) for c in codes) + "m"

RESET   = ansi(0)
BOLD    = ansi(1)

# foreground colors
FG_BLACK   = ansi(30)
FG_RED     = ansi(31)
FG_GREEN   = ansi(32)
FG_YELLOW  = ansi(33)
FG_BLUE    = ansi(34)
FG_CYAN    = ansi(36)
FG_WHITE   = ansi(37)

# background colors
BG_BLACK   = ansi(40)
BG_RED     = ansi(41)
BG_GREEN   = ansi(42)
BG_YELLOW  = ansi(43)
BG_BLUE    = ansi(44)
BG_CYAN    = ansi(46)
BG_WHITE   = ansi(47)

SKY    = BG_BLUE   + FG_CYAN
GROUND = BG_GREEN  + FG_WHITE  + BOLD
PIPE   = BG_GREEN  + FG_WHITE  + BOLD
BIRD   = BG_BLUE   + FG_YELLOW + BOLD
SCORE  = BG_BLUE   + FG_WHITE  + BOLD
GOLD   = BG_BLACK  + FG_YELLOW + BOLD
UI     = BG_BLACK  + FG_WHITE
BORDER = BG_BLACK  + FG_YELLOW + BOLD

def goto(r, c):
    return f"\033[{r+1};{c+1}H"

def clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()

def term_size():
    try:
        size = os.get_terminal_size()
        return size.lines, size.columns
    except Exception:
        return 30, 80

# ── non-blocking keyboard (Windows) ───────────────────────
if sys.platform == "win32":
    import msvcrt

    _key_buf = []
    _key_lock = threading.Lock()

    def _key_reader():
        while True:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                with _key_lock:
                    _key_buf.append(ch)
            time.sleep(0.005)

    _reader_thread = threading.Thread(target=_key_reader, daemon=True)
    _reader_thread.start()

    def get_key():
        with _key_lock:
            if _key_buf:
                return _key_buf.pop(0)
        return None
else:
    import tty, termios, select

    def get_key():
        dr, _, _ = select.select([sys.stdin], [], [], 0)
        if dr:
            return sys.stdin.read(1)
        return None

# ─── SETTINGS ─────────────────────────────────────────────
FPS        = 24
GRAVITY    = 0.18
FLAP_FORCE = -1.3
MAX_FALL   = 2.2
PIPE_SPEED = 0.14
PIPE_GAP   = 7
PIPE_INTER = 3.8
BIRD_COL   = 6

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)

# ─── GAME ─────────────────────────────────────────────────
class Flappy:
    def __init__(self):
        self.H, self.W = term_size()
        self.gr    = self.H - 3
        self.best  = 0
        self.state = "start"
        self.init_game()
        log(f"=== Flappy Bird Starting === terminal={self.W}x{self.H}")

    def init_game(self):
        self.bird_yf   = float(self.gr // 2)
        self.bird_y    = int(self.bird_yf)
        self.bird_vy   = 0.0
        self.pipes     = []
        self.score     = 0
        self.alive     = True
        self.last_pipe = time.time() - 1.5
        self.tick      = 0

    def run(self):
        hide_cursor()
        clear_screen()
        interval = 1.0 / FPS
        try:
            while True:
                t0 = time.perf_counter()
                self.H, self.W = term_size()
                self.gr = self.H - 3

                self.handle_input()
                self.update()
                self.render()

                elapsed = time.perf_counter() - t0
                sleep = interval - elapsed
                if sleep > 0:
                    time.sleep(sleep)
        except KeyboardInterrupt:
            pass
        finally:
            show_cursor()
            clear_screen()
            log("=== Game Closed ===")

    def handle_input(self):
        key = get_key()
        if key is None:
            return

        k = key.lower() if len(key) == 1 else key

        if k in ('q', '\x1b'):   # q or ESC
            log("=== Quit ===")
            show_cursor()
            clear_screen()
            sys.exit(0)

        if k in (' ', '\r', '\n', 'w'):
            if self.state == "start":
                log(">>> Game started")
                self.state = "play"
            elif self.state == "play":
                self.bird_vy = FLAP_FORCE
                log(f"  Flap | row={self.bird_y}")
            elif self.state == "dead":
                log(f">>> Restarted | last={self.score} best={self.best}")
                self.init_game()
                self.state = "play"

    def update(self):
        self.tick += 1
        if self.state != "play":
            return

        self.bird_vy  += GRAVITY
        self.bird_vy   = max(min(self.bird_vy, MAX_FALL), -MAX_FALL)
        self.bird_yf  += self.bird_vy
        self.bird_y    = int(self.bird_yf)

        if self.bird_y >= self.gr - 1:
            self.bird_y = self.gr - 1
            log(f"  Hit ground | score={self.score}")
            self._die()
            return

        if self.bird_y <= 0:
            self.bird_yf = 0.0
            self.bird_y  = 0
            self.bird_vy = 0

        now = time.time()
        if now - self.last_pipe > PIPE_INTER:
            top = random.randint(2, self.gr - PIPE_GAP - 3)
            self.pipes.append({"xf": float(self.W - 1),
                                "top": top,
                                "bot": top + PIPE_GAP,
                                "passed": False})
            self.last_pipe = now
            log(f"  New pipe | top={top} bot={top+PIPE_GAP}")

        bx = BIRD_COL
        by = self.bird_y
        for p in self.pipes:
            p["xf"] -= PIPE_SPEED * (60 / FPS)
            px = int(p["xf"])
            if bx >= px and bx <= px + 1:
                if by <= p["top"] or by >= p["bot"]:
                    log(f"  Hit pipe | y={by} top={p['top']} bot={p['bot']}")
                    self._die()
                    return
            if not p["passed"] and px + 1 < bx:
                p["passed"] = True
                self.score += 1
                log(f"  Pipe cleared | score={self.score}")

        self.pipes = [p for p in self.pipes if int(p["xf"]) > -4]

    def _die(self):
        if self.alive:
            self.alive = False
            self.state = "dead"
            self.best  = max(self.best, self.score)
            log(f">>> DIED | score={self.score} best={self.best}")

    def render(self):
        H, W, gr = self.H, self.W, self.gr
        buf = []

        def put(r, c, text, style=""):
            if 0 <= r < H and 0 <= c < W - 1:
                clipped = text[:max(0, W - c - 1)]
                buf.append(goto(r, c) + style + clipped + RESET)

        def hline(r, c, ch, n, style=""):
            if 0 <= r < H and n > 0:
                n = min(n, W - c - 1)
                buf.append(goto(r, c) + style + ch * n + RESET)

        # ── sky ──
        for r in range(gr):
            hline(r, 0, ' ', W, SKY)

        # ── clouds ──
        for cx in [6, 22, 42, 60]:
            cc = (cx - self.tick // 12) % max(1, W)
            put(2, cc, "~~~", SKY + FG_WHITE)

        # ── pipes ──
        for p in self.pipes:
            px = int(p["xf"])
            if not (0 <= px < W):
                continue
            for r in range(p["top"]):
                put(r, px,   "||", PIPE)
            for r in range(p["bot"], gr):
                put(r, px,   "||", PIPE)
            cap = max(0, px - 1)
            if p["top"] > 0:
                put(p["top"] - 1, cap, "[==]", PIPE)
            if p["bot"] < gr:
                put(p["bot"],     cap, "[==]", PIPE)

        # ── ground ──
        for c in range(0, W - 1, 3):
            put(gr, c, "^", GROUND)
        hline(gr,   0, '-', W, GROUND)
        hline(gr+1, 0, '=', W, GROUND)
        if gr + 2 < H:
            hline(gr+2, 0, '#', W, GROUND)

        # ── bird ──
        frames = [">o>", ">O>", ">0>"]
        if self.state == "dead":
            bstr = "x_x"
        else:
            bstr = frames[(self.tick // 5) % 3]
        put(self.bird_y, BIRD_COL, bstr, BIRD)

        # ── score ──
        sc = f" Score: {self.score} "
        put(0, W // 2 - len(sc) // 2, sc, SCORE)
        bs = f" Best: {self.best} "
        put(0, W - len(bs) - 1, bs, GOLD)

        # ── hint ──
        hint = " SPACE/ENTER: Flap   Q/ESC: Quit "
        put(H - 1, max(0, W // 2 - len(hint) // 2), hint, UI)

        # ── start overlay ──
        if self.state == "start":
            self._box(buf, H//2 - 4, W//2 - 16, 7, 32)
            put(H//2 - 3, W//2 - 7,  "  FLAPPY BIRD  ",          BORDER)
            put(H//2 - 1, W//2 - 12, " SPACE / ENTER to start ", UI)
            put(H//2 + 1, W//2 - 7,  "  Q / ESC to quit  ",      UI)

        # ── dead overlay ──
        if self.state == "dead":
            self._box(buf, H//2 - 5, W//2 - 16, 9, 32)
            put(H//2 - 4, W//2 - 6,  "  GAME OVER  ",                  BORDER)
            put(H//2 - 2, W//2 - 9,  f"  Score : {self.score:<5}  ",   UI)
            put(H//2 - 0, W//2 - 9,  f"  Best  : {self.best:<5}  ",    GOLD)
            put(H//2 + 2, W//2 - 13, " SPACE / ENTER to restart ",     UI)

        sys.stdout.write("".join(buf))
        sys.stdout.flush()

    def _box(self, buf, top, left, h, w):
        def put(r, c, text, style):
            if 0 <= r < self.H and 0 <= c < self.W - 1:
                buf.append(goto(r, c) + style + text[:max(0, self.W-c-1)] + RESET)

        def hline(r, c, ch, n, style):
            if 0 <= r < self.H and n > 0:
                n = min(n, self.W - c - 1)
                buf.append(goto(r, c) + style + ch * n + RESET)

        for r in range(top + 1, top + h - 1):
            hline(r, left + 1, ' ', w - 2, UI)
        put(top,       left, '+' + '-' * (w - 2) + '+', BORDER)
        put(top + h-1, left, '+' + '-' * (w - 2) + '+', BORDER)
        for r in range(top + 1, top + h - 1):
            put(r, left,       '|', BORDER)
            put(r, left+w - 1, '|', BORDER)


if __name__ == "__main__":
    log("=== Flappy Bird Terminal (ANSI) ===")
    game = Flappy()
    game.run()