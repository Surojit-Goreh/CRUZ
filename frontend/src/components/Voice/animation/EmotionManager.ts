import type { VoiceState, EmotionType } from "./types";
import { MathPool } from "./MathPool";

export class EmotionManager {
  public currentEmotion: EmotionType = "neutral";
  public targetEmotion: EmotionType = "neutral";
  public gestureIntensity = 0.40;
  public targetIntensity = 0.40;

  public setEmotion(emotion: EmotionType): void {
    this.targetEmotion = emotion;
  }

  public update(dt: number, state: VoiceState): void {
    // If emotion is neutral, automatically modulate based on voice state
    if (this.targetEmotion === "neutral") {
      switch (state) {
        case "speaking":
          this.targetIntensity = 0.55;
          break;
        case "thinking":
        case "transcribing":
          this.targetIntensity = 0.30;
          break;
        case "listening":
          this.targetIntensity = 0.35;
          break;
        default:
          this.targetIntensity = 0.25;
          break;
      }
    } else {
      switch (this.targetEmotion) {
        case "excited":
          this.targetIntensity = 0.85;
          break;
        case "happy":
          this.targetIntensity = 0.65;
          break;
        case "thinking":
          this.targetIntensity = 0.30;
          break;
        case "sad":
          this.targetIntensity = 0.20;
          break;
        case "confused":
          this.targetIntensity = 0.35;
          break;
        default:
          this.targetIntensity = 0.40;
          break;
      }
    }

    this.currentEmotion = this.targetEmotion;
    this.gestureIntensity = MathPool.damp(this.gestureIntensity, this.targetIntensity, 5.0, dt);
  }
}
