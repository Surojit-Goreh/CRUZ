import { VRM } from "@pixiv/three-vrm";
import type { VoiceState, EmotionType } from "./types";
import { MathPool } from "./MathPool";
import { JointConstraints } from "./JointConstraints";

export class BodyController {
  private vrm: VRM;

  // Time & Oscillation
  private swayTime = 0;
  private breatheTime = 0;

  // Weight Shift State
  public weightLeg: "left" | "center" | "right" = "center";
  private weightShiftTarget = 0; // -1 (left), 0 (center), +1 (right)
  private currentWeightShift = 0;
  private weightShiftTimer = 6.0;

  // Posture modifiers
  public postureEnergy = 1.0;
  public bodyLeanForward = 0.0;
  public bodyTiltLateral = 0.0;

  // Shoulder offset (procedural)
  public leftShoulderY = 0;
  public rightShoulderY = 0;

  constructor(vrm: VRM) {
    this.vrm = vrm;
  }

  /**
   * Updates weight shift timing and target leg selection.
   */
  private updateWeightShift(dt: number, state: VoiceState): void {
    this.weightShiftTimer -= dt;
    if (this.weightShiftTimer <= 0) {
      // Pick next weight leg randomly with center bias
      const r = Math.random();
      if (this.weightLeg === "center") {
        this.weightLeg = r > 0.5 ? "left" : "right";
      } else {
        this.weightLeg = r > 0.6 ? (this.weightLeg === "left" ? "right" : "left") : "center";
      }

      this.weightShiftTarget = this.weightLeg === "left" ? -0.85 : this.weightLeg === "right" ? 0.85 : 0.0;
      this.weightShiftTimer = 5.5 + Math.random() * 6.5; // Shift every 5.5 - 12.0 seconds
    }

    // Smooth weight transition
    const speed = state === "speaking" ? 1.8 : 1.2;
    this.currentWeightShift = MathPool.damp(this.currentWeightShift, this.weightShiftTarget, speed, dt);
  }

  /**
   * Main procedural body update loop.
   */
  public update(dt: number, state: VoiceState, emotion: EmotionType, intensity: number): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    this.swayTime += dt;
    this.breatheTime += dt;
    this.updateWeightShift(dt, state);

    // ── Respiration Rate & Amplitude Modulation ─────────────────────────
    const isSpeaking = state === "speaking";
    const isExcited = emotion === "excited";
    const breatheSpeed = isSpeaking ? 2.8 : isExcited ? 2.2 : 0.65;
    const breatheAmp = (isSpeaking ? 0.024 : 0.012) * intensity;
    const breathe = Math.sin(this.breatheTime * breatheSpeed) * breatheAmp;

    // ── Distributed Multi-Joint Bending & Spine Kinematics ──────────────
    const spine = h.getNormalizedBoneNode("spine");
    const chest = h.getNormalizedBoneNode("chest");
    const hips = h.getNormalizedBoneNode("hips");

    // Base sway
    const swayX = Math.sin(this.swayTime * 0.3) * 0.008;
    const swayZ = Math.cos(this.swayTime * 0.25) * 0.006;

    if (spine) {
      const targetSpineX = 0.018 + breathe * 0.7 + this.bodyLeanForward * 0.45 + swayX;
      const targetSpineY = this.currentWeightShift * 0.015;
      const targetSpineZ = -this.currentWeightShift * 0.025 + this.bodyTiltLateral * 0.4 + swayZ;

      spine.rotation.x = MathPool.damp(spine.rotation.x, targetSpineX, 6.0, dt);
      spine.rotation.y = MathPool.damp(spine.rotation.y, targetSpineY, 6.0, dt);
      spine.rotation.z = MathPool.damp(spine.rotation.z, targetSpineZ, 6.0, dt);
      JointConstraints.clampBoneRotation(spine, JointConstraints.Spine);
    }

    if (chest) {
      const targetChestX = breathe * 0.5 + this.bodyLeanForward * 0.35;
      const targetChestY = -this.currentWeightShift * 0.01;
      const targetChestZ = -this.currentWeightShift * 0.015 + this.bodyTiltLateral * 0.3;

      chest.rotation.x = MathPool.damp(chest.rotation.x, targetChestX, 6.0, dt);
      chest.rotation.y = MathPool.damp(chest.rotation.y, targetChestY, 6.0, dt);
      chest.rotation.z = MathPool.damp(chest.rotation.z, targetChestZ, 6.0, dt);
      JointConstraints.clampBoneRotation(chest, JointConstraints.Chest);
    }

    // ── Hips & Pelvic Weight Shift (Contrapposto) ────────────────────────
    if (hips) {
      // Center of mass balance compensation
      const targetHipsX = -this.bodyLeanForward * 0.18 + breathe * 0.2;
      const targetHipsY = this.currentWeightShift * 0.035;
      const targetHipsZ = this.currentWeightShift * 0.045; // Pelvic lateral tilt

      hips.rotation.x = MathPool.damp(hips.rotation.x, targetHipsX, 5.0, dt);
      hips.rotation.y = MathPool.damp(hips.rotation.y, targetHipsY, 5.0, dt);
      hips.rotation.z = MathPool.damp(hips.rotation.z, targetHipsZ, 5.0, dt);
      JointConstraints.clampBoneRotation(hips, JointConstraints.Hips);
    }

