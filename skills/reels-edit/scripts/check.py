"""Check a finished reel before publishing.

Usage:
  python3 check.py final.mp4 [--every 0.7]

Prints length, integrated loudness and true peak, and saves <final>-sheet.jpg:
a contact sheet with one frame every 0.7 s. Look at it before you publish
(captions on the mouth, black frames, a blink on the first frame).
For the words, run transcribe.py on the final file and compare with the script.
"""
import argparse
import re
import subprocess

p = argparse.ArgumentParser()
p.add_argument('video')
p.add_argument('--every', type=float, default=0.7)
a = p.parse_args()

dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', a.video],
                           capture_output=True, text=True).stdout)
log = subprocess.run(['ffmpeg', '-hide_banner', '-i', a.video, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                     capture_output=True, text=True).stderr
summary = log[log.rfind('Summary:'):]
lufs = float(re.search(r'I:\s+(-?[\d.]+) LUFS', summary).group(1))
peak = float(re.search(r'Peak:\s+(-?[\d.]+) dBFS', summary).group(1))

n = int(dur / a.every) + 1
cols = 6
rows = (n + cols - 1) // cols
sheet = a.video.rsplit('.', 1)[0] + '-sheet.jpg'
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', a.video, '-vf',
                f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{a.every})',scale=270:-1,tile={cols}x{rows}",
                '-fps_mode', 'vfr', '-frames:v', '1', sheet], check=True)

print(f'length      {dur:.1f} s')
print(f'loudness    {lufs:.1f} LUFS  (target -14, ok between -15 and -13)')
print(f'true peak   {peak:.1f} dBTP  (should be -1.5 or lower)')
print(f'sheet       {sheet}  ({n} frames, every {a.every} s)')
if not -15 <= lufs <= -13 or peak > -1.5:
    print('!! loudness out of range')
