import * as THREE from "three";

/**
 * Reusable scratch buffers for 60 FPS real-time animation math.
 * Ensures ZERO garbage collection allocations inside the requestAnimationFrame loop.
 */
export class MathPool {
  // Scratch Vectors
  public static readonly v0 = new THREE.Vector3();
  public static readonly v1 = new THREE.Vector3();
  public static readonly v2 = new THREE.Vector3();
  public static readonly v3 = new THREE.Vector3();
  public static readonly v4 = new THREE.Vector3();
  public static readonly v5 = new THREE.Vector3();
  public static readonly v6 = new THREE.Vector3();
  public static readonly v7 = new THREE.Vector3();

  // Scratch Quaternions
  public static readonly q0 = new THREE.Quaternion();
  public static readonly q1 = new THREE.Quaternion();
  public static readonly q2 = new THREE.Quaternion();
  public static readonly q3 = new THREE.Quaternion();
  public static readonly q4 = new THREE.Quaternion();

  // Scratch Matrices
  public static readonly m0 = new THREE.Matrix4();
  public static readonly m1 = new THREE.Matrix4();
  public static readonly m2 = new THREE.Matrix4();

  // Scratch Eulers
  public static readonly e0 = new THREE.Euler(0, 0, 0, "YXZ");
  public static readonly e1 = new THREE.Euler(0, 0, 0, "XYZ");
  public static readonly e2 = new THREE.Euler(0, 0, 0, "ZXY");

  /** Standard linear interpolation */
  public static lerp(a: number, b: number, t: number): number {
    return a + (b - a) * t;
  }

  /** Clamps value between min and max */
  public static clamp(val: number, min: number, max: number): number {
    return Math.max(min, Math.min(max, val));
  }

  /** Smooth Hermite interpolation between 0 and 1 */
  public static smoothstep(min: number, max: number, value: number): number {
    const x = MathPool.clamp((value - min) / (max - min), 0, 1);
    return x * x * (3 - 2 * x);
  }

  /** Smootherstep (Ken Perlin's 5th order polynomial) */
  public static smootherstep(min: number, max: number, value: number): number {
    const x = MathPool.clamp((value - min) / (max - min), 0, 1);
    return x * x * x * (x * (x * 6 - 15) + 10);
  }

  /** Frame-rate independent exponential decay / damping */
  public static damp(current: number, target: number, lambda: number, dt: number): number {
    return MathPool.lerp(current, target, 1 - Math.exp(-lambda * dt));
  }

  /** Frame-rate independent Vector3 damping */
  public static dampV3(current: THREE.Vector3, target: THREE.Vector3, lambda: number, dt: number): void {
    const t = 1 - Math.exp(-lambda * dt);
    current.lerp(target, t);
  }

  /** Frame-rate independent Quaternion damping (slerp) */
  public static dampQ(current: THREE.Quaternion, target: THREE.Quaternion, lambda: number, dt: number): void {
    const t = 1 - Math.exp(-lambda * dt);
    current.slerp(target, t);
  }

  /** Safe angle normalization (-PI to +PI) */
  public static normalizeAngle(angle: number): number {
    while (angle > Math.PI) angle -= 2 * Math.PI;
    while (angle < -Math.PI) angle += 2 * Math.PI;
    return angle;
  }
}
