import * as THREE from "three";
import { VRM } from "@pixiv/three-vrm";
import type { VoiceState, EmotionType } from "./types";
import { MathPool } from "./MathPool";
import { JointConstraints } from "./JointConstraints";

export class FaceController {
  private vrm: VRM;

  // Gaze / Mouse coordinates (-1 .. 1)
  public mouseNX = 0;
  public mouseNY = 0;

  // Head Orientation Targets
  public headOffset = new THREE.Euler(0, 0, 0, "YXZ");
  public headNodAngle = 0;
  public headTiltAngle = 0;

  // Blinking State
  private blinkVal = 0;
  private blinkTarget = 0;
  private blinkTimer = 3.0;

  // Lip-Sync Viseme State
  private lipTime = 0;

  constructor(vrm: VRM) {
    this.vrm = vrm;
  }

  public setMouse(nx: number, ny: number): void {
    this.mouseNX = nx;
    this.mouseNY = ny;
  }

  /**
   * Updates natural randomized blinking.
   */
  private updateBlinking(dt: number, state: VoiceState): void {
    this.blinkTimer -= dt;
    if (this.blinkTimer <= 0) {
      if (this.blinkTarget === 0) {
        this.blinkTarget = 1;
        this.blinkTimer = 0.10; // Blink close duration: 100ms
      } else {
        this.blinkTarget = 0;
        this.blinkTimer = 2.8 + Math.random() * 2.8; // Next blink in 2.8 - 5.6s
      }
    }

    this.blinkVal = MathPool.damp(this.blinkVal, this.blinkTarget, 16.0, dt);
    const blinkMultiplier = state === "speaking" ? 0.45 : 1.0;
    const finalBlink = this.blinkVal * blinkMultiplier;

    this.setBlend(["blinkLeft", "blink_l", "blink"], finalBlink);
    this.setBlend(["blinkRight", "blink_r", "blink"], finalBlink);
  }

  /**
   * Helper to set blendshapes safely supporting both VRM 0.0 and VRM 1.0 naming conventions.
   */
  private setBlend(names: string[], value: number): void {
    const mgr = this.vrm.expressionManager;
    if (!mgr) return;
    for (const name of names) {
      try {
        mgr.setValue(name, value);
      } catch {
        // Safe ignore
      }
    }
  }

  /**
   * Helper to get blendshape value across possible naming aliases.
   */
  private getBlend(names: string[]): number {
    const mgr = this.vrm.expressionManager;
    if (!mgr) return 0;
    for (const name of names) {
      const v = mgr.getValue(name);
      if (v !== null && v !== undefined) return v;
    }
    return 0;
  }

  /**
   * Updates multi-vowel viseme lip sync.
   */
  private updateLipSync(dt: number, state: VoiceState): void {
    const mgr = this.vrm.expressionManager;
    if (!mgr) return;

    if (state === "speaking") {
      this.lipTime += dt;
      const c = (this.lipTime * 7.5) % (Math.PI * 2);

      const aa = MathPool.clamp(Math.sin(c) * 0.85 + 0.35, 0, 1);
      const oh = MathPool.clamp(Math.sin(c * 1.4 + 0.8) * 0.75, 0, 1);
      const ih = MathPool.clamp(Math.sin(c + 1.6) * 0.55, 0, 1);
      const ou = MathPool.clamp(Math.sin(c + 2.6) * 0.45, 0, 1);
      const ee = MathPool.clamp(Math.sin(c * 1.2 + 1.2) * 0.50, 0, 1);

      this.setBlend(["aa", "a", "A", "viseme_aa"], aa);
      this.setBlend(["oh", "o", "O", "viseme_oh"], oh);
      this.setBlend(["ih", "i", "I", "viseme_ih"], ih);
      this.setBlend(["ou", "u", "U", "viseme_ou"], ou);
      this.setBlend(["ee", "e", "E", "viseme_ee"], ee);
    } else {
      const curAa = this.getBlend(["aa", "a", "A", "viseme_aa"]);
      const nextAa = MathPool.damp(curAa, 0, 12.0, dt);
      this.setBlend(["aa", "a", "A", "viseme_aa"], nextAa);
      this.setBlend(["oh", "o", "O", "viseme_oh"], 0);
      this.setBlend(["ih", "i", "I", "viseme_ih"], 0);
      this.setBlend(["ou", "u", "U", "viseme_ou"], 0);
      this.setBlend(["ee", "e", "E", "viseme_ee"], 0);
    }
  }

