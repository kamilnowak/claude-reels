"""Write a HyperFrames composition (index.html) with animated captions and a hook card over the base cut.

Usage:
  python3 hf_captions.py hf.json

hf.json:
{
  "project": "my-reel",                  # folder made by `npx hyperframes init`
  "video": "base.mp4",                   # base cut from edit.py with "captions": false
  "words": "base.mp4.words.json",        # written by edit.py next to the video
  "hook": {"text": "Your hook?", "end": 2.8},
  "fix": {"Acme Co": "AcmeCo"},           # transcript mistakes to fix in captions (phrase or word)
  "caption_y": 1300, "max_words": 3, "max_chars": 16,
  "highlight": "#ffd400", "font": "Montserrat"
}
Copies the video to <project>/assets/base.mp4. Then: npx hyperframes check / snapshot / render inside the project.
"""
import html
import json
import os
import shutil
import subprocess
import sys

PUNCT = ',.?!:;…'
SHORT_WORD = 0.15


def load(path):
    c = json.load(open(path))
    base = os.path.dirname(os.path.abspath(path))
    for k in ('project', 'video', 'words'):
        c[k] = os.path.join(base, c[k])
    c.setdefault('caption_y', 1300)
    c.setdefault('max_words', 3)
    c.setdefault('max_chars', 16)
    c.setdefault('highlight', '#ffd400')
    c.setdefault('font', 'Montserrat')
    return c


def apply_fix(words, fix):
    words = [dict(w) for w in words]
    for wrong, right in fix.items():
        wr = wrong.lower().split()
        i = 0
        while i <= len(words) - len(wr):
            chunk = [w['w'].strip(PUNCT).lower() for w in words[i:i + len(wr)]]
            if chunk == wr:
                last = words[i + len(wr) - 1]
                tail = last['w'][len(last['w'].rstrip(PUNCT)):]
                words[i:i + len(wr)] = [{'w': right + tail, 's': words[i]['s'], 'e': last['e']}]
            i += 1
    return words


def merge_symbols(words):
    out = []
    for w in words:
        if out and w['w'].strip(PUNCT + '%') == '':
            out[-1]['w'] += w['w']
            out[-1]['e'] = w['e']
        else:
            out.append(w)
    return out


def groups(words, c):
    out, cur = [], []
    for w in words:
        cur.append(w)
        chars = sum(len(x['w']) + 1 for x in cur)
        if len(cur) >= c['max_words'] or chars >= c['max_chars'] or w['w'][-1] in PUNCT:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def main():
    c = load(sys.argv[1])
    os.makedirs(os.path.join(c['project'], 'assets'), exist_ok=True)
    shutil.copy(c['video'], os.path.join(c['project'], 'assets', 'base.mp4'))
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', c['video']],
                               capture_output=True, text=True).stdout)
    words = apply_fix(merge_symbols(json.load(open(c['words']))), c.get('fix', {}))
    hook_end = c['hook']['end'] if c.get('hook') else 0

    els, js = [], []
    gs = groups(words, c)
    for gi, g in enumerate(gs):
        start = max(0, g[0]['s'] - 0.07)
        end = dur if gi == len(gs) - 1 else gs[gi + 1][0]['s'] - 0.07
        spans = ''.join(f'<span class="w" id="g{gi}w{wi}">{html.escape(w["w"].upper())}</span>' for wi, w in enumerate(g))
        els.append(f'<div class="cap" id="g{gi}"><div class="pill" id="p{gi}"></div>{spans}</div>')
        js.append(f'tl.set("#g{gi}", {{opacity: 1}}, {start:.3f}); tl.set("#g{gi}", {{opacity: 0}}, {end:.3f});')
        first = True
        for wi, w in enumerate(g):
            if w['e'] - w['s'] < SHORT_WORD and not first:
                continue
            js.append(f'pill({gi}, {wi}, {w["s"]:.3f}, {str(first).lower()});')
            first = False
    hook = ''
    if c.get('hook'):
        t = html.escape(c['hook']['text'])
        hook = f'<div id="hook">{t}</div>'
        js.append(f'tl.fromTo("#hook", {{scale: 0.6, rotation: -4, opacity: 0}}, {{scale: 1, rotation: 0, opacity: 1, duration: 0.45, ease: "back.out(2.2)"}}, 0.05);')
        js.append(f'tl.to("#hook", {{opacity: 0, duration: 0.15}}, {hook_end - 0.15:.3f});')

    page = f'''<!doctype html>
<html lang="en" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<link href="https://fonts.googleapis.com/css2?family={c['font'].replace(' ', '+')}:wght@900&display=block" rel="stylesheet" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #000; }}
#root {{ position: relative; width: 1080px; height: 1920px; font-family: '{c['font']}', sans-serif; }}
#base {{ position: absolute; inset: 0; width: 1080px; height: 1920px; object-fit: cover; }}
.cap {{ position: absolute; left: 0; right: 0; top: {c['caption_y']}px; display: flex; justify-content: center; gap: 18px;
        opacity: 0; font-weight: 900; font-size: 72px; paint-order: stroke fill; }}
.w {{ position: relative; z-index: 1; padding: 0 10px; color: var(--c, #fff); -webkit-text-stroke: var(--s, 3px) #000; }}
.pill {{ position: absolute; left: 0; top: -4px; width: 100px; height: 92px; border-radius: 16px; transform-origin: 0 50%; opacity: 0; background: {c['highlight']}; z-index: 0; }}
#hook {{ position: absolute; left: 50%; top: 330px; transform: translateX(-50%); max-width: 900px; background: #fff; color: #111;
         font-weight: 900; font-size: 80px; line-height: 1.05; text-align: center; padding: 26px 40px; border-radius: 28px;
         box-shadow: 0 12px 40px rgba(0,0,0,.35); opacity: 0; }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{dur:.3f}" data-width="1080" data-height="1920">
<video id="base" src="assets/base.mp4" data-has-audio="true" class="clip" data-start="0" data-duration="{dur:.3f}" data-track-index="0"></video>
{chr(10).join(els)}
{hook}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
function pill(g, w, t, first) {{
  const el = document.getElementById(`g${{g}}w${{w}}`), p = document.getElementById(`p${{g}}`);
  tl.set(`#g${{g}} .w`, {{ '--c': '#fff', '--s': '3px' }}, t);
  tl.set(el, {{ '--c': '#000', '--s': '0px' }}, t);
  if (first) tl.set(p, {{ x: () => el.offsetLeft, scaleX: () => el.offsetWidth / 100, scaleY: 1.12, opacity: 1 }}, t).to(p, {{ scaleY: 1, duration: 0.12 }}, t);
  else tl.to(p, {{ x: () => el.offsetLeft, scaleX: () => el.offsetWidth / 100, duration: 0.1, ease: 'power2.out' }}, t);
}}
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
'''
    open(os.path.join(c['project'], 'index.html'), 'w').write(page)
    print('wrote', os.path.join(c['project'], 'index.html'), f'({dur:.1f} s)')


if __name__ == '__main__':
    main()
