"""Turn a spec + measured voice durations into an absolute timeline.
The voice drives the clock: every line is placed after the previous one (plus a gap); visual events are
written in the spec relative to lines ("B8+0.8", "B8.end", "@start+0.6") and resolved here."""
import re

DEFAULT_GAP = {'cold_open': 0.15, 'context': 0.2, 'radar': 0.9, 'cards': 0.25, 'clue': 0.3, 'reveal': 0.2, 'predict': 0.2}

class Timeline:
    def __init__(self, spec, durs):
        self.spec, self.durs = spec, durs
        self.lines = {}      # id -> dict(t, d, end, cap, role, section)
        self.sections = []   # dicts with t0, t1, type, spec, idx
        self.build()

    # ------------------------------------------------------------ refs
    def ref(self, r, sec=None, default=None):
        """'B8', 'B8.end', 'B8+0.8', '@start+0.6', '@end-1', or a number (seconds from section start)."""
        if r is None: return default
        if isinstance(r, (int, float)): return (sec['t0'] if sec else 0) + float(r)
        m = re.fullmatch(r'\s*(@start|@end|[A-Za-z0-9_]+)(\.end)?\s*([+-]\s*[\d.]+)?\s*', str(r))
        if not m: raise ValueError(f'bad time ref: {r}')
        base, end, off = m.group(1), m.group(2), m.group(3)
        if base == '@start': t = sec['t0']
        elif base == '@end': t = sec['t1']
        else:
            if base not in self.lines: raise KeyError(f'unknown line id in ref: {r}')
            L = self.lines[base]; t = L['end'] if end else L['t']
        return t + (float(off.replace(' ', '')) if off else 0.0)

    # ------------------------------------------------------------ placement
    def _place(self, lines, cursor, stype, sec_idx, gap=None):
        g = DEFAULT_GAP.get(stype, 0.25) if gap is None else gap
        first = True
        for ln in lines:
            cursor += ln.get('gap', 0.0 if first else g)
            d = self.durs[ln['id']]
            self.lines[ln['id']] = dict(t=cursor, d=d, end=cursor + d, cap=ln.get('cap', ln['say']), role=ln.get('role'), section=sec_idx)
            cursor += d; first = False
        return cursor

    def build(self):
        t = 0.0
        for i, s in enumerate(self.spec['sections']):
            ty = s['type']; sec = dict(type=ty, spec=s, idx=i, t0=t)
            if ty == 'rewind':
                t += 0.5
            elif ty == 'cold_open':
                t = max(self._place(s.get('lines', []), t + 0.2, ty, i) + 0.15, sec['t0'] + 4.0)
            elif ty == 'context':
                sec['beats'] = []
                for b in s['beats']:
                    b0 = t; t = self._place(b.get('lines', []), t + 0.1, ty, i) + 0.15
                    sec['beats'].append(dict(spec=b, t0=b0, t1=t))
                t += 0.9  # camera rise / transition into the next section
            elif ty == 'radar':
                t = self._place(s.get('lines', []), t + s.get('lead', 1.4), ty, i, s.get('gap')) + s.get('tail', 0.6)
            elif ty == 'cards':
                sec['cards'] = []
                for c in s['cards']:
                    c0 = t; t = self._place(c.get('lines', []), t + 0.15, ty, i) + c.get('hold', 0.5)
                    sec['cards'].append(dict(spec=c, t0=c0, t1=t))
            elif ty == 'predict':
                t = self._place(s.get('lines', []), t + 0.2, ty, i)
                sec['count'] = [t + 0.2 + 0.6 * k for k in range(3)]; t = sec['count'][-1] + 0.8
            elif ty == 'clue':
                t = self._place(s.get('lines', []), t + 0.3, ty, i) + 0.5
            elif ty == 'reveal':
                q = [l for l in s['lines'] if l.get('role') not in ('answer', 'cta')]
                rest = [l for l in s['lines'] if l.get('role') in ('answer', 'cta')]
                t = self._place(q, t + 0.15, ty, i)
                sec['count'] = [t + 0.2 + 0.6 * k for k in range(3)]; sec['R0'] = sec['count'][-1] + 0.6
                t = self._place(rest, sec['R0'] + 0.3, ty, i, 0.35) + 0.5
            else:
                raise ValueError(f'unknown section type {ty}')
            sec['t1'] = t; self.sections.append(sec)
        self.duration = t
        # resolve radar scenes (sections sharing a scene keep one continuous local clock; predict freezes it)
        self.radar_scenes = {}
        for sec in self.sections:
            if sec['type'] == 'radar':
                key = sec['spec'].get('scene', f"scene{sec['idx']}")
                self.radar_scenes.setdefault(key, []).append(sec); sec['scene'] = key

    def section_at(self, t):
        for s in self.sections:
            if s['t0'] <= t < s['t1']: return s
        return self.sections[-1]

    def captions(self):
        """voice-synced chunks (<= 3 words, break after punctuation) for every line with a caption."""
        out = []
        ids = sorted(self.lines, key=lambda k: self.lines[k]['t'])
        for n, lid in enumerate(ids):
            L = self.lines[lid]
            if not L['cap'] or L['role'] in ('punch', 'big', 'answer', 'question'): continue
            words = L['cap'].split(); groups, cur = [], []
            for w in words:
                cur.append(w)
                if len(cur) >= 3 or re.search(r'[.,…:?!]$', w): groups.append(cur); cur = []
            if cur: groups.append(cur)
            tot = sum(len(' '.join(g)) for g in groups); tt = L['t'] + 0.05; d = L['d'] - 0.1
            nxt = self.lines[ids[n + 1]]['t'] if n + 1 < len(ids) else self.duration
            for gi, g in enumerate(groups):
                dd = d * len(' '.join(g)) / tot
                end = tt + dd if gi < len(groups) - 1 else min(nxt - 0.05, tt + dd + 0.4)
                out.append((tt, end, g)); tt += dd
        return out

    def report(self):
        rows = [f"{s['type']:<10} {s['t0']:6.2f} → {s['t1']:6.2f}" for s in self.sections]
        rows.append(f'TOTAL {self.duration:.2f}s')
        return '\n'.join(rows)
