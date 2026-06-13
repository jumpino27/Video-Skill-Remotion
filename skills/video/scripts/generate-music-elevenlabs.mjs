#!/usr/bin/env node
// Generate background music with ElevenLabs Music (alternative to Suno).
//
// Usage:
//   node generate-music-elevenlabs.mjs --prompt "calm lofi tech bed, no vocals" \
//        --length-ms 40000 --out public/music.mp3 [--instrumental] [--format mp3_44100_128]
//
// length-ms must be 3000–600000 (3s–10min). Tip: pass the video's voice duration in ms so the
// track fits; the composition also loops/crops + ducks it anyway.
import fs from "node:fs";
import path from "node:path";
import { getElevenLabsKey, parseArgs, die } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));
let prompt = args.prompt;
if (args["prompt-file"]) prompt = fs.readFileSync(args["prompt-file"], "utf8");
if (!prompt || !prompt.trim()) die("Provide --prompt or --prompt-file");
if (args.instrumental) prompt = prompt.trim() + " Instrumental only, no vocals, no lyrics.";

const out = args.out || "music.mp3";
const format = args.format || "mp3_44100_128";
let lengthMs = args["length-ms"] != null ? Number(args["length-ms"]) : 40000;
lengthMs = Math.max(3000, Math.min(600000, Math.round(lengthMs)));

const url = `https://api.elevenlabs.io/v1/music?output_format=${encodeURIComponent(format)}`;
const res = await fetch(url, {
  method: "POST",
  headers: { "xi-api-key": getElevenLabsKey(), "Content-Type": "application/json" },
  body: JSON.stringify({ prompt: prompt.trim(), music_length_ms: lengthMs }),
});
if (!res.ok) die(`ElevenLabs Music failed (${res.status}): ${await res.text()}`);

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const buf = Buffer.from(await res.arrayBuffer());
fs.writeFileSync(out, buf);
console.log(JSON.stringify({ ok: true, out, bytes: buf.length, provider: "elevenlabs-music", lengthMs, format }));
