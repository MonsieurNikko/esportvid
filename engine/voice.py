"""Narration with Kokoro (Apache-2.0, OK for monetised videos).
Rules that keep the voice clean (learned the hard way):
  * speed is ALWAYS 1.0 — the timeline adapts to the voice, never the reverse;
  * each line is generated once, with soft 12 ms fades and natural padding (no hard trims);
  * no leading '...' and no one-word lines (Kokoro glitches on them) — write 'And Freeberg.' not 'Freeberg.';
  * write names/numbers the way they are SAID in `say` ('Get Right', 'Forest', 'sixteen to fourteen')."""
import hashlib, json, urllib.request
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'models'
URLS = {'kokoro-v1.0.onnx': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
        'voices-v1.0.bin': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin'}
SR = 48000

def ensure_models():
    MODELS.mkdir(exist_ok=True)
    for name, url in URLS.items():
        p = MODELS / name
        if not p.exists() or p.stat().st_size < 1_000_000:
            print(f'downloading {name} ...', flush=True); urllib.request.urlretrieve(url, p)

_k = None
def kokoro():
    global _k
    if _k is None:
        ensure_models()
        from kokoro_onnx import Kokoro
        _k = Kokoro(str(MODELS / 'kokoro-v1.0.onnx'), str(MODELS / 'voices-v1.0.bin'))
    return _k

def check_line(text):
    probs = []
    if text.strip().startswith(('...', '…')): probs.append('starts with an ellipsis')
    if len(text.split()) < 2: probs.append('single word (pad it: "And X." / "It\'s X.")')
    return probs

def synth_lines(lines, workdir, voice='am_michael'):
    """lines: list of dicts with id + say. Writes workdir/vo/<id>.wav, returns {id: duration_s}."""
    vo = Path(workdir) / 'vo'; vo.mkdir(parents=True, exist_ok=True)
    cache_f = vo / 'cache.json'; cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    durs = {}
    for ln in lines:
        lid, text = ln['id'], ln['say']
        for p in check_line(text): print(f'  [voice warning] {lid}: {p}', flush=True)
        h = hashlib.sha1(f'{voice}|{text}'.encode()).hexdigest()[:16]
        out = vo / f'{lid}.wav'
        if cache.get(lid, {}).get('h') == h and out.exists():
            durs[lid] = cache[lid]['d']; continue
        s, sr = kokoro().create(text, voice=voice, speed=1.0, lang='en-us')
        s = resample_poly(s, SR, sr)
        nz = np.nonzero(np.abs(s) > 1e-4)[0]
        if len(nz): s = s[max(0, nz[0] - int(0.04 * SR)): nz[-1] + int(0.12 * SR)]
        f = int(0.012 * SR); s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)
        s = s / max(float(np.max(np.abs(s))), 1e-6) * 0.85
        wavfile.write(out, SR, (s * 32767).astype(np.int16))
        d = round(len(s) / SR, 3); wps = len(text.split()) / d
        if wps > 3.8 or wps < 1.0: print(f'  [voice check] {lid}: {wps:.2f} words/s — listen to it', flush=True)
        cache[lid] = {'h': h, 'd': d}; durs[lid] = d
        print(f'  voice {lid}: {d:.2f}s  "{text}"', flush=True)
    cache_f.write_text(json.dumps(cache, indent=1))
    return durs
