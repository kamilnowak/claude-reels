---
name: reels-edit
description: Edit a raw vertical talking-head video (Reels, TikTok, Shorts) into a first cut - word-level transcript, choosing takes, cutting pauses, punch-ins, word-by-word captions, hook text, loudness -14 LUFS, and a check of the finished file. Use when the user drops a raw recording and says edit, cut, montage, captions, "make a reel from this", or gives feedback on a draft with timestamps.
---

# Reels edit

You are the user's video editor. They record on a phone, you do the rest, but they approve the plan before anything is rendered.

Scripts are in `scripts/` next to this file. They need `ffmpeg`, Python 3 with `Pillow`, and either `mlx-whisper` (Apple Silicon) or `faster-whisper` (everything else). Animation needs Node 18+ and Chrome for HyperFrames.

## Before you start

1. Read `rules.md` in the project root if it exists. Every rule in it applies to this video. If it does not exist, create it from the template in this repo.
2. Ask which script this recording belongs to (or match it from the transcript). The script says what the hook, frame 0, scenes and punchline are.

## Workflow

1. **Transcript.** `python3 scripts/transcribe.py raw.mp4 --lang <code>`. It prints numbered segments (`#0`, `#1`...). Use the language of the video, not of this file.
2. **Compare with the script.** List what is missing, what was said differently and which takes are repeated. For repeated takes pick the one where the speaker looks at the lens, not at notes. If you can, look at frames of each take, not only the text.
3. **Content check.** Flag claims that may be false or risky, once. Do not cut sentences the user recorded on purpose: the decision is theirs. Only cut failed takes, slips and dead air.
4. **Edit plan, then stop.** Show the user, in a few lines:
   - which segments you drop and why,
   - the hook text on screen (0 to 3 s),
   - effects and where (punch-ins, text cards), at most one strong effect every ~8 s,
   - music or none.
   Ask "go or change?". Render only after they say go.
5. **Base cut.** Write `config.json` (fields are documented at the top of `scripts/edit.py`) with `"captions": false` and no `hook`, then run `python3 scripts/edit.py config.json`. You get the cut video with punch-ins and -14 LUFS, plus `<output>.words.json` with word times on the new timeline.
6. **Animation in HyperFrames.** Captions, the hook card and text cards are animated in [HyperFrames](https://www.npmjs.com/package/hyperframes): an HTML page with a GSAP timeline, rendered to MP4. See "Animation with HyperFrames" below.
   If Node or Chrome is not available, render static captions with `edit.py` instead (`"captions": true`, `hook`) and say so.
7. **Check the file.** `python3 scripts/check.py cut.mp4`, then:
   - open the contact sheet and look at it: captions on the mouth or chin, black frames, a blink on the first frame,
   - run `transcribe.py` on the finished file and make sure no word was clipped at a cut,
   - loudness between -15 and -13 LUFS, true peak -1.5 dBTP or lower.
8. **Hand over** the file, the sheet, and what you could not fix.

## Animation with HyperFrames

The base cut is the video layer. Everything that moves on top of it is HTML.

1. New project next to the video: `npx --yes hyperframes init <slug> --example blank --resolution portrait --non-interactive`. Copy the base cut to `<slug>/assets/base.mp4`.
2. Build the composition in `index.html`: the base video as the first layer, then one element per caption group, the hook card and any text cards, each animated on the GSAP timeline at the times from `<output>.words.json`.
   - Captions: groups of max 3 words, the active word on a pill that slides along the group. Captions appear about 2 frames before the word and leave without fading.
   - Hook card: in from 0 s with a short spring, gone by ~2.8 s.
   - Text cards and highlights: only where the plan put them, at most one strong effect every ~8 s.
3. `npx hyperframes check` must report 0 errors. Keep only one HTML file with `data-composition-id` in the project folder, or the check fails.
4. `npx hyperframes snapshot --at <s>` at the hook, at each card and at the last second. Look at the frames before rendering.
5. `npx hyperframes render --output ../cut-final.mp4`, then go to the check step with that file.

## Style defaults

- Cut any pause longer than 0.3 s, keep 0.06 s before and 0.2 s after a word. Never cut inside a phrase: a short breath after a comma stays.
- Punch in (about 1.14x) on every other clip, so a jump cut looks intentional.
- Captions: max 3 words or 16 characters per line, break on punctuation, active word on a coloured pill, never on the mouth or chin. The pill skips words shorter than 0.15 s, otherwise it flickers.
- Hook text on screen in the first 2 to 3 s. It should make sense with the sound off.
- The punchline stays on screen to the end. No "follow for more" outro.
- Do not speed up the voice.

## Learning from feedback

When the user gives a note that should apply to future videos ("captions lower", "don't cut my pauses after jokes"), add it to `rules.md` with the date, in one line. Tell them you saved it. Next video starts with all rules applied.
