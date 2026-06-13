#!/usr/bin/env node
// Generate narration audio with Microsoft MAI-Voice-2 via OpenRouter.
//
// House rule for this project: we ONLY use the en-US-Harper:MAI-Voice-2 voice
// (an English-named, multilingual persona — handles Romanian etc. via the model's
// multilingual capability). See ~/Documents/instructions.md §1.
//
// Usage:
//   node generate-voice.mjs --script-file script.txt --out public/voice.mp3 \
//        [--style cheerful] [--styledegree 1.2] [--speed 1.0] [--format mp3]
//   node generate-voice.mjs --text "Hello world" --out voice.mp3 --style friendly
//
// Emotion is a SINGLE predefined style + intensity per request (NOT free text):
//   style       one of the supported vocabulary words (see SKILL.md / instructions.md §1.4):
//               cheerful sad excited angry friendly hopeful terrified shouting whispering
//               calm gentle affectionate empathetic  (also: joy excitement empathy)
//               Unsupported styles are silently ignored (neutral delivery) — test before relying.
//   styledegree 0.01–2.0 intensity (default 1.0; ~1.4–2.0 for stronger expression)
//   speed       0.5–2.0 playback rate (default 1.0)
// Output formats: mp3 (default) pcm   (24 kHz)
//
// For a clip that CHANGES emotion partway through, OpenRouter gives one style per call —
// split the script by emotion, call this script once per segment with its own --style,
// then concatenate the MP3s (see instructions.md §1.5, Option A).
import fs from "node:fs";
import path from "node:path";
import { getOpenRouterKey, parseArgs, die } from "./_shared.mjs";

const args = parseArgs(process.argv.slice(2));

let text = args.text;
if (args["script-file"]) text = fs.readFileSync(args["script-file"], "utf8");
if (!text || !text.trim()) die("Provide --text or --script-file");

const VOICE = "en-US-Harper:MAI-Voice-2"; // house rule — the only voice we use
const model = args.model || "microsoft/mai-voice-2";
const format = (args.format || "mp3").toLowerCase(); // mp3 | pcm
const out = args.out || "voice.mp3";
const speed = args.speed != null ? Number(args.speed) : 1.0;

const body = {
  model,
  input: text.trim(),
  voice: VOICE,
  response_format: format,
  speed,
};

// Emotion: a single predefined style + intensity, passed via provider.options.azure.
if (args.style) {
  body.provider = {
    options: {
      azure: {
        style: String(args.style),
        styledegree: args.styledegree != null ? Number(args.styledegree) : 1.0,
      },
    },
  };
}

const res = await fetch("https://openrouter.ai/api/v1/audio/speech", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${getOpenRouterKey()}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify(body),
});

// Success is raw audio bytes; failures come back as JSON with error.message.
if (!res.ok) {
  let msg;
  try {
    msg = (await res.json())?.error?.message;
  } catch {
    msg = await res.text();
  }
  die(`TTS request failed (${res.status}): ${msg}`);
}

fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
const buf = Buffer.from(await res.arrayBuffer());
fs.writeFileSync(out, buf);

// Billed per character of input text at $22 / 1M chars; output is free.
const estCostUSD = Number((text.trim().length * 0.000022).toFixed(6));
console.log(
  JSON.stringify({
    ok: true,
    out,
    bytes: buf.length,
    voice: VOICE,
    model,
    format,
    style: args.style || null,
    styledegree: args.style ? (args.styledegree != null ? Number(args.styledegree) : 1.0) : null,
    speed,
    chars: text.trim().length,
    estCostUSD,
    generationId: res.headers.get("X-Generation-Id") || null,
  })
);
