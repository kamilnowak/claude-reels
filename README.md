# claude-reels

A short-form video workflow for one person and Claude Code: from studying other accounts, through a scored script, to an automatic first cut with captions.

You record on your phone. Claude finds the topic patterns, writes and scores the script, cuts the recording, adds captions and checks the file. You make two decisions: which topic, and "go" on the edit plan.

## What's inside

| File | What it does |
|---|---|
| `starter-prompt.md` | One prompt that runs the whole process. Works in any Claude chat, no setup. Start here. |
| `skills/reels-ideas/` | Claude Code skill: analyse 3 benchmark accounts, build a topic bank, write and score a script card. |
| `skills/reels-edit/` | Claude Code skill and scripts: transcript, take selection, cutting pauses, punch-ins, captions, hook text, -14 LUFS, final check. |
| `rules.md` | The editor's memory. Every note you give becomes a rule for the next video. |

## The six steps

1. **Idea.** 3 accounts you learn from, their outliers (10x the median views), hooks, topics, gaps.
2. **Script.** Hook in max 7 words, frame 0, text for the first 3 s, scenes, punchline. Max ~25 s.
3. **Score.** Stop x Hold x Convert, 0 to 1000. Fix the script below ~500, before you record.
4. **Recording.** You, a phone, a few takes.
5. **Edit.** Claude shows a plan, you say go, it renders and checks the result.
6. **Publishing.** Description, hashtags and a schedule for all platforms at once.

## Quick start

**Just the prompt:** open `starter-prompt.md`, fill in the brackets, paste it into Claude.

**With Claude Code:**

```bash
git clone https://github.com/kamilnowak/claude-reels.git
cp -r claude-reels/skills/* ~/.claude/skills/
cp claude-reels/rules.md /path/to/your/videos/
```

Then, in Claude Code, inside your videos folder: "find me reel ideas" or "edit raw.mp4".

### Requirements for the edit scripts

- `ffmpeg` on your PATH
- Python 3.10+ with `Pillow`
- Transcription: `pip install mlx-whisper` on a Mac with Apple Silicon, `pip install faster-whisper` anywhere else

You can run the scripts by hand too:

```bash
python3 skills/reels-edit/scripts/transcribe.py raw.mp4 --lang en
python3 skills/reels-edit/scripts/edit.py config.json
python3 skills/reels-edit/scripts/check.py cut.mp4
```

Every option of `config.json` is documented at the top of `edit.py`.

## Works in any language

The prompts are in English, but Claude writes scripts, captions and descriptions in the language of your videos. Set it once in the prompt (`Language of my videos: ...`) and pass `--lang` to `transcribe.py`, or leave it out for auto-detect.

## Level 2

Things that make the result look more produced, but need extra accounts or setup. Not included here:

- animated captions and cards rendered from HTML, e.g. [HyperFrames](https://www.npmjs.com/package/hyperframes)
- text behind the speaker, by cutting out the person with [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting)
- scheduling posts from Claude through a social media tool with an MCP server, e.g. [Publer](https://publer.com)
- voice-over from a text-to-speech service, music and sound effects from a licensed library

## Credits

- 3x3 scoring method: [Jakub Biel](https://jakubbiel.pl/3x3/). A practical method, not a scientific one.
- Some editing rules (cut between phrases, one strong effect every ~8 s, check the finished file frame by frame) follow [herk-edit-kit](https://github.com/nateherkai/herk-edit-kit) by Nate Herk, MIT.

## License

MIT
