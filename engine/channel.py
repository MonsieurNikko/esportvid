"""Channel identity (handle shown as watermark, name used in the publish kit).
Looked up, first found wins:  <episode folder>/channel.json  ->  <repo root>/channel.json  ->  ~/.esportvid/channel.json
{"handle": "@mychannel", "name": "My Channel"}   — handle null/"" = no watermark (channel not created yet)."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def channel_paths(episode_dir=None):
    out = []
    if episode_dir: out.append(Path(episode_dir) / 'channel.json')
    return out + [ROOT / 'channel.json', Path.home() / '.esportvid' / 'channel.json']

def load_channel(episode_dir=None, warn=True):
    for p in channel_paths(episode_dir):
        if p.exists():
            try: return json.loads(p.read_text(encoding='utf-8'))
            except Exception as e: print(f'  [channel] cannot read {p}: {e}')
    if warn: print('  [channel] no channel.json found -> no watermark. Ask the user for the channel handle and save it to '
                   f'{ROOT / "channel.json"} as {{"handle": "@name", "name": "Name"}}', flush=True)
    return {}
