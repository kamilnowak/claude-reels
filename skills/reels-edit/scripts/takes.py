"""Choose the best takes from several clips and join them into one video with a ready transcript.

Usage:
  python3 takes.py sheets clip1.mp4 clip2.mp4 ...   # frame strip of every take, to judge eyes and framing
  python3 takes.py join takes.json                  # cut the chosen takes and join them

sheets: needs <clip>.json from transcribe.py. Writes <clip>-takes.jpg: one row per segment, 4 frames from it,
labelled "#n 12.3s", so you can see where the speaker looks at the lens and where at notes.

takes.json:
{
  "output": "joined.mp4",
  "parts": [
    {"clip": "VID_1.mp4", "segments": [0, 1]},     # whole segments from a clip's transcript
    {"clip": "VID_3.mp4", "segments": [4]},
    {"clip": "VID_6.mp4", "from": 12.4, "to": 15.0} # or an exact range in seconds
  ],
  "pad_in": 0.08, "pad_out": 0.30
}
Writes the joined video (1080x1920, 30 fps) and <output>.json in the transcribe.py format, with word times
moved to the joined timeline, so edit.py can run on it without a second transcription.
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont


def font(size):
    for f in ['/System/Library/Fonts/Supplemental/Arial Bold.ttf', 'C:/Windows/Fonts/arialbd.ttf',
              '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf']:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def frame(video, t, w=260):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.2f}', '-i', video, '-frames:v', '1',
                          '-vf', f'scale={w}:-2', '-f', 'image2pipe', '-vcodec', 'png', '-'], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(raw)).convert('RGB')


def sheets(clips):
    for clip in clips:
        segs = json.load(open(os.path.splitext(clip)[0] + '.json'))['segments']
        rows = []
        for i, s in enumerate(segs):
            ts = [s['start'] + (s['end'] - s['start']) * k / 3 for k in range(4)]
            ims = [frame(clip, t) for t in ts]
            row = Image.new('RGB', (260 * 4 + 420, ims[0].height), 'white')
            for k, im in enumerate(ims):
                row.paste(im, (260 * k, 0))
            d = ImageDraw.Draw(row)
            d.text((260 * 4 + 12, 10), f"#{i} {s['start']:.1f}s", fill='black', font=font(26))
            words, line, y = s['text'].split(), '', 50
            for w in words:
                if len(line) + len(w) > 26:
                    d.text((260 * 4 + 12, y), line, fill='black', font=font(22)); y += 28; line = ''
                line += w + ' '
            d.text((260 * 4 + 12, y), line, fill='black', font=font(22))
            rows.append(row)
        sheet = Image.new('RGB', (rows[0].width, sum(r.height for r in rows)), 'white')
        y = 0
        for r in rows:
            sheet.paste(r, (0, y)); y += r.height
        out = os.path.splitext(clip)[0] + '-takes.jpg'
        sheet.save(out, quality=85)
        print(out, f'({len(rows)} takes)')


def join(cfg_path):
    c = json.load(open(cfg_path))
    base = os.path.dirname(os.path.abspath(cfg_path))
    pad_in, pad_out = c.get('pad_in', 0.08), c.get('pad_out', 0.30)
    tmp = tempfile.mkdtemp(prefix='takes-')
    files, segments, t0 = [], [], 0.0
    for n, p in enumerate(c['parts']):
        clip = os.path.join(base, p['clip'])
        segs = json.load(open(os.path.splitext(clip)[0] + '.json'))['segments']
        if 'segments' in p:
            chosen = [segs[i] for i in p['segments']]
            start = max(0.0, chosen[0]['start'] - pad_in)
            end = chosen[-1]['end'] + pad_out
        else:
            start, end = p['from'], p['to']
            chosen = [s for s in segs if s['start'] >= start - 0.05 and s['end'] <= end + 0.05]
        out = os.path.join(tmp, f'{n:03d}.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{start:.3f}', '-to', f'{end:.3f}', '-i', clip,
                        '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,format=yuv420p',
                        '-af', 'aresample=48000', '-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                        '-c:a', 'aac', '-b:a', '192k', out], check=True)
        dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', out],
                                   capture_output=True, text=True).stdout)
        for s in chosen:
            shift = t0 - start
            segments.append({'start': s['start'] + shift, 'end': s['end'] + shift, 'text': s['text'],
                             'words': [{'word': w['word'], 'start': w['start'] + shift, 'end': w['end'] + shift}
                                       for w in s.get('words', [])]})
        files.append(out)
        print(f"{p['clip']:28s} {start:6.2f}-{end:6.2f}  at {t0:6.2f}  {' '.join(s['text'] for s in chosen)[:70]}")
        t0 += dur
    lst = os.path.join(tmp, 'list.txt')
    open(lst, 'w').write(''.join(f"file '{f}'\n" for f in files))
    output = os.path.join(base, c['output'])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', output], check=True)
    json.dump({'segments': segments}, open(os.path.splitext(output)[0] + '.json', 'w'), ensure_ascii=False, indent=1)
    print(f'-> {output} ({t0:.1f} s) and {os.path.splitext(output)[0]}.json')


if __name__ == '__main__':
    if sys.argv[1] == 'sheets':
        sheets(sys.argv[2:])
    elif sys.argv[1] == 'join':
        join(sys.argv[2])
    else:
        sys.exit(__doc__)
