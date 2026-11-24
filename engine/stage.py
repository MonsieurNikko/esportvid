"""Render the 3D stage intro frames with headless Chromium (three.js)."""
import hashlib, json, os, platform, shutil, socket, threading, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

WEB = Path(__file__).resolve().parent / 'web'

class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def _server():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
    httpd = ThreadingHTTPServer(('127.0.0.1', port), functools.partial(_Quiet, directory=str(WEB)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port

def _launch(p):
    args = ['--ignore-gpu-blocklist']
    exe = os.environ.get('ESPORT_CHROME')
    if platform.system() == 'Linux':
        args += ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
        exe = exe or shutil.which('google-chrome') or shutil.which('chromium')
    try:
        return p.chromium.launch(args=args, executable_path=exe) if exe else p.chromium.launch(args=args)
    except Exception:
        return p.chromium.launch(channel='chrome', args=args)

def render_stage(sched, times, outdir):
    """times: list of (frame_index, t). Writes outdir/f_XXXXX.jpg + info.json; skips if cached."""
    from playwright.sync_api import sync_playwright
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    h = hashlib.sha1((json.dumps(sched, sort_keys=True) + (WEB / 'stage.html').read_text()).encode()).hexdigest()[:16]
    meta = outdir / 'info.json'
    if meta.exists():
        m = json.loads(meta.read_text())
        if m.get('hash') == h and all((outdir / f'f_{n:05d}.jpg').exists() for n, _ in times):
            print('  3D stage: cached', flush=True); return {int(k): v for k, v in m['info'].items()}
    httpd, port = _server(); info = {}
    try:
        with sync_playwright() as p:
            b = _launch(p); pg = b.new_page(viewport={'width': 810, 'height': 1440})
            pg.on('pageerror', lambda e: print('  [3D error]', e, flush=True))
            pg.goto(f'http://127.0.0.1:{port}/stage.html'); pg.wait_for_function('window.ready===true', timeout=120000)
            pg.evaluate('s => window.setup(s)', sched); pg.wait_for_function('window.ready2===true', timeout=60000)
            c = pg.locator('#c')
            for i, (n, t) in enumerate(times):
                info[n] = pg.evaluate(f'renderAt({t})')
                fn = outdir / f'f_{n:05d}.jpg'; c.screenshot(path=str(fn) + '.tmp.jpg', type='jpeg', quality=92); os.replace(str(fn) + '.tmp.jpg', fn)
                if i % 90 == 0: print(f'  3D stage: {i}/{len(times)}', flush=True)
            b.close()
    finally:
        httpd.shutdown()
    meta.write_text(json.dumps({'hash': h, 'info': info}))
    return info