  /**
   * Updates facial expressions and blend shapes with warm anime aesthetics.
   */
  private updateExpressions(dt: number, state: VoiceState, emotion: EmotionType): void {
    const mgr = this.vrm.expressionManager;
    if (!mgr) return;

    let targetHappy = 0.40; // Default warm, lively smile
    let targetRelaxed = 0.25;
    let targetSurprised = 0;
    let targetSad = 0;

    switch (emotion) {
      case "happy":
        targetHappy = 0.85;
        targetRelaxed = 0.30;
        break;
      case "excited":
        targetHappy = 0.95;
        targetSurprised = 0.25;
        break;
      case "thinking":
        targetHappy = 0.20;
        targetSurprised = 0.35;
        targetRelaxed = 0.35;
        break;
      case "confused":
        targetHappy = 0.10;
        targetSurprised = 0.50;
        break;
      case "sad":
        targetHappy = 0;
        targetSad = 0.60;
        break;
      default:
        if (state === "speaking") {
          targetHappy = 0.65;
          targetRelaxed = 0.20;
        } else if (state === "listening") {
          targetHappy = 0.50;
          targetRelaxed = 0.30;
        } else if (state === "thinking" || state === "transcribing") {
          targetHappy = 0.15;
          targetSurprised = 0.35;
        } else {
          targetHappy = 0.38; // Gentle friendly resting smile
          targetRelaxed = 0.30;
        }
        break;
    }

    const speed = 6.0;
    const curHappy = this.getBlend(["happy", "joy", "fun", "smile"]);
    const curRelaxed = this.getBlend(["relaxed", "neutral"]);
    const curSurprised = this.getBlend(["surprised", "surprise"]);
    const curSad = this.getBlend(["sad", "sorrow"]);

    const newHappy = MathPool.damp(curHappy, targetHappy, speed, dt);
    const newRelaxed = MathPool.damp(curRelaxed, targetRelaxed, speed, dt);
    const newSurprised = MathPool.damp(curSurprised, targetSurprised, speed, dt);
    const newSad = MathPool.damp(curSad, targetSad, speed, dt);

    this.setBlend(["happy", "joy", "fun", "smile"], newHappy);
    this.setBlend(["relaxed", "neutral"], newRelaxed);
    this.setBlend(["surprised", "surprise"], newSurprised);
    this.setBlend(["sad", "sorrow"], newSad);
  }

  /**
   * Updates head and neck rotations (gaze, nods, communicative tilts).
   */
  private updateHeadAndNeck(dt: number, state: VoiceState): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    const head = h.getNormalizedBoneNode("head");
    const neck = h.getNormalizedBoneNode("neck");
    if (!head) return;

    let targetHx = this.headOffset.x;
    let targetHy = this.headOffset.y;
    let targetHz = this.headOffset.z + this.headTiltAngle;

    if (state === "idle") {
      // Natural gaze tracking in idle
      const gazeX = MathPool.clamp(-this.mouseNY * 0.22, -0.32, 0.24);
      const gazeY = MathPool.clamp(this.mouseNX * 0.26, -0.38, 0.38);
      targetHx += gazeX;
      targetHy += gazeY;
    } else if (state === "listening") {
      // Attentive listener posture
      const gazeX = MathPool.clamp(-this.mouseNY * 0.15 - 0.08, -0.25, 0.15);
      const gazeY = MathPool.clamp(this.mouseNX * 0.18, -0.25, 0.25);
      targetHx += gazeX;
      targetHy += gazeY;
      targetHz += 0.04; // subtle interested tilt
    } else if (state === "thinking" || state === "transcribing") {
      // Pensive looking upward/away
      targetHx += -0.10;
      targetHy += -0.14;
      targetHz += 0.06;
    } else if (state === "speaking") {
      // Conversational nod & emphasis
      targetHx += this.headNodAngle;
    }

    head.rotation.x = MathPool.damp(head.rotation.x, targetHx, 8.0, dt);
    head.rotation.y = MathPool.damp(head.rotation.y, targetHy, 8.0, dt);
    head.rotation.z = MathPool.damp(head.rotation.z, targetHz, 8.0, dt);
    JointConstraints.clampBoneRotation(head, JointConstraints.Head);

    if (neck) {
      neck.rotation.x = MathPool.damp(neck.rotation.x, head.rotation.x * 0.45, 8.0, dt);
      neck.rotation.y = MathPool.damp(neck.rotation.y, head.rotation.y * 0.45, 8.0, dt);
      neck.rotation.z = MathPool.damp(neck.rotation.z, head.rotation.z * 0.35, 8.0, dt);
      JointConstraints.clampBoneRotation(neck, JointConstraints.Neck);
    }
  }

  /**
   * Main face update pass.
   */
  public update(dt: number, state: VoiceState, emotion: EmotionType): void {
    this.updateBlinking(dt, state);
    this.updateLipSync(dt, state);
    this.updateExpressions(dt, state, emotion);
    this.updateHeadAndNeck(dt, state);
  }
}
