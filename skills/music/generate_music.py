#!/usr/bin/env python3
"""
/music skill — ElevenLabs Music (Eleven Music) generator.

Calls POST https://api.elevenlabs.io/v1/music with either a free-text prompt
OR a composition_plan JSON (mutually exclusive), writes the audio file, and
prints a JSON summary.

Usage:
  python generate_music.py --prompt "an 80s synthwave instrumental..." --out song.mp3
  python generate_music.py --prompt-file PROMPT.txt --out song.mp3 --length-ms 90000
  python generate_music.py --prompt-file PROMPT.txt --out bed.mp3 --instrumental --length-ms 45000
  python generate_music.py --plan-file plan.json --out song.mp3

Flags:
  --prompt / --prompt-file   free-text prompt (genre, mood, instruments, BPM, key,
                             structure, lyrics or lyric direction)
  --plan-file                composition_plan JSON for precise section/lyrics control
                             (cannot be combined with --prompt)
  --length-ms                3000..600000 (3s–10min). Only with --prompt. Omit to let
                             the model pick a fitting length.
  --instrumental             sets force_instrumental=true (guaranteed no vocals)
  --format                   output_format, default mp3_44100_128
  --out                      output file path (default music_output/song.mp3)

The API key is read from the ELEVEN_LABS env var, then from a .env (skill folder,
the shared skills .env, ~/.claude/.env, or the path in SKILL_ENV_FILE).
"""
import argparse, json, os, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ENDPOINT = "https://api.elevenlabs.io/v1/music"
KEY_NAMES = ("ELEVEN_LABS", "ELEVENLABS_API_KEY", "ELEVEN_API_KEY", "XI_API_KEY")


def _env_files():
    """.env files to search, in order (first hit wins per key). Override with
    SKILL_ENV_FILE to point at any .env."""
    home = os.path.expanduser("~")
    skills_dir = os.path.dirname(HERE)  # parent of all skills (e.g. ~/.claude/skills)
    files = []
    if os.environ.get("SKILL_ENV_FILE"):
        files.append(os.environ["SKILL_ENV_FILE"])
    files += [
        os.path.join(HERE, ".env"),               # skill-local .env
        os.path.join(skills_dir, ".env"),         # shared .env next to the skills folder
        os.path.join(home, ".claude", ".env"),    # user-global Claude .env
        os.path.join(home, "Documents", ".env"),  # legacy fallback
    ]
    return files


def load_key():
    """Names are in PRIORITY order: for each name check the env var, then the
    .env files, before trying the next name. The canonical ELEVEN_LABS therefore
    beats a stale legacy env var like ELEVENLABS_API_KEY left in the environment."""
    file_vals = {}
    for envp in _env_files():
        if os.path.exists(envp):
            for line in open(envp, encoding="utf-8"):
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    file_vals.setdefault(k.strip(), v.strip().strip("'\""))
    for name in KEY_NAMES:
        if os.environ.get(name, "").strip():
            return os.environ[name].strip()
        if file_vals.get(name):
            return file_vals[name]
    sys.exit("ERROR: no ElevenLabs key found. Set ELEVEN_LABS in the environment or add it "
             "to a .env (skill folder, ~/.claude/.env, or point SKILL_ENV_FILE at one).")


def magic_ext(raw: bytes) -> str:
    if raw[:3] == b"ID3" or raw[:2] in (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"):
        return "mp3"
    if raw[:4] == b"RIFF":
        return "wav"
    if raw[:4] == b"OggS":
        return "ogg"
    return "mp3"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--plan-file", help="composition_plan JSON file (excludes --prompt)")
    ap.add_argument("--length-ms", type=int, help="3000..600000; only with --prompt")
    ap.add_argument("--instrumental", action="store_true")
    ap.add_argument("--format", default="mp3_44100_128")
    ap.add_argument("--out", default=os.path.join("music_output", "song.mp3"))
    args = ap.parse_args()

    prompt = args.prompt
    if args.prompt_file:
        prompt = open(args.prompt_file, encoding="utf-8").read().strip()

    body = {}
    if args.plan_file:
        if prompt:
            sys.exit("ERROR: --plan-file and --prompt are mutually exclusive (API constraint).")
        body["composition_plan"] = json.load(open(args.plan_file, encoding="utf-8"))
    else:
        if not prompt:
            sys.exit("ERROR: provide --prompt/--prompt-file or --plan-file.")
        body["prompt"] = prompt
        if args.length_ms is not None:
            body["music_length_ms"] = max(3000, min(600000, args.length_ms))
    if args.instrumental:
        body["force_instrumental"] = True

    url = f"{ENDPOINT}?output_format={args.format}"
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key": load_key(), "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: ElevenLabs Music failed ({e.code}): {e.read().decode('utf-8', 'replace')}")

    out = args.out
    ext = magic_ext(raw)
    root, cur = os.path.splitext(out)
    if cur.lstrip(".").lower() != ext:
        out = root + "." + ext
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "wb") as f:
        f.write(raw)

    print(json.dumps({
        "ok": True,
        "out": out,
        "bytes": len(raw),
        "provider": "elevenlabs-music",
        "mode": "composition_plan" if args.plan_file else "prompt",
        "length_ms": body.get("music_length_ms"),
        "force_instrumental": args.instrumental,
        "format": args.format,
    }))


if __name__ == "__main__":
    main()
