import tkinter as tk
import random
import math
import time

# ─── SETTINGS ──────────────────────────────────────────────
W, H        = 480, 640
GROUND_H    = 80
FPS         = 60
GRAVITY     = 0.72
FLAP_FORCE  = -10.0
MAX_FALL    = 14
PIPE_SPEED  = 2.6
PIPE_GAP    = 175
PIPE_W      = 62
PIPE_INTER  = 2400
BIRD_X      = 110

C = dict(
    sky1="#5BB8FF", sky2="#B8DEFF",
    ground1="#56A832", ground2="#72C840", ground3="#7B4F1A",
    pipe1="#2E9E2E", pipe2="#1E7A1E", pipe3="#50D050",
    bird="#FFD700", wing="#FFAA00", eye="#FFFFFF",
    pupil="#141414", beak="#FF8C00", blush="#FFB0B0",
    sun="#FFE050", cloud="#FFFFFF",
    white="#FFFFFF", black="#000000",
    gold="#FFD700",
)

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


class FlappyApp:
    def __init__(self, root):
        self.root = root
        root.title("Flappy Bird")
        root.resizable(True, True)
        root.configure(bg="black")

        self.fullscreen = False
        self.scale  = 1.0
        self.off_x  = 0
        self.off_y  = 0

        self.canvas = tk.Canvas(root, width=W, height=H, bg="black",
                                highlightthickness=0)
        self.canvas.pack(expand=True, fill=tk.BOTH)

        root.bind("<space>",     self.on_input)
        root.bind("<Button-1>",  self.on_input)
        root.bind("<Return>",    self.on_input)
        root.bind("<F11>",       self.toggle_fullscreen)
        root.bind("<Escape>",    self.exit_fullscreen)
        root.bind("<Configure>", self.on_resize)

        self.best       = 0
        self.state      = "start"
        self.wing_phase = 0.0
        self.ground_off = 0
        self.clouds     = [{"x": random.randint(0, W),
                             "y": random.randint(20, 140),
                             "s": random.uniform(0.8, 1.5),
                             "sp": random.uniform(0.3, 0.7)} for _ in range(6)]
        self.init_game()
        log("=== Flappy Bird Starting ===")
        log(f"Settings: gravity={GRAVITY} flap={FLAP_FORCE} pipe_interval={PIPE_INTER}ms gap={PIPE_GAP}px")
        self._loop()

    def toggle_fullscreen(self, event=None):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        log(f"Fullscreen: {'ON' if self.fullscreen else 'OFF'}")

    def exit_fullscreen(self, event=None):
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)
            log("ESC -> exited fullscreen")

    def on_resize(self, event=None):
        if event and event.widget != self.root:
            return
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        if rw < 10 or rh < 10:
            return
        self.scale = min(rw / W, rh / H)
        self.off_x = (rw - W * self.scale) / 2
        self.off_y = (rh - H * self.scale) / 2

    def tx(self, x): return self.off_x + x * self.scale
    def ty(self, y): return self.off_y + y * self.scale

    def init_game(self):
        self.bird_y    = H // 2
        self.bird_vy   = 0.0
        self.pipes     = []
        self.score     = 0
        self.alive     = True
        self.last_pipe = int(time.time() * 1000) - 800

    def on_input(self, event=None):
        if self.state == "start":
            log(">>> Game started")
            self.state = "play"
        elif self.state == "play":
            self.bird_vy    = FLAP_FORCE
            self.wing_phase = 0
            log(f"  Flap | y={self.bird_y:.1f}")
        elif self.state == "dead":
            log(f">>> Restarted | last_score={self.score} best={self.best}")
            self.init_game()
            self.state = "play"

    def _loop(self):
        t0 = time.perf_counter()
        self.update()
        self.draw()
        elapsed = int((time.perf_counter() - t0) * 1000)
        delay   = max(1, 1000 // FPS - elapsed)
        self.root.after(delay, self._loop)

    def update(self):
        self.ground_off = (self.ground_off + PIPE_SPEED) % W
        self.wing_phase += 0.20

        for c in self.clouds:
            c["x"] -= c["sp"]
        self.clouds = [c for c in self.clouds if c["x"] > -120]
        if random.random() < 0.007:
            self.clouds.append({"x": W + 60,
                                "y": random.randint(20, 140),
                                "s": random.uniform(0.8, 1.5),
                                "sp": random.uniform(0.3, 0.7)})

        if self.state != "play":
            return

        self.bird_vy += GRAVITY
        self.bird_vy  = max(min(self.bird_vy, MAX_FALL), -MAX_FALL)
        self.bird_y  += self.bird_vy

        if self.bird_y >= H - GROUND_H - 16:
            self.bird_y = H - GROUND_H - 16
            log(f"  Hit ground | score={self.score}")
            self._die()
            return

        if self.bird_y <= 10:
            self.bird_y  = 10
            self.bird_vy = 0

        now = int(time.time() * 1000)
        if now - self.last_pipe > PIPE_INTER:
            top_h = random.randint(90, H - GROUND_H - PIPE_GAP - 90)
            self.pipes.append({"x": W + 10, "top": top_h,
                               "bot": top_h + PIPE_GAP, "passed": False})
            self.last_pipe = now
            log(f"  New pipe spawned | top={top_h} bot={top_h+PIPE_GAP}")

        bx1 = BIRD_X - 16; bx2 = BIRD_X + 16
        by1 = self.bird_y - 12; by2 = self.bird_y + 12

        for p in self.pipes:
            p["x"] -= PIPE_SPEED
            if bx2 > p["x"] - 4 and bx1 < p["x"] + PIPE_W + 4:
                if by1 < p["top"] or by2 > p["bot"]:
                    log(f"  Hit pipe | bird_y={self.bird_y:.1f} top={p['top']} bot={p['bot']}")
                    self._die()
                    return
            if not p["passed"] and p["x"] + PIPE_W < BIRD_X:
                p["passed"] = True
                self.score += 1
                log(f"  Pipe cleared | score={self.score}")

        self.pipes = [p for p in self.pipes if p["x"] > -PIPE_W - 20]

    def _die(self):
        if self.alive:
            self.alive = False
            self.state = "dead"
            self.best  = max(self.best, self.score)
            log(f">>> DIED | score={self.score} best={self.best}")

    def draw(self):
        self.canvas.delete("all")
        self._draw_sky()
        self._draw_sun()
        for c in self.clouds:
            self._draw_cloud(c["x"], c["y"], c["s"])
        for p in self.pipes:
            self._draw_pipe(p["x"], p["top"], p["bot"])
        self._draw_ground()
        self._draw_bird(BIRD_X, int(self.bird_y))
        if self.state in ("play", "dead"):
            self._draw_score(self.score)
        if self.state == "start":
            self._draw_start()
        if self.state == "dead":
            self._draw_panel(self.score, self.best)

    # ── helpers ─────────────────────────────────────────────
    def _r(self, x, y, x2, y2, **kw):
        self.canvas.create_rectangle(
            self.tx(x), self.ty(y), self.tx(x2), self.ty(y2), **kw)

    def _o(self, x, y, x2, y2, **kw):
        self.canvas.create_oval(
            self.tx(x), self.ty(y), self.tx(x2), self.ty(y2), **kw)

    def _p(self, pts, **kw):
        sc = []
        for i in range(0, len(pts), 2):
            sc += [self.tx(pts[i]), self.ty(pts[i+1])]
        self.canvas.create_polygon(sc, **kw)

    def _t(self, x, y, font_size=14, bold=False, **kw):
        sz = max(6, int(font_size * self.scale))
        kw["font"] = ("Arial", sz, "bold" if bold else "normal")
        self.canvas.create_text(self.tx(x), self.ty(y), **kw)

    def _l(self, x1, y1, x2, y2, width=1, **kw):
        self.canvas.create_line(
            self.tx(x1), self.ty(y1), self.tx(x2), self.ty(y2),
            width=max(1, width * self.scale), **kw)

    # ── visuals ─────────────────────────────────────────────
    def _draw_sky(self):
        sky_h = H - GROUND_H
        for i in range(20):
            t = i / 20
            r = int(0x5B + (0xB8 - 0x5B) * t)
            g = int(0xB8 + (0xDE - 0xB8) * t)
            self._r(0, sky_h*i/20, W, sky_h*(i+1)/20,
                    fill=f"#{r:02x}{g:02x}ff", outline="")

    def _draw_sun(self):
        cx, cy = 56, 56
        self._o(cx-32, cy-32, cx+32, cy+32, fill="#FFEE88", outline="")
        self._o(cx-24, cy-24, cx+24, cy+24, fill=C["sun"],  outline="")
        for i in range(8):
            a = math.radians(i * 45)
            self._l(cx+28*math.cos(a), cy+28*math.sin(a),
                    cx+42*math.cos(a), cy+42*math.sin(a),
                    fill=C["sun"], width=3)

    def _draw_cloud(self, x, y, s):
        for dx, dy, w, h in [(0,0,40,22),(28,-14,34,28),(-14,-8,32,24),(34,-2,28,20)]:
            self._o(x+dx*s, y+dy*s, x+(dx+w)*s, y+(dy+h)*s,
                    fill=C["cloud"], outline="")

    def _draw_pipe(self, x, top_h, bot_y):
        pw, cap_h = PIPE_W, 18
        cx2, cw   = x - 5, pw + 10
        gnd       = H - GROUND_H
        self._r(x, 0, x+pw, top_h, fill=C["pipe1"], outline="")
        self._r(x+pw-10, 0, x+pw, top_h, fill=C["pipe3"], outline="")
        self._r(cx2, top_h-cap_h, cx2+cw, top_h, fill=C["pipe1"], outline="")
        self._r(x+pw-6, top_h-cap_h, x+pw, top_h, fill=C["pipe3"], outline="")
        self._r(cx2, top_h-cap_h, cx2+cw, top_h-cap_h+3, fill=C["pipe2"], outline="")
        self._r(x, bot_y, x+pw, gnd, fill=C["pipe1"], outline="")
        self._r(x+pw-10, bot_y, x+pw, gnd, fill=C["pipe3"], outline="")
        self._r(cx2, bot_y, cx2+cw, bot_y+cap_h, fill=C["pipe1"], outline="")
        self._r(x+pw-6, bot_y, x+pw, bot_y+cap_h, fill=C["pipe3"], outline="")
        self._r(cx2, bot_y+cap_h-3, cx2+cw, bot_y+cap_h, fill=C["pipe2"], outline="")

    def _draw_ground(self):
        gy  = H - GROUND_H
        off = int(self.ground_off)
        self._r(0, gy, W, H, fill=C["ground3"], outline="")
        self._r(0, gy, W, gy+18, fill=C["ground2"], outline="")
        for i in range(-1, W//24+2):
            bx = i*24 - off%24
            self._p([bx,gy, bx+6,gy-7, bx+12,gy], fill=C["ground1"], outline="")
            self._p([bx+10,gy, bx+16,gy-5, bx+22,gy], fill=C["ground1"], outline="")

    def _draw_bird(self, cx, cy):
        wy = cy + int(math.sin(self.wing_phase) * 7)
        self._p([cx-4,cy, cx-20,wy+10, cx-14,cy-4], fill=C["wing"], outline="")
        self._p([cx-18,cy+4, cx-34,cy+10, cx-34,cy+2, cx-22,cy-2],
                fill=C["wing"], outline="")
        self._o(cx-22, cy-16, cx+22, cy+16, fill=C["bird"],  outline="")
        self._o(cx+2,  cy-12, cx+16, cy,    fill=C["eye"],   outline="")
        self._o(cx+6,  cy-10, cx+14, cy-2,  fill=C["pupil"], outline="")
        self._o(cx+11, cy-9,  cx+13, cy-7,  fill=C["white"], outline="")
        self._o(cx+2,  cy+3,  cx+12, cy+9,  fill=C["blush"], outline="")
        self._p([cx+18,cy-3, cx+30,cy+1, cx+18,cy+5], fill=C["beak"], outline="")

    def _draw_score(self, score):
        self._t(W//2+1, 50, font_size=46, bold=True, text=str(score), fill="#333333")
        self._t(W//2,   49, font_size=46, bold=True, text=str(score), fill=C["white"])

    def _draw_start(self):
        self._r(W//2-160, H//2-90, W//2+160, H//2+22, fill="#1a1a2e", outline=C["gold"], width=2)
        self._t(W//2, H//2-57, font_size=38, bold=True, text="FLAPPY BIRD",         fill=C["gold"])
        self._t(W//2, H//2-18, font_size=18,             text="SPACE or CLICK to play", fill=C["white"])
        self._t(W//2, H//2+9,  font_size=13,             text="F11 → Fullscreen  |  ESC → Exit", fill="#aaaaaa")

    def _draw_panel(self, score, best):
        px, py = W//2-155, H//2-155
        self._r(px, py, px+310, py+300, fill="#1a1a2e", outline=C["gold"], width=3)
        self._t(W//2, py+42,  font_size=36, bold=True, text="GAME OVER",                   fill=C["gold"])
        self._t(W//2, py+105, font_size=26,             text=f"Score:   {score}",           fill=C["white"])
        self._t(W//2, py+148, font_size=26, bold=True,  text=f"Best:    {best}",            fill=C["gold"])
        self._t(W//2, py+215, font_size=17,             text="SPACE or CLICK to restart",   fill="#cccccc")
        self._t(W//2, py+252, font_size=13,             text="F11 → Fullscreen  |  ESC → Exit", fill="#888888")


if __name__ == "__main__":
    log("=== Flappy Bird Starting ===")
    root = tk.Tk()
    app  = FlappyApp(root)
    root.mainloop()
    log("=== Game Closed ===")