"""Signature score ("theme C", A minor, dark bell hook) arranged ON the timeline:
logo sting at 0 s → filtered build in the context → full theme in the action (accents on kills) → riser + 0.4 s silence
→ full motif on the reveal → hard cut that falls back on bar 1 (loop). Pure numpy, no licensed music, nothing to claim.
Recipe sources: sound-on platforms want a bold recognisable hook; build into reveals (rising pitch, dissonance);
end on a cut, not a fade; same theme in every video for recognition; music ~15-20 % of the voice level."""
import numpy as np
from scipy.signal import butter, sosfilt, lfilter

SR = 48000
BPM = 78
SPB = 60 / BPM
HOOK = [(76, .5), (76, .5), (79, 1), (76, .5), (74, .5), (72, 1),
        (74, .5), (74, .5), (76, 1), (69, 2),
        (76, .5), (76, .5), (79, 1), (76, .5), (74, .5), (72, 1),
        (74, .5), (72, .5), (71, .5), (69, 2.5)]
LOGO = [(76, .5), (76, .5), (79, 1), (69, 1.5)]
CHORDS = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (52, [52, 56, 59])]  # Am F C E

def mtof(m): return 440 * 2 ** ((m - 69) / 12)
def _lp(x, f): return sosfilt(butter(2, f, 'low', fs=SR, output='sos'), x)
def _hp(x, f): return sosfilt(butter(2, f, 'high', fs=SR, output='sos'), x)
def _adsr(n, a, d, s, r):
    A, D, R = int(a * SR), int(d * SR), int(r * SR); S = max(0, n - A - D)
    return np.concatenate([np.linspace(0, 1, A, False), np.linspace(1, s, D, False), np.full(S, s), np.linspace(s, 0, R)])

def bell(f, dur):
    t = np.arange(int((dur + 0.8) * SR)) / SR
    return 0.5 * sum(a * np.sin(2 * np.pi * f * m * t) * np.exp(-t * k) for m, a, k in ((1, 1, 3), (2.0, .5, 5), (3.01, .25, 7), (4.2, .12, 9)))
def pad(f, dur):
    n = int(dur * SR); e = _adsr(n, 0.4, 0.3, 0.8, 0.6); t = np.arange(len(e)) / SR
    return sum(np.sin(2 * np.pi * f * (1 + d) * t) for d in (-0.004, 0, 0.004)) / 3 * e * 0.4
def bass(f, dur):
    n = int(dur * SR); e = _adsr(n, 0.005, 0.15, 0.6, 0.08); t = np.arange(len(e)) / SR
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * e * 0.7
def kick():
    t = np.arange(int(.35 * SR)) / SR; return np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 9)
def hat(rng):
    t = np.arange(int(.06 * SR)) / SR; return _hp(rng.standard_normal(len(t)), 7000) * np.exp(-t * 60) * .25
def reverb(x, mix=0.35):
    out = x.copy()
    for d, g in ((0.0297, .77), (0.0371, .74), (0.0411, .72), (0.0437, .7)):
        k = int(d * SR); a = np.zeros(k + 1); a[0] = 1; a[k] = -g
        out += _lp(lfilter([1.0], a, x), 4000) * mix / 4
    return out

def _put(buf, sig, t, g=1.0):
    i = int(t * SR)
    if i >= len(buf) or i < 0: return
    s = sig[:len(buf) - i] * g; buf[i:i + len(s)] += s

