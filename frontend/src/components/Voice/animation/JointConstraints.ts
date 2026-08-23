import * as THREE from "three";
import { MathPool } from "./MathPool";

export interface AngleLimit {
  min: number;
  max: number;
}

export interface JointLimit {
  x: AngleLimit;
  y: AngleLimit;
  z: AngleLimit;
}

/**
 * Anatomical joint constraints to enforce natural human biomechanics
 * and eliminate broken poses, backwards elbows, and hyperextended knees.
 */
export class JointConstraints {
  public static readonly Head: JointLimit = {
    x: { min: -0.42, max: 0.35 }, // nod down (+) / look up (-)
    y: { min: -0.65, max: 0.65 }, // look left / right
    z: { min: -0.28, max: 0.28 }, // head tilt
  };

  public static readonly Neck: JointLimit = {
    x: { min: -0.25, max: 0.20 },
    y: { min: -0.35, max: 0.35 },
    z: { min: -0.15, max: 0.15 },
  };

  public static readonly Spine: JointLimit = {
    x: { min: -0.10, max: 0.20 }, // lean back / forward
    y: { min: -0.18, max: 0.18 }, // torso twist
    z: { min: -0.12, max: 0.12 }, // side bend
  };

  public static readonly Chest: JointLimit = {
    x: { min: -0.08, max: 0.15 },
    y: { min: -0.15, max: 0.15 },
    z: { min: -0.10, max: 0.10 },
  };

  public static readonly Hips: JointLimit = {
    x: { min: -0.08, max: 0.12 },
    y: { min: -0.15, max: 0.15 },
    z: { min: -0.08, max: 0.08 }, // weight shift tilt
  };

  public static readonly LeftUpperArm: JointLimit = {
    x: { min: -1.20, max: 1.60 },
    y: { min: -1.10, max: 1.10 },
    z: { min: -0.30, max: 1.80 },
  };

  public static readonly RightUpperArm: JointLimit = {
    x: { min: -1.20, max: 1.60 },
    y: { min: -1.10, max: 1.10 },
    z: { min: -1.80, max: 0.30 },
  };

  public static readonly LeftLowerArm: JointLimit = {
    x: { min: -1.20, max: 1.20 }, // Forearm forward/backward bend
    y: { min: -0.30, max: 2.30 }, // Inward elbow angle
    z: { min: -0.80, max: 0.80 },
  };

  public static readonly RightLowerArm: JointLimit = {
    x: { min: -1.20, max: 1.20 }, // Forearm forward/backward bend
    y: { min: -2.30, max: 0.30 }, // Inward elbow angle
    z: { min: -0.80, max: 0.80 },
  };

  public static readonly LeftHand: JointLimit = {
    x: { min: -0.60, max: 0.60 },
    y: { min: -0.50, max: 0.50 },
    z: { min: -0.45, max: 0.45 },
  };

  public static readonly RightHand: JointLimit = {
    x: { min: -0.60, max: 0.60 },
    y: { min: -0.50, max: 0.50 },
    z: { min: -0.45, max: 0.45 },
  };

  public static readonly LeftUpperLeg: JointLimit = {
    x: { min: -0.50, max: 0.80 },
    y: { min: -0.40, max: 0.40 },
    z: { min: -0.50, max: 0.30 }, // Allows wide open confident stance
  };

  public static readonly RightUpperLeg: JointLimit = {
    x: { min: -0.50, max: 0.80 },
    y: { min: -0.40, max: 0.40 },
    z: { min: -0.30, max: 0.50 }, // Allows wide open confident stance
  };

  public static readonly LeftLowerLeg: JointLimit = {
    x: { min: -0.05, max: 1.60 }, // Knee flexion
    y: { min: -0.10, max: 0.10 },
    z: { min: -0.10, max: 0.10 },
  };

  public static readonly RightLowerLeg: JointLimit = {
    x: { min: -0.05, max: 1.60 }, // Knee flexion
    y: { min: -0.10, max: 0.10 },
    z: { min: -0.10, max: 0.10 },
  };

  /**
   * Applies clamping constraints to a bone's Euler rotation in-place.
   */
  public static clampEuler(euler: THREE.Euler, limit: JointLimit): void {
    euler.x = MathPool.clamp(euler.x, limit.x.min, limit.x.max);
    euler.y = MathPool.clamp(euler.y, limit.y.min, limit.y.max);
    euler.z = MathPool.clamp(euler.z, limit.z.min, limit.z.max);
  }

  /**
   * Applies constraints to an Object3D's rotation.
   */
  public static clampBoneRotation(bone: THREE.Object3D, limit: JointLimit): void {
    bone.rotation.x = MathPool.clamp(bone.rotation.x, limit.x.min, limit.x.max);
    bone.rotation.y = MathPool.clamp(bone.rotation.y, limit.y.min, limit.y.max);
    bone.rotation.z = MathPool.clamp(bone.rotation.z, limit.z.min, limit.z.max);
  }
}
