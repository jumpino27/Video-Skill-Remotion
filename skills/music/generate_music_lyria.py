#!/usr/bin/env python3
"""
/music skill — Google Lyria 3 generator via OpenRouter.

Streams audio from OpenRouter's chat/completions endpoint (Lyria requires
stream=true for audio output), assembles the base64 chunks, and writes a
real audio file plus a sidecar .txt with the lyric/structure timeline.

Usage:
  python generate_music.py --prompt-file PROMPT.txt --out song.mp3 [--model clip|pro]
  python generate_music.py --prompt "an 80s synthwave instrumental..." --out song.mp3 --model pro

Models:
  clip -> google/lyria-3-clip-preview  (fixed 30s, $0.04)  -- great for drafts
  pro  -> google/lyria-3-pro-preview   (full song, $0.08)  -- final masterpiece

The OpenRouter key is read from the .env next to this script (OPENROUTER_API_KEY),
or from the OPENROUTER_API_KEY environment variable if set.
"""
import argparse, base64, json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = {
    "clip": "google/lyria-3-clip-preview",
    "pro":  "google/lyria-3-pro-preview",
}
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


def load_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    home = os.path.expanduser("~")
    candidates = []
    if os.environ.get("SKILL_ENV_FILE"):
        candidates.append(os.environ["SKILL_ENV_FILE"])
    candidates += [
        os.path.join(HERE, ".env"),                      # skill-local .env
        os.path.join(os.path.dirname(HERE), ".env"),     # shared skills .env
        os.path.join(home, ".claude", ".env"),           # user-global Claude .env
        os.path.join(home, "Documents", ".env"),         # legacy fallback
    ]
    for envp in candidates:
        if os.path.exists(envp):
            for line in open(envp, encoding="utf-8"):
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() == "OPENROUTER_API_KEY" and v.strip():
                    return v.strip().strip("'\"")
    sys.exit("ERROR: no OPENROUTER_API_KEY found (checked env var and .env files).")


def magic_ext(raw: bytes) -> str:
    if raw[:3] == b"ID3" or raw[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if raw[:4] == b"RIFF":
        return "wav"
    if raw[:4] == b"OggS":
        return "ogg"
    if raw[:4] == b"fLaC":
        return "flac"
    return "mp3"


def generate(prompt: str, model_key: str, out: str):
    model = MODELS[model_key]
    key = load_key()
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["text", "audio"],
        "audio": {"format": "wav"},  # provider may override; we sniff the bytes
        "stream": True,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://claude.ai",
            "X-Title": "ClaudeCode /music",
        },
        method="POST",
    )

    audio_parts, text_parts, cost = [], [], None
    print(f"[music] generating with {model} ...", file=sys.stderr)
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", "ignore").strip()
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    obj = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if obj.get("error"):
                    sys.exit(f"API error: {obj['error']}")
                u = obj.get("usage")
                if u and u.get("cost") is not None:
                    cost = u["cost"]
                for ch in obj.get("choices", []):
                    d = ch.get("delta", {})
                    au = d.get("audio")
                    if au and au.get("data"):
                        audio_parts.append(au["data"])
                    if d.get("content"):
                        text_parts.append(d["content"])
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode('utf-8','ignore')}")

    if not audio_parts:
        sys.exit("No audio returned. (Was the prompt blocked by safety filters? "
                 "Remember: never include real artist names / copyrighted lyrics.)")

    raw = base64.b64decode("".join(audio_parts))
    ext = magic_ext(raw)
    base, _ = os.path.splitext(out)
    final = base + "." + ext
    with open(final, "wb") as f:
        f.write(raw)

    timeline = "".join(text_parts)
    if timeline.strip():
        with open(base + "_timeline.txt", "w", encoding="utf-8") as f:
            f.write(timeline)

    kb = len(raw) // 1024
    print(json.dumps({
        "file": os.path.abspath(final),
        "timeline": os.path.abspath(base + "_timeline.txt") if timeline.strip() else None,
        "format": ext,
        "size_kb": kb,
        "model": model,
        "cost_usd": cost,
    }, indent=2))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prompt")
    g.add_argument("--prompt-file")
    ap.add_argument("--out", required=True, help="output path (extension auto-corrected to real format)")
    ap.add_argument("--model", choices=["clip", "pro"], default="pro")
    a = ap.parse_args()
    prompt = a.prompt if a.prompt else open(a.prompt_file, encoding="utf-8").read()
    generate(prompt.strip(), a.model, a.out)


if __name__ == "__main__":
    main()
