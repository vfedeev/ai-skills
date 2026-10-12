# Tips for bypassing YouTube 403 Forbidden with yt-dlp

## 1. Keep yt-dlp updated
```bash
pip install -U yt-dlp          # or via uv: uv pip install -U yt-dlp
```

## 2. Use browser cookies
Export cookies once from a logged‑in browser (Chrome example):
```bash
yt-dlp --cookies-from-browser chrome --cookies cookies.txt
```
Then reuse:
```bash
yt-dlp --cookies cookies.txt <URL>
```

## 3. Force a mobile/embedded player client
Web client triggers stricter checks; Android/iOS often work:
```bash
yt-dlp --extractor-args "youtube:player_client=android" <URL>
# alternatives: ios, web, tv_embedded
```

## 4. Throttle requests
Avoid triggering anti‑abuse limits:
```bash
yt-dlp --sleep-interval 5 <URL>
```

## 5. Choose a simple, progressive format
Adaptive formats (DASH/HLS) cause extra requests; a single MP4 is more reliable:
```bash
# Best overall quality
yt-dlp -f "bestvideo+bestaudio/best" <URL>
# Known safe fallback (360p mp4)
yt-dlp -f 18 <URL>
```

## 6. Combined robust command
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

## 7. If still 403
- Switch client (`ios`, `web`).
- Try via an invidious instance: `yt-dlp "https://yewtu.be/watch?v=VIDEO_ID"`.
- Refresh cookies (export again after login).

## 8. After download: generate subtitles
If you need subtitles and the video lacks them, run a local transcription tool (e.g., Whisper) on the downloaded file.