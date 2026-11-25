"""Frame compositor: stage 3D frames, radar, cards, predict, clue, reveal + captions, series tag, transitions."""
import json, math, os, random, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops
from . import style as S
from .style import (W, H, FPS, F, ANTON, INTER_K, INTER_B, WHITE, GRAY, RED, col, text_img, caption_img, blit, chip, pop, prog,
                    eo, clamp, lerp, crosshair_bg, watermark)
from .radar import RadarScene

def stage_schedule(tl, game, mood):
    """Schedule handed to stage.html (3D intro)."""
    cold = next((s for s in tl.sections if s['type'] == 'cold_open'), None)
    ctx = next((s for s in tl.sections if s['type'] == 'context'), None)
    if not cold and not ctx: return None
    sched = dict(hero_color=list(col(game['hero_color'])), opp_color=list(col(game['opp_color'])), mood=mood,
                 hero_long_gun=game.get('hero_long_gun', True), guns=game.get('guns', True), cold=dict(t0=0, t1=0, enemies=0), beats=[], rise=dict(t0=1e9, t1=1e9))
    if cold:
        cs = cold['spec']; punch = [tl.lines[l['id']]['t'] for l in cs.get('lines', []) if l.get('role') == 'punch']
        sched['cold'] = dict(t0=cold['t0'], t1=cold['t1'], enemies=cs.get('enemies', 0), title3d=cs.get('title3d'),
                             title_color=list(col(cs.get('title_color', 'red'))), punch_t0=punch[0] if punch else None)
    if ctx:
        for b in ctx['beats']:
            bs = b['spec']
            sched['beats'].append(dict(kind=bs['kind'], t0=b['t0'], t1=b['t1'] if b is not ctx['beats'][-1] else ctx['t1'],
                                       text3d=bs.get('text3d', ''), sub3d=bs.get('sub3d'), color=list(col(bs.get('color', 'gold'))),
                                       names=bs.get('names', []), long_gun=bs.get('long_gun', [])))
        sched['rise'] = dict(t0=ctx['t1'] - 1.0, t1=ctx['t1'] - 0.1)
    return sched

def stage_times(tl):
    out = []
    for s in tl.sections:
        if s['type'] in ('cold_open', 'context'):
            for n in range(round(s['t0'] * FPS), round(s['t1'] * FPS)): out.append((n, n / FPS))
    return out

