---
name: reels-edit
description: Edit raw vertical talking-head clips (Reels, TikTok, Shorts) into a reel - transcript of every clip, picking the best take of each line by picture and text, joining them, cutting pauses, punch-ins, animated captions and hook card in HyperFrames, loudness -14 LUFS, and a check of the finished file. Use when the user drops one or more raw recordings and says edit, cut, montage, captions, "make a reel from this", or gives feedback on a draft with timestamps.
---

# Reels edit

You are the user's video editor. They record on a phone, you do the rest, but they approve the plan before anything is rendered.

Scripts are in `scripts/` next to this file. They need `ffmpeg`, Python 3 with `Pillow`, and either `mlx-whisper` (Apple Silicon) or `faster-whisper` (everything else). Animation needs Node 18+ and Chrome for HyperFrames.

## Before you start

1. Read `rules.md` in the project root if it exists. Every rule in it applies to this video. If it does not exist, create it from the template in this repo.
2. Ask which script these recordings belong to (or match it from the transcripts). The script says what the hook, frame 0, scenes and punchline are.

## Workflow

Expect several clips: a phone session is usually a few files, each with one or more takes of the same lines.

1. **Transcript of every clip.** `python3 scripts/transcribe.py clip1.mp4 clip2.mp4 ... --lang <code>`. Each clip gets its own `<clip>.json` and a numbered list of segments (`#0`, `#1`...). Transcribe clips one by one, never a long joined file: on long files Whisper can loop on one word over noise. Use the language of the video, not of this file.
2. **Takes per line.** Put the script next to the transcripts and make a table: each line of the script, every take of it (clip and segment number), and what differs (missing words, different wording, a slip). Lines that are not in the script are worth a look too: sometimes an improvised line is the best one.
3. **Pick takes by picture, not only by text.** `python3 scripts/takes.py sheets clip1.mp4 ...` writes `<clip>-takes.jpg`: one row per take, 4 frames, the segment number and its text. Open the sheets and pick, for each line, the take where the speaker looks at the lens (not at notes), does not blink on the first frame, and the gesture or prop is in frame. Text decides between takes only when the picture is equal. Takes of one line can come from different clips.
4. **Content check.** Flag claims that may be false or risky, once. Do not cut sentences the user recorded on purpose: the decision is theirs. Only cut failed takes, slips and dead air.
5. **Edit plan, then stop.** Show the user, in a few lines:
   - the chosen take for each line (clip and #) and why, plus what you leave out,
   - the hook text on screen (0 to 3 s),
   - effects and where (punch-ins, text cards), at most one strong effect every ~8 s,
   - music or none,
   - length: aim for 15 to 25 s; if longer, say which lines you would cut.
   Ask "go or change?". Render only after they say go.
6. **Join the takes.** Write `takes.json` (fields at the top of `scripts/takes.py`) with the chosen segments in order and run `python3 scripts/takes.py join takes.json`. You get one video and its transcript on the new timeline, no second transcription needed. With a single clip and a single take you can skip this step.
7. **Base cut.** Write `config.json` (fields at the top of `scripts/edit.py`) with the joined video and transcript, `"captions": false` and no `hook`, then `python3 scripts/edit.py config.json`. It cuts pauses, punches in, sets -14 LUFS and writes `<output>.words.json` with word times on the final timeline. A clip start moves back by itself when speech is audible just before it, because Whisper often places a shouted or repeated word too late.
8. **Animation in HyperFrames.** Captions, the hook card and text cards are animated in [HyperFrames](https://www.npmjs.com/package/hyperframes). See "Animation with HyperFrames" below.
   If Node or Chrome is not available, render static captions with `edit.py` instead (`"captions": true`, `hook`) and say so.
9. **Check the file.** `python3 scripts/check.py final.mp4`, then:
   - open the contact sheet and look at it: captions on the mouth or chin, black frames, a blink on the first frame, names spelled right,
   - run `transcribe.py` on the finished file and compare it with the script: every chosen line is there, no word clipped at a cut,
   - loudness between -15 and -13 LUFS, true peak -1.5 dBTP or lower.
10. **Hand over** the file, the sheet, and what you could not fix.

## Animation with HyperFrames

The base cut is the video layer. Everything that moves on top of it is HTML with a GSAP timeline, rendered to MP4.

1. New project next to the video: `npx --yes hyperframes init <slug> --example blank --resolution portrait --non-interactive`. It also installs the HyperFrames skills; read `/hyperframes` before changing the composition by hand.
2. Write `hf.json` (fields at the top of `scripts/hf_captions.py`) and run `python3 scripts/hf_captions.py hf.json`. It copies the base cut into the project and writes `index.html` with:
   - captions: groups of max 3 words, the active word on a pill that slides along the group, in 2 frames before the word,
   - the hook card: in with a short spring from 0 s, out at `hook.end`,
   - `fix`: spelling fixes for words Whisper gets wrong, above all brand and product names. Check every name on the contact sheet.
3. Text cards, highlights or other effects from the plan: add them to `index.html` as extra elements on the same timeline, or take a ready block from the HyperFrames registry. At most one strong effect every ~8 s.
4. `npx hyperframes check` inside the project must pass (0 errors). Warnings about the safe zone or short last lines are worth a look, not a blocker. Keep only one HTML file with `data-composition-id` in the folder.
5. `npx hyperframes snapshot --at <s>` at the hook, at each card and at the last second. Look at the frames before rendering.
6. `npx hyperframes render --output ../final.mp4`, then go to the check step with that file.

## Style defaults

- Cut any pause longer than 0.3 s, keep 0.06 s before and 0.2 s after a word. Never cut inside a phrase: a short breath after a comma stays.
- Punch in (about 1.14x) on every other clip, so a jump cut looks intentional.
- Captions: max 3 words or 16 characters per line, break on punctuation, active word on a coloured pill, never on the mouth or chin. The pill skips words shorter than 0.15 s, otherwise it flickers.
- Hook text on screen in the first 2 to 3 s. It should make sense with the sound off.
- The punchline stays on screen to the end. No "follow for more" outro.
- Do not speed up the voice.

## Learning from feedback

When the user gives a note that should apply to future videos ("captions lower", "don't cut my pauses after jokes"), add it to `rules.md` with the date, in one line. Tell them you saved it. Next video starts with all rules applied.