    // ── Leg Contrapposto Stance & Knee Compensation ─────────────────────
    const lUL = h.getNormalizedBoneNode("leftUpperLeg");
    const rUL = h.getNormalizedBoneNode("rightUpperLeg");
    const lLL = h.getNormalizedBoneNode("leftLowerLeg");
    const rLL = h.getNormalizedBoneNode("rightLowerLeg");
    const lFoot = h.getNormalizedBoneNode("leftFoot");
    const rFoot = h.getNormalizedBoneNode("rightFoot");

    // Weight bearing leg stays straight, relaxed leg has slight knee flexion
    const leftWeightRatio = MathPool.clamp(-this.currentWeightShift, -1, 1);
    const rightWeightRatio = MathPool.clamp(this.currentWeightShift, -1, 1);

    // ── Wide, Confident Open Leg Stance ─────────────────────────────
    // Note: In VRM normalized coordinates, negative Z opens the left leg OUTWARD,
    // and positive Z opens the right leg OUTWARD.
    if (lUL) {
      const targetLULz = -0.22 - leftWeightRatio * 0.04; // Open left leg outward
      const targetLULy = 0.08;  // Natural outward toe flare
      const targetLULx = -0.02 + (leftWeightRatio < 0 ? 0.04 : 0.0);
      lUL.rotation.z = MathPool.damp(lUL.rotation.z, targetLULz, 5.0, dt);
      lUL.rotation.y = MathPool.damp(lUL.rotation.y, targetLULy, 5.0, dt);
      lUL.rotation.x = MathPool.damp(lUL.rotation.x, targetLULx, 5.0, dt);
      JointConstraints.clampBoneRotation(lUL, JointConstraints.LeftUpperLeg);
    }

    if (rUL) {
      const targetRULz = 0.22 + rightWeightRatio * 0.04; // Open right leg outward
      const targetRULy = -0.08; // Natural outward toe flare
      const targetRULx = -0.02 + (rightWeightRatio < 0 ? 0.04 : 0.0);
      rUL.rotation.z = MathPool.damp(rUL.rotation.z, targetRULz, 5.0, dt);
      rUL.rotation.y = MathPool.damp(rUL.rotation.y, targetRULy, 5.0, dt);
      rUL.rotation.x = MathPool.damp(rUL.rotation.x, targetRULx, 5.0, dt);
      JointConstraints.clampBoneRotation(rUL, JointConstraints.RightUpperLeg);
    }

    if (lLL) {
      const targetLLLx = leftWeightRatio < 0 ? 0.06 : 0.03; // Relaxed knees
      lLL.rotation.x = MathPool.damp(lLL.rotation.x, targetLLLx, 5.0, dt);
      JointConstraints.clampBoneRotation(lLL, JointConstraints.LeftLowerLeg);
    }

    if (rLL) {
      const targetRLLx = rightWeightRatio < 0 ? 0.06 : 0.03;
      rLL.rotation.x = MathPool.damp(rLL.rotation.x, targetRLLx, 5.0, dt);
      JointConstraints.clampBoneRotation(rLL, JointConstraints.RightLowerLeg);
    }

    // Ground feet firmly flat on the floor with matching counter-tilt
    if (lFoot) {
      lFoot.rotation.z = MathPool.damp(lFoot.rotation.z, 0.20, 5.0, dt);
      lFoot.rotation.y = MathPool.damp(lFoot.rotation.y, 0.08, 5.0, dt);
      lFoot.rotation.x = MathPool.damp(lFoot.rotation.x, 0.02, 5.0, dt);
    }
    if (rFoot) {
      rFoot.rotation.z = MathPool.damp(rFoot.rotation.z, -0.20, 5.0, dt);
      rFoot.rotation.y = MathPool.damp(rFoot.rotation.y, -0.08, 5.0, dt);
      rFoot.rotation.x = MathPool.damp(rFoot.rotation.x, 0.02, 5.0, dt);
    }

    // ── Shoulders & Clavicles ───────────────────────────────────────────
    const lShldr = h.getNormalizedBoneNode("leftShoulder");
    const rShldr = h.getNormalizedBoneNode("rightShoulder");

    const shldrBreath = breathe * 0.35;
    if (lShldr) {
      lShldr.rotation.z = MathPool.damp(lShldr.rotation.z, 0.035 + shldrBreath + this.leftShoulderY, 6.0, dt);
    }
    if (rShldr) {
      rShldr.rotation.z = MathPool.damp(rShldr.rotation.z, -0.035 - shldrBreath - this.rightShoulderY, 6.0, dt);
    }
  }
}
