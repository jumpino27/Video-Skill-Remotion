<div align="center">

# 🎬 Media Skills for Claude Code

### Turn one sentence into a finished **video**, **song**, or **image** — without ever leaving your editor.

<p>
  <a href="https://www.instagram.com/jumpino27/">
    <img alt="Follow @jumpino27 on Instagram" src="https://img.shields.io/badge/Follow%20%40jumpino27-AI%20%C2%B7%20news%20%C2%B7%20skills%20%26%20repos-E4405F?style=for-the-badge&logo=instagram&logoColor=white">
  </a>
  &nbsp;
  <a href="https://revolut.me/jumpino">
    <img alt="Support my work on Revolut" src="https://img.shields.io/badge/%E2%9D%A4%20Support%20my%20work-Revolut-0666EB?style=for-the-badge&logo=revolut&logoColor=white">
  </a>
</p>

> 📲 **Follow [@jumpino27](https://www.instagram.com/jumpino27/)** for AI, news, skills & repos — &nbsp; ❤️ **Like these skills? [Support me on Revolut](https://revolut.me/jumpino).**

<p>
  <img alt="License" src="https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-skills-6C5CE7?style=for-the-badge">
  <img alt="Skills" src="https://img.shields.io/badge/skills-4-3b82f6?style=for-the-badge">
  <img alt="PRs welcome" src="https://img.shields.io/badge/PRs-welcome-f59e0b?style=for-the-badge">
</p>

<p>
  <img alt="ElevenLabs" src="https://img.shields.io/badge/ElevenLabs-Eleven%20v3-000000?style=flat-square">
  <img alt="OpenAI" src="https://img.shields.io/badge/OpenAI-whisper--1%20%C2%B7%20gpt--image--2-10a37f?style=flat-square">
  <img alt="Remotion" src="https://img.shields.io/badge/Remotion-render-0b84f3?style=flat-square">
</p>

**`/video`**  ·  **`/music`**  ·  **`/image`**  ·  **`/crop`**

</div>

---

<table>
<tr>
<td width="25%" align="center"><h3>🎥<br>/video</h3></td>
<td>Narrated video, <b>end-to-end</b>. Writes a viral-structured script, voices it with an expressive AI voiceover, transcribes for word-level <b>karaoke captions</b>, then builds & renders an animated <a href="https://www.remotion.dev/">Remotion</a> video sized for YouTube / Shorts / Reels / TikTok — plus ready-to-paste social copy.</td>
</tr>
<tr>
<td align="center"><h3>🎵<br>/music</h3></td>
<td>Original <b>songs or instrumentals</b> from a prompt or a precise section-by-section composition plan. Interviews you first; style-matches references copyright-safely.</td>
</tr>
<tr>
<td align="center"><h3>🖼️<br>/image</h3></td>
<td>Generate, edit, or <b>animate images</b> (sprite sheets / frame-by-frame) with an up-front quality-cost gate. Transparent assets are auto-keyed via <code>/crop</code>.</td>
</tr>
<tr>
<td align="center"><h3>✂️<br>/crop</h3></td>
<td>The helper for <code>/image</code>: removes backgrounds into clean <b>transparent PNGs</b> and slices sprite sheets into aligned frames.</td>
</tr>
</table>

> `/video` uses `/music` and `/image` under the hood, and `/image` uses `/crop` — but each skill works on its own too.

---

## ⚡ Install

### 🅰️ Option A — Let the AI install it for you  *(easiest, works in any agent)*

Paste this prompt into **Claude Code**, **Codex**, or **any coding agent**:

```text
Read the GitHub repo https://github.com/jumpino27/Video-Skill-Remotion and install its
four skills (video, music, image, crop) into my GLOBAL skills folder — that's
~/.claude/skills/ for Claude Code, or the equivalent skills folder for whatever agent
you are. Then install the Python requirements with `pip install -r requirements.txt`,
and tell me exactly which API keys I need to put in my .env (ElevenLabs + OpenAI).
```

That's it — the agent clones the repo, copies the four skill folders into place, installs the dependencies, and tells you what keys to add.

### 🅱️ Option B — Native plugin command  *(Claude Code)*

```bash
/plugin marketplace add jumpino27/Video-Skill-Remotion
/plugin install media-skills@video-skill-remotion
```

Installs all four skills **globally** (available in every project), with managed updates via `/plugin marketplace update`. When installed as a plugin they're invoked namespaced — `/media-skills:video`, `/media-skills:music`, … — and still auto-trigger when you simply ask for "a video / a song / an image".

### 🅲 Option C — Manual

Copy the four folders into your skills directory and restart Claude Code:

```
skills/video  →  ~/.claude/skills/video
skills/music  →  ~/.claude/skills/music
skills/image  →  ~/.claude/skills/image
skills/crop   →  ~/.claude/skills/crop
```

Then install the Python deps: `pip install -r requirements.txt`

---

## 🔑 API keys

Copy the template and fill in your keys:

```bash
cp .env.example .env        # then edit .env
```

| Key | Used by | Get it |
|-----|---------|--------|
| `ELEVEN_LABS` | `/video` voiceover · `/music` | [elevenlabs.io](https://elevenlabs.io) → Profile → API Keys |
| `OPENAI_API_KEY` | `/video` captions · `/image` | [platform.openai.com](https://platform.openai.com/api-keys) |

The skills find your keys automatically, in this order *(an env var of the same name always wins over a file)*:

```
process env  →  $SKILL_ENV_FILE / $VIDEO_ENV_FILE  →  skills/<name>/.env
            →  ~/.claude/skills/.env  →  ~/.claude/.env  →  ~/Documents/.env
```

The simplest setup is **one shared `.env`** at `~/.claude/skills/.env`.

> 🔒 `.env` and your personal `persona.json` are git-ignored — they never get committed.

---

## 🎨 Make `/video` yours

Out of the box `/video` ships with neutral defaults. To personalize it — **your name, brand, links, voice, presenter, accent color** — drop in a persona file:

```bash
cp skills/video/config/persona.example.json skills/video/config/persona.json
```

```jsonc
{
  "creatorName": "Ada Lovelace",
  "brandName":   "Analytical Engine",
  "links":   { "website": "https://ada.dev", "youtube": "", "instagram": "", "tiktok": "", "x": "" },
  "voice":   { "id": "eXO2dNYP4zo4oPWzuLta", "name": "Ivy", "model": "eleven_v3", "stability": "natural" },
  "presenter":   { "name": "Eve", "skill": "eve" },
  "accentColor": "#6C5CE7",
  "defaultPlatform": "shorts",
  "distribution":    { "linkPlacement": "description" }
}
```

- **Voice id** — grab yours from the ElevenLabs Voice Library (each voice has an id). Override per render with `--voice-id` or the `VIDEO_VOICE_ID` env var.
- **Links / accent / distribution** — the script writer and social-copy step use these so spoken CTAs and captions point where *you* want viewers to go.
- **Presenter** — only matters if you want an on-screen avatar host (default points at a separate `/eve` skill).

If `persona.json` is absent, the skill falls back to `persona.example.json` — so it always runs.

---

## 🕹️ Usage

Just talk to your agent:

- 🎥 **`/video`** — *"a 30-second TikTok on why my note-taking app saves an hour a week."* → interviews you, writes & shows the script for approval, then voices, captions, animates, and renders to `out/video.mp4` + a `content.md` with title/caption/hashtags.
- 🎵 **`/music`** — *"a dreamy 80s synthwave instrumental, 110 BPM, for a launch video."* → asks the missing details, crafts a producer-grade prompt, renders to `music_output/`.
- 🖼️ **`/image`** — *"a glossy transparent fox logo, sprite sheet, 6 frames."* → asks the quality tier (with prices), generates, auto-keys to transparent PNGs via `/crop`.

Each skill's full playbook lives in its `SKILL.md`.

---

## 🧩 Requirements

| | |
|---|---|
| **Node.js 18–22** | `/video` only (Remotion is unstable on Node 23+). Not needed for the others. |
| **Python 3.9+** | `/music`, `/image`, `/crop` |
| **ffmpeg** | on your PATH (audio trim/concat in `/video`) |
| **Keys** | ElevenLabs + OpenAI |

```bash
pip install -r requirements.txt
```

## 💸 Costs

These skills call paid APIs (ElevenLabs, OpenAI) billed to **your** accounts. `/image` always asks you to pick a quality tier *with prices* before spending; `/video` and `/music` bill per character / track length. **Nothing is generated without your go-ahead.**

---

## 📁 Layout

```
.
├── .claude-plugin/         marketplace.json + plugin.json  (Option B)
├── .env.example            API-key template  →  copy to .env
├── requirements.txt        Python deps for /image, /crop
└── skills/
    ├── video/   SKILL.md · scripts/ · assets/remotion-template/ · config/persona.example.json
    ├── music/   SKILL.md · generate_music.py · generate_music_lyria.py
    ├── image/   SKILL.md · image.py
    └── crop/    SKILL.md · crop.py
```

---

<div align="center">

### Enjoying these skills?

<a href="https://www.instagram.com/jumpino27/">
  <img alt="Follow @jumpino27 on Instagram" src="https://img.shields.io/badge/Follow%20%40jumpino27-Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white">
</a>
&nbsp;
<a href="https://revolut.me/jumpino">
  <img alt="Support my work on Revolut" src="https://img.shields.io/badge/%E2%9D%A4%20Support%20my%20work-Revolut-0666EB?style=for-the-badge&logo=revolut&logoColor=white">
</a>

<sub>AI · news · skills & repos on Instagram · support keeps new skills coming</sub>

<br><br>

**MIT** © [jumpino27](https://github.com/jumpino27) — see [LICENSE](LICENSE).

<sub>You're responsible for complying with the underlying APIs (ElevenLabs, OpenAI) and for anything you generate and publish.</sub>

</div>
