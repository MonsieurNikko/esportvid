"""Episode cover (thumbnail) in the house style.

Layout rule: every key element sits inside y 420-1500 (the 1080x1080 centre that
TikTok's profile grid keeps, also inside Instagram's 3:4 grid crop) and stays out
of the bottom 300 px (TikTok caption bar).

Usage: python -m engine.cli cover spec.json   (or engine.cover.make_cover(...))
spec["cover"] = {"frame": 96, "kicker": "GUESS THE PRO #1", "headline": "WHO IS HE?",
                 "tag": "50 HP · NO ARMOR"}   # all optional
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from .style import W, H, F, ANTON, INTER_K, WHITE, RED, MOODS, text_img, blit, watermark

def make_cover(spec, episode_dir, handle=None, out=None):
    episode_dir = Path(episode_dir)
    c = spec.get('cover', {})
    mood = MOODS[spec.get('mood', 'default')]; acc = mood['accent']
    frames = sorted((episode_dir / 'build' / 'stage').glob('f_*.jpg'))
    if frames:
        bg = Image.open(frames[min(c.get('frame', 96), len(frames) - 1)]).convert('RGB').resize((W, H))
        bg = ImageEnhance.Brightness(bg).enhance(0.8)
    else:
        bg = Image.new('RGB', (W, H), mood['bg_bot'])
    fr = bg.convert('RGBA')
    # darken top and bottom bands so the text reads on any frame
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(shade)
    for y in range(H):
        a = 0
        if y < 700: a = int(190 * (1 - y / 700) ** 0.8)
        if y > 1180: a = max(a, int(215 * min(1, (y - 1180) / 420)))
        d.line((0, y, W, y), fill=(0, 0, 0, a))
    fr = Image.alpha_composite(fr, shade)

    kicker = c.get('kicker', f"{spec.get('format', 'guess_the_pro').replace('_', ' ').upper()} #{spec.get('episode', 1)}")
    headline = c.get('headline', 'WHO IS HE?')
    tag = c.get('tag')

    # kicker chip
    k = text_img(kicker, F(INTER_K, 46), WHITE, shadow=False)
    chip = Image.new('RGBA', (k.width - 20, 96), (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle((0, 0, chip.width - 1, 95), 18, fill=acc + (255,))
    chip.paste(k, ((chip.width - k.width) // 2, (96 - k.height) // 2), k)
    blit(fr, chip, W / 2, 462)
    # headline, '?' in accent
    if headline.endswith('?'):
        a = text_img(headline[:-1], F(ANTON, 200), WHITE, stroke=6)
        q = text_img('?', F(ANTON, 200), acc, stroke=6, glow=10)
        tot = a.width + q.width - 110
        blit(fr, a, W / 2 - tot / 2 + a.width / 2, 612)
        blit(fr, q, W / 2 + tot / 2 - q.width / 2, 612 - (q.height - a.height) / 2)
    else:
        blit(fr, text_img(headline, F(ANTON, 200), WHITE, stroke=6), W / 2, 612)
    # bottom tag (inside the safe window)
    if tag:
        t = text_img(tag, F(ANTON, 104), RED, stroke=5, glow=6)
        blit(fr, t, W / 2, 1400)
    if handle:
        watermark(fr, handle, acc)
    out = Path(out or episode_dir / 'cover.jpg')
    fr.convert('RGB').save(out, quality=93)
    return out
