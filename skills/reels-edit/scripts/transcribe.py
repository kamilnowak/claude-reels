"""Word-level transcript of one or more videos, run locally.

Usage:
  python3 transcribe.py clip1.mp4 [clip2.mp4 ...] [--lang pl]
  python3 transcribe.py video.mp4 --out transcript.json

Writes <video>.json next to each video and prints numbered segments so you can refer to them ("drop #3").
Uses mlx-whisper on Apple Silicon, faster-whisper everywhere else.
Empty and looping segments (Whisper repeating one word over noise) are removed.
"""
import argparse
import json
import os
import platform

p = argparse.ArgumentParser()
p.add_argument('videos', nargs='+')
p.add_argument('--lang', default=None, help='language code, e.g. pl, en; default: auto-detect')
p.add_argument('--out', default=None, help='output path, only with one video')
a = p.parse_args()
MLX = platform.system() == 'Darwin' and platform.machine() == 'arm64'
if not MLX:
    from faster_whisper import WhisperModel
    model = WhisperModel('large-v3-turbo', compute_type='auto')


def run(video):
    if MLX:
        import mlx_whisper
        r = mlx_whisper.transcribe(video, path_or_hf_repo='mlx-community/whisper-large-v3-turbo', language=a.lang,
                                   word_timestamps=True)
        return [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip(),
                 'words': [{'word': w['word'], 'start': w['start'], 'end': w['end']} for w in s.get('words', [])]}
                for s in r['segments']]
    segs, _ = model.transcribe(video, language=a.lang, word_timestamps=True)
    return [{'start': s.start, 'end': s.end, 'text': s.text.strip(),
             'words': [{'word': w.word, 'start': w.start, 'end': w.end} for w in (s.words or [])]}
            for s in segs]


def clean(segments):
    out = []
    for s in segments:
        if not s['text'] or s['end'] - s['start'] < 0.15:
            continue
        if len(out) >= 2 and s['text'] == out[-1]['text'] == out[-2]['text'] and len(s['text'].split()) <= 2:
            continue
        out.append(s)
    return out


for video in a.videos:
    out = a.out if a.out and len(a.videos) == 1 else os.path.splitext(video)[0] + '.json'
    segments = clean(run(video))
    json.dump({'segments': segments}, open(out, 'w'), ensure_ascii=False, indent=1)
    print(f'== {os.path.basename(video)}')
    for i, s in enumerate(segments):
        print(f"#{i} [{s['start']:5.1f}-{s['end']:5.1f}] {s['text']}")
    print('->', out)