def score(tl, mood='default'):
    """Returns a mono numpy track (unnormalised) arranged on tl.sections."""
    N = int(tl.duration * SR); rng = np.random.default_rng(5)
    stems = {k: np.zeros(N) for k in ('pad', 'bass', 'hook', 'perc', 'fx')}
    bar = 4 * SPB; nbars = int(tl.duration / bar) + 2
    for b in range(nbars):                      # harmonic bed on a global bar grid
        root, triad = CHORDS[b % 4]; t0 = b * bar
        for m in triad: _put(stems['pad'], pad(mtof(m), bar), t0, 0.5)
        _put(stems['bass'], bass(mtof(root - 12), bar * 0.95), t0, 0.8)
        for k in range(4):
            if k in (0, 2): _put(stems['perc'], kick() * 0.7, t0 + k * SPB)
            _put(stems['perc'], hat(rng), t0 + k * SPB + SPB / 2, 0.6)
    def hook_from(t, until):                    # the hook restarts at the start of its section (phrase-aligned)
        beat = 0.0
        while t + beat * SPB < until:
            for m, d in HOOK:
                tt = t + beat * SPB
                if tt >= until: break
                _put(stems['hook'], bell(mtof(m + 12), d * SPB * 0.95), tt, 0.55); beat += d
    def logo(t, g=1.0):
        beat = 0.0
        for m, d in LOGO:
            _put(stems['fx'], bell(mtof(m + 12), d * SPB) * 1.1, t + beat * SPB * 0.7, g); beat += d
        _put(stems['fx'], bass(mtof(45), 1.2), t + 2 * SPB * 0.7, 0.9 * g); _put(stems['fx'], kick(), t + 2 * SPB * 0.7, 0.9 * g)
    # gain automation per section
    G = {k: np.zeros(N) for k in stems if k != 'fx'}
    lv = {'cold_open': dict(pad=.6, bass=.5, hook=0, perc=0), 'rewind': dict(pad=.2, bass=.2, hook=0, perc=0),
          'context': dict(pad=.7, bass=.8, hook=0, perc=.25), 'radar': dict(pad=.55, bass=1, hook=.8, perc=.6),
          'cards': dict(pad=.7, bass=.6, hook=.55, perc=.2), 'predict': dict(pad=.3, bass=0, hook=0, perc=0),
          'clue': dict(pad=.6, bass=.3, hook=0, perc=0), 'reveal': dict(pad=.45, bass=.2, hook=0, perc=0)}
    for s in tl.sections:
        a, b = int(s['t0'] * SR), int(s['t1'] * SR)
        for k, v in lv[s['type']].items(): G[k][a:b] = v
        if s['type'] in ('radar', 'cards'): hook_from(s['t0'] + (0.0 if s['type'] == 'cards' else s['spec'].get('lead', 1.4)), s['t1'])
        if s['type'] == 'cold_open' and s['idx'] == 0: logo(0.05)
        if s['type'] == 'reveal':
            R0 = s['R0']; r0, r1 = int((R0 - 0.4) * SR), int(R0 * SR)
            for k in G: G[k][r0:r1] = 0.0           # the 0.4 s silence before the answer
            G['pad'][r1:b] = .5; G['bass'][r1:b] = .5
            logo(R0, 1.0); hook_from(R0 + 2.2, s['t1'])
        if s['type'] == 'radar' and s['spec'].get('events'):
            for e in s['spec']['events']:
                if e['type'] == 'kill':
                    _put(stems['fx'], bell(mtof(81), 0.4), tl.ref(e['at'], s), 0.5); _put(stems['fx'], kick(), tl.ref(e['at'], s), 0.5)
    win = int(0.25 * SR); ker = np.ones(win) / win
    mix = stems['fx'].copy()
    for k in G:
        g = np.convolve(G[k], ker, mode='same')    # 250 ms crossfades between sections
        x = stems[k] * g
        if k == 'bass':                            # context: low-pass sweep opening up (the build)
            ctx = next((s for s in tl.sections if s['type'] == 'context'), None)
            if ctx:
                a, b = int(ctx['t0'] * SR), int(ctx['t1'] * SR)
                seg = x[a:b]; half = len(seg) // 2
                x[a:a + half] = _lp(seg[:half], 300); x[a + half:b] = _lp(seg[half:], 900)
        mix += x
    if mood == 'dark': mix = mix * 0.9
    # rewind: the previous 2 s of music, reversed and squeezed into the rewind window (tape effect)
    for s in tl.sections:
        if s['type'] == 'rewind':
            a, b = int(s['t0'] * SR), int(s['t1'] * SR); src = mix[max(0, a - 2 * SR):a][::-1]
            if len(src): mix[a:b] = np.interp(np.linspace(0, len(src) - 1, b - a), np.arange(len(src)), src) * 0.8
    mix = reverb(mix, 0.35)
    end = int(tl.duration * SR); f = int(0.03 * SR); mix[end - f:end] *= np.linspace(1, 0, f)   # hard cut, not a fade
    return mix[:N]
