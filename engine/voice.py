"""Narration with controllable emotion.

Engines (spec.voice.engine):
  "auto" (default)  -> Chatterbox if it is installed and a CUDA GPU is present, else Kokoro
  "chatterbox"      -> Resemble AI Chatterbox (MIT). Standard model = emotion intensity knob; Turbo = [gasp]/[sigh]… reactions
  "kokoro"          -> Kokoro-82M (Apache-2.0), no emotion control (tags are stripped)
  "maya1"           -> Maya Research Maya1 (Apache-2.0), voice described in words + emotion tags — see docs/voice.md

Per line in the spec:  {"say": "Then Forest. [gasp] Through a crate.", "emo": "shock", "intensity": 0.8}
  * emo: calm | neutral | serious | tense | excited | shock | hype | sad   (sets a default intensity)
  * intensity 0..1 overrides it (0.3 = flat narrator, 1.0 = very dramatic)
  * reactions in [brackets] (Chatterbox Turbo): [gasp] [sigh] [laugh] [chuckle] [groan] [sniff] [cough] [clear throat] [shush]
Rules that keep any engine clean: one generation per line, soft 12 ms fades, no leading '…', no one-word lines,
names/numbers spelled the way they are said ('Get Right', 'sixteen to fourteen')."""
import hashlib, json, re, urllib.request
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'models'
SR = 48000
KOKORO_URLS = {'kokoro-v1.0.onnx': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx',
               'voices-v1.0.bin': 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin'}
TAGS = ['clear throat', 'sigh', 'shush', 'cough', 'groan', 'sniff', 'gasp', 'chuckle', 'laugh']
TAG_RE = re.compile(r'\[(' + '|'.join(TAGS) + r')\]', re.I)
EMO = {'calm': 0.3, 'neutral': 0.45, 'serious': 0.5, 'sad': 0.4, 'tense': 0.6, 'excited': 0.75, 'shock': 0.85, 'hype': 0.95}
REF_TEXT = ("February, twenty-fifteen. One round left, and the whole season on the line. "
            "Four players stand between you and the final. No armor, fifty HP, and the clock is running.")

def ensure_models():
    MODELS.mkdir(exist_ok=True)
    for name, url in KOKORO_URLS.items():
        p = MODELS / name
        if not p.exists() or p.stat().st_size < 1_000_000:
            print(f'downloading {name} ...', flush=True); urllib.request.urlretrieve(url, p)

def strip_tags(t): return re.sub(r'\s{2,}', ' ', TAG_RE.sub('', t)).strip()

def check_line(text):
    probs = []
    if text.strip().startswith(('...', '…')): probs.append('starts with an ellipsis')
    if len(strip_tags(text).split()) < 2: probs.append('single word (pad it: "And X." / "It\'s X.")')
    for tag in re.findall(r'\[([^\]]+)\]', text):
        if tag.lower() not in TAGS: probs.append(f'unknown reaction [{tag}] (allowed: {", ".join(TAGS)})')
    return probs

# ---------------------------------------------------------------- engines
class Kokoro:
    name = 'kokoro'
    def __init__(self, voice='am_michael'):
        ensure_models(); from kokoro_onnx import Kokoro as K
        self.k = K(str(MODELS / 'kokoro-v1.0.onnx'), str(MODELS / 'voices-v1.0.bin')); self.voice = voice
    def synth(self, text, intensity):
        s, sr = self.k.create(strip_tags(text), voice=self.voice, speed=1.0, lang='en-gb' if self.voice.startswith('b') else 'en-us')
        return np.asarray(s, dtype=np.float64), sr

class Chatterbox:
    name = 'chatterbox'
    def __init__(self, ref_wav, device='cuda'):
        self.ref, self.device, self._std, self._turbo = str(ref_wav), device, None, None
    def std(self):
        if self._std is None:
            from chatterbox.tts import ChatterboxTTS; self._std = ChatterboxTTS.from_pretrained(device=self.device)
        return self._std
    def turbo(self):
        if self._turbo is None:
            from chatterbox.tts_turbo import ChatterboxTurboTTS; self._turbo = ChatterboxTurboTTS.from_pretrained(device=self.device)
        return self._turbo
    def synth(self, text, intensity):
        if TAG_RE.search(text):                     # reactions only exist in Turbo
            m = self.turbo(); wav = m.generate(text, audio_prompt_path=self.ref)
        else:                                       # intensity knob lives in the standard model
            m = self.std()
            wav = m.generate(text, audio_prompt_path=self.ref, exaggeration=float(0.3 + 0.7 * intensity),
                             cfg_weight=float(0.5 - 0.2 * intensity))
        return wav.squeeze().detach().cpu().numpy().astype(np.float64), m.sr

class Maya1:
    name = 'maya1'
    def __init__(self, description):
        raise NotImplementedError('Maya1 backend not wired yet: see docs/voice.md ("Finish the Maya1 backend") — '
                                  'Claude Code on your PC can implement it from the model card in one pass.')

def _cuda():
    try:
        import torch; return torch.cuda.is_available()
    except Exception: return False

def reference_wav(ref):
    """'kokoro:<voice>' -> a 12 s neutral read by that Kokoro voice (timbre to clone), or a path to your own wav."""
    if not ref.startswith('kokoro:'): return Path(ref)
    v = ref.split(':', 1)[1]; out = MODELS / f'ref_{v}.wav'
    if not out.exists():
        s, sr = Kokoro(v).synth(REF_TEXT, 0.5); wavfile.write(out, sr, (s / np.max(np.abs(s)) * 0.9 * 32767).astype(np.int16))
    return out

def get_engine(cfg):
    eng = cfg.get('engine', 'auto'); ref = cfg.get('ref', 'kokoro:' + cfg.get('voice', 'am_michael'))
    if eng == 'maya1': return Maya1(cfg.get('description', ''))
    if eng in ('auto', 'chatterbox'):
        try:
            import chatterbox  # noqa: F401
            if _cuda() or eng == 'chatterbox':
                return Chatterbox(reference_wav(ref), 'cuda' if _cuda() else 'cpu')
        except ImportError:
            if eng == 'chatterbox': raise
        print('  [voice] Chatterbox unavailable (not installed or no CUDA) -> Kokoro fallback', flush=True)
    return Kokoro(cfg.get('voice', 'am_michael'))

# ---------------------------------------------------------------- lines
def synth_lines(lines, workdir, cfg=None):
    """lines: dicts with id, say, optional emo/intensity. Writes workdir/vo/<id>.wav; returns {id: seconds}."""
    cfg = cfg if isinstance(cfg, dict) else {'voice': cfg or 'am_michael'}
    vo = Path(workdir) / 'vo'; vo.mkdir(parents=True, exist_ok=True)
    cache_f = vo / 'cache.json'; cache = json.loads(cache_f.read_text()) if cache_f.exists() else {}
    engine, durs = None, {}
    sig = json.dumps({k: cfg.get(k) for k in ('engine', 'voice', 'ref', 'description')}, sort_keys=True)
    for ln in lines:
        lid, text = ln['id'], ln['say']
        inten = float(ln.get('intensity', EMO.get(ln.get('emo', 'neutral'), 0.45)))
        for p in check_line(text): print(f'  [voice warning] {lid}: {p}', flush=True)
        h = hashlib.sha1(f'{sig}|{text}|{inten:.2f}'.encode()).hexdigest()[:16]
        out = vo / f'{lid}.wav'
        if cache.get(lid, {}).get('h') == h and out.exists(): durs[lid] = cache[lid]['d']; continue
        if engine is None: engine = get_engine(cfg); print(f'  [voice] engine: {engine.name}', flush=True)
        s, sr = engine.synth(text, inten)
        s = resample_poly(s, SR, sr)
        nz = np.nonzero(np.abs(s) > 1e-4)[0]
        if len(nz): s = s[max(0, nz[0] - int(0.04 * SR)): nz[-1] + int(0.12 * SR)]
        f = int(0.012 * SR); s[:f] *= np.linspace(0, 1, f); s[-f:] *= np.linspace(1, 0, f)
        s = s / max(float(np.max(np.abs(s))), 1e-6) * 0.85
        wavfile.write(out, SR, (s * 32767).astype(np.int16))
        d = round(len(s) / SR, 3); wps = len(strip_tags(text).split()) / d
        if wps > 3.8 or wps < 1.0: print(f'  [voice check] {lid}: {wps:.2f} words/s — listen to it', flush=True)
        cache[lid] = {'h': h, 'd': d}; durs[lid] = d
        print(f'  voice {lid} ({engine.name}, {inten:.2f}): {d:.2f}s  "{text}"', flush=True)
    cache_f.write_text(json.dumps(cache, indent=1))
    return durs
