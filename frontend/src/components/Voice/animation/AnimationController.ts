import { VRM } from "@pixiv/three-vrm";
import type { VoiceState, EmotionType, GestureType, AnimationDebugInfo } from "./types";
import { BodyController } from "./BodyController";
import { IKController } from "./IKController";
import { FaceController } from "./FaceController";
import { GestureManager } from "./GestureManager";
import { EmotionManager } from "./EmotionManager";
import { MathPool } from "./MathPool";
import { JointConstraints } from "./JointConstraints";

export class AnimationController {
  private vrm: VRM;

  public body: BodyController;
  public ik: IKController;
  public face: FaceController;
  public gestures: GestureManager;
  public emotions: EmotionManager;

  public voiceState: VoiceState = "idle";
  private elapsedTime = 0;
  private frameCount = 0;
  private fpsTimer = 0;
  private currentFps = 60;

  constructor(vrm: VRM) {
    this.vrm = vrm;
    this.body = new BodyController(vrm);
    this.ik = new IKController(vrm);
    this.face = new FaceController(vrm);
    this.gestures = new GestureManager(this.ik);
    this.emotions = new EmotionManager();

    this.applyInitialRestPose();
  }

  /**
   * Sets natural, relaxed resting humanoid posture with open arms and relaxed curved fingers.
   */
  private applyInitialRestPose(): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    const lUA = h.getNormalizedBoneNode("leftUpperArm");
    const rUA = h.getNormalizedBoneNode("rightUpperArm");
    const lLA = h.getNormalizedBoneNode("leftLowerArm");
    const rLA = h.getNormalizedBoneNode("rightLowerArm");
    const lHand = h.getNormalizedBoneNode("leftHand");
    const rHand = h.getNormalizedBoneNode("rightHand");
    const spine = h.getNormalizedBoneNode("spine");

    // Simple, clean natural upper arms resting at sides
    if (lUA) { lUA.rotation.set(0.04, -0.02, 1.18); }
    if (rUA) { rUA.rotation.set(0.04, 0.02, -1.18); }
    // Gentle natural elbow relaxation
    if (lLA) { lLA.rotation.set(0.06, 0.12, 0.0); }
    if (rLA) { rLA.rotation.set(0.06, -0.12, 0.0); }
    // Simple relaxed natural hands
    if (lHand) { lHand.rotation.set(0.0, 0.04, 0.02); }
    if (rHand) { rHand.rotation.set(0.0, -0.04, -0.02); }
    if (spine) { spine.rotation.set(0.02, 0, 0); }

