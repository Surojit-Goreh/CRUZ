import * as THREE from "three";

export type VoiceState = "idle" | "listening" | "transcribing" | "thinking" | "speaking";

export type EmotionType =
  | "neutral"
  | "happy"
  | "sad"
  | "excited"
  | "thinking"
  | "confused"
  | "surprised";

export type GestureType =
  | "idle"
  | "talk"
  | "explain"
  | "greeting"
  | "point"
  | "shrug"
  | "thinking"
  | "excited"
  | "agree_nod"
  | "disagree_shake"
  | "confused";

export type GesturePhase =
  | "idle"
  | "preparing"
  | "performing"
  | "holding"
  | "returning"
  | "cooldown";

export interface GestureDefinition {
  name: GestureType;
  duration: number; // total target duration in seconds
  prepDuration: number;
  holdDuration: number;
  returnDuration: number;
  cooldownDuration: number;
  priority: number; // higher overrides lower
  leftArmTarget?: THREE.Vector3;
  rightArmTarget?: THREE.Vector3;
  leftArmPole?: THREE.Vector3;
  rightArmPole?: THREE.Vector3;
  leftHandRotation?: THREE.Euler;
  rightHandRotation?: THREE.Euler;
  headOffset?: THREE.Euler;
  torsoOffset?: THREE.Euler;
  leftShoulderOffset?: THREE.Euler;
  rightShoulderOffset?: THREE.Euler;
  emotionalEnergy?: number;
}

export interface IKChain {
  root: THREE.Object3D;
  mid: THREE.Object3D;
  tip: THREE.Object3D;
  target: THREE.Vector3;
  poleTarget: THREE.Vector3;
  poleAngle?: number;
  length1: number;
  length2: number;
  weight: number; // 0 (pure FK) to 1 (pure IK)
  isLeg?: boolean;
}

export interface AnimationDebugInfo {
  state: VoiceState;
  emotion: EmotionType;
  gesture: GestureType;
  gesturePhase: GesturePhase;
  gestureProgress: number; // 0.0 - 1.0
  gestureIntensity: number;
  weightLeg: "left" | "center" | "right";
  ikActive: boolean;
  fps: number;
}
