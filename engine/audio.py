"""Synthesised score + SFX (no licensed music, nothing to claim) and narration mix with ducking."""
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000

class Mixer:
    def __init__(self, dur, seed=3):
        self.N = int(SR * dur); self.L = np.zeros(self.N); self.R = np.zeros(self.N); self.rng = np.random.default_rng(seed)
    # filters / generators
    def lp(self, x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
    def hp(self, x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
    def bp(self, x, a, b, o=2): return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)
    def tt(self, d): return np.arange(int(d * SR)) / SR
    def noise(self, d): return self.rng.standard_normal(int(d * SR))
    def env(self, d, a=0.005, k=8.0):
        x = self.tt(d); e = np.exp(-x * k); na = max(1, int(a * SR)); e[:na] *= np.linspace(0, 1, na); return e
    def add(self, sig, t, g=1.0, pan=0.0):
        i = int(t * SR)
        if i >= self.N or i < 0: return
        s = sig[:self.N - i] * g
        self.L[i:i + len(s)] += s * (1 - max(0, pan)); self.R[i:i + len(s)] += s * (1 + min(0, pan))
    # sounds
    def tick(self, f=2200, d=0.04, k=90): x = self.tt(d); return np.sin(2 * np.pi * f * x) * self.env(d, 0.001, k)
    def blip(self, f, d=0.09): x = self.tt(d); return np.sin(2 * np.pi * f * x) * self.env(d, 0.002, 30)
    def thud(self, f0=80, d=0.35):
        x = self.tt(d); f = f0 * np.exp(-x * 4); ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * self.env(d, 0.002, 11) + 0.15 * self.lp(self.noise(d), 900) * self.env(d, 0.001, 40)
    def whoosh(self, d=0.6): x = self.tt(d); return self.bp(self.noise(d), 500, 4500) * np.sin(np.pi * x / d) ** 2 * 0.5
    def ping(self, f=1100, d=0.6): x = self.tt(d); return (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(2 * np.pi * f * 2.01 * x)) * self.env(d, 0.003, 7)
    def heartbeat(self): return np.concatenate([self.thud(60, 0.16), np.zeros(int(0.03 * SR)), 0.7 * self.thud(55, 0.2)])
    def gun(self, cls='sniper'):
        if cls == 'ability': return self.whoosh(0.4) * 1.5 + self.thud(70, 0.5)
        crack_d, boom_f, boom_k, tail_d, g = {'sniper': (0.035, 160, 7, 1.2, 1.0), 'rifle': (0.03, 140, 10, 0.5, 0.8),
                                              'pistol': (0.025, 200, 14, 0.35, 0.6), 'shotgun': (0.05, 110, 8, 0.7, 1.0)}.get(cls, (0.03, 140, 10, 0.5, 0.8))
        crack = self.hp(self.noise(crack_d), 1500) * self.env(crack_d, 0.0005, 120) * 1.6
        x = self.tt(0.5); f = boom_f * np.exp(-x * boom_k) + 40; boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * self.env(0.5, 0.001, boom_k) * 1.1
        tail = self.lp(self.noise(tail_d), 1400) * self.env(tail_d, 0.002, 4 / tail_d) * 0.45
        out = np.zeros(int((tail_d + 0.8) * SR)); out[:len(crack)] += crack; out[:len(boom)] += boom; out[:len(tail)] += tail
        for dl, gg in ((0.11, 0.35), (0.23, 0.18)):
            i = int(dl * SR); out[i:] += gg * self.lp(out[:len(out) - i], 2500)
        if cls == 'sniper':
            for dt in (0.55, 0.68):
                i = int(dt * SR); c = self.hp(self.noise(0.02), 2000) * self.env(0.02, 0.0005, 150) * 0.35; out[i:i + len(c)] += c
        return out * g
    def wood(self): return self.bp(self.noise(0.18), 250, 1600) * self.env(0.18, 0.001, 22) * 0.9
    def ding(self):
        x = self.tt(0.7); return sum(a * np.sin(2 * np.pi * f * x) for f, a in ((2600, 1), (5210, 0.4), (7800, 0.15))) * self.env(0.7, 0.001, 9) * 0.25
    def riser(self, d):
        x = self.tt(d); p = x / d; f = 180 + 700 * p ** 2
        return self.bp(self.noise(d), 300, 6000) * (p ** 2.2) * 0.5 + 0.25 * np.sin(2 * np.pi * np.cumsum(f) / SR) * p ** 1.5
    def impact(self, d=3.0):
        x = self.tt(d); f = 70 * np.exp(-x * 2) + 28; boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * self.env(d, 0.001, 2.2) * 1.2
        burst = self.lp(self.noise(d), 2500) * self.env(d, 0.001, 3.5) * 0.6
        chord = sum(np.sign(np.sin(2 * np.pi * fr * x)) * 0.07 + np.sin(2 * np.pi * fr * x) * 0.15 for fr in (220, 261.63, 329.63, 440))
        return boom + burst + self.lp(chord, 2200) * self.env(d, 0.01, 1.4)
    def stinger(self):
        x = self.tt(1.4); return self.lp(sum(np.sin(2 * np.pi * fr * x) for fr in (196, 246.9, 293.7, 392)), 3000) * self.env(1.4, 0.01, 3) * 0.18
    def rewind(self, d=0.5):
        x = self.tt(d); f = 3000 * (1 - x / d) + 300
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15 + self.bp(self.noise(d), 1500, 7000) * 0.35) * np.sin(np.pi * x / d)
    def siren(self, d=0.45, f=880): x = self.tt(d); return np.sin(2 * np.pi * f * x) * self.env(d, 0.01, 4) * 0.12

