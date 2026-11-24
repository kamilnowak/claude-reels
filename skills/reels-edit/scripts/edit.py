"""First cut of a talking-head reel: cut pauses and dropped takes, punch-in on every other clip,
word-by-word captions, optional hook text, loudness -14 LUFS.

Usage:
  python3 edit.py config.json

config.json (only "video", "transcript" and "output" are required):
{
  "video": "raw.mp4",
  "transcript": "raw.json",          # from transcribe.py
  "output": "cut.mp4",
  "drop_segments": [0, 3],           # transcript segments to remove (bad takes, slips)
  "gap": 0.30,                       # a pause longer than this becomes a cut
  "pad_in": 0.06, "pad_out": 0.20,   # breathing room before and after words
  "zoom": 1.14,                      # punch-in on every other clip, 1.0 = off
  "zoom_center": [540, 820],         # roughly where the face is, in 1080x1920
  "captions": true,
  "caption_y": 1300,                 # keep captions off the mouth and chin
  "font": null,                      # path to a bold .ttf; auto-detected if null
  "font_size": 78,
  "max_words": 3, "max_chars": 16,
  "highlight": "#ffd400",
  "hook": {"text": "Your hook here?", "end": 2.8}
}
Writes <output> and <output>.words.json (word times on the new timeline, for checking).
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
FONT_CANDIDATES = [
    '/System/Library/Fonts/Supplemental/Arial Black.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    'C:/Windows/Fonts/ariblk.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]
PUNCT = ',.?!:;…'
SHORT_WORD = 0.15  # highlight skips words shorter than this, otherwise it flickers


def load_cfg():
    cfg = json.load(open(sys.argv[1]))
    d = dict(drop_segments=[], gap=0.30, pad_in=0.06, pad_out=0.20, zoom=1.14, zoom_center=[540, 820],
             captions=True, caption_y=1300, font=None, font_size=78, max_words=3, max_chars=16,
             highlight='#ffd400', hook=None)
    d.update(cfg)
    if not d['font']:
        d['font'] = next((f for f in FONT_CANDIDATES if os.path.exists(f)), None)
        if not d['font']:
            sys.exit('No bold font found, set "font" in config.json')
    return d


def duration(path):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout
    return float(out)


def collect_words(tr, drop):
    words = []
    for i, s in enumerate(tr['segments']):
        if i in drop:
            continue
        for w in s.get('words', []):
            t = w['word'].strip()
            if t:
                words.append({'w': t, 's': w['start'], 'e': w['end']})
    return words


def loudness_track(video):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', video, '-ac', '1', '-ar', '16000', '-f', 's16le', '-'],
                         capture_output=True).stdout
    import array
    a = array.array('h', raw)
    n = 320
    out = []
    for i in range(0, len(a) - n, n):
        chunk = a[i:i + n]
        out.append((sum(x * x for x in chunk) / n) ** 0.5)
    return out


def snap_starts(clips, rms, total):
    """Whisper often starts a loud or repeated word late. Move a clip start back while speech is still audible."""
    if not rms:
        return
    loud = sorted(rms)[int(len(rms) * 0.9)]
    for c in clips:
        i = int(c['a'] / 0.02)
        j = i
        while j > 5 and i - j < 30 and max(rms[j - 6:j]) > loud * 0.25:
            j -= 1
        if j < i:
            c['a'] = max(0.0, j * 0.02 - 0.04)


def clips_from_words(words, cfg, total, rms=None):
    clips = []
    for w in words:
        if clips and w['s'] - clips[-1]['words'][-1]['e'] <= cfg['gap']:
            clips[-1]['words'].append(w)
        else:
            clips.append({'words': [w]})
    for c in clips:
        c['a'] = max(0.0, c['words'][0]['s'] - cfg['pad_in'])
        c['b'] = min(total, c['words'][-1]['e'] + cfg['pad_out'])
    snap_starts(clips, rms, total)
    merged = []
    for c in clips:
        if merged and c['a'] <= merged[-1]['b']:
            merged[-1]['b'] = c['b']
            merged[-1]['words'] += c['words']
        else:
            merged.append(c)
    t = 0.0
    for c in merged:
        c['offset'] = t
        for w in c['words']:
            w['ns'], w['ne'] = t + w['s'] - c['a'], t + w['e'] - c['a']
        t += c['b'] - c['a']
    return merged, t


def caption_groups(words, cfg):
    groups, cur = [], []
    for w in words:
        text = ' '.join(x['w'] for x in cur + [w])
        if cur and (len(cur) >= cfg['max_words'] or len(text) > cfg['max_chars']):
            groups.append(cur)
            cur = []
        cur.append(w)
        if w['w'][-1] in PUNCT:
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def draw_caption(group, active, cfg, font):
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    words = [w['w'].upper() for w in group]
    space = d.textlength(' ', font=font)
    widths = [d.textlength(w, font=font) for w in words]
    x = (W - sum(widths) - space * (len(words) - 1)) / 2
    y = cfg['caption_y']
    for i, (w, wd) in enumerate(zip(words, widths)):
        if i == active:
            l, t, r, b = d.textbbox((x, y), w, font=font)
            d.rounded_rectangle((l - 16, t - 12, r + 16, b + 12), radius=18, fill=cfg['highlight'])
            d.text((x, y), w, font=font, fill='black')
        else:
            d.text((x, y), w, font=font, fill='white', stroke_width=6, stroke_fill='black')
        x += wd + space
    return img


def draw_hook(text, cfg):
    font = ImageFont.truetype(cfg['font'], 84)
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    lines, line = [], ''
    for word in text.split():
        test = (line + ' ' + word).strip()
        if d.textlength(test, font=font) > W - 220 and line:
            lines.append(line)
            line = word
        else:
            line = test
    lines.append(line)
    lh = 100
    box_h = lh * len(lines) + 60
    top = 250
    d.rounded_rectangle((70, top, W - 70, top + box_h), radius=28, fill='white')
    for i, ln in enumerate(lines):
        tw = d.textlength(ln, font=font)
        d.text(((W - tw) / 2, top + 30 + i * lh), ln, font=font, fill='black')
    return img


def caption_track(clips, total, cfg, tmp):
    """PNG timeline for the ffmpeg concat demuxer: one transparent overlay stream."""
    font = ImageFont.truetype(cfg['font'], cfg['font_size'])
    words = [w for c in clips for w in c['words']]
    blank = os.path.join(tmp, 'blank.png')
    Image.new('RGBA', (W, H), (0, 0, 0, 0)).save(blank)
    events = []
    for g_i, g in enumerate(caption_groups(words, cfg)):
        active = 0
        for i, w in enumerate(g):
            if w['ne'] - w['ns'] >= SHORT_WORD or i == 0:
                active = i
            start = w['ns'] - 2 / FPS
            end = g[i + 1]['ns'] - 2 / FPS if i + 1 < len(g) else w['ne'] + 0.25
            path = os.path.join(tmp, f'c{g_i:03d}_{i}.png')
            draw_caption(g, active, cfg, font).save(path)
            events.append((max(0.0, start), end, path))
    lines, t = [], 0.0
    for s, e, path in events:
        s = max(s, t)
        if s > t:
            lines += [f"file '{blank}'", f'duration {s - t:.3f}']
        if e > s:
            lines += [f"file '{path}'", f'duration {e - s:.3f}']
            t = e
    if t < total:
        lines += [f"file '{blank}'", f'duration {total - t:.3f}']
    lines.append(f"file '{blank}'")
    lst = os.path.join(tmp, 'captions.txt')
    open(lst, 'w').write('\n'.join(lines) + '\n')
    return lst


def main():
    cfg = load_cfg()
    tr = json.load(open(cfg['transcript']))
    total = duration(cfg['video'])
    clips, new_total = clips_from_words(collect_words(tr, set(cfg['drop_segments'])), cfg, total, loudness_track(cfg['video']))
    if not clips:
        sys.exit('No words left after dropping segments')

    tmp = tempfile.mkdtemp(prefix='reels-')
    inputs = ['-i', cfg['video']]
    fc = []
    zx, zy = cfg['zoom_center']
    for i, c in enumerate(clips):
        v = (f"[0:v]trim={c['a']:.3f}:{c['b']:.3f},setpts=PTS-STARTPTS,"
             f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}")
        if cfg['zoom'] > 1 and i % 2 == 1:
            z = cfg['zoom']
            cx = min(max(zx * z - W / 2, 0), W * z - W)
            cy = min(max(zy * z - H / 2, 0), H * z - H)
            v += f",scale={round(W * z)}:{round(H * z)},crop={W}:{H}:{cx:.0f}:{cy:.0f}"
        fc.append(v + ',setsar=1' + f'[v{i}]')
        fc.append(f"[0:a]atrim={c['a']:.3f}:{c['b']:.3f},asetpts=PTS-STARTPTS[a{i}]")
    fc.append(''.join(f'[v{i}][a{i}]' for i in range(len(clips))) + f'concat=n={len(clips)}:v=1:a=1[vc][ac]')
    last = 'vc'
    n_in = 1
    if cfg['captions']:
        inputs += ['-f', 'concat', '-safe', '0', '-i', caption_track(clips, new_total, cfg, tmp)]
        fc.append(f'[{n_in}:v]fps={FPS},format=rgba[cap]')
        fc.append(f'[{last}][cap]overlay=0:0:eof_action=pass[vcap]')
        last, n_in = 'vcap', n_in + 1
    if cfg['hook']:
        hook_png = os.path.join(tmp, 'hook.png')
        draw_hook(cfg['hook']['text'], cfg).save(hook_png)
        inputs += ['-loop', '1', '-t', f'{new_total:.3f}', '-i', hook_png]
        fc.append(f"[{last}][{n_in}:v]overlay=0:0:enable='lt(t,{cfg['hook']['end']})'[vhook]")
        last = 'vhook'
    fc.append('[ac]loudnorm=I=-14:TP=-1.5:LRA=11[aout]')

    cmd = ['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', ';'.join(fc),
           '-map', f'[{last}]', '-map', '[aout]', '-t', f'{new_total:.3f}',
           '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p',
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-movflags', '+faststart', cfg['output']]
    subprocess.run(cmd, check=True)

    words_out = [{'w': w['w'], 's': round(w['ns'], 3), 'e': round(w['ne'], 3)} for c in clips for w in c['words']]
    json.dump(words_out, open(cfg['output'] + '.words.json', 'w'), ensure_ascii=False, indent=1)
    print(f"{len(clips)} clips, {total:.1f}s -> {new_total:.1f}s -> {cfg['output']}")
    for c in clips:
        print(f"  {c['a']:6.2f}-{c['b']:6.2f}  at {c['offset']:5.2f}  {' '.join(w['w'] for w in c['words'])}")


if __name__ == '__main__':
    main()
