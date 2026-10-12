---
name: youtube-content
description: "YouTube transcripts to summaries, threads, blogs."
platforms: [linux, macos, windows]
---

# YouTube Content Tool

## When to use

Use when the user shares a YouTube URL or video link, asks to summarize a video, requests a transcript, or wants to extract and reformat content from any YouTube video. Transforms transcripts into structured content (chapters, summaries, threads, blog posts).

Extract transcripts from YouTube videos and convert them into useful formats.

## Setup

The skill ships a private venv at `.venv/` (next to SKILL.md) with
`youtube-transcript-api` installed. Do NOT use `uv run` / bare python —
always call the venv python directly:

```bash
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py ...
```

If the venv is missing (fresh machine), recreate it:
```bash
cd SKILL_DIR && uv venv .venv && uv pip install --python .venv/bin/python youtube-transcript-api
```

## Helper Script

`SKILL_DIR` is the directory containing this SKILL.md file. The script accepts any standard YouTube URL format, short links (youtu.be), shorts, embeds, live links, or a raw 11-character video ID.

```bash
# JSON output with metadata
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "https://youtube.com/watch?v=VIDEO_ID"

# Plain text (good for piping into further processing)
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only

# With timestamps
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "URL" --timestamps

# Compact: [MM:SS] text only, no metadata (saves tokens)
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "URL" --compact

# Specific language with fallback chain
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "URL" --language tr,en
```

The script already extracts the video ID from any URL form (watch?v=, youtu.be,
shorts, live, embed) and handles v1.x API of youtube-transcript-api.

## Formatting Rules

**Each logical paragraph must start on a new line.** This applies to all output formats — summaries, transcripts, chapters, blog posts, etc. Do not merge sentences into a wall of text. Break at logical topic shifts, speaker changes, or thought transitions.

## Output Formats

After fetching the transcript, format it based on what the user asks for:

- **Chapters**: Group by topic shifts, output timestamped chapter list
- **Summary**: Concise 5-10 sentence overview of the entire video
- **Chapter summaries**: Chapters with a short paragraph summary for each
- **Thread**: Twitter/X thread format — numbered posts, each under 280 chars
- **Blog post**: Full article with title, sections, and key takeaways
- **Quotes**: Notable quotes with timestamps

### Example — Chapters Output

```
00:00 Introduction — host opens with the problem statement
03:45 Background — prior work and why existing solutions fall short
12:20 Core method — walkthrough of the proposed approach
24:10 Results — benchmark comparisons and key takeaways
31:55 Q&A — audience questions on scalability and next steps
```

## Fetching the Transcript — Priority Order

### 1. Local Python script (primary)

NEVER use a YouTube-transcript MCP server: `@fabriqa.ai/youtube-transcript-mcp`
is broken (its bundled TS lib misparses URLs — passes full URLs where video IDs
are expected → false "Video unavailable / Invalid video ID" on perfectly
playable videos) and must not be used. The local
script works reliably.

```bash
SKILL_DIR/.venv/bin/python SKILL_DIR/scripts/fetch_transcript.py "URL" --text-only --timestamps
# or --compact for [MM:SS] lines
```

If the transcript comes back empty or the video has no subtitles at all, try
`--language ru,en` style fallbacks, then move to option 2.

### 2. yt-dlp subtitles (when youtube-transcript-api finds nothing but subs exist)

```bash
mkdir -p /tmp/yt-subs && cd /tmp/yt-subs
yt-dlp --skip-download --write-subs --write-auto-subs --sub-langs "ru,ru-orig,en" \
  --sub-format json3 -o "video" "URL"
```

Manual vs auto subs: `--write-subs` first, `--write-auto-subs` adds ASR ones.
Parse `*.json3` events (`tStartMs`, `segs[].utf8`) into `[MM:SS] text` lines.

### 3. Groq STT (for videos WITHOUT subtitles) — RECOMMENDED for long videos

If both MCP and local script return empty/missing transcripts (video has no subtitles), use the **Groq transcription pipeline**:

```bash
# One-command pipeline: download → split → transcribe → merge
# SKILL_DIR = directory containing this SKILL.md
bash SKILL_DIR/scripts/groq_transcribe.sh "URL" /tmp/transcript.txt ru

# With time range (extract only practical part)
# Use compact_transcript.py to filter after transcription
python3 SKILL_DIR/scripts/compact_transcript.py /tmp/transcript.json --from 48:00 --to 80:00
```

**How it works:**
1. Downloads audio via yt-dlp (quiet, no progress bar — saves tokens)
2. Splits into 20-min chunks (Groq limit ~25MB)
3. Transcribes each chunk via Groq Whisper API (free tier)
4. Merges into clean `[MM:SS] text` format — **no verbose JSON overhead**

**Limits**: Groq free tier, file ≤25MB per chunk (~20min audio). Handled automatically by the script.

**Time range extraction** — to transcribe only a portion:
```bash
# Transcribe full video first, then filter
bash SKILL_DIR/scripts/groq_transcribe.sh "URL" /tmp/full.txt ru
python3 SKILL_DIR/scripts/compact_transcript.py /tmp/full.json --from 48:00 --to 80:00
```

**Token savings vs old approach:**
- yt-dlp: `--quiet --no-progress` → ~100K tokens saved per download
- Groq: compact format instead of raw JSON → ~150K tokens saved per transcript
- Total: ~250K tokens saved per session