    // Natural expressive relaxed finger pose
    this.poseRelaxedFingers();
  }

  /**
   * Poses fingers with natural, gentle curves to prevent stiff hands.
   */
  private poseRelaxedFingers(): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    const fingerBones = [
      // Left Hand (Simple relaxed natural finger curves)
      { name: "leftThumbProximal", rot: [0.08, -0.08, -0.12] },
      { name: "leftThumbDistal", rot: [0.05, 0, -0.06] },
      { name: "leftIndexProximal", rot: [0.12, 0, 0.02] },
      { name: "leftIndexIntermediate", rot: [0.14, 0, 0] },
      { name: "leftMiddleProximal", rot: [0.14, 0, 0.01] },
      { name: "leftMiddleIntermediate", rot: [0.16, 0, 0] },
      { name: "leftRingProximal", rot: [0.14, 0, -0.01] },
      { name: "leftRingIntermediate", rot: [0.16, 0, 0] },
      { name: "leftLittleProximal", rot: [0.14, 0, -0.02] },
      { name: "leftLittleIntermediate", rot: [0.16, 0, 0] },
      // Right Hand (Simple relaxed natural finger curves)
      { name: "rightThumbProximal", rot: [0.08, 0.08, 0.12] },
      { name: "rightThumbDistal", rot: [0.05, 0, 0.06] },
      { name: "rightIndexProximal", rot: [0.12, 0, -0.02] },
      { name: "rightIndexIntermediate", rot: [0.14, 0, 0] },
      { name: "rightMiddleProximal", rot: [0.14, 0, -0.01] },
      { name: "rightMiddleIntermediate", rot: [0.16, 0, 0] },
      { name: "rightRingProximal", rot: [0.14, 0, 0.01] },
      { name: "rightRingIntermediate", rot: [0.16, 0, 0] },
      { name: "rightLittleProximal", rot: [0.14, 0, 0.02] },
      { name: "rightLittleIntermediate", rot: [0.16, 0, 0] },
    ] as const;

    for (const f of fingerBones) {
      const node = h.getNormalizedBoneNode(f.name as any);
      if (node) {
        node.rotation.set(f.rot[0], f.rot[1], f.rot[2]);
      }
    }
  }

  public setVoiceState(state: VoiceState): void {
    if (this.voiceState !== state) {
      this.voiceState = state;
      if (state === "speaking") {
        // Trigger an initial greeting or conversational gesture on speech start
        if (this.gestures.activePhase === "idle") {
          this.gestures.trigger("talk");
        }
      } else if (state === "thinking") {
        this.gestures.trigger("thinking");
      }
    }
  }

  public setEmotion(emotion: EmotionType): void {
    this.emotions.setEmotion(emotion);
  }

  public setMouse(nx: number, ny: number): void {
    this.face.setMouse(nx, ny);
  }

  public triggerGesture(gesture: GestureType, force = false): boolean {
    return this.gestures.trigger(gesture, force);
  }

  /**
   * Applies simple natural resting FK arm movements with gentle breathing sway when IK is not dominant.
   */
  private updateFKArms(dt: number): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    const t = this.elapsedTime;
    const lUA = h.getNormalizedBoneNode("leftUpperArm");
    const rUA = h.getNormalizedBoneNode("rightUpperArm");
    const lLA = h.getNormalizedBoneNode("leftLowerArm");
    const rLA = h.getNormalizedBoneNode("rightLowerArm");
    const lHand = h.getNormalizedBoneNode("leftHand");
    const rHand = h.getNormalizedBoneNode("rightHand");

    // Clean, natural resting arms at sides with gentle sway
    if (lUA) {
      const lUaZ = 1.18 + Math.sin(t * 0.4) * 0.015;
      lUA.rotation.z = MathPool.damp(lUA.rotation.z, lUaZ, 5.0, dt);
      lUA.rotation.x = MathPool.damp(lUA.rotation.x, 0.04, 5.0, dt);
      lUA.rotation.y = MathPool.damp(lUA.rotation.y, -0.02, 5.0, dt);
      JointConstraints.clampBoneRotation(lUA, JointConstraints.LeftUpperArm);
    }

    if (lLA) {
      lLA.rotation.y = MathPool.damp(lLA.rotation.y, 0.12, 5.0, dt);
      lLA.rotation.x = MathPool.damp(lLA.rotation.x, 0.06, 5.0, dt);
      lLA.rotation.z = MathPool.damp(lLA.rotation.z, 0.0, 5.0, dt);
      JointConstraints.clampBoneRotation(lLA, JointConstraints.LeftLowerArm);
    }

    if (rUA) {
      const rUaZ = -1.18 - Math.sin(t * 0.4) * 0.015;
      rUA.rotation.z = MathPool.damp(rUA.rotation.z, rUaZ, 5.0, dt);
      rUA.rotation.x = MathPool.damp(rUA.rotation.x, 0.04, 5.0, dt);
      rUA.rotation.y = MathPool.damp(rUA.rotation.y, 0.02, 5.0, dt);
      JointConstraints.clampBoneRotation(rUA, JointConstraints.RightUpperArm);
    }

    if (rLA) {
      rLA.rotation.y = MathPool.damp(rLA.rotation.y, -0.12, 5.0, dt);
      rLA.rotation.x = MathPool.damp(rLA.rotation.x, 0.06, 5.0, dt);
      rLA.rotation.z = MathPool.damp(rLA.rotation.z, 0.0, 5.0, dt);
      JointConstraints.clampBoneRotation(rLA, JointConstraints.RightLowerArm);
    }

    if (lHand) {
      lHand.rotation.x = MathPool.damp(lHand.rotation.x, 0.0, 5.0, dt);
      lHand.rotation.y = MathPool.damp(lHand.rotation.y, 0.04, 5.0, dt);
      lHand.rotation.z = MathPool.damp(lHand.rotation.z, 0.02, 5.0, dt);
    }
    if (rHand) {
      rHand.rotation.x = MathPool.damp(rHand.rotation.x, 0.0, 5.0, dt);
      rHand.rotation.y = MathPool.damp(rHand.rotation.y, -0.04, 5.0, dt);
      rHand.rotation.z = MathPool.damp(rHand.rotation.z, -0.02, 5.0, dt);
    }
  }

  /**
   * Master frame update pass (executes at 60 FPS in requestAnimationFrame).
   */
  public update(dt: number): void {
    // Clamp delta time to avoid huge simulation jumps after background tabs
    const clampedDt = MathPool.clamp(dt, 0.001, 0.1);
    this.elapsedTime += clampedDt;

    // Track FPS
    this.frameCount++;
    this.fpsTimer += clampedDt;
    if (this.fpsTimer >= 0.5) {
      this.currentFps = Math.round((this.frameCount / this.fpsTimer));
      this.frameCount = 0;
      this.fpsTimer = 0;
    }

    const state = this.voiceState;
    const emotion = this.emotions.currentEmotion;
    const intensity = this.emotions.gestureIntensity;

    // 1. Update Emotions
    this.emotions.update(clampedDt, state);

    // 2. Update Gestures
    this.gestures.update(clampedDt, state, emotion, intensity);

    // 3. Update Body (Spine, Breathing, Weight Shifts, Balance)
    this.body.leftShoulderY = this.gestures.leftShoulderOffset.z;
    this.body.rightShoulderY = this.gestures.rightShoulderOffset.z;
    this.body.bodyLeanForward = this.gestures.torsoOffset.x;
    this.body.update(clampedDt, state, emotion, intensity);

    // 4. Update Face (Gaze, Blinking, Lip-Sync, Expressions)
    this.face.headOffset.copy(this.gestures.headOffset);
    if (state === "speaking") {
      this.face.headNodAngle = Math.sin(this.elapsedTime * 3.6) * 0.065 + Math.sin(this.elapsedTime * 1.6) * 0.035;
    } else {
      this.face.headNodAngle = 0;
    }
    this.face.update(clampedDt, state, emotion);

    // 5. Apply Resting FK to Arms
    this.updateFKArms(clampedDt);

    // 6. Solve IK Chains
    this.ik.update(clampedDt);

    // 7. Update Spring Bones & Expressions
    this.vrm.update(clampedDt);
  }

  /**
   * Retrieves live diagnostic info for the debug overlay HUD.
   */
  public getDebugInfo(): AnimationDebugInfo {
    return {
      state: this.voiceState,
      emotion: this.emotions.currentEmotion,
      gesture: this.gestures.activeGesture,
      gesturePhase: this.gestures.activePhase,
      gestureProgress: Math.round(this.gestures.totalProgress * 100) / 100,
      gestureIntensity: Math.round(this.emotions.gestureIntensity * 100) / 100,
      weightLeg: this.body.weightLeg,
      ikActive: this.ik.leftArmWeight > 0.05 || this.ik.rightArmWeight > 0.05,
      fps: this.currentFps,
    };
  }
}
