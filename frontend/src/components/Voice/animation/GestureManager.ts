import * as THREE from "three";
import type { GestureType, GesturePhase, GestureDefinition, VoiceState, EmotionType } from "./types";
import { GestureLibrary } from "./GestureLibrary";
import { MathPool } from "./MathPool";
import { IKController } from "./IKController";

export class GestureManager {
  private ikController: IKController;

  public activeGesture: GestureType = "idle";
  public activePhase: GesturePhase = "idle";
  public phaseTime = 0;
  public totalProgress = 0;

  private currentDef: GestureDefinition = GestureLibrary.get("idle");
  private cooldowns: Map<GestureType, number> = new Map();
  private speechGestureTimer = 0;

  // Active Offsets for Body & Head
  public headOffset = new THREE.Euler();
  public torsoOffset = new THREE.Euler();
  public leftShoulderOffset = new THREE.Euler();
  public rightShoulderOffset = new THREE.Euler();

  constructor(ikController: IKController) {
    this.ikController = ikController;
  }

  /**
   * Triggers a specific gesture if priority permits and not in cooldown.
   */
  public trigger(type: GestureType, force = false): boolean {
    const def = GestureLibrary.get(type);
    if (!force && (this.cooldowns.get(type) ?? 0) > 0) return false;
    if (!force && this.activePhase !== "idle" && this.currentDef.priority > def.priority) return false;

    this.activeGesture = type;
    this.currentDef = def;
    this.activePhase = "preparing";
    this.phaseTime = 0;
    this.totalProgress = 0;
    return true;
  }

  /**
   * Automatically picks speech gestures during speaking state.
   */
  private updateSpeechScheduler(dt: number, state: VoiceState, emotion: EmotionType): void {
    if (state !== "speaking") {
      this.speechGestureTimer = 0.4;
      return;
    }

    this.speechGestureTimer -= dt;
    if (this.speechGestureTimer <= 0 && this.activePhase === "idle") {
      // Pick next speaking gesture based on emotion
      const candidateList: GestureType[] =
        emotion === "excited"
          ? ["excited", "explain", "talk", "agree_nod"]
          : emotion === "thinking"
          ? ["thinking", "explain", "talk"]
          : emotion === "confused"
          ? ["confused", "shrug", "talk"]
          : ["talk", "explain", "agree_nod", "point", "shrug"];

      // Find available candidate with lowest cooldown
      const available = candidateList.filter((g) => (this.cooldowns.get(g) ?? 0) <= 0);
      if (available.length > 0) {
        const picked = available[Math.floor(Math.random() * available.length)];
        this.trigger(picked);
      }

      // Next gesture scheduled after a natural pause (1.2 - 2.8s)
      this.speechGestureTimer = 1.4 + Math.random() * 1.6;
    }
  }

  /**
   * Main gesture state machine update loop.
   */
  public update(dt: number, state: VoiceState, emotion: EmotionType, intensity: number): void {
    // Decrement active cooldowns
    for (const [key, time] of this.cooldowns.entries()) {
      if (time > 0) this.cooldowns.set(key, Math.max(0, time - dt));
    }

    this.updateSpeechScheduler(dt, state, emotion);

    if (this.activePhase === "idle") {
      this.ikController.releaseArms();
      this.headOffset.set(0, 0, 0);
      this.torsoOffset.set(0, 0, 0);
      this.leftShoulderOffset.set(0, 0, 0);
      this.rightShoulderOffset.set(0, 0, 0);
      return;
    }

    this.phaseTime += dt;
    const def = this.currentDef;

    let blendWeight = 0;

    switch (this.activePhase) {
      case "preparing": {
        const progress = MathPool.clamp(this.phaseTime / Math.max(0.01, def.prepDuration), 0, 1);
        blendWeight = MathPool.smoothstep(0, 1, progress);
        this.totalProgress = progress * 0.3;

        if (this.phaseTime >= def.prepDuration) {
          this.activePhase = "holding";
          this.phaseTime = 0;
        }
        break;
      }
      case "holding": {
        blendWeight = 1.0;
        const progress = MathPool.clamp(this.phaseTime / Math.max(0.01, def.holdDuration), 0, 1);
        this.totalProgress = 0.3 + progress * 0.4;

        if (this.phaseTime >= def.holdDuration) {
          this.activePhase = "returning";
          this.phaseTime = 0;
        }
        break;
      }
      case "returning": {
        const progress = MathPool.clamp(this.phaseTime / Math.max(0.01, def.returnDuration), 0, 1);
        blendWeight = 1.0 - MathPool.smoothstep(0, 1, progress);
        this.totalProgress = 0.7 + progress * 0.3;

        if (this.phaseTime >= def.returnDuration) {
          this.activePhase = "idle";
          this.phaseTime = 0;
          this.totalProgress = 1.0;
          this.cooldowns.set(def.name, def.cooldownDuration);
        }
        break;
      }
      default:
        break;
    }

    // Apply IK targets scaled by emotional intensity and gesture blend weight
    const effWeight = blendWeight * MathPool.clamp(intensity * 1.5, 0.2, 1.0);

    if (def.leftArmTarget) {
      this.ikController.setLeftArm(def.leftArmTarget, def.leftArmPole, effWeight);
    }
    if (def.rightArmTarget) {
      this.ikController.setRightArm(def.rightArmTarget, def.rightArmPole, effWeight);
    }

    // Apply Head and Torso offsets
    if (def.headOffset) {
      this.headOffset.x = def.headOffset.x * blendWeight;
      this.headOffset.y = def.headOffset.y * blendWeight;
      this.headOffset.z = def.headOffset.z * blendWeight;
    }
    if (def.torsoOffset) {
      this.torsoOffset.x = def.torsoOffset.x * blendWeight;
      this.torsoOffset.y = def.torsoOffset.y * blendWeight;
      this.torsoOffset.z = def.torsoOffset.z * blendWeight;
    }
    if (def.leftShoulderOffset) {
      this.leftShoulderOffset.z = def.leftShoulderOffset.z * blendWeight;
    }
    if (def.rightShoulderOffset) {
      this.rightShoulderOffset.z = def.rightShoulderOffset.z * blendWeight;
    }
  }
}
