import React, { useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  spring,
} from "remotion";
import { type Caption } from "@remotion/captions";

/**
 * One-word-at-a-time captions (karaoke style).
 * At any moment we show ONLY the word the voice is currently saying, for the
 * exact duration it is spoken, then it leaves and the next word appears.
 * Genuinely fast words (a word shorter than MIN_UNIT_MS, like a quick "I make")
 * are shown together as one unit so they don't flash by unreadably.
 */

const MIN_UNIT_MS = 140; // a word shorter than this pairs with the next...
const MAX_UNIT_WORDS = 2; // ...but never merge more than two words
const JOIN_GAP_MS = 150; // ...and only if they're spoken back-to-back (not across a pause)
const HOLD_MS = 120; // keep a word up this little bit after it's spoken

type Unit = { startMs: number; endMs: number; text: string };

function buildUnits(captions: Caption[]): Unit[] {
  const units: Unit[] = [];
  let i = 0;
  while (i < captions.length) {
    let j = i;
    while (
      j + 1 < captions.length &&
      j - i + 1 < MAX_UNIT_WORDS &&
      captions[j].endMs - captions[i].startMs < MIN_UNIT_MS &&
      captions[j + 1].startMs - captions[j].endMs <= JOIN_GAP_MS
    ) {
      j++;
    }
    units.push({
      startMs: captions[i].startMs,
      endMs: captions[j].endMs,
      text: captions
        .slice(i, j + 1)
        .map((c) => c.text.trim())
        .join(" "),
    });
    i = j + 1;
  }
  return units;
}

export const CaptionsLayer: React.FC<{
  captions: Caption[];
  style: "tiktok" | "line";
  accent: string;
}> = ({ captions, accent }) => {
  const frame = useCurrentFrame();
  const { fps, height, width } = useVideoConfig();
  const ms = (frame / fps) * 1000;

  const units = useMemo(() => buildUnits(captions), [captions]);

  // the word currently being spoken = latest unit that has started
  let idx = -1;
  for (let u = 0; u < units.length; u++) {
    if (units[u].startMs <= ms) idx = u;
    else break;
  }
  if (idx < 0) return null;

  const unit = units[idx];
  const isLast = idx === units.length - 1;
  // hide once the word is done (during the pause before the next word). The
  // last word lingers through the short tail at the end of the video.
  if (!isLast && ms > unit.endMs + HOLD_MS) return null;

  const startFrame = (unit.startMs / 1000) * fps;
  const pop = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 200 },
    durationInFrames: 7,
  });

  // Fit the text to the screen.
  // - a multi-word unit ("automate servers") that is too wide stacks vertically
  //   (one word above the other);
  // - any single line that is still too wide (a very long word) shrinks until
  //   it fits within the safe area.
  const words = unit.text.split(" ");
  const baseFont = height * 0.064;
  const safe = width * 0.86; // usable width in px
  const CHAR_EM = 0.62; // rough width of an Inter-900 char, in font-size units
  const PAD_EM = 0.55; // pill horizontal padding, in font-size units
  const estWidth = (chars: number, fs: number) => chars * fs * CHAR_EM + fs * PAD_EM;

  const oneLineChars = unit.text.length;
  const stack = words.length > 1 && estWidth(oneLineChars, baseFont) > safe;
  const lines = stack ? words : [unit.text];

  const longest = Math.max(...lines.map((l) => l.length));
  let fontSize = baseFont;
  if (estWidth(longest, fontSize) > safe) {
    fontSize = Math.max(height * 0.038, (baseFont * safe) / estWidth(longest, baseFont));
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: Math.round(height * 0.17),
        paddingLeft: "6%",
        paddingRight: "6%",
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: Math.round(fontSize * 0.16),
          transform: `scale(${0.82 + 0.18 * pop})`,
          opacity: pop,
        }}
      >
        {lines.map((line, i) => (
          <div
            key={i}
            style={{
              fontFamily:
                "'Inter', 'Helvetica Neue', Arial, system-ui, sans-serif",
              fontWeight: 900,
              fontSize,
              letterSpacing: "-1px",
              color: "#05131a",
              backgroundColor: accent,
              padding: "0.05em 0.26em",
              borderRadius: 20,
              boxShadow: `0 0 44px ${accent}aa`,
              whiteSpace: "nowrap",
            }}
          >
            {line}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
