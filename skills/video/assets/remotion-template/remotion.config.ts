import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
// H.264 MP4 is the default codec; good for YouTube/IG/TikTok.
Config.setCodec("h264");
