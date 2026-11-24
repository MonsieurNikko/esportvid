"""One-time setup (Windows / macOS / Linux):
    python setup.py          # engine + Kokoro voice (CPU)
    python setup.py --gpu    # + Chatterbox (emotion-controlled voice) with CUDA PyTorch — recommended on NVIDIA
Tip: run it inside a virtual env:  python -m venv .venv  &&  .venv\\Scripts\\activate"""
import shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
def run(cmd): print('>', ' '.join(cmd), flush=True); subprocess.run(cmd, check=True)
pip = [sys.executable, '-m', 'pip', 'install']
run(pip + ['-r', str(ROOT / 'requirements.txt')])
run([sys.executable, '-m', 'playwright', 'install', 'chromium'])
sys.path.insert(0, str(ROOT)); from engine import voice; voice.ensure_models()
if '--gpu' in sys.argv:
    run(pip + ['chatterbox-tts'])
    import importlib, torch; ver = torch.__version__.split('+')[0]; importlib.invalidate_caches()
    # chatterbox pulls a CPU torch from PyPI on Windows: swap in the CUDA build of the same version
    run(pip + ['--force-reinstall', '--no-deps', f'torch=={ver}', f'torchaudio=={ver}', '--index-url', 'https://download.pytorch.org/whl/cu124'])
    out = subprocess.run([sys.executable, '-c', 'import torch;print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else "")'],
                         capture_output=True, text=True).stdout.strip()
    print('CUDA:', out)
    if not out.startswith('True'): print('[!] CUDA not visible to PyTorch: update the NVIDIA driver, then re-run python setup.py --gpu')
if not shutil.which('ffmpeg'):
    print('\n[!] ffmpeg not found. Windows: winget install --id Gyan.FFmpeg -e  (then open a NEW terminal)'
          '\n    macOS: brew install ffmpeg   Linux: sudo apt install ffmpeg')
else:
    print('ffmpeg OK')
print('\nSetup done. Test:  python -m engine.cli build examples/guess_the_pro_kennys/spec.json')