def build_audio(tl, game, workdir, out_wav, mood='default'):
    D = tl.duration; m = Mixer(D)
    wcls = game.get('weapon_class', {}); dcls = game.get('default_weapon_class', 'rifle')
    for i, s in enumerate(tl.sections):
        S, t0, t1, ty = s['spec'], s['t0'], s['t1'], s['type']
        if i > 0 and ty != 'rewind': m.add(m.whoosh(), t0 - 0.3, 0.9)
        if ty == 'cold_open':
            for k in range(S.get('enemies', 0)):
                m.add(m.thud(60, 0.6), t0 + 0.5 + 0.45 * k, 0.6); m.add(m.ping(700 + 90 * k, 0.7), t0 + 0.5 + 0.45 * k, 0.18)
            for ln in S.get('lines', []):
                if ln.get('role') == 'punch': m.add(m.impact()[:int(1.2 * SR)] * 0.6, tl.lines[ln['id']]['t'])
        elif ty == 'rewind': m.add(m.rewind(), t0, 1.0)
        elif ty == 'context':
            t = t0; k = 0
            while t < t1: m.add(m.tick(2600 if k % 2 == 0 else 2000, 0.03, 120), t, 0.12); t += 0.5; k += 1
            for b in s['beats']:
                kind = b['spec']['kind']; m.add(m.thud(95, 0.4), b['t0'] + 0.05, 0.7)
                if kind == 'title': m.add(m.stinger() * 1.4, b['t0'] + 0.1)
                if kind == 'alarm':
                    for q in range(4): m.add(m.siren(0.45, 880 if q % 2 == 0 else 660), b['t0'] + 0.05 + q * 0.5)
            m.add(m.whoosh(1.0), t1 - 1.0, 1.0)
        elif ty == 'radar':
            R = lambda r: tl.ref(r, s)
            for mt in S.get('mates', []): m.add(m.thud(70, 0.3), R(mt['die']), 0.7); m.add(m.blip(520, 0.12), R(mt['die']) + 0.02, 0.18)
            for e in S.get('enemies', []): m.add(m.ping(), R(e['appear']), 0.25, 0.4)
            kills = [e for e in S['events'] if e['type'] == 'kill']
            for e in S['events']:
                ty_ = e['type']; t = R(e['at'])
                if ty_ == 'pickup': m.add(m.blip(660), t, 0.35); m.add(m.blip(990), t + 0.09, 0.35)
                if ty_ in ('kill', 'shot'):
                    cls = wcls.get(e.get('weapon', game.get('default_weapon')), dcls)
                    m.add(m.gun(cls), t, 0.95 if ty_ == 'kill' else 0.6)
                    if e.get('tag') == 'WALL': m.add(m.wood(), t + 0.02, 0.8)
                    if e.get('tag') == 'HS': m.add(m.ding(), t + 0.03, 0.9)
                if ty_ == 'hit': m.add(m.thud(65, 0.4), t, 1.0); m.add(np.sin(2 * np.pi * 3100 * m.tt(1.4)) * m.env(1.4, 0.05, 2.5) * 0.06, t + 0.05)
            if S.get('heartbeat'):
                a, b = R(S['heartbeat'][0]), R(S['heartbeat'][1]); t = a
                while t < b: m.add(m.heartbeat(), t, 0.85); t += 0.85 + (0.55 - 0.85) * min(1, (t - a) / max(b - a, 1e-3))
            if kills:
                lk = max(R(e['at']) for e in kills); d0 = R(S['duel_from']) if S.get('duel_from') else lk - 8; t = d0; k = 0
                while t < lk: m.add(m.tick(2600 if k % 2 == 0 else 2000, 0.03, 120), t, 0.16); t += 0.5; k += 1
                m.add(m.stinger(), lk + 0.6, 1.0)
            if S.get('stats'):
                st = R(S['stats']['at'])
                for q in range(3): m.add(m.thud(100, 0.3), st + 0.2 + 0.8 * q, 0.6)
        elif ty == 'cards':
            for c in s['cards']: m.add(m.thud(55 if mood == 'dark' else 95, 0.5), c['t0'] + 0.1, 0.8)
        elif ty == 'predict':
            m.add(m.impact()[:int(1.0 * SR)] * 0.5, t0); m.add(m.riser(max(0.5, s['count'][-1] - t0)), t0, 0.6)
            for c in s['count']: m.add(m.tick(1500, 0.06, 50), c, 0.6)
        elif ty == 'clue':
            for ln in S.get('lines', []):
                if ln.get('role') == 'big': m.add(m.thud(90, 0.4), tl.lines[ln['id']]['t'], 0.8); m.add(m.ding() * 0.6, tl.lines[ln['id']]['t'] + 0.02)
        elif ty == 'reveal':
            m.add(m.riser(s['R0'] - t0 - 0.05), t0, 0.9)
            for c in s['count']: m.add(m.tick(1500, 0.06, 50), c, 0.6)
            m.add(m.impact(), s['R0'], 1.0); m.add(m.thud(120, 0.25), s['R0'] + 0.4, 0.4); m.add(m.thud(120, 0.25), s['R0'] + 1.2, 0.4)
    # narration
    vo = np.zeros(m.N)
    for lid, L in tl.lines.items():
        sr_, s = wavfile.read(Path(workdir) / 'vo' / f'{lid}.wav'); s = s.astype(np.float64) / 32768
        i0 = int(L['t'] * SR); s = s[:max(0, m.N - i0)]; vo[i0:i0 + len(s)] += s
    # signature score arranged on the timeline (engine/music.py)
    from .music import score
    mus = score(tl, mood)[:m.N]; mus = np.pad(mus, (0, m.N - len(mus)))
    active = np.abs(vo) > 0.02
    v_rms = np.sqrt(np.mean(vo[active] ** 2)) if active.any() else 0.2
    m_rms = np.sqrt(np.mean(mus ** 2)) or 1.0
    mus = mus / m_rms * v_rms * 0.36            # ~0.36 of the voice when alone, ~0.18 (15-20 %) under the voice
    sfx = np.stack([m.L, m.R], 1); sfx = np.tanh(sfx * 1.3) / np.tanh(1.3)
    sfx = sfx / (np.max(np.abs(sfx)) or 1) * 0.7
    win = int(0.12 * SR); env = np.convolve(np.abs(vo), np.ones(win) / win, mode='same')
    duck = 1 - 0.5 * np.clip(env / 0.05, 0, 1)
    out = (mus * duck)[:, None] + sfx * (1 - 0.25 * np.clip(env / 0.05, 0, 1))[:, None] + vo[:, None] * 0.98
    out = np.tanh(out * 1.1) / np.tanh(1.1); out /= np.max(np.abs(out)) / 0.92
    f = int(0.03 * SR); out[-f:] *= np.linspace(1, 0, f)[:, None]
    wavfile.write(out_wav, SR, (out * 32767).astype(np.int16))
