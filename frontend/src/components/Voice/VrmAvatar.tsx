import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { VRMLoaderPlugin, VRM, VRMUtils } from "@pixiv/three-vrm";
import "./VrmAvatar.css";

export type VoiceState = "listening" | "transcribing" | "thinking" | "speaking" | "idle";

interface Props {
  voiceState: VoiceState;
  connected: boolean;
  onStartVoice: () => void;
  onStopVoice?: () => void;
}

function lerp(a: number, b: number, t: number) { return a + (b - a) * t; }
function clamp(v: number, lo: number, hi: number) { return Math.max(lo, Math.min(hi, v)); }

export default function VrmAvatar({
  voiceState,
  connected,
  onStartVoice,
  onStopVoice,
}: Props) {
  const mountRef    = useRef<HTMLDivElement | null>(null);
  const vrmRef      = useRef<VRM | null>(null);
  const rafRef      = useRef<number | null>(null);
  const voiceRef    = useRef<VoiceState>(voiceState);
  const connectedRef = useRef(connected);
  const onStartVoiceRef = useRef(onStartVoice);
  const onStopVoiceRef = useRef(onStopVoice);

  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");

  // Mouse tracking (-1..1) for head gaze
  const mouseNX = useRef(0);
  const mouseNY = useRef(0);

  // Orbit controls
  const orbitRef = useRef<OrbitControls | null>(null);

  // Click vs drag
  const pointerDownPos = useRef({ x: 0, y: 0 });
  const isDragging     = useRef(false);

  // Blink
  const blinkVal    = useRef(0);
  const blinkTarget = useRef(0);
  const blinkTimer  = useRef(3.0);

  // Time refs
  const swayT = useRef(0);
  const lipT  = useRef(0);

  // Light color lerp
  const keyR = useRef(1.0), keyG = useRef(0.85), keyB = useRef(0.75);
  const rimR = useRef(0.3), rimG = useRef(0.5),  rimB = useRef(1.0);

  useEffect(() => { voiceRef.current = voiceState; }, [voiceState]);
  useEffect(() => { connectedRef.current = connected; }, [connected]);
  useEffect(() => { onStartVoiceRef.current = onStartVoice; }, [onStartVoice]);
  useEffect(() => { onStopVoiceRef.current = onStopVoice; }, [onStopVoice]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    setLoadState("loading");

    // ── Renderer — Calibrated for rich contrast without blowing out face ──
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping      = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.78; // Balanced exposure to prevent white-washed face
    mount.appendChild(renderer.domElement);

    // ── Scene ────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0812, 0.05);

    // ── Camera — Framed head-to-shoes ────────────────────────
    const camera = new THREE.PerspectiveCamera(
      28,
      mount.clientWidth / mount.clientHeight,
      0.1, 50
    );
    camera.position.set(0.08, 0.90, 2.9);
    camera.lookAt(0, 0.80, 0);

    // ── Orbit Controls — Smooth 360° Rotation ONLY (No Zoom) ──
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping    = true;
    orbit.dampingFactor    = 0.08;
    orbit.enablePan        = false;
    orbit.enableZoom       = false;
    orbit.minPolarAngle    = Math.PI * 0.12;
    orbit.maxPolarAngle    = Math.PI * 0.82;
    orbit.target.set(0, 0.80, 0);
    orbit.mouseButtons = {
      LEFT:   THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT:  THREE.MOUSE.ROTATE,
    };
    orbitRef.current = orbit;

    // ── Soft Studio Lighting (Face Shading & Shadow Depth) ──
    const ambient = new THREE.AmbientLight(0x22183a, 0.85); // Gentle ambient, not washed out
    scene.add(ambient);

    // Soft warm key light — angled slightly from the left to create facial depth
    const keyLight = new THREE.DirectionalLight(0xffecd6, 1.45);
    keyLight.position.set(-1.8, 2.2, 2.0);
    scene.add(keyLight);

    // Vibrant cool rim light on the edge/back
    const rimLight = new THREE.DirectionalLight(0x38bdf8, 2.2);
    rimLight.position.set(2.2, 1.4, -2.0);
    scene.add(rimLight);

    // Soft gentle fill
    const fillLight = new THREE.DirectionalLight(0xffaacc, 0.45);
    fillLight.position.set(0.8, -0.4, 1.6);
    scene.add(fillLight);

    // Top hair/rim light
    const hairLight = new THREE.DirectionalLight(0xc084fc, 1.2);
    hairLight.position.set(0, 3.6, 0.4);
    scene.add(hairLight);

    // ── Load VRM ─────────────────────────────────────────────
    const loader = new GLTFLoader();
    loader.register(p => new VRMLoaderPlugin(p));

    let isDisposed = false;

    loader.load(
      "/avatar.vrm",
      (gltf) => {
        if (isDisposed) return;
        const vrm: VRM = gltf.userData.vrm;
        VRMUtils.rotateVRM0(vrm);
        scene.add(vrm.scene);
        vrmRef.current = vrm;

        // Apply natural initial posture
        const h = vrm.humanoid;
        const lUA     = h.getNormalizedBoneNode("leftUpperArm");
        const rUA     = h.getNormalizedBoneNode("rightUpperArm");
        const lLA     = h.getNormalizedBoneNode("leftLowerArm");
        const rLA     = h.getNormalizedBoneNode("rightLowerArm");
        const lHand   = h.getNormalizedBoneNode("leftHand");
        const rHand   = h.getNormalizedBoneNode("rightHand");
        const lShldr  = h.getNormalizedBoneNode("leftShoulder");
        const rShldr  = h.getNormalizedBoneNode("rightShoulder");
        const spine   = h.getNormalizedBoneNode("spine");
        const hips    = h.getNormalizedBoneNode("hips");
        const lULeg   = h.getNormalizedBoneNode("leftUpperLeg");
        const rULeg   = h.getNormalizedBoneNode("rightUpperLeg");
        const lLLeg   = h.getNormalizedBoneNode("leftLowerLeg");
        const rLLeg   = h.getNormalizedBoneNode("rightLowerLeg");

        // Lower arms down along sides naturally
        if (lUA)    { lUA.rotation.z   =  1.26; lUA.rotation.x   =  0.08; lUA.rotation.y = -0.04; }
        if (rUA)    { rUA.rotation.z   = -1.26; rUA.rotation.x   =  0.08; rUA.rotation.y =  0.04; }
        if (lLA)    { lLA.rotation.y   =  0.22; lLA.rotation.x   =  0.06; }
        if (rLA)    { rLA.rotation.y   = -0.22; rLA.rotation.x   =  0.06; }
        if (lHand)  { lHand.rotation.z =  0.04; }
        if (rHand)  { rHand.rotation.z = -0.04; }
        if (lShldr) { lShldr.rotation.z =  0.04; }
        if (rShldr) { rShldr.rotation.z = -0.04; }
        if (spine)  { spine.rotation.x  =  0.02; }

        // Natural relaxed leg stance
        if (hips)   { hips.rotation.z  =  0.03; hips.rotation.y  =  0.02; }
        if (lULeg)  { lULeg.rotation.z =  0.04; lULeg.rotation.x =  0.02; }
        if (rULeg)  { rULeg.rotation.z = -0.02; rULeg.rotation.x = -0.01; }
        if (lLLeg)  { lLLeg.rotation.x =  0.03; }
        if (rLLeg)  { rLLeg.rotation.x =  0.01; }

        setLoadState("ready");
      },
      undefined,
      (err) => {
        if (!isDisposed) {
          console.error("VRM load error", err);
          setLoadState("error");
        }
      }
    );

    // ── Mouse tracking for head gaze ─────────────────────────
    const onMouseMove = (e: MouseEvent) => {
      const rect = mount.getBoundingClientRect();
      mouseNX.current = ((e.clientX - rect.left) / rect.width  - 0.5) * 2;
      mouseNY.current = ((e.clientY - rect.top)  / rect.height - 0.5) * 2;
    };
    mount.addEventListener("mousemove", onMouseMove);

    const onMouseLeave = () => {
      mouseNX.current = 0;
      mouseNY.current = 0;
    };
    mount.addEventListener("mouseleave", onMouseLeave);

    // ── Pointer down/up for click vs drag ────────────────────
    const onPointerDown = (e: PointerEvent) => {
      pointerDownPos.current = { x: e.clientX, y: e.clientY };
      isDragging.current = false;
    };

    const onPointerMove = (e: PointerEvent) => {
      const dx = e.clientX - pointerDownPos.current.x;
      const dy = e.clientY - pointerDownPos.current.y;
      if (Math.hypot(dx, dy) > 4) isDragging.current = true;
    };

    const onPointerUp = () => {
      if (!isDragging.current && connectedRef.current) {
        if (voiceRef.current === "idle") {
          onStartVoiceRef.current();
        } else if (onStopVoiceRef.current) {
          onStopVoiceRef.current();
        }
      }
      isDragging.current = false;
    };

    renderer.domElement.addEventListener("pointerdown", onPointerDown);
    renderer.domElement.addEventListener("pointermove", onPointerMove);
    renderer.domElement.addEventListener("pointerup",   onPointerUp);

    // ── Resize ───────────────────────────────────────────────
    const onResize = () => {
      renderer.setSize(mount.clientWidth, mount.clientHeight);
      camera.aspect = mount.clientWidth / mount.clientHeight;
      camera.updateProjectionMatrix();
    };
    window.addEventListener("resize", onResize);

    // ── Animation Loop ───────────────────────────────────────
    const clock = new THREE.Clock();

    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const dt = clock.getDelta();
      const t  = clock.getElapsedTime();
      const vrm = vrmRef.current;

      orbit.update();

      if (!vrm) {
        renderer.render(scene, camera);
        return;
      }

      const state = voiceRef.current;
      const h     = vrm.humanoid;

      // ── Dynamic light hues ────────────────────────────────
      const tKeyR = state === "thinking" ? 0.7  : state === "speaking" ? 1.0 : 0.95;
      const tKeyG = state === "thinking" ? 0.7  : state === "speaking" ? 0.9 : 0.85;
      const tKeyB = state === "thinking" ? 0.95 : state === "speaking" ? 0.85 : 0.75;
      const tRimR = state === "listening" ? 0.1 : state === "speaking" ? 0.5 : 0.3;
      const tRimG = state === "listening" ? 0.8 : state === "speaking" ? 0.3 : 0.5;
      const tRimB = 1.0;
      const lf = 0.05;
      keyR.current = lerp(keyR.current, tKeyR, lf);
      keyG.current = lerp(keyG.current, tKeyG, lf);
      keyB.current = lerp(keyB.current, tKeyB, lf);
      rimR.current = lerp(rimR.current, tRimR, lf);
      rimG.current = lerp(rimG.current, tRimG, lf);
      rimB.current = lerp(rimB.current, tRimB, lf);
      keyLight.color.setRGB(keyR.current, keyG.current, keyB.current);
      rimLight.color.setRGB(rimR.current, rimG.current, rimB.current);

      // ── Natural Blinking ──────────────────────────────────
      blinkTimer.current -= dt;
      if (blinkTimer.current <= 0) {
        if (blinkTarget.current === 0) {
          blinkTarget.current = 1;
          blinkTimer.current  = 0.10;
        } else {
          blinkTarget.current = 0;
          blinkTimer.current  = 2.8 + Math.random() * 2.8;
        }
      }
      blinkVal.current = lerp(blinkVal.current, blinkTarget.current, 0.28);
      const blink = blinkVal.current * (state === "speaking" ? 0.4 : 1.0);
      vrm.expressionManager?.setValue("blinkLeft",  blink);
      vrm.expressionManager?.setValue("blinkRight", blink);

      // ── Expressive & Distinct Lip Sync ────────────────────
      lipT.current += dt;
      if (state === "speaking") {
        const c  = (lipT.current * 7.5) % (Math.PI * 2);
        // Wide clear mouth opening vowels:
        const aa = clamp(Math.sin(c) * 0.85 + 0.35, 0, 1);
        const oh = clamp(Math.sin(c * 1.4 + 0.8) * 0.75, 0, 1);
        const ih = clamp(Math.sin(c + 1.6) * 0.55, 0, 1);
        const ou = clamp(Math.sin(c + 2.6) * 0.45, 0, 1);

        vrm.expressionManager?.setValue("aa", aa);
        vrm.expressionManager?.setValue("oh", oh);
        vrm.expressionManager?.setValue("ih", ih);
        vrm.expressionManager?.setValue("ou", ou);
        vrm.expressionManager?.setValue("happy", 0.4);
      } else {
        vrm.expressionManager?.setValue("aa", lerp(vrm.expressionManager?.getValue("aa") ?? 0, 0, 0.2));
        vrm.expressionManager?.setValue("oh", 0);
        vrm.expressionManager?.setValue("ih", 0);
        vrm.expressionManager?.setValue("ou", 0);
      }

      // ── Expressions ───────────────────────────────────────
      const eL = 0.06;
      if (state !== "speaking") {
        vrm.expressionManager?.setValue("happy",    lerp(vrm.expressionManager?.getValue("happy")     ?? 0, (state === "idle" || state === "listening") ? 0.35 : 0, eL));
      }
      vrm.expressionManager?.setValue("relaxed",  lerp(vrm.expressionManager?.getValue("relaxed")   ?? 0, state === "idle" ? 0.25 : 0, eL));
      vrm.expressionManager?.setValue("surprised",lerp(vrm.expressionManager?.getValue("surprised") ?? 0, state === "thinking" ? 0.45 : 0, eL));

      // ── Procedural Pose & Sway ────────────────────────────
      swayT.current += dt;
      const st = swayT.current;

      const breatheAmp   = state === "speaking" ? 0.035 : 0.012;
      const breatheSpeed = state === "speaking" ? 3.0   : 0.55;
      const breathe      = Math.sin(t * breatheSpeed) * breatheAmp;
      const spineNode = h.getNormalizedBoneNode("spine");
      const chestNode = h.getNormalizedBoneNode("chest");
      if (spineNode) spineNode.rotation.x = 0.02 + breathe;
      if (chestNode) chestNode.rotation.x = breathe * 0.6;

      // ── Head & Neck Animations ──────────────────────────────
      const headNode = h.getNormalizedBoneNode("head");
      const neckNode = h.getNormalizedBoneNode("neck");
      if (headNode) {
        let hX = Math.sin(st * 0.16) * 0.03;
        let hY = Math.sin(st * 0.10) * 0.04;
        let hZ = 0;

        if (state === "idle") {
          const targetHX = clamp(-mouseNY.current * 0.22, -0.32, 0.24);
          const targetHY = clamp( mouseNX.current * 0.26, -0.38, 0.38);
          hX = lerp(hX, targetHX, 0.08);
          hY = lerp(hY, targetHY, 0.08);
        } else if (state === "listening") {
          // Attentive listening posture: head tilted slightly forward & interested
          const targetHX = clamp(-mouseNY.current * 0.15 - 0.08, -0.25, 0.15);
          const targetHY = clamp( mouseNX.current * 0.18, -0.25, 0.25);
          hX = lerp(hX, targetHX, 0.08);
          hY = lerp(hY, targetHY, 0.08);
          hZ = 0.04; // subtle cute head tilt
        } else if (state === "thinking" || state === "transcribing") {
          // Pensive thinking posture: head turned and tilted upward
          hX = -0.10 + Math.sin(t * 1.2) * 0.02;
          hY = -0.14 + Math.sin(t * 0.8) * 0.02;
          hZ = 0.06;
        } else if (state === "speaking") {
          // Dynamic conversational nodding while explaining
          hX = Math.sin(t * 3.6) * 0.065 + Math.sin(t * 1.6) * 0.035;
          hY = Math.sin(t * 1.8) * 0.055;
          hZ = Math.sin(t * 2.2) * 0.03;
        }

        headNode.rotation.x = lerp(headNode.rotation.x, hX, 0.08);
        headNode.rotation.y = lerp(headNode.rotation.y, hY, 0.08);
        headNode.rotation.z = lerp(headNode.rotation.z, hZ, 0.08);
      }
      if (neckNode && headNode) {
        neckNode.rotation.x = headNode.rotation.x * 0.45;
        neckNode.rotation.y = headNode.rotation.y * 0.45;
      }

      // ── Arms & Hands (Natural & Elegant) ─────────────────────
      const lUA   = h.getNormalizedBoneNode("leftUpperArm");
      const rUA   = h.getNormalizedBoneNode("rightUpperArm");
      const lLA   = h.getNormalizedBoneNode("leftLowerArm");
      const rLA   = h.getNormalizedBoneNode("rightLowerArm");
      const lHand = h.getNormalizedBoneNode("leftHand");
      const rHand = h.getNormalizedBoneNode("rightHand");

      // Left Arm — Natural resting pose with soft breathing sway
      const lUaZ = 1.26 + Math.sin(st * 0.4) * 0.015;
      const lUaX = 0.08;
      const lUaY = -0.04;
      const lLaY = 0.22;
      const lLaX = 0.06;

      // Right Arm — Natural resting pose with gentle conversational sway during speech
      let rUaZ = -1.26 - Math.sin(st * 0.4) * 0.015;
      const rUaX = 0.08;
      const rUaY = 0.04;
      let rLaY = -0.22;
      const rLaX = 0.06;

      if (state === "speaking") {
        // Subtle, elegant conversational gesture on right arm
        rUaZ = -1.18 + Math.sin(t * 2.0) * 0.03;
        rLaY = -0.32 + Math.sin(t * 3.0) * 0.05;
      }

      if (lUA) {
        lUA.rotation.z = lerp(lUA.rotation.z, lUaZ, 0.06);
        lUA.rotation.x = lerp(lUA.rotation.x, lUaX, 0.06);
        lUA.rotation.y = lerp(lUA.rotation.y, lUaY, 0.06);
      }
      if (rUA) {
        rUA.rotation.z = lerp(rUA.rotation.z, rUaZ, 0.06);
        rUA.rotation.x = lerp(rUA.rotation.x, rUaX, 0.06);
        rUA.rotation.y = lerp(rUA.rotation.y, rUaY, 0.06);
      }
      if (lLA) {
        lLA.rotation.y = lerp(lLA.rotation.y, lLaY, 0.06);
        lLA.rotation.x = lerp(lLA.rotation.x, lLaX, 0.06);
      }
      if (rLA) {
        rLA.rotation.y = lerp(rLA.rotation.y, rLaY, 0.06);
        rLA.rotation.x = lerp(rLA.rotation.x, rLaX, 0.06);
      }
      if (lHand) {
        lHand.rotation.z = lerp(lHand.rotation.z, 0.04, 0.06);
      }
      if (rHand) {
        rHand.rotation.z = lerp(rHand.rotation.z, -0.04, 0.06);
        rHand.rotation.x = lerp(rHand.rotation.x, 0.00, 0.06);
      }

      // ── Hips & Legs Stance (Natural Contrapposto) ─────────────
      const hips = h.getNormalizedBoneNode("hips");
      const lLeg = h.getNormalizedBoneNode("leftUpperLeg");
      const rLeg = h.getNormalizedBoneNode("rightUpperLeg");

      let targetHipsZ = 0.03 + Math.sin(st * 0.35) * 0.015;
      const targetLLegZ = 0.04 + Math.sin(st * 0.35) * 0.01;
      const targetRLegZ = -0.02 - Math.sin(st * 0.35) * 0.01;

      if (state === "speaking") {
        targetHipsZ = 0.025 + Math.sin(t * 1.8) * 0.015;
      }

      if (hips) {
        hips.rotation.z = lerp(hips.rotation.z, targetHipsZ, 0.06);
        hips.rotation.x = breathe * 0.3;
      }
      if (lLeg) {
        lLeg.rotation.z = lerp(lLeg.rotation.z, targetLLegZ, 0.05);
      }
      if (rLeg) {
        rLeg.rotation.z = lerp(rLeg.rotation.z, targetRLegZ, 0.05);
      }

      vrm.update(dt);
      renderer.render(scene, camera);
    };

    tick();

    return () => {
      isDisposed = true;
      window.removeEventListener("resize", onResize);
      mount.removeEventListener("mousemove", onMouseMove);
      mount.removeEventListener("mouseleave", onMouseLeave);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup",   onPointerUp);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      orbit.dispose();
      const vrm = vrmRef.current;
      if (vrm) {
        scene.remove(vrm.scene);
        VRMUtils.deepDispose(vrm.scene);
        vrmRef.current = null;
      }
      renderer.dispose();
      if (mount.contains(renderer.domElement)) mount.removeChild(renderer.domElement);
    };
  }, []);

  const isBusy = voiceState !== "idle";

  return (
    <div className="vrm-avatar-container">
      <div
        className={`vrm-stage ${voiceState} ${isBusy ? "busy" : ""}`}
        ref={mountRef}
        title={!connected ? "Voice server disconnected" : isBusy ? "Click to stop" : "Drag to rotate 360° · Click to speak"}
      >
        {loadState === "loading" && (
          <div className="vrm-loading">
            <div className="vrm-loading-orb" />
            <p>Loading 3D Anime Character...</p>
          </div>
        )}
        {loadState === "error" && (
          <div className="vrm-loading vrm-error">
            <p>⚠ Avatar unavailable</p>
            <p className="vrm-error-sub">Place avatar.vrm in /public</p>
          </div>
        )}
        <div className={`vrm-glow-ring ${voiceState}`} />

        {/* Dynamic Speaking Waves Effect */}
        {voiceState === "speaking" && (
          <div className="vrm-speaking-waves">
            <div className="vrm-wave vrm-wave-1" />
            <div className="vrm-wave vrm-wave-2" />
            <div className="vrm-wave vrm-wave-3" />
          </div>
        )}
      </div>
    </div>
  );
}