## Workflow

1. **Fetch** the transcript with the local script via `.venv/bin/python` (option 1). No MCP.
2. **Validate**: confirm the output is non-empty and in the expected language. If empty, retry without `--language` to get any available transcript; if still empty, try yt-dlp subs (option 2).
3. **If still empty** (no subtitles on video): use **Groq STT pipeline** — `bash SKILL_DIR/scripts/groq_transcribe.sh "URL"`. This handles download, splitting, transcription, and merge in one command.
4. **Time range**: if user wants only a portion (e.g. practical part), filter with `compact_transcript.py --from MM:SS --to MM:SS` or specify range in the note.
5. **Chunk if needed**: if the transcript exceeds ~50K characters, split into overlapping chunks (~40K with 2K overlap) and summarize each chunk before merging.
6. **Transform** into the requested output format. If the user did not specify a format, default to a summary.
7. **Verify**: re-read the transformed output to check for coherence, correct timestamps, and completeness before presenting.

## Token Optimization

**Critical:** yt-dlp and raw JSON transcripts are the biggest token consumers. Always use:
- `yt-dlp --quiet --no-progress` — suppresses thousands of progress lines
- `compact_transcript.py` or `groq_transcribe.sh` — outputs clean `[MM:SS] text` instead of verbose JSON
- `terminal(timeout=...)` with background processes for long downloads

When downloading a video file, save it to a scratch/working directory — NOT into synced notes folders (vault), to avoid pushing 300MB+ files through file-sync.

## Additional Rules
- YouTube live streams (ended): клиент `tv_embedded` работает (DASH-манифест напрямую): `yt-dlp --extractor-args "youtube:player_client=tv_embedded" -f "bestaudio/best"`.
- Яндекс.Диск видео: прямые ссылки не работают через curl/yt-dlp. Для скачивания: Playwright → извлечь m3u8 URL → ffmpeg с Referer header.

## Error Handling

- **YouTube 429 / rate limit on datacenter IP**: the script already sleeps 3–15s before the request; retry once after ~30s, then fall back to yt-dlp (option 2) or Groq STT.
- **Transcript disabled / no subtitles**: use **Groq STT pipeline** — `bash SKILL_DIR/scripts/groq_transcribe.sh "URL"`. This is the recommended fallback for long videos.
- **Private/unavailable video**: relay the error and ask the user to verify the URL.
- **No matching language**: if using MCP, retry `get-transcript-languages` to list options; if using the script, retry without `--language` to fetch any available transcript, then note the actual language to the user.
- **Dependency missing** (fallback script only): run `uv pip install youtube-transcript-api` and retry.
- **File too large for Groq** (>25MB): the `groq_transcribe.sh` script handles this automatically by splitting into chunks.
- **yt-dlp 403 errors**: see "Downloading video" section below for workarounds (cookies, client switching, Invidious).

## Downloading video when transcripts are not available

Sometimes a video has no subtitles or they are disabled. In that case you can download the video file itself using `yt-dlp` with a few work‑arounds that bypass YouTube’s 403 Forbidden block:

1. **Update yt‑dlp** – if installed via apt use the system updater, otherwise:
   ```bash
   pip install -U yt-dlp
   # or, if you prefer the uv‑managed environment:
   uv pip install -U yt-dlp
   ```

2. **Load browser cookies** – many 403 errors disappear when you send the same cookies you get from a logged‑in browser session:
   ```bash
   # Export cookies once (Chrome example)
   yt-dlp --cookies-from-browser chrome --cookies cookies.txt
   # Then reuse the file:
   yt-dlp --cookies cookies.txt <URL>
   ```

3. **Force a mobile/embedded player client** – YouTube’s web player sometimes triggers stricter checks. Using the Android (or iOS) client often works:
   ```bash
   yt-dlp --extractor-args "youtube:player_client=android" <URL>
   # alternatives: ios, web, tv_embedded
   ```

4. **Throttle requests** – add a short pause between attempts to avoid triggering anti‑abuse thresholds:
   ```bash
   yt-dlp --sleep-interval 5 <URL>
   ```

5. **Select a simple format** – adaptive formats (DASH/HLS) often trigger extra requests; a single progressive MP4 is more reliable:
   ```bash
   yt-dlp -f "bestvideo+bestaudio/best" <URL>   # best overall
   # or a known safe fallback:
   yt-dlp -f 18 <URL>   # 360p mp4
   ```

6. **Putting it together** – a robust command that usually works:
   ```bash
   yt-dlp \
       --cookies cookies.txt \
       --extractor-args "youtube:player_client=android" \
       --sleep-interval 5 \
       --no-part \
       -f "bestvideo+bestaudio/best" \
       -o "%(title)s.%(ext)s" \
       "<URL>"
   ```

If you still get 403, try:
- Switching the client (`ios`, `web`).
- Using a public invidious instance as a URL prefix:  
  `yt-dlp "https://yewtu.be/watch?v=VIDEO_ID"`.
- Checking that your cookies file is up‑to‑date (export again after login).

After downloading, you can feed the resulting file to any local transcription tool (e.g., Whisper) if you need subtitles.

**Save location:** When downloading a video, save to a scratch/working directory, not into synced note folders — avoids pushing 300MB+ files through file-sync tools (e.g. Syncthing). Serve via a web-accessible directory if the user wants a link.