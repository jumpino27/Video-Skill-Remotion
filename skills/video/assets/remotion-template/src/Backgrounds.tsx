import React from "react";
import {
  AbsoluteFill,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

// Animated SVG fallback used when the user provides no images/videos.
// A slowly shifting gradient + drifting translucent blobs in the accent color.
function hexToRgb(hex: string) {
  const h = hex.replace("#", "");
  const n = parseInt(
    h.length === 3
      ? h
          .split("")
          .map((c) => c + c)
          .join("")
      : h,
    16
  );
  return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255 };
}

export const AnimatedBackground: React.FC<{ accent: string }> = ({
  accent,
}) => {
  const frame = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();
  const { r, g, b } = hexToRgb(accent);

  const hueShift = interpolate(frame, [0, durationInFrames], [0, 40]);
  const blobs = [
    { x: 0.25, y: 0.3, r: 0.45, speed: 1.0, phase: 0 },
    { x: 0.75, y: 0.65, r: 0.55, speed: 0.7, phase: 2 },
    { x: 0.5, y: 0.5, r: 0.4, speed: 1.3, phase: 4 },
  ];

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(${135 + hueShift}deg, rgba(${r},${g},${b},0.95) 0%, #0c0c12 70%)`,
      }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{ position: "absolute", inset: 0 }}
      >
        <defs>
          <filter id="blur">
            <feGaussianBlur stdDeviation={Math.round(width * 0.06)} />
          </filter>
        </defs>
        {blobs.map((bl, i) => {
          const t = (frame * bl.speed) / 60;
          const cx = (bl.x + Math.sin(t + bl.phase) * 0.08) * width;
          const cy = (bl.y + Math.cos(t * 0.8 + bl.phase) * 0.08) * height;
          const rr =
            bl.r * Math.min(width, height) * (0.9 + 0.1 * Math.sin(t + i));
          const alpha = 0.18 + 0.07 * Math.sin(t + i);
          return (
            <circle
              key={i}
              cx={cx}
              cy={cy}
              r={rr}
              fill={`rgba(${r},${g},${b},${alpha})`}
              filter="url(#blur)"
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
