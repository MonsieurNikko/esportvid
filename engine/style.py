"""House style: palette, fonts, text/caption rendering, backgrounds, small drawing helpers.
Everything visual that must stay identical across episodes lives here."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / 'fonts'
ANTON = str(FONTS / 'Anton-Regular.ttf')
INTER_B = str(FONTS / 'Inter-Bold.otf')
INTER_K = str(FONTS / 'Inter-Black.otf')
MONO = str(FONTS / 'DejaVuSansMono-Bold.ttf')
SANS_B = str(FONTS / 'DejaVuSans-Bold.ttf')

W, H, FPS = 1080, 1920, 30
WHITE = (255, 255, 255)
GRAY = (150, 158, 172)
RED = (255, 64, 64)
GOLD = (255, 192, 74)
# team colours (left = hero side, right = opponents); games can override in games/*.json
TEAM = {'t': (242, 163, 58), 'ct': (96, 172, 255), 'red': (255, 84, 84), 'blue': (96, 172, 255),
        'gold': GOLD, 'white': WHITE, 'gray': GRAY}
MOODS = {  # accent palette per mood
    'default': {'accent': (242, 163, 58), 'alarm': RED, 'bg_top': (15, 18, 26), 'bg_bot': (5, 6, 9)},
    'dark':    {'accent': (255, 70, 70), 'alarm': (255, 40, 40), 'bg_top': (18, 10, 14), 'bg_bot': (5, 3, 5)},
}

def col(c):
    if isinstance(c, (list, tuple)): return tuple(c)
    return TEAM.get(c, WHITE)

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a)) if b > a else float(t >= a)
def eo(p): return 1 - (1 - p) ** 3
def eio(p): return p * p * (3 - 2 * p)
def eback(p):
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
def lerp(a, b, p): return a + (b - a) * p
def lerp2(a, b, p): return (lerp(a[0], b[0], p), lerp(a[1], b[1], p))

def pop(t, a, b=None, dur=0.16, out=0.12):
    """(scale, alpha) for an element shown on [a, b)."""
    if t < a or (b is not None and t >= b): return 0, 0
    p = prog(t, a, a + dur); s = 0.75 + 0.25 * eback(p); al = p
    if b is not None: al *= 1 - prog(t, b - out, b)
    return s, al

# ---------------------------------------------------------------- text
_fonts, _cache = {}, {}
def F(path, size):
    k = (path, size)
    if k not in _fonts: _fonts[k] = ImageFont.truetype(path, size)
    return _fonts[k]

def text_img(text, font, fill, stroke=0, glow=None, shadow=True):
    fill = col(fill)
    key = ('t', text, font.path, font.size, fill, stroke, glow, shadow)
    if key in _cache: return _cache[key]
    bb = font.getbbox(text, stroke_width=stroke); w, h = bb[2] - bb[0], bb[3] - bb[1]
    pad = 30 + (glow or 0) * 3
    img = Image.new('RGBA', (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0)); org = (pad - bb[0], pad - bb[1])
    if glow:
        g = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(g).text(org, text, font=font, fill=fill + (200,), stroke_width=stroke + 2, stroke_fill=fill + (200,))
        img = Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(glow)))
    if shadow:
        s = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(s).text((org[0] + 4, org[1] + 7), text, font=font, fill=(0, 0, 0, 170), stroke_width=stroke, stroke_fill=(0, 0, 0, 170))
        img = Image.alpha_composite(img, s.filter(ImageFilter.GaussianBlur(5)))
    ImageDraw.Draw(img).text(org, text, font=font, fill=fill + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
    _cache[key] = img
    return img

def _nlines(words, font, maxw):
    sp = font.getlength(' '); n, cw = 1, 0
    for w in words:
        ww = font.getlength(w)
        if cw and cw + sp + ww > maxw: n += 1; cw = ww
        else: cw += (sp if cw else 0) + ww
    return n

def caption_img(parts, size=None, maxw=920):
    """parts: list of (word_or_phrase, colour). Auto-shrinks to stay on <= 2 lines."""
    words = [(w, col(c)) for txt, c in parts for w in txt.split()]
    if size is None:
        size = next((s for s in (100, 92, 84, 76) if _nlines([w for w, _ in words], F(ANTON, s), maxw) <= 2), 76)
    key = ('c', tuple(words), size, maxw)
    if key in _cache: return _cache[key]
    font = F(ANTON, size); sp = font.getlength(' ')
    lines, cur, curw = [], [], 0
    for w, c in words:
        ww = font.getlength(w)
        if cur and curw + sp + ww > maxw: lines.append(cur); cur, curw = [], 0
        curw += (sp if cur else 0) + ww; cur.append((w, c, ww))
    lines.append(cur)
    asc, desc = font.getmetrics(); lh = int((asc + desc) * 0.98)
    Wc, Hc = maxw + 100, lh * len(lines) + 90
    txt = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0)); sh = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 0))
    dt, ds = ImageDraw.Draw(txt), ImageDraw.Draw(sh)
    for i, line in enumerate(lines):
        lw = sum(x[2] for x in line) + sp * (len(line) - 1); x = (Wc - lw) / 2; y = 40 + i * lh
        for w, c, ww in line:
            ds.text((x + 4, y + 8), w, font=font, fill=(0, 0, 0, 190), stroke_width=9, stroke_fill=(0, 0, 0, 190))
            dt.text((x, y), w, font=font, fill=c + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255))
            x += ww + sp
    img = Image.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), txt)
    _cache[key] = img
    return img

def blit(frame, img, cx, cy, scale=1.0, alpha=1.0, anchor='c'):
    if alpha <= 0.01 or scale <= 0.01: return
    if abs(scale - 1.0) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.BILINEAR)
    if alpha < 0.999:
        a = img.getchannel('A').point(lambda v: int(v * alpha)); img = img.copy(); img.putalpha(a)
    if anchor == 'c': x, y = cx - img.width / 2, cy - img.height / 2
    elif anchor == 'r': x, y = cx - img.width, cy - img.height / 2
    else: x, y = cx, cy - img.height / 2
    frame.paste(img, (int(x), int(y)), img)

def chip(fr, d, txt, colour, y, s, al, size=72):
    """Rounded outlined label (the 'WIN → KYIV' style)."""
    if al <= 0.01: return
    colour = col(colour)
    img = text_img(txt, F(ANTON, size), colour, stroke=4); w_, h_ = img.width - 40, img.height - 40
    d.rounded_rectangle((W / 2 - w_ / 2 - 28, y - h_ / 2 - 14, W / 2 + w_ / 2 + 28, y + h_ / 2 + 14), 20,
                        fill=(10, 12, 18, int(190 * al)), outline=colour + (int(255 * al),), width=4)
    blit(fr, img, W / 2, y, s, al)

def watermark(fr, handle, accent):
    """Channel mark = small reticle (brand icon) + handle, semi-transparent, bottom-left of the radar panel:
    outside TikTok/Shorts/Reels UI zones (top tabs, right action rail, bottom-left caption block)."""
    if not handle: return
    key = ('wm', handle, accent)
    if key not in _cache:
        txt = text_img(handle, F(INTER_K, 28), WHITE, stroke=2, shadow=False)
        im = Image.new('RGBA', (txt.width + 50, max(txt.height, 60)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        cx, cy, r = 26, im.height / 2, 14
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=accent + (255,), width=3)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            d.line((cx + dx * r * 0.6, cy + dy * r * 0.6, cx + dx * r * 1.45, cy + dy * r * 1.45), fill=accent + (255,), width=3)
        d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=accent + (255,))
        im.paste(txt, (34, int((im.height - txt.height) / 2)), txt); _cache[key] = im
    blit(fr, _cache[key], 84, 1316, 1, 0.6, anchor='l')

def crosshair_bg(d, t, a=16):
    cx, cy = W / 2, 900; r = 330 + 10 * math.sin(t * 0.8)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, a), width=3)
    for ang in (0, 90, 180, 270):
        rad = math.radians(ang + t * 6)
        d.line((cx + math.cos(rad) * (r - 60), cy + math.sin(rad) * (r - 60), cx + math.cos(rad) * (r + 90), cy + math.sin(rad) * (r + 90)),
               fill=(255, 255, 255, a), width=3)

# ---------------------------------------------------------------- backgrounds
def make_bgs(mood='default'):
    m = MOODS[mood]; rng = np.random.default_rng(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    g = (yy / H)[..., None]
    base = np.array(m['bg_top'], np.float32) * (1 - g) + np.array(m['bg_bot'], np.float32) * g
    r = np.sqrt(((xx - W / 2) / (W * 0.75)) ** 2 + ((yy - H * 0.45) / (H * 0.6)) ** 2)
    base = base * np.clip(1.15 - r * 0.75, 0.35, 1.0)[..., None]
    base = base * (1 - 0.06 * ((yy.astype(int) // 3) % 2))[..., None]
    bgs = [Image.fromarray(np.clip(base + rng.normal(0, 4.5, (H, W, 1)), 0, 255).astype(np.uint8), 'RGB') for _ in range(6)]
    rv = np.clip((r - 0.55) * 1.6, 0, 1); reds = []
    for lv in range(1, 7):
        im = np.zeros((H, W, 4), np.uint8); im[..., 0] = 200; im[..., 1] = 20; im[..., 2] = 25
        im[..., 3] = (rv * 15 * lv).clip(0, 255).astype(np.uint8); reds.append(Image.fromarray(im, 'RGBA'))
    return bgs, reds

def make_vignette():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    a = np.maximum(np.clip(r - 0.55, 0, 1) ** 1.4 * 200, np.clip((yy - 1250) / 670, 0, 1) * 140).clip(0, 210).astype(np.uint8)
    v = np.zeros((H, W, 4), np.uint8); v[..., 3] = a
    return Image.fromarray(v, 'RGBA')

# ---------------------------------------------------------------- small shapes
def dot(d, p, r, c, outline=(10, 10, 14), ow=4, a=255):
    x, y = p; c = col(c); d.ellipse((x - r, y - r, x + r, y + r), fill=c + (a,), outline=outline + (a,), width=ow)
def xmark(d, p, c, r=16, w=6, a=255):
    x, y = p; c = col(c)
    d.line((x - r, y - r, x + r, y + r), fill=c + (a,), width=w); d.line((x - r, y + r, x + r, y - r), fill=c + (a,), width=w)
def ring(d, p, r, c, a, w=4):
    x, y = p; c = col(c); d.ellipse((x - r, y - r, x + r, y + r), outline=c + (int(a),), width=w)
def objective_icon(d, p, label='C4', a=255, s=1.0, c=(230, 120, 40)):
    x, y = p; w, h = (14 + 9 * len(label)) * s, 20 * s
    d.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), 4, fill=c + (a,), outline=(20, 10, 0, a), width=2)
    d.text((x - w / 2 + 6 * s, y - 9 * s), label, font=F(INTER_K, int(14 * s)), fill=(20, 10, 0, a))

def killfeed_img(killer, victim, weapon, tag, kcol, vcol):
    key = ('kf', killer, victim, weapon, tag, kcol, vcol)
    if key in _cache: return _cache[key]
    fb = F(INTER_K, 30); fs = F(INTER_K, 20)
    w1 = fb.getlength(killer); w2 = fs.getlength(weapon) + 22; w3 = fs.getlength(tag) + 18 if tag else 0; w4 = fb.getlength(victim)
    Wk = int(24 + w1 + 14 + w2 + (10 + w3 if tag else 0) + 14 + w4 + 24); Hk = 54
    img = Image.new('RGBA', (Wk, Hk), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, Wk - 1, Hk - 1), 10, fill=(14, 16, 22, 225), outline=(210, 40, 40, 255), width=3)
    x = 24; d.text((x, 10), killer, font=fb, fill=col(kcol) + (255,)); x += w1 + 14
    d.rounded_rectangle((x, 13, x + w2, 41), 6, fill=(225, 228, 235, 255)); d.text((x + 11, 15), weapon, font=fs, fill=(15, 15, 20, 255)); x += w2
    if tag:
        x += 10; d.rounded_rectangle((x, 13, x + w3, 41), 6, fill=(255, 210, 80, 255) if tag == 'HS' else (180, 130, 70, 255))
        d.text((x + 9, 15), tag, font=fs, fill=(15, 15, 20, 255)); x += w3
    x += 14; d.text((x, 10), victim, font=fb, fill=col(vcol) + (255,))
    _cache[key] = img
    return img

def score_img(a, b, ca, cb, big=330):
    key = ('score', a, b, ca, cb, big)
    if key in _cache: return _cache[key]
    f = F(ANTON, big); img = Image.new('RGBA', (1000, big + 160), (0, 0, 0, 0))
    la = text_img(str(a), f, ca); lb = text_img(str(b), f, cb); dash = text_img('–', f, (90, 96, 110))
    img.paste(la, (int(440 - la.width), 60), la)
    img.paste(dash, (int(500 - dash.width / 2), int(60 + (la.height - dash.height) / 2)), dash)
    img.paste(lb, (560, 60), lb)
    _cache[key] = img
    return img
