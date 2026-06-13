import { Composition } from "remotion";
import { Main, calculateMetadata, DEFAULT_PROPS } from "./Main";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Main"
      component={Main}
      // These are placeholders; calculateMetadata() overrides them from props.json
      // (driven by the real voice duration + platform dimensions).
      durationInFrames={300}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={DEFAULT_PROPS}
      calculateMetadata={calculateMetadata}
    />
  );
};