class Composer:
    def __init__(self, spec, tl, game, workdir):
        self.spec, self.tl, self.game, self.wd = spec, tl, game, Path(workdir)
        self.mood = spec['meta'].get('mood', 'default'); self.accent = S.MOODS[self.mood]['accent']
        self.hero_c, self.opp_c = col(game['hero_color']), col(game['opp_color'])
        self.bgs, self.reds = S.make_bgs(self.mood); self.vig = S.make_vignette()
        self.scenes = {k: RadarScene(v, tl, game, self.mood) for k, v in tl.radar_scenes.items()}
        info_f = self.wd / 'stage' / 'info.json'
        self.sinfo = {int(k): v for k, v in json.loads(info_f.read_text())['info'].items()} if info_f.exists() else {}
        self.caps = tl.captions()
        from .channel import load_channel
        self.handle = load_channel(Path(workdir).parent).get('handle')

    # ------------------------------------------------------------ words colouring in captions
    def wcol(self, w):
        hi = self.spec['meta'].get('highlight', {})
        for word, c in hi.items():
            if word.lower() in w.lower(): return col(c)
        if 'HP' in w: return RED
        import re
        if re.search(r'\d', w): return self.accent
        return WHITE

    def stage_frame(self, t):
        n = round(t * FPS); p = self.wd / 'stage' / f'f_{n:05d}.jpg'
        if not p.exists():
            cands = sorted(self.sinfo); n = min(cands, key=lambda k: abs(k - n)) if cands else n; p = self.wd / 'stage' / f'f_{n:05d}.jpg'
        fr = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS); fr.paste(self.vig, (0, 0), self.vig)
        return fr, self.sinfo.get(n)

    # ------------------------------------------------------------ sections
    def cold(self, sec, t):
        fr, info = self.stage_frame(t); d = ImageDraw.Draw(fr, 'RGBA'); cs = sec['spec']
        punch = next((self.tl.lines[l['id']] for l in cs.get('lines', []) if l.get('role') == 'punch'), None)
        if info:
            lab = cs.get('you_label', 'YOU')
            if info['you'][2] and lab: blit(fr, text_img(lab, F(INTER_K, 30), WHITE, stroke=3), info['you'][0], info['you'][1] - 30, 1, 1)
            if not punch or t < punch['t']:
                for i, p in enumerate(info['hunt']):
                    a = eo(prog(t, sec['t0'] + 0.7 + i * 0.45, sec['t0'] + 1.0 + i * 0.45))
                    if p[2] and a > 0: blit(fr, text_img('?', F(ANTON, 70), self.opp_c, stroke=4), p[0], p[1] - 40, 0.8 + 0.2 * a, a)
        if punch:
            s, al = pop(t, punch['t'], sec['t1'], out=0.08)
            blit(fr, text_img(cs.get('punch_text', 'GUESS WHO?'), F(ANTON, 150), self.accent, glow=14, stroke=4), W / 2, 760, s, al)
        return fr, 0

    def rewind(self, sec, t):
        cold = next(s for s in self.tl.sections if s['type'] == 'cold_open')
        src = max(cold['t0'], sec['t0'] - (t - sec['t0']) * 8)
        fr, _ = self.stage_frame(min(src, cold['t1'] - 1 / FPS))
        r_, g_, b_ = fr.split(); fr = Image.merge('RGB', (ImageChops.offset(r_, 14, 0), g_, ImageChops.offset(b_, -14, 0)))
        d = ImageDraw.Draw(fr, 'RGBA')
        for y in range(0, H, 6): d.line((0, y, W, y), fill=(0, 0, 0, 60))
        blit(fr, text_img('◀◀', F(INTER_K, 160), WHITE), W / 2, 760); blit(fr, text_img('REWIND', F(ANTON, 90), WHITE), W / 2, 900)
        return fr, 0

    def context(self, sec, t):
        fr, info = self.stage_frame(t); d = ImageDraw.Draw(fr, 'RGBA')
        for bi, b in enumerate(sec['beats']):
            bs = b['spec']; t1 = b['t1'] if bi < len(sec['beats']) - 1 else sec['t1']
            if not (b['t0'] <= t < t1): continue
            c = col(bs.get('chip_color', bs.get('color', 'gold')))
            s, al = pop(t, b['t0'] + 0.05, t1, out=0.15)
            if bs.get('chip'): chip(fr, d, bs['chip'], c, 330, s, al, bs.get('chip_size', 66))
            for k, fact in enumerate(bs.get('facts', [])):
                if isinstance(fact, dict): ft, txt = self.tl.ref(fact['at'], sec), fact['text']
                else:
                    lines = bs.get('lines', []); txt = fact
                    ft = self.tl.lines[lines[k + 1]['id']]['t'] if k + 1 < len(lines) else b['t0'] + 0.6 + 0.8 * k
                s2, al2 = pop(t, ft, t1, out=0.15)
                blit(fr, text_img(txt, F(INTER_K, 32), WHITE if k == 0 else GRAY, stroke=2), W / 2, 435 + 50 * k, s2, al2)
            if bs['kind'] == 'lineup' and info:
                for k, p in enumerate(info.get('line', [])):
                    s3, al3 = pop(t, b['t0'] + 0.4 + k * 0.25, dur=0.2)
                    if p[2] and k < len(bs['names']):
                        blit(fr, text_img(bs['names'][k], F(INTER_K, 26), c, stroke=3), p[0], p[1] - 30 - (k % 2) * 34, s3, al3)
        return fr, 0

    def radar(self, sec, t, n):
        fr = self.bgs[n % 6].copy(); d = ImageDraw.Draw(fr, 'RGBA')
        sc = self.scenes[sec['scene']]; shake = sc.draw(fr, d, t, self.accent)
        if sc.heart:
            lt = sc.loc(t); a, b = sc.heart
            if a <= lt < b + 0.8:
                per = lerp(0.85, 0.55, prog(lt, a, b)); ph = ((lt - a) % per) / per
                beat = math.exp(-ph * 7) + 0.6 * math.exp(-max(0, ph - 0.22) * 9) * (ph > 0.22)
                lv = int(clamp(beat * 0.9 + 0.25) * 6 * (1 - prog(lt, b, b + 0.7)))
                if lv > 0: fr.paste(self.reds[lv - 1], (0, 0), self.reds[lv - 1])
        prev = self.tl.sections[sec['idx'] - 1] if sec['idx'] > 0 else None
        if prev and prev['type'] in ('context', 'cold_open') and t < sec['t0'] + 0.6:
            sf, _ = self.stage_frame(sec['t0'] - 1 / FPS); fr = Image.blend(sf, fr, prog(t, sec['t0'], sec['t0'] + 0.6))
        return fr, shake

    def cards(self, sec, t, n):
        fr = self.bgs[n % 6].copy(); d = ImageDraw.Draw(fr, 'RGBA'); crosshair_bg(d, t); shake = 0
        for c in sec['cards']:
            cs = c['spec']
            if not (c['t0'] <= t < c['t1']): continue
            cc = col(cs.get('color', self.accent))
            if cs.get('kicker'):
                s, al = pop(t, c['t0'], c['t1'], out=0.12); blit(fr, text_img(cs['kicker'], F(INTER_K, 40), GRAY), W / 2, 600, s, al)
            s, al = pop(t, c['t0'] + 0.1, c['t1'], out=0.12)
            head = cs['headline']; size = 150 if len(head) <= 10 else (120 if len(head) <= 14 else 92)
            blit(fr, text_img(head, F(ANTON, size), cc, glow=12, stroke=4), W / 2, 820, s, al)
            if cs.get('sub'):
                s2, al2 = pop(t, c['t0'] + 0.5, c['t1'], out=0.12); blit(fr, text_img(cs['sub'], F(INTER_K, 36), WHITE, stroke=2), W / 2, 980, s2, al2)
            if self.mood == 'dark' and t < c['t0'] + 0.25:
                shake = 9 * (1 - prog(t, c['t0'], c['t0'] + 0.25))
        return fr, shake

    def predict(self, sec, t, n):
        prev = next(s for s in reversed(self.tl.sections[:sec['idx']]) if s['type'] == 'radar')
        fr, _ = self.radar(prev, prev['t1'] - 0.02, n)
        fr = Image.blend(fr, Image.new('RGB', (W, H), (6, 8, 12)), 0.55); d = ImageDraw.Draw(fr, 'RGBA'); ps = sec['spec']
        s, al = pop(t, sec['t0'] + 0.1); blit(fr, text_img(ps.get('question', 'WHO WINS?'), F(ANTON, 170), self.accent, glow=14, stroke=4), W / 2, 640, s, al)
        opts = ps.get('options', [])
        for k, o in enumerate(opts[:2]):
            s2, al2 = pop(t, sec['t0'] + 0.4 + 0.2 * k); x = W / 2 + (k - 0.5) * 460 if len(opts) > 1 else W / 2
            im = text_img(o['label'], F(ANTON, 76), col(o.get('color', 'white')), stroke=4); w_, h_ = im.width - 40, im.height - 40
            d.rounded_rectangle((x - w_ / 2 - 24, 860 - h_ / 2 - 14, x + w_ / 2 + 24, 860 + h_ / 2 + 14), 20, fill=(10, 12, 18, int(200 * al2)), outline=col(o.get('color', 'white')) + (int(255 * al2),), width=4)
            blit(fr, im, x, 860, s2, al2)
        s3, al3 = pop(t, sec['t0'] + 0.8); blit(fr, text_img('Comment your pick ▼', F(ANTON, 70), WHITE), W / 2, 1020, s3, al3)
        for k, ct in enumerate(sec['count']):
            s4, al4 = pop(t, ct, ct + 0.55, out=0.2); blit(fr, text_img(str(3 - k), F(ANTON, 130), RED), W / 2, 1200, s4 * 1.1, al4)
        return fr, 0

    def clue(self, sec, t, n):
        fr = self.bgs[n % 6].copy(); d = ImageDraw.Draw(fr, 'RGBA'); crosshair_bg(d, t); cs = sec['spec']; shake = 0
        s, al = pop(t, sec['t0'] + 0.1, sec['t1'], out=0.15); blit(fr, text_img(cs.get('label', 'LAST CLUE'), F(INTER_K, 40), GRAY), W / 2, 640, s, al)
        big = next((self.tl.lines[l['id']]['t'] for l in cs.get('lines', []) if l.get('role') == 'big'), None)
        if big is not None:
            s, al = pop(t, big, sec['t1'], out=0.15)
            blit(fr, text_img(cs['big'], F(ANTON, 180 if len(cs['big']) <= 14 else 130), self.accent, glow=14), W / 2, 880, s * (1 + 0.03 * max(0, t - big)), al)
            if t >= big: shake = 6 * (1 - prog(t, big, big + 0.25))
        return fr, shake

    def reveal(self, sec, t, n):
        fr = self.bgs[n % 6].copy(); d = ImageDraw.Draw(fr, 'RGBA'); rs = sec['spec']; R0 = sec['R0']; shake = 0
        if t < R0:
            blit(fr, text_img('?', F(ANTON, 1100), (24, 28, 38), shadow=False), W / 2, 880, 1 + 0.02 * (t - sec['t0']), 1)
            s, al = pop(t, sec['t0'] + 0.1, R0 - 0.05, out=0.05); blit(fr, text_img(rs.get('lead', 'SO…'), F(ANTON, 120), GRAY), W / 2, 640, s, al)
            q = rs.get('question', 'WHO ARE YOU?').rsplit(' ', 1)
            s2, al2 = pop(t, sec['t0'] + 0.8, R0 - 0.05, out=0.05)
            blit(fr, text_img(q[0], F(ANTON, 190), WHITE), W / 2, 860, s2, al2)
            if len(q) > 1: blit(fr, text_img(q[1], F(ANTON, 260), self.accent, glow=14), W / 2, 1110, s2, al2)
            s4, al4 = pop(t, sec['t0'] + 1.8, R0 - 0.05, out=0.05); blit(fr, text_img(rs.get('prompt', 'Comment your guess ▼'), F(ANTON, 70), WHITE), W / 2, 1290, s4, al4)
            for k, ct in enumerate(sec['count']):
                s3, al3 = pop(t, ct, ct + 0.55, out=0.2); blit(fr, text_img(str(3 - k), F(ANTON, 130), RED), W / 2, 1450, s3 * 1.1, al3)
        else:
            crosshair_bg(d, t, a=22); p = prog(t, R0, R0 + 0.5)
            ans = rs['answer']; name = text_img(ans, F(ANTON, 300 if len(ans) <= 8 else 220), self.accent, glow=18)
            if p < 1:
                off = int(40 * (1 - eo(p))); rr = name.copy(); rr.putalpha(name.getchannel('A').point(lambda v: v // 2))
                blit(fr, rr, W / 2 - off, 860 + off * 0.3, 1.0, 0.8); blit(fr, rr, W / 2 + off, 860 - off * 0.3, 1.0, 0.8)
            blit(fr, name, W / 2, 860, 1 + 0.15 * (1 - eo(p)), 1)
            s, al = pop(t, R0 + 0.4); blit(fr, text_img(rs.get('answer_sub', ''), F(INTER_K, 40), GRAY), W / 2, 1060, s, al)
            s2, al2 = pop(t, R0 + 1.2)
            blit(fr, text_img(rs.get('cta1', 'Got it right?'), F(ANTON, 96), WHITE), W / 2, 1330, s2, al2)
            blit(fr, text_img(rs.get('cta2', 'Comment below ▼'), F(ANTON, 72), self.accent), W / 2, 1440, s2, al2)
            if t < R0 + 0.4: shake = 16 * (1 - prog(t, R0, R0 + 0.4))
        return fr, shake

    # ------------------------------------------------------------ frame
    def frame(self, n):
        t = n / FPS; sec = self.tl.section_at(t); ty = sec['type']
        if ty == 'cold_open': fr, shake = self.cold(sec, t)
        elif ty == 'rewind': fr, shake = self.rewind(sec, t)
        elif ty == 'context': fr, shake = self.context(sec, t)
        elif ty == 'radar': fr, shake = self.radar(sec, t, n)
        elif ty == 'cards': fr, shake = self.cards(sec, t, n)
        elif ty == 'predict': fr, shake = self.predict(sec, t, n)
        elif ty == 'clue': fr, shake = self.clue(sec, t, n)
        else: fr, shake = self.reveal(sec, t, n)
        if ty not in ('reveal', 'predict', 'rewind'):
            y = 1460
            for (a, b, g) in self.caps:
                if a <= t < b:
                    s, al = pop(t, a, b, dur=0.1, out=0.06); blit(fr, caption_img([(w, self.wcol(w)) for w in g], size=92, maxw=960), W / 2, y, s, al)
        if ty not in ('rewind', 'reveal', 'predict'): watermark(fr, self.handle, self.accent)
        if ty == 'reveal' and sec['R0'] <= t < sec['R0'] + 0.25:
            fr = Image.blend(fr, Image.new('RGB', (W, H), WHITE), 0.85 * (1 - prog(t, sec['R0'], sec['R0'] + 0.25)))
        if shake > 0.5:
            rnd = random.Random(n); fr = ImageChops.offset(fr, int(rnd.uniform(-shake, shake)), int(rnd.uniform(-shake, shake)))
        return fr

def render_range(args):
    """worker: (spec_path, workdir, n0, n1, out_mp4)"""
    spec_path, workdir, n0, n1, out = args
    from .cli import load_all
    spec, tl, game = load_all(spec_path, workdir, synth=False)
    c = Composer(spec, tl, game, workdir); tmp = out + '.part.mp4'
    p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-r', str(FPS), tmp], stdin=subprocess.PIPE)
    for n in range(n0, n1): p.stdin.write(c.frame(n).tobytes())
    p.stdin.close()
    if p.wait() != 0: raise RuntimeError(f'ffmpeg failed for {out}')
    os.replace(tmp, out); return out
