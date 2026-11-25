"""Top-down tactical radar (the 'map' part of every episode). Fully driven by the spec:
map layout traced from the game's radar image, entity paths, events (kills, shots, hits, objective)."""
import math
from PIL import Image, ImageDraw
from .style import (W, H, F, ANTON, INTER_B, INTER_K, MONO, WHITE, GRAY, RED, col, text_img, blit, pop, prog, eo, eio,
                    lerp, lerp2, clamp, dot, xmark, ring, objective_icon, killfeed_img)

PX0, PY0, PX1, PY1 = 70, 466, 1010, 1346

def path_pos(pts, t, a, b):
    p = eio(prog(t, a, b)); segs = [math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    if not segs: return tuple(pts[0])
    tot = sum(segs) or 1; s = p * tot
    for i, L in enumerate(segs):
        if s <= L or i == len(segs) - 1: return lerp2(pts[i], pts[i + 1], clamp(s / L if L else 1))
        s -= L
    return tuple(pts[-1])

class RadarScene:
    def __init__(self, secs, tl, game, mood):
        self.secs, self.tl, self.game, self.mood = secs, tl, game, mood
        S = secs[0]['spec']; self.S = S; sec0 = secs[0]
        tr = S['map'].get('transform', {}); self.k = tr.get('k', 2.0)
        self.ox, self.oy, self.sx, self.sy = tr.get('x0', 600), tr.get('y0', 450), tr.get('sx', 190), tr.get('sy', 470)
        R = lambda r, sec=sec0: self.loc(tl.ref(r, self._sec_of(r) or sec))
        self.hero_c = col(game['hero_color']); self.opp_c = col(game['opp_color'])
        # entities
        self.you = [dict(pts=self.TP(sg['pts']), a=R(sg['from']), b=R(sg['to'])) for sg in S['you']]
        self.mates = [dict(pts=self.TP(m['pts']), a=R(m['from']), b=R(m['to']), die=R(m['die']), carrier=m.get('carrier', False)) for m in S.get('mates', [])]
        self.kills = [dict(t=R(e['at']), src=self.T(*e['from']) if e.get('from') else None, victim=e['victim'], weapon=e.get('weapon', game['default_weapon']), tag=e.get('tag'))
                      for e in S['events'] if e['type'] == 'kill']
        kt = {k['victim']: k['t'] for k in self.kills}
        self.enemies = {}
        for e in S['enemies']:
            die = kt.get(e['name'], 1e9)
            segs = [dict(pts=self.TP(sg['pts']), a=R(sg['from']), b=R(sg['to'])) for sg in e.get('path', [])]
            self.enemies[e['name']] = dict(app=R(e['appear']), e=self.T(*e['entry']), f=segs[-1]['pts'][-1] if segs else self.T(*e['final']), segs=segs,
                                           m0=R(e.get('move_from', e['appear'])), m1=R(e['arrive']) if 'arrive' in e else die - 0.6,
                                           die=die, side=e.get('label_side', 'u'), tag=e.get('tag'))
        # abilities: cast (label + optional dash line), shadow (ghost left on the map), aoe (circles), line (projectile)
        P = lambda p: self.T(*p) if p else None
        self.casts = [dict(t=R(e['at']), by=e['by'], label=e['label'], a=P(e.get('from')), b=P(e.get('to'))) for e in S['events'] if e['type'] == 'cast']
        self.ghosts = [dict(t=R(e['at']), end=R(e['until']), by=e['by'], p=P(e['pos'])) for e in S['events'] if e['type'] == 'shadow']
        self.aoes = [dict(t=R(e['at']), by=e['by'], ps=self.TP(e['pos']), r=e['r'] * self.k) for e in S['events'] if e['type'] == 'aoe']
        self.lines_ = [dict(t=R(e['at']), by=e['by'], a=P(e['from']), b=P(e['to'])) for e in S['events'] if e['type'] == 'line']
        self.trk = [dict(name=x['name'], by=x['by'], hp=[(R(r), v) for r, v in x.get('hp', [])],
                         items=[(it[0], R(it[1]), R(it[2]) if len(it) > 2 else R(it[1])) for it in x.get('items', [])]) for x in S.get('trackers', [])]
        self.shots = [dict(t=R(e['at']), to=self.T(*e['to'])) for e in S['events'] if e['type'] == 'shot']
        self.hits = [dict(t=R(e['at']), hp=e['hp']) for e in S['events'] if e['type'] == 'hit']
        pk = [e for e in S['events'] if e['type'] == 'pickup']
        self.pickup = dict(t=R(pk[0]['at']), pos=self.T(*pk[0]['pos'])) if pk else None
        self.objective = game.get('objective', 'C4')
        hud = S.get('hud', {})
        self.hud0 = R(hud.get('from')) if hud.get('from') else None
        self.hp0 = hud.get('hp', 100); self.armor = hud.get('armor_text', game.get('armor_text', 'ARMOR 0'))
        self.clock = [(R(r), v) for r, v in hud.get('clock', [])]
        self.duel0 = R(S['duel_from']) if S.get('duel_from') else (self.kills[0]['t'] - 2 if self.kills else None)
        self.last_kill = max([k['t'] for k in self.kills], default=None)
        sc = S.get('score', {}); self.score = sc
        self.score_change = R(sc['change_at']) if sc.get('change_at') else ((self.last_kill + 0.25) if self.last_kill else 1e9)
        st = S.get('stats'); self.stats = dict(st, t=R(st['at'])) if st else None
        hb = S.get('heartbeat'); self.heart = (R(hb[0]), R(hb[1])) if hb else None
        self.map_img = self.make_map()
        self.t_enter = self.loc(sec0['t0']); self.t_exit = self.loc(secs[-1]['t1'])

    # ---------------- time mapping (predict sections freeze the radar)
    def _sec_of(self, r):
        if isinstance(r, str) and not r.startswith('@'):
            lid = r.split('.')[0].split('+')[0].split('-')[0]
            if lid in self.tl.lines: return self.tl.sections[self.tl.lines[lid]['section']]
        return None
    def loc(self, t):
        off, prev_end = 0.0, None
        for k, s in enumerate(self.secs):
            if k > 0: off += s['t0'] - self.secs[k - 1]['t1']
            if t < s['t0']: return prev_end if prev_end is not None else t
            if t < s['t1'] or k == len(self.secs) - 1: return t - off
            prev_end = s['t1'] - off
        return t - off

    # ---------------- geometry
    def T(self, x, y): return (self.sx + (x - self.ox) * self.k, self.sy + (y - self.oy) * self.k)
    def TR(self, r): a = self.T(r[0], r[1]); b = self.T(r[2], r[3]); return (a[0], a[1], b[0], b[1])
    def TP(self, pts): return [self.T(*p) for p in pts]

    def make_map(self):
        M = self.S['map']; m = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
        d.rounded_rectangle((PX0, PY0, PX1, PY1), 26, fill=(14, 17, 24, 240), outline=(44, 52, 68, 255), width=3)
        for x in range(PX0 + 30, PX1, 40): d.line((x, PY0 + 4, x, PY1 - 4), fill=(255, 255, 255, 6))
        for y in range(PY0 + 30, PY1, 40): d.line((PX0 + 4, y, PX1 - 4, y), fill=(255, 255, 255, 6))
        lane, edge = (40, 45, 56, 255), (82, 90, 106, 255)
        for r in M.get('lanes', []): d.rectangle(self.TR(r), fill=lane)
        for r in M.get('sunny', []): d.rectangle(self.TR(r), fill=(58, 54, 40, 255))
        for r in M.get('lanes', []) + M.get('sunny', []): d.rectangle(self.TR(r), outline=edge, width=2)
        for poly in M.get('walls', []):   # polygons (organic walls, e.g. LoL jungle)
            pts = self.TP(poly); d.polygon(pts, fill=(14, 17, 24, 255)); d.line(pts + pts[:1], fill=edge, width=3)
        for rr in M.get('covered', []):
            rr = self.TR(rr); d.rectangle(rr, fill=(26, 29, 37, 255), outline=(130, 138, 154, 255), width=4)
            for k in range(int(rr[0]) - 400, int(rr[2]), 20):
                x0, x1 = max(rr[0] + 3, k), min(rr[2] - 3, k + (rr[3] - rr[1]))
                if x1 > x0: d.line((x0, rr[1] + 3 + (x0 - k), x1, rr[1] + 3 + (x1 - k)), fill=(255, 255, 255, 9), width=2)
        for z in M.get('zones', []):
            bz = self.TR(z['rect']); d.rectangle(bz, fill=(150, 30, 30, 40), outline=(210, 60, 60, 150), width=3)
            blit(m, text_img(z.get('label', 'A'), F(ANTON, 150), (120, 40, 40), shadow=False), (bz[0] + bz[2]) / 2 + 10, (bz[1] + bz[3]) / 2 + 30)
        for (x, y) in M.get('pillars', []):
            X, Y = self.T(x, y); d.rectangle((X - 12, Y - 12, X + 12, Y + 12), fill=(98, 98, 106, 255), outline=(30, 30, 34, 255), width=2)
        for c in M.get('crates', []):
            c = self.TR(c); d.rectangle(c, fill=(118, 84, 46, 255), outline=(196, 146, 84, 255), width=4)
            d.line((c[0], c[1], c[2], c[3]), fill=(80, 56, 30, 255), width=4); d.line((c[0], c[3], c[2], c[1]), fill=(80, 56, 30, 255), width=4)
        for c in M.get('containers', []):
            c = self.TR(c); d.rectangle(c, fill=(46, 52, 60, 255), outline=(160, 166, 178, 255), width=3)
            for x in range(int(c[0]) + 10, int(c[2]), 10): d.line((x, c[1], x, c[3]), fill=(160, 166, 178, 110), width=1)
        for lab in M.get('labels', []):
            txt, x, y = lab[0], lab[1], lab[2]; ang = lab[3] if len(lab) > 3 else 0; sz = lab[4] if len(lab) > 4 else 20
            im = text_img(txt, F(INTER_K, sz), (128, 136, 152), shadow=False)
            blit(m, im.rotate(ang, expand=True, resample=Image.BICUBIC) if ang else im, *self.T(x, y))
        if M.get('title'): blit(m, text_img(M['title'], F(INTER_K, 22), (100, 108, 124), shadow=False), 250, 500)
        if M.get('clip'):
            mask = Image.new('L', (W, H), 0); ImageDraw.Draw(mask).rounded_rectangle((PX0, PY0, PX1, PY1), 26, fill=255)
            m = Image.composite(m, Image.new('RGBA', (W, H), (0, 0, 0, 0)), mask)
        return m.crop((PX0 - 10, PY0 - 10, PX1 + 10, PY1 + 10))

    # ---------------- state
    def you_pos(self, t):
        seg = self.you[0]
        for s in self.you:
            if t >= s['a']: seg = s
        if t < self.you[0]['a']: return self.you[0]['pts'][0]
        return path_pos(seg['pts'], t, seg['a'], seg['b'])
    def nip_pos(self, n, t):
        d = self.enemies[n]
        if d['segs']:
            seg = next((s for s in reversed(d['segs']) if t >= s['a']), None)
            return path_pos(seg['pts'], t, seg['a'], seg['b']) if seg else d['e']
        return path_pos([d['e'], d['f']], t, d['m0'], d['m1'])

    # ---------------- draw
    def draw(self, fr, d, tg, accent):
        """tg = global time. Returns camera-shake amount."""
        t = self.loc(tg); shake = 0.0
        pin = eo(prog(t, self.t_enter, self.t_enter + 0.5))
        st0 = self.stats['t'] if self.stats else 1e9
        dim = 1 - 0.75 * eo(prog(t, st0, st0 + 0.5)); fade_out = 1 - prog(t, self.t_exit - 0.4, self.t_exit)
        mal = pin * dim * fade_out
        if mal < 0.999: blit(fr, self.map_img, PX0 - 10, (PY0 + PY1) / 2, 0.97 + 0.03 * pin, mal, anchor='l')
        else: fr.paste(self.map_img, (PX0 - 10, PY0 - 10), self.map_img)
        ea = int(255 * mal)
        if ea < 6: return 0.0
        sc = self.score
        if sc:
            score = sc.get('after', '') if t >= self.score_change else sc.get('before', '')
            s, al = pop(t, self.t_enter + 0.2); al *= fade_out
            bump = (1 + 0.15 * (1 - prog(t, self.score_change, self.score_change + 0.3))) if t >= self.score_change else 1
            blit(fr, text_img(f"{sc.get('left', 'YOU')}  {score}  {sc.get('right', '')}", F(INTER_K, 46), WHITE), W / 2, 215, s * bump, al)
            if sc.get('sub'): blit(fr, text_img(sc['sub'], F(INTER_B, 26), RED if t < self.score_change else accent, shadow=False), W / 2, 262, s, al)
        for m in self.mates:
            p = path_pos(m['pts'], t, m['a'], m['b']) if t < m['die'] else m['pts'][-1]
            if t < m['a'] - 0.1: continue
            if t < m['die']: dot(d, p, 16, self.hero_c, a=ea)
            else:
                xmark(d, p, (150, 110, 70), a=int(ea * 0.8)); q = prog(t, m['die'], m['die'] + 0.5)
                if q < 1: ring(d, p, 18 + 60 * eo(q), RED, ea * (1 - q), 5)
            if m['carrier'] and self.pickup and m['die'] <= t < self.pickup['t'] and int(t * 4) % 2 == 0:
                objective_icon(d, self.pickup['pos'], self.objective, ea)
        yp = (0, 0)
        if t >= self.you[0]['a'] - 0.1:
            yp = self.you_pos(t)
            order = [k['victim'] for k in sorted(self.kills, key=lambda k: k['t'])]
            if self.duel0 and self.duel0 <= t < (self.last_kill or 0) + 0.6 and order and not self.trk:   # aim cone: shooters only
                seq = [(self.duel0, order[0])] + [(sorted(self.kills, key=lambda k: k['t'])[i]['t'], order[i + 1]) for i in range(len(order) - 1)]
                def ang_to(nm): q = self.nip_pos(nm, t); return math.degrees(math.atan2(q[1] - yp[1], q[0] - yp[0]))
                cur, prev = seq[0], None
                for k, (ts, nm) in enumerate(seq):
                    if t >= ts: cur = (ts, nm); prev = seq[k - 1][1] if k > 0 else None
                ang = ang_to(cur[1])
                for sh in self.shots:
                    if abs(t - sh['t']) < 0.6: ang = math.degrees(math.atan2(sh['to'][1] - yp[1], sh['to'][0] - yp[0]))
                if prev and t < cur[0] + 0.35: ang = lerp(ang_to(prev), ang, eio(prog(t, cur[0], cur[0] + 0.35)))
                ca = int(34 * mal * prog(t, self.duel0, self.duel0 + 0.5) * (1 - prog(t, self.last_kill + 0.2, self.last_kill + 0.6)))
                Rr = 560; d.pieslice((yp[0] - Rr, yp[1] - Rr, yp[0] + Rr, yp[1] + Rr), ang - 16, ang + 16, fill=(255, 220, 160, ca))
            pr = (t * 0.9) % 1.0
            ring(d, yp, 22 + 30 * pr, WHITE, ea * 0.5 * (1 - pr), 3); dot(d, yp, 21, self.hero_c, outline=WHITE, ow=4, a=ea)
            blit(fr, text_img(self.S.get('you_label', 'YOU'), F(INTER_K, 28), WHITE), yp[0], yp[1] - 48, 1, mal)
            if self.pickup and t >= self.pickup['t']:
                objective_icon(d, (yp[0] + 46, yp[1] - 48), self.objective, ea, 0.9); q = prog(t, self.pickup['t'], self.pickup['t'] + 0.5)
                if q < 1:
                    ring(d, self.pickup['pos'], 20 + 50 * eo(q), self.hero_c, ea * (1 - q), 5)
                    blit(fr, text_img('+ ' + self.objective, F(INTER_K, 32), self.hero_c), self.pickup['pos'][0] - 90, self.pickup['pos'][1] - 30 - 30 * q, 1, mal * (1 - q))
        self.draw_abilities(fr, d, t, yp, ea, mal)
        for nm, dd in self.enemies.items():
            if t < dd['app']: continue
            p = self.nip_pos(nm, t) if t < dd['die'] else dd['f']; s, al = pop(t, dd['app'], dur=0.2)
            if t < dd['die']:
                q = prog(t, dd['app'], dd['app'] + 0.6)
                if q < 1: ring(d, p, 18 + 50 * q, self.opp_c, ea * (1 - q), 4)
                dot(d, p, 16 * s, self.opp_c, a=int(ea * al))
                off = {'u': (0, -40), 'd': (0, 40), 'l': (-88, 0), 'r': (90, 0)}[dd['side']]
                blit(fr, text_img(nm, F(INTER_K, 26), self.opp_c), p[0] + off[0], p[1] + off[1], s, al * mal)
                if dd['tag']: blit(fr, text_img(dd['tag'], F(INTER_B, 20), GRAY, shadow=False), p[0] + off[0], p[1] + off[1] + 28, s, al * mal)
            else: xmark(d, p, (90, 120, 160), a=int(ea * 0.9))
        for sh in self.shots:
            q = prog(t, sh['t'], sh['t'] + 0.35)
            if t >= sh['t'] and q < 1:
                a = ea * (1 - q); mp = sh['to']
                d.line((yp[0], yp[1], mp[0], mp[1]), fill=(255, 255, 255, int(a * 0.8)), width=3)
                dot(d, yp, 26 * (1 - q), (255, 240, 200), outline=(255, 200, 120), ow=2, a=int(a)); shake = max(shake, 7 * (1 - q))
                blit(fr, text_img('NO KILL', F(ANTON, 50), GRAY, stroke=3), mp[0] + 10, mp[1] - 46 - 20 * q, 1, mal * (1 - q))
        for k in self.kills:
            if t < k['t']: continue
            q = prog(t, k['t'], k['t'] + 0.45); vp = self.enemies[k['victim']]['f']
            if q < 1:
                a = ea * (1 - q)
                src = k['src'] or yp
                d.line((src[0], src[1], vp[0], vp[1]), fill=(255, 230, 180, int(a * 0.35)), width=16)
                d.line((src[0], src[1], vp[0], vp[1]), fill=(255, 255, 255, int(a)), width=5)
                ring(d, vp, 18 + 80 * eo(q), RED, a, 6)
                if q < 0.35: dot(d, src, 34 * (1 - q), (255, 240, 200), outline=(255, 200, 120), ow=3, a=int(ea * (1 - q / 0.35)))
                shake = max(shake, 12 * (1 - prog(t, k['t'], k['t'] + 0.22)))
            if k['tag']:
                s, al = pop(t, k['t'] + 0.05, k['t'] + 1.6, out=0.25)
                label, c = {'WALL': ('WALLBANG', (210, 160, 90)), 'HS': ('HEADSHOT', (255, 214, 90))}.get(k['tag'], (k['tag'], (255, 214, 90)))
                pos = ((yp[0] + vp[0]) / 2, (yp[1] + vp[1]) / 2 + 60) if k['tag'] == 'WALL' else (vp[0] - 40, vp[1] - 75)
                blit(fr, text_img(label, F(ANTON, 64), c, stroke=4), pos[0], pos[1], s, al * mal)
                if k['tag'] == 'WALL' and q < 1:
                    for c_ in self.S['map'].get('crates', []):
                        cr = self.TR(c_); cx, cy = (cr[0] + cr[2]) / 2, (cr[1] + cr[3]) / 2
                        if _seg_dist((cx, cy), yp, vp) < 30: d.rectangle(cr, outline=(255, 90, 60, int(ea * (1 - q))), width=6)
        self.draw_trackers(fr, d, t, mal)
        nk = sum(1 for k in self.kills if t >= k['t'])
        if self.duel0 and t >= self.duel0 and self.kills and not self.trk:
            s, al = pop(t, self.duel0)
            pk = 1 + 0.25 * max([1 - prog(t, k['t'], k['t'] + 0.25) for k in self.kills if t >= k['t']] + [0])
            blit(fr, text_img(f'{nk}/{len(self.kills)}', F(ANTON, 76), self.hero_c if nk else GRAY), 480, 375, s * pk, al * mal)
            blit(fr, text_img('KILLS', F(INTER_K, 22), GRAY, shadow=False), 480, 432, s, al * mal)
        y = 292
        for k in self.kills:
            if t >= k['t']:
                s, al = pop(t, k['t'], dur=0.15)
                blit(fr, killfeed_img(self.S.get('hero_label', '???'), k['victim'], k['weapon'], k['tag'], self.hero_c, self.opp_c), 1012 + (1 - s) * 60, y, 1,
                     al * fade_out * (1 if t < st0 else max(dim * 1.3, 0.3)), anchor='r'); y += 57
        if self.hud0 is not None and t >= self.hud0:
            s, al = pop(t, self.hud0); al *= fade_out
            if self.clock:
                cv = self.clock_at(t)
                blit(fr, text_img(f'0:{int(cv):02d}', F(MONO, 44), RED if t < self.score_change else GRAY), 70, 300, s, al, anchor='l')
            hp = self.hp0; hit_t = None
            for h_ in self.hits:
                if t >= h_['t']: hp = h_['hp']; hit_t = h_['t']
            hit = hit_t is not None and t < hit_t + 0.5
            hpcol = RED if (hp < 30 or (hit and int(t * 12) % 2 == 0)) else WHITE
            blit(fr, text_img(f'+ {hp}', F(ANTON, 86), hpcol), 70, 390, s * (1 + (0.2 * (1 - prog(t, hit_t, hit_t + 0.3)) if hit else 0)), al, anchor='l')
            blit(fr, text_img(self.armor, F(INTER_K, 24), (190, 90, 90), shadow=False), 250, 400, s, al, anchor='l')
            bx0, by0, bw = 74, 445, 300
            d.rounded_rectangle((bx0, by0, bx0 + bw, by0 + 12), 6, fill=(255, 255, 255, int(40 * al)))
            prev_hp = self.hp0
            for h_ in self.hits:
                if h_['t'] < (hit_t or -1): prev_hp = h_['hp']
            shown = lerp(prev_hp, hp, eo(prog(t, hit_t, hit_t + 0.3))) if hit_t is not None else hp
            d.rounded_rectangle((bx0, by0, bx0 + bw * shown / 100, by0 + 12), 6, fill=(hpcol if hp < 30 else (240, 240, 240)) + (int(255 * al),))
            if hit: shake = max(shake, 14 * (1 - prog(t, hit_t, hit_t + 0.3)))
        if self.stats and t >= st0:
            items = self.stats.get('items', [])
            xs = [360, 740] if len(items) == 2 else [W / 2] * len(items)
            for i, it in enumerate(items[:2]):
                s, al = pop(t, st0 + 0.2 + 0.8 * i, self.t_exit, out=0.3)
                blit(fr, text_img(it['big'], F(ANTON, 300 if len(it['big']) < 3 else 230), self.hero_c if i == 0 else WHITE, glow=14), xs[i], 860, s, al)
                blit(fr, text_img(it['label'], F(ANTON, 80), WHITE if i == 0 else GRAY), xs[i], 1060, s, al)
            if self.stats.get('note'):
                s, al = pop(t, st0 + 1.8, self.t_exit, out=0.3)
                blit(fr, text_img(self.stats['note'], F(ANTON, 72), (230, 120, 40), stroke=4), W / 2, 1200, s, al)
            if self.stats.get('banner'):
                bt = self.tl.ref(self.stats['banner_at'], self.secs[0]) if self.stats.get('banner_at') else st0 + 2.8
                s, al = pop(t, self.loc(bt), self.t_exit, out=0.3)
                blit(fr, text_img(self.stats['banner'], F(ANTON, 66), self.hero_c, stroke=4), W / 2, 1290, s, al)
        return shake

    # ---------------- abilities (MOBA / hero games)
    def _col(self, by): return self.hero_c if by == 'hero' else self.opp_c
    def draw_abilities(self, fr, d, t, yp, ea, mal):
        for g in self.ghosts:
            if not g['t'] <= t < g['end']: continue
            c = self._col(g['by']); dot(d, g['p'], 15, (18, 18, 24), outline=c, ow=3, a=int(ea * 0.8))
            blit(fr, text_img('SHADOW', F(INTER_K, 16), c, shadow=False), g['p'][0], g['p'][1] + 28, 1, 0.75 * mal)
        for x in self.aoes:
            q = prog(t, x['t'], x['t'] + 0.55)
            if t >= x['t'] and q < 1:
                for p in x['ps']:
                    r = x['r'] * (0.35 + 0.65 * eo(min(1, q * 2))); d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=self._col(x['by']) + (int(ea * 0.20 * (1 - q)),))
                    ring(d, p, r, self._col(x['by']), ea * (1 - q), 5)
        for x in self.lines_:
            q = prog(t, x['t'], x['t'] + 0.5)
            if t >= x['t'] and q < 1:
                h = lerp2(x['a'], x['b'], eo(min(1, q * 2))); d.line((*x['a'], *h), fill=self._col(x['by']) + (int(ea * (1 - q)),), width=7); dot(d, h, 8, WHITE, a=int(ea * (1 - q)))
        for c in self.casts:
            if t < c['t'] or t > c['t'] + 1.25: continue
            if any(o['by'] == c['by'] and c['t'] < o['t'] <= t for o in self.casts): continue   # latest label wins
            col_ = self._col(c['by']); s, al = pop(t, c['t'], c['t'] + 1.25, out=0.25); q = prog(t, c['t'], c['t'] + 0.6)
            if c['a'] and q < 1: d.line((*c['a'], *c['b']), fill=col_ + (int(ea * 0.7 * (1 - q)),), width=6)
            p = yp if c['by'] == 'hero' else self.nip_pos(c['by'], t)
            im = text_img(c['label'], F(ANTON, 46), col_, stroke=4); w2 = im.width / 2
            x = clamp(p[0], PX0 + w2 + 10, PX1 - w2 - 10)
            o = yp if c['by'] != 'hero' else min((self.nip_pos(n, t) for n, e in self.enemies.items() if e['app'] <= t < e['die']), key=lambda q_: (q_[0] - yp[0]) ** 2 + (q_[1] - yp[1]) ** 2, default=(0, 0))
            up = p[1] <= o[1]                                       # label on the side away from the other player
            y = p[1] + ((-100 if up else 70) if c['by'] == 'hero' else (-62 if up else 62))
            blit(fr, im, x, clamp(y, PY0 + 34, PY1 - 60), s, al * mal)
    def draw_trackers(self, fr, d, t, mal):
        for i, x in enumerate(self.trk):
            y = 352 + 60 * i; c = self._col(x['by']); a = int(255 * mal)
            blit(fr, text_img(x['name'], F(INTER_K, 30), c), 74, y - 2, 1, mal, anchor='l')
            if x['hp']:
                v = x['hp'][0][1]
                for j, (tt, hv) in enumerate(x['hp']):
                    if t >= tt: v = lerp(x['hp'][j - 1][1] if j else hv, hv, eo(prog(t, tt, tt + 0.3)))
                d.rounded_rectangle((206, y - 10, 444, y + 8), 7, fill=(255, 255, 255, int(a * 0.16)))
                if v > 0.5: d.rounded_rectangle((206, y - 10, 206 + max(14, 2.38 * v), y + 8), 7, fill=(RED if v < 30 else (240, 240, 240)) + (a,))
                blit(fr, text_img(f'{v:.0f}%', F(INTER_K, 26), RED if v < 30 else WHITE, shadow=False), 454, y - 1, 1, mal, anchor='l')
            xx = 570
            for lab, on, off in x['items']:
                f = F(INTER_K, 20); w = int(f.getlength(lab)) + 22; used = t >= off; act = on <= t < off
                flash = 1 - prog(t, on, on + 0.5) if t >= on else 0
                fill = (34, 38, 48) if used else ((255, 214, 90) if act else c); tc = (92, 98, 112) if used else (14, 14, 20)
                d.rounded_rectangle((xx - 4 * flash, y - 20 - 4 * flash, xx + w + 4 * flash, y + 16 + 4 * flash), 8, fill=fill + (a,), outline=(255, 255, 255, int(a * flash)) if flash else None, width=3)
                d.text((xx + 11, y - 15), lab, font=f, fill=tc + (a,)); xx += w + 8

    def clock_at(self, t):
        C = self.clock
        if t <= C[0][0]: return C[0][1]
        for (a, va), (b, vb) in zip(C, C[1:]):
            if a <= t < b: return va + (vb - va) * (t - a) / (b - a)
        return C[-1][1]

def _seg_dist(p, a, b):
    ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy or 1; u = clamp(((px - ax) * dx + (py - ay) * dy) / L)
    return math.hypot(ax + u * dx - px, ay + u * dy - py)
