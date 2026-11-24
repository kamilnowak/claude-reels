"""Word-level transcript of a video, run locally.

Usage:
  python3 transcribe.py video.mp4 [--lang pl] [--out transcript.json]

Uses mlx-whisper on Apple Silicon, faster-whisper everywhere else.
Prints numbered segments so you can refer to them ("drop #3").
"""
import argparse
import json
import os
import platform

p = argparse.ArgumentParser()
p.add_argument('video')
p.add_argument('--lang', default=None, help='language code, e.g. pl, en; default: auto-detect')
p.add_argument('--out', default=None)
a = p.parse_args()
out = a.out or os.path.splitext(a.video)[0] + '.json'

if platform.system() == 'Darwin' and platform.machine() == 'arm64':
    import mlx_whisper
    r = mlx_whisper.transcribe(a.video, path_or_hf_repo='mlx-community/whisper-large-v3-turbo',
                               language=a.lang, word_timestamps=True)
    segments = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip(),
                 'words': [{'word': w['word'], 'start': w['start'], 'end': w['end']} for w in s.get('words', [])]}
                for s in r['segments']]
else:
    from faster_whisper import WhisperModel
    model = WhisperModel('large-v3-turbo', compute_type='auto')
    segs, _ = model.transcribe(a.video, language=a.lang, word_timestamps=True)
    segments = [{'start': s.start, 'end': s.end, 'text': s.text.strip(),
                 'words': [{'word': w.word, 'start': w.start, 'end': w.end} for w in (s.words or [])]}
                for s in segs]

json.dump({'segments': segments}, open(out, 'w'), ensure_ascii=False, indent=1)
for i, s in enumerate(segments):
    print(f"#{i} [{s['start']:5.1f}-{s['end']:5.1f}] {s['text']}")
print('->', out)
