import * as THREE from "three";
import { VRM } from "@pixiv/three-vrm";
import type { IKChain } from "./types";
import { TwoBoneIKSolver } from "./TwoBoneIKSolver";
import { MathPool } from "./MathPool";

export class IKController {
  private vrm: VRM;

  public leftArmChain: IKChain | null = null;
  public rightArmChain: IKChain | null = null;
  public leftLegChain: IKChain | null = null;
  public rightLegChain: IKChain | null = null;

  // Active Target Positions (World Space)
  public leftHandTarget = new THREE.Vector3();
  public rightHandTarget = new THREE.Vector3();
  public leftElbowPole = new THREE.Vector3();
  public rightElbowPole = new THREE.Vector3();

  // Resting Default Offsets (Local to Root/Hips)
  public leftHandRest = new THREE.Vector3(-0.24, 0.76, 0.02);
  public rightHandRest = new THREE.Vector3(0.24, 0.76, 0.02);
  public leftElbowRest = new THREE.Vector3(-0.35, 0.95, -0.25);
  public rightElbowRest = new THREE.Vector3(0.35, 0.95, -0.25);

  // Blend Weights
  public leftArmWeight = 0;
  public rightArmWeight = 0;
  public targetLeftArmWeight = 0;
  public targetRightArmWeight = 0;

  constructor(vrm: VRM) {
    this.vrm = vrm;
    this.initChains();
  }

  private initChains(): void {
    const h = this.vrm.humanoid;
    if (!h) return;

    // Left Arm Chain
    const lUA = h.getNormalizedBoneNode("leftUpperArm");
    const lLA = h.getNormalizedBoneNode("leftLowerArm");
    const lHand = h.getNormalizedBoneNode("leftHand");

    if (lUA && lLA && lHand) {
      this.leftArmChain = {
        root: lUA,
        mid: lLA,
        tip: lHand,
        target: this.leftHandTarget,
        poleTarget: this.leftElbowPole,
        length1: 0.24,
        length2: 0.22,
        weight: 0,
        isLeg: false,
      };
    }

    // Right Arm Chain
    const rUA = h.getNormalizedBoneNode("rightUpperArm");
    const rLA = h.getNormalizedBoneNode("rightLowerArm");
    const rHand = h.getNormalizedBoneNode("rightHand");

    if (rUA && rLA && rHand) {
      this.rightArmChain = {
        root: rUA,
        mid: rLA,
        tip: rHand,
        target: this.rightHandTarget,
        poleTarget: this.rightElbowPole,
        length1: 0.24,
        length2: 0.22,
        weight: 0,
        isLeg: false,
      };
    }

    // Leg Chains
    const lUL = h.getNormalizedBoneNode("leftUpperLeg");
    const lLL = h.getNormalizedBoneNode("leftLowerLeg");
    const lFoot = h.getNormalizedBoneNode("leftFoot");

    if (lUL && lLL && lFoot) {
      this.leftLegChain = {
        root: lUL,
        mid: lLL,
        tip: lFoot,
        target: new THREE.Vector3(-0.10, 0.05, 0.0),
        poleTarget: new THREE.Vector3(-0.10, 0.40, 0.40),
        length1: 0.38,
        length2: 0.38,
        weight: 0,
        isLeg: true,
      };
    }

    const rUL = h.getNormalizedBoneNode("rightUpperLeg");
    const rLL = h.getNormalizedBoneNode("rightLowerLeg");
    const rFoot = h.getNormalizedBoneNode("rightFoot");

    if (rUL && rLL && rFoot) {
      this.rightLegChain = {
        root: rUL,
        mid: rLL,
        tip: rFoot,
        target: new THREE.Vector3(0.10, 0.05, 0.0),
        poleTarget: new THREE.Vector3(0.10, 0.40, 0.40),
        length1: 0.38,
        length2: 0.38,
        weight: 0,
        isLeg: true,
      };
    }
  }

  /**
   * Set target position and pole for left arm IK.
   */
  public setLeftArm(target: THREE.Vector3, pole?: THREE.Vector3, weight = 1): void {
    this.leftHandTarget.copy(target);
    if (pole) this.leftElbowPole.copy(pole);
    else this.leftElbowPole.set(target.x - 0.2, target.y + 0.1, -0.3);
    this.targetLeftArmWeight = weight;
  }

  /**
   * Set target position and pole for right arm IK.
   */
  public setRightArm(target: THREE.Vector3, pole?: THREE.Vector3, weight = 1): void {
    this.rightHandTarget.copy(target);
    if (pole) this.rightElbowPole.copy(pole);
    else this.rightElbowPole.set(target.x + 0.2, target.y + 0.1, -0.3);
    this.targetRightArmWeight = weight;
  }

  /**
   * Releases arm IK back toward procedural FK posture.
   */
  public releaseArms(): void {
    this.targetLeftArmWeight = 0;
    this.targetRightArmWeight = 0;
  }

  /**
   * Updates solver weights and executes IK passes.
   */
  public update(dt: number): void {
    // Smooth weight transitions
    this.leftArmWeight = MathPool.damp(this.leftArmWeight, this.targetLeftArmWeight, 8.0, dt);
    this.rightArmWeight = MathPool.damp(this.rightArmWeight, this.targetRightArmWeight, 8.0, dt);

    if (this.leftArmChain) {
      this.leftArmChain.weight = this.leftArmWeight;
      if (this.leftArmWeight > 0.01) {
        TwoBoneIKSolver.solve(this.leftArmChain);
      }
    }

    if (this.rightArmChain) {
      this.rightArmChain.weight = this.rightArmWeight;
      if (this.rightArmWeight > 0.01) {
        TwoBoneIKSolver.solve(this.rightArmChain);
      }
    }
  }
}
