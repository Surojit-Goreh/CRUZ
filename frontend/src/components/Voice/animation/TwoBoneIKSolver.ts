import * as THREE from "three";
import type { IKChain } from "./types";
import { MathPool } from "./MathPool";

/**
 * High-performance Analytical Two-Bone Inverse Kinematics Solver.
 * Solves exact joint angles in closed-form via the Law of Cosines with pole vector guidance.
 * Zero dynamic heap allocation per frame.
 */
export class TwoBoneIKSolver {
  /**
   * Solves a 2-bone IK chain (Root -> Mid -> Tip) toward a target in world space.
   */
  public static solve(chain: IKChain): void {
    if (chain.weight <= 0.001) return;

    const { root, mid, tip, target, poleTarget, isLeg } = chain;

    // Get world positions
    root.getWorldPosition(MathPool.v0);       // pRoot
    mid.getWorldPosition(MathPool.v1);        // pMid
    tip.getWorldPosition(MathPool.v2);        // pTip

    const pRoot = MathPool.v0;
    const pMid  = MathPool.v1;
    const pTip  = MathPool.v2;

    // Bone lengths (cache if not initialized)
    if (chain.length1 <= 0.001) chain.length1 = pRoot.distanceTo(pMid) || 0.25;
    if (chain.length2 <= 0.001) chain.length2 = pMid.distanceTo(pTip) || 0.25;

    const l1 = chain.length1;
    const l2 = chain.length2;

    // Direction to target
    MathPool.v3.subVectors(target, pRoot);     // dirTarget
    const rawDist = MathPool.v3.length();
    if (rawDist < 0.001) return;

    // Clamp distance to prevent hyperextension singularity
    const maxReach = (l1 + l2) * 0.999;
    const minReach = Math.max(0.01, Math.abs(l1 - l2) * 1.001);
    const d = MathPool.clamp(rawDist, minReach, maxReach);

    MathPool.v3.normalize();                  // unitDirTarget
    const unitTarget = MathPool.v3;

    // Law of Cosines: Root angle alpha
    const cosAlpha = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d);
    const alpha = Math.acos(MathPool.clamp(cosAlpha, -1, 1));

    // Vector to pole target from root
    MathPool.v4.subVectors(poleTarget, pRoot);
    if (MathPool.v4.lengthSq() < 0.001) {
      // Default pole fallback
      MathPool.v4.set(0, 0, isLeg ? 1 : -1);
    }
    MathPool.v4.normalize();

    // Normal to bending plane
    MathPool.v5.crossVectors(unitTarget, MathPool.v4);
    if (MathPool.v5.lengthSq() < 0.0001) {
      // Degenerate collinear pole, create arbitrary perpendicular normal
      MathPool.v5.crossVectors(unitTarget, THREE.Object3D.DEFAULT_UP);
      if (MathPool.v5.lengthSq() < 0.0001) {
        MathPool.v5.set(1, 0, 0);
      }
    }
    MathPool.v5.normalize();                  // planeNormal

    // Vector in bending plane perpendicular to unitTarget
    MathPool.v6.crossVectors(MathPool.v5, unitTarget).normalize(); // planePerp

    // Calculate desired world position for Mid joint
    // pMidDesired = pRoot + unitTarget * (l1 * cos(alpha)) + planePerp * (l1 * sin(alpha))
    MathPool.v7.copy(pRoot)
      .addScaledVector(unitTarget, l1 * Math.cos(alpha))
      .addScaledVector(MathPool.v6, l1 * Math.sin(alpha));
    const pMidDesired = MathPool.v7;

    // Save base FK rotations for blending
    MathPool.q4.copy(root.quaternion); // qRootBase
    const qMidBase = MathPool.q1.copy(mid.quaternion);

    // Apply rotation to Root bone
    // Calculate rotation from current (pMid - pRoot) to (pMidDesired - pRoot)
    const curRootToMid = MathPool.v1.subVectors(pMid, pRoot).normalize();
    const desRootToMid = MathPool.v2.subVectors(pMidDesired, pRoot).normalize();

    MathPool.q0.setFromUnitVectors(curRootToMid, desRootToMid);

    // Transform world delta rotation into root local space
    if (root.parent) {
      root.parent.getWorldQuaternion(MathPool.q2);
      MathPool.q3.copy(MathPool.q2).invert();
      const localDelta = MathPool.q2.copy(MathPool.q3).multiply(MathPool.q0).multiply(MathPool.q2);
      root.quaternion.premultiply(localDelta);
    } else {
      root.quaternion.premultiply(MathPool.q0);
    }

    if (chain.weight < 0.999) {
      root.quaternion.copy(MathPool.q4).slerp(root.quaternion, chain.weight);
    }
    root.updateMatrixWorld(true);

    // Apply rotation to Mid bone
    // Calculate rotation from (pTip - pMid) to (target - pMidDesired)
    mid.getWorldPosition(MathPool.v0);
    tip.getWorldPosition(MathPool.v1);
    const curMidToTip = MathPool.v1.sub(MathPool.v0).normalize();
    const desMidToTip = MathPool.v2.subVectors(target, pMidDesired).normalize();

    MathPool.q0.setFromUnitVectors(curMidToTip, desMidToTip);

    if (mid.parent) {
      mid.parent.getWorldQuaternion(MathPool.q2);
      MathPool.q3.copy(MathPool.q2).invert();
      const localDelta = MathPool.q2.copy(MathPool.q3).multiply(MathPool.q0).multiply(MathPool.q2);
      mid.quaternion.premultiply(localDelta);
    } else {
      mid.quaternion.premultiply(MathPool.q0);
    }

    if (chain.weight < 0.999) {
      mid.quaternion.copy(qMidBase).slerp(mid.quaternion, chain.weight);
    }
    mid.updateMatrixWorld(true);
  }
}
