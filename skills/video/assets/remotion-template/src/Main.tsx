import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
  CalculateMetadataFunction,
} from "remotion";
import { getAudioDurationInSeconds } from "@remotion/media-utils";
import type { Caption } from "@remotion/captions";
import { CaptionsLayer } from "./Captions";
import { AnimatedBackground } from "./Backgrounds";
import { Scenes, type Lang } from "./Scenes";

export type MediaItem = { src: string; type: "image" | "video" };

export type Props = {
  platform: string;
  width: number;
  height: number;
  fps: number;
  audioFile: string; // relative to public/, e.g. "voice.mp3"
  captionsFile?: string; // relative to public/, e.g. "captions.json"
  captions?: Caption[];
  media: MediaItem[];
  captionStyle: "tiktok" | "line" | "none";
  accent: string; // hex color
  lang?: Lang; // localizes the animated scene text (en/de/it/ro)
  musicFile?: string; // optional background track in public/, e.g. "music.mp3"
  musicVolume?: number; // "normal" music level (default 0.28); narration stays on top
  title?: string;
};

export const DEFAULT_PROPS: Props = {
  platform: "tiktok",
  width: 1080,
  height: 1920,
  fps: 30,
  audioFile: "voice.mp3",
  captionsFile: "captions.json",
  captions: [],
  media: [],
  captionStyle: "tiktok",
  accent: "#6C5CE7",
  lang: "en",
  title: "",
};

// Duration of the whole video is derived from the narration audio length.
export const calculateMetadata: CalculateMetadataFunction<Props> = async ({
  props,
}) => {
  const fps = props.fps || 30;
  const durationSec = await getAudioDurationInSeconds(
    staticFile(props.audioFile)
  );

  let captions: Caption[] = props.captions || [];
  if (props.captionsFile) {
    try {
      const res = await fetch(staticFile(props.captionsFile));
      captions = await res.json();
    } catch (e) {
      // keep whatever was passed in props
    }
  }

  const tail = Math.round(fps * 0.5); // small breathing room after the voice ends
  return {
    durationInFrames: Math.ceil(durationSec * fps) + tail,
    fps,
    width: props.width,
    height: props.height,
    props: { ...props, captions },
  };
};

// One media clip with a slow Ken-Burns zoom/pan.
const MediaClip: React.FC<{ item: MediaItem; durationInFrames: number }> = ({
  item,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, durationInFrames], [1.08, 1.18], {
    extrapolateRight: "clamp",
  });
  const opacity = interpolate(
    frame,
    [0, 12, durationInFrames - 12, durationInFrames],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  return (
    <AbsoluteFill style={{ opacity, overflow: "hidden" }}>
      {item.type === "video" ? (
        <OffthreadVideo
          src={staticFile(item.src)}
          muted
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      ) : (
        <Img
          src={staticFile(item.src)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      )}
    </AbsoluteFill>
  );
};

export const Main: React.FC<Props> = (props) => {
  const { durationInFrames, fps } = useVideoConfig();
  const { media, accent, audioFile, captions, captionStyle, lang, musicFile, musicVolume } =
    props;

  return (
    <AbsoluteFill style={{ backgroundColor: "#07080d" }}>
      {/* BACKGROUND LAYER */}
      {media && media.length > 0 ? (
        media.map((item, i) => {
          const per = Math.floor(durationInFrames / media.length);
          const from = i * per;
          const len = i === media.length - 1 ? durationInFrames - from : per;
          return (
            <Sequence key={i} from={from} durationInFrames={len}>
              <MediaClip item={item} durationInFrames={len} />
            </Sequence>
          );
        })
      ) : (
        <>
          {/* faint animated backdrop for depth */}
          <AbsoluteFill style={{ opacity: 0.35 }}>
            <AnimatedBackground accent={accent} />
          </AbsoluteFill>
          {/* radial vignette to focus center */}
          <AbsoluteFill
            style={{
              background: `radial-gradient(circle at 50% 42%, ${accent}14 0%, rgba(7,8,13,0) 55%), radial-gradient(circle at 50% 50%, rgba(7,8,13,0) 40%, #07080d 100%)`,
            }}
          />
          {/* crisp animated SVG scenes that present the narration */}
          <Scenes accent={accent} lang={lang} captions={captions} />
        </>
      )}

      {/* subtle dark gradient so captions stay readable over any media */}
      <AbsoluteFill
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 45%)",
        }}
      />

      {/* CAPTIONS */}
      {captionStyle !== "none" && captions && captions.length > 0 && (
        <CaptionsLayer captions={captions} style={captionStyle} accent={accent} />
      )}

      {/* NARRATION */}
      <Audio src={staticFile(audioFile)} />

      {/* BACKGROUND MUSIC — looped to fill, auto-cropped to the video length, with a
          low→normal fade-in at the start and normal→low fade-out at the end. */}
      {musicFile && (
        <Audio
          src={staticFile(musicFile)}
          loop
          volume={(f) => {
            const lo = 0.1;
            const hi = musicVolume ?? 0.28;
            const inEnd = Math.round(fps * 1.5);
            const outStart = durationInFrames - Math.round(fps * 2);
            const up = interpolate(f, [0, inEnd], [lo, hi], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const down = interpolate(f, [outStart, durationInFrames], [hi, lo], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return Math.min(up, down);
          }}
        />
      )}
    </AbsoluteFill>
  );
};
