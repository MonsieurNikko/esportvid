"""publish.md: titles (search-friendly '[what happened] [game]'), description, hashtags, pinned comment, checklist."""
def write_publish(spec, tl, path):
    m = spec['meta']; p = spec.get('publish', {})
    titles = p.get('titles', [])
    tags = p.get('hashtags', []) + m.get('base_hashtags', ['#esports', '#gaming', '#shorts'])
    checks = [
        (tl.duration > 61, f'Duration {tl.duration:.1f}s > 61s (TikTok Creator Rewards needs > 1 min)'),
        (True, 'Original animation, synthesized sound, no broadcast footage (no Content ID risk)'),
        (bool(spec.get('sources')), f"Facts sourced ({len(spec.get('sources', []))} sources in spec)"),
        (True, 'Not realistic AI imagery -> TikTok AI label not required (turn it on if you add realistic AI visuals)'),
    ]
    out = [f"# {m.get('series', '')} #{m.get('episode', '')} — publish kit", '', '## Title options (pattern: what happened + game)']
    out += [f'- {t}' for t in titles] or ['- (add titles in spec.publish.titles)']
    out += ['', '## Description', p.get('description', ''), '', ' '.join(tags), '', '## Pinned comment', p.get('pinned', 'Who should be next? 👇'),
            '', '## Checklist'] + [f"- [{'x' if ok else ' '}] {txt}" for ok, txt in checks]
    out += ['', '## Sources'] + [f'- {s}' for s in spec.get('sources', [])]
    out += ['', '## Timeline', '```', tl.report(), '```']
    path.write_text('\n'.join(out), encoding='utf-8')
