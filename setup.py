"""One-time setup (Windows / macOS / Linux):  python setup.py
Installs Python deps, the headless browser for the 3D intro, the Kokoro voice model, and checks ffmpeg."""
import shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
def run(cmd): print('>', ' '.join(cmd), flush=True); subprocess.run(cmd, check=True)
run([sys.executable, '-m', 'pip', 'install', '-r', str(ROOT / 'requirements.txt')])
run([sys.executable, '-m', 'playwright', 'install', 'chromium'])
sys.path.insert(0, str(ROOT)); from engine import voice; voice.ensure_models()
if not shutil.which('ffmpeg'):
    print('\n[!] ffmpeg not found. Windows: run  winget install --id Gyan.FFmpeg -e  then open a NEW terminal.'
          '\n    macOS: brew install ffmpeg   Linux: sudo apt install ffmpeg')
else:
    print('ffmpeg OK')
print('\nSetup done. Test:  python -m engine.cli build examples/guess_the_pro_kennys/spec.json')
