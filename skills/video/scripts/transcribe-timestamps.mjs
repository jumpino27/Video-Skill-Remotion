#!/usr/bin/env node
// Transcribe an audio file to WORD-LEVEL timestamps with OpenAI whisper-1.
// (gpt-4o-transcribe does NOT return word timestamps — whisper-1 is required for this step.)
//
// Usage:
//   node transcribe-timestamps.mjs --audio public/voice.mp3 --out public/captions.json
//
// Output: a JSON array in the @remotion/captions Caption[] shape:
//   [{ text: " Hello", startMs, endMs, timestampMs, confidence }, ...]
// Also prints { ok, words, durationSec } to stdout.
import fs from "node:fs";
import path from "node:path";
import { getApiKey, parseArgs, die } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));
const audio = args.audio;
const out = args.out || "captions.json";
if (!audio || !fs.existsSync(audio)) die("Provide a valid --audio path");

const bytes = fs.readFileSync(audio);
const form = new FormData();
form.append("file", new Blob([bytes]), path.basename(audio));
form.append("model", "whisper-1");
form.append("response_format", "verbose_json");
form.append("timestamp_granularities[]", "word");

const res = await fetch("https://api.openai.com/v1/audio/transcriptions", {
  method: "POST",
  headers: { Authorization: `Bearer ${getApiKey()}` },
  body: form,
});

if (!res.ok) die(`Transcription failed (${res.status}): ${await res.text()}`);

const data = await res.json();
const words = data.words || [];
if (!words.length) die("No word timestamps returned. Check the audio file.");

const captions = words.map((w) => {
  const startMs = Math.round((w.start ?? 0) * 1000);
  const endMs = Math.round((w.end ?? w.start ?? 0) * 1000);
  return {
    text: " " + String(w.word).trim(), // leading space is required by @remotion/captions
    startMs,
    endMs,
    timestampMs: Math.round((startMs + endMs) / 2),
    confidence: null,
  };
});

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
fs.writeFileSync(out, JSON.stringify(captions, null, 2));
console.log(
  JSON.stringify({
    ok: true,
    out,
    words: captions.length,
    durationSec: data.duration ?? (captions.at(-1)?.endMs ?? 0) / 1000,
  })
);
