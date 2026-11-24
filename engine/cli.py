"""python -m engine.cli build <spec.json> [--stills 1.5,20,40] [--workers 2]"""
import argparse, json, os, shutil, subprocess, sys, time
from multiprocessing import Pool
from pathlib import Path
from .style import FPS
from .timeline import Timeline
from . import voice

ROOT = Path(__file__).resolve().parent.parent

def all_lines(spec):
    out = []
    for s in spec['sections']:
        out += s.get('lines', [])
        for b in s.get('beats', []) + s.get('cards', []): out += b.get('lines', [])
    return out

def load_all(spec_path, workdir, synth=True):
    spec = json.loads(Path(spec_path).read_text(encoding='utf-8'))
    game = json.loads((ROOT / 'games' / f"{spec['meta']['game']}.json").read_text(encoding='utf-8'))
    game.update(spec.get('game_overrides', {}))
    lines = all_lines(spec)
    ids = [l['id'] for l in lines]; dup = {i for i in ids if ids.count(i) > 1}
    if dup: raise ValueError(f'duplicate line ids: {dup}')
    if synth: durs = voice.synth_lines(lines, workdir, spec.get('voice', {}).get('voice', 'am_michael'))
    else: durs = {k: v['d'] for k, v in json.loads((Path(workdir) / 'vo' / 'cache.json').read_text()).items()}
    return spec, Timeline(spec, durs), game

def build(spec_path, workers=2, stills=None):
    spec_path = Path(spec_path).resolve(); wd = spec_path.parent / 'build'; wd.mkdir(exist_ok=True)
    t0 = time.time()
    print('[1/6] voice', flush=True); spec, tl, game = load_all(spec_path, wd)
    print('[2/6] timeline\n' + tl.report(), flush=True); (wd / 'timeline.txt').write_text(tl.report())
    from .compose import Composer, stage_schedule, stage_times, render_range
    from .stage import render_stage
    mood = spec['meta'].get('mood', 'default')
    sched = stage_schedule(tl, game, mood)
    if sched:
        print('[3/6] 3D stage', flush=True); render_stage(sched, stage_times(tl), wd / 'stage')
    if stills:
        c = Composer(spec, tl, game, wd); (wd / 'stills').mkdir(exist_ok=True)
        for ts in stills: c.frame(round(float(ts) * FPS)).save(wd / 'stills' / f's_{ts}.jpg', quality=88)
        print('stills ->', wd / 'stills'); return
    print('[4/6] sound', flush=True)
    from .audio import build_audio
    build_audio(tl, game, wd, str(wd / 'mix.wav'), mood)
    print('[5/6] frames', flush=True)
    N = int(round(tl.duration * FPS)); step = 150; jobs = []
    (wd / 'parts').mkdir(exist_ok=True)
    for i, n0 in enumerate(range(0, N, step)):
        jobs.append((str(spec_path), str(wd), n0, min(N, n0 + step), str(wd / 'parts' / f'p{i:03d}.mp4')))
    with Pool(workers) as pool:
        for k, out in enumerate(pool.imap(render_range, jobs)): print(f'  part {k + 1}/{len(jobs)}', flush=True)
    (wd / 'parts.txt').write_text(''.join(f"file '{Path(j[4]).as_posix()}'\n" for j in jobs))
    print('[6/6] mux + compress', flush=True)
    name = spec['meta'].get('out', spec_path.parent.name)
    out = spec_path.parent / f'{name}.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', str(wd / 'parts.txt'), '-i', str(wd / 'mix.wav'),
                    '-map', '0:v', '-map', '1:a', '-vf', 'hqdn3d=2:2:3:3', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '25', '-maxrate', '5M',
                    '-bufsize', '10M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', str(out)], check=True)
    from .publish import write_publish
    write_publish(spec, tl, spec_path.parent / 'publish.md')
    print(f'done in {time.time() - t0:.0f}s -> {out}  ({tl.duration:.1f}s)', flush=True)

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('spec'); b.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    b.add_argument('--stills', default=None, help='comma-separated times to preview instead of rendering')
    t = sub.add_parser('timeline'); t.add_argument('spec')
    a = ap.parse_args()
    if a.cmd == 'build': build(a.spec, a.workers, a.stills.split(',') if a.stills else None)
    elif a.cmd == 'timeline':
        wd = Path(a.spec).resolve().parent / 'build'; wd.mkdir(exist_ok=True); _, tl, _ = load_all(a.spec, wd); print(tl.report())
        for lid, L in sorted(tl.lines.items(), key=lambda kv: kv[1]['t']): print(f"  {lid:<5} {L['t']:6.2f} +{L['d']:.2f}  {L['cap']}")

if __name__ == '__main__':
    main()
