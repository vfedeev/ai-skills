#!/bin/bash
# Groq Whisper transcription pipeline
# Downloads audio, splits into chunks, transcribes via Groq API, merges result
#
# Usage:
#   bash groq_transcribe.sh <youtube_url> [output_file] [language] [max_chunk_seconds]
#
# Examples:
#   bash groq_transcribe.sh "https://youtube.com/watch?v=XXX"
#   bash groq_transcribe.sh "https://youtube.com/watch?v=XXX" /tmp/transcript.txt ru 1200
#
# Output: timestamped text [MM:SS] per line
# Requires: yt-dlp, ffmpeg, curl, GROQ_API_KEY in ~/.hermes/.env

set -euo pipefail

URL="${1:?Usage: groq_transcribe.sh <youtube_url> [output_file] [language] [max_chunk_sec]}"
OUTPUT="${2:-/tmp/groq_transcript.txt}"
LANGUAGE="${3:-ru}"
CHUNK_SEC="${4:-1200}"  # 20 minutes per chunk (Groq limit ~25MB)

WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

# --- Get Groq API key ---
API_KEY=$(grep GROQ_API_KEY ~/.hermes/.env | head -1 | cut -d= -f2- | cut -d'#' -f1 | tr -d ' ')
if [ -z "$API_KEY" ]; then
    echo "ERROR: GROQ_API_KEY not found in ~/.hermes/.env" >&2
    exit 1
fi

# --- Download audio (quiet, no progress bar) ---
echo "[1/4] Downloading audio..." >&2
yt-dlp \
    --extractor-args "youtube:player_client=android" \
    -f "bestaudio[ext=m4a]/bestaudio" \
    --extract-audio --audio-format mp3 \
    --no-progress --quiet \
    -o "$WORKDIR/audio.%(ext)s" \
    "$URL" 2>/dev/null

AUDIO=$(ls "$WORKDIR"/audio.* 2>/dev/null | head -1)
if [ -z "$AUDIO" ]; then
    echo "ERROR: Download failed" >&2
    exit 1
fi

DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$AUDIO" 2>/dev/null)
echo "   Duration: $(printf '%02d:%02d:%02d' $((${DURATION%.*}/3600)) $(((${DURATION%.*}%3600)/60)) $((${DURATION%.*}%60)))" >&2

# --- Split into chunks ---
echo "[2/4] Splitting into chunks (${CHUNK_SEC}s each)..." >&2
TOTAL_SEC=${DURATION%.*}
CHUNKS=0
OFFSET=0

while [ $OFFSET -lt $TOTAL_SEC ]; do
    ffmpeg -y -i "$AUDIO" -ss "$OFFSET" -t "$CHUNK_SEC" -c copy "$WORKDIR/chunk_${CHUNKS}.mp3" 2>/dev/null
    OFFSET=$((OFFSET + CHUNK_SEC))
    CHUNKS=$((CHUNKS + 1))
done

echo "   $CHUNKS chunks created" >&2

# --- Transcribe each chunk ---
echo "[3/4] Transcribing via Groq Whisper..." >&2
> "$WORKDIR/all_segments.jsonl"

for i in $(seq 0 $((CHUNKS - 1))); do
    CHUNK_FILE="$WORKDIR/chunk_${i}.mp3"
    OFFSET_SEC=$((i * CHUNK_SEC))
    
    echo "   Chunk $((i+1))/$CHUNKS (offset ${OFFSET_SEC}s)..." >&2
    
    RESPONSE=$(curl -s -X POST "https://api.groq.com/openai/v1/audio/transcriptions" \
        -H "Authorization: Bearer $API_KEY" \
        -F "file=@$CHUNK_FILE" \
        -F "model=whisper-large-v3-turbo" \
        -F "language=$LANGUAGE" \
        -F "response_format=verbose_json")
    
    # Extract segments and adjust timestamps
    echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
offset = $OFFSET_SEC
for seg in data.get('segments', []):
    seg['start'] += offset
    seg['end'] += offset
    print(json.dumps(seg, ensure_ascii=False))
" >> "$WORKDIR/all_segments.jsonl"
    
    # Rate limit: 1 req/sec for Groq free tier
    sleep 1
done

# --- Merge and format ---
echo "[4/4] Merging transcript..." >&2
python3 -c "
import json, sys

segments = []
with open('$WORKDIR/all_segments.jsonl') as f:
    for line in f:
        line = line.strip()
        if line:
            segments.append(json.loads(line))

segments.sort(key=lambda s: s['start'])

for seg in segments:
    mins = int(seg['start'] // 60)
    secs = int(seg['start'] % 60)
    text = seg['text'].strip()
    if text:
        print(f'[{mins:02d}:{secs:02d}] {text}')
" > "$OUTPUT"

LINES=$(wc -l < "$OUTPUT")
CHARS=$(wc -c < "$OUTPUT")
echo "   Done: $LINES lines, $CHARS chars" >&2
cat "$OUTPUT"
