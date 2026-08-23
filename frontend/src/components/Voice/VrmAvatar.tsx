import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { VRMLoaderPlugin, VRM, VRMUtils } from "@pixiv/three-vrm";
import { AnimationController } from "./animation";
import type { AnimationDebugInfo, VoiceState } from "./animation";
import "./VrmAvatar.css";

export type { VoiceState } from "./animation";

interface Props {
  voiceState: VoiceState;
  connected: boolean;
  onStartVoice: () => void;
  onStopVoice?: () => void;
}

function lerp(a: number, b: number, t: number) {
  return a + (b - a) * t;
}

export default function VrmAvatar({
  voiceState,
  connected,
  onStartVoice,
  onStopVoice,
}: Props) {
  const mountRef = useRef<HTMLDivElement | null>(null);
  const vrmRef = useRef<VRM | null>(null);
  const animControllerRef = useRef<AnimationController | null>(null);
  const rafRef = useRef<number | null>(null);
  const voiceRef = useRef<VoiceState>(voiceState);
  const connectedRef = useRef(connected);
  const onStartVoiceRef = useRef(onStartVoice);
  const onStopVoiceRef = useRef(onStopVoice);

  const [loadState, setLoadState] = useState<"loading" | "ready" | "error">("loading");
  const [showDebug, setShowDebug] = useState(false);
  const [debugInfo, setDebugInfo] = useState<AnimationDebugInfo | null>(null);

  // Mouse tracking (-1..1) for head gaze
  const mouseNX = useRef(0);
  const mouseNY = useRef(0);

  // Orbit controls
  const orbitRef = useRef<OrbitControls | null>(null);

  // Click vs drag detection
  const pointerDownPos = useRef({ x: 0, y: 0 });
  const isDragging = useRef(false);

  // Light color lerp refs
  const keyR = useRef(1.0), keyG = useRef(0.85), keyB = useRef(0.75);
  const rimR = useRef(0.3), rimG = useRef(0.5),  rimB = useRef(1.0);

  useEffect(() => {
    voiceRef.current = voiceState;
    if (animControllerRef.current) {
      animControllerRef.current.setVoiceState(voiceState);
    }
  }, [voiceState]);

  useEffect(() => { connectedRef.current = connected; }, [connected]);
  useEffect(() => { onStartVoiceRef.current = onStartVoice; }, [onStartVoice]);
  useEffect(() => { onStopVoiceRef.current = onStopVoice; }, [onStopVoice]);

  // Global Shift+D keyboard shortcut for animation debug overlay
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.shiftKey && (e.key === "D" || e.key === "d")) {
        setShowDebug((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) return;

    setLoadState("loading");

    // ── WebGL Renderer with High-Contrast ACES Filmic Tone Mapping ────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(mount.clientWidth, mount.clientHeight);
    renderer.setClearColor(0x000000, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.78;
    mount.appendChild(renderer.domElement);

    // ── Three.js Scene & Fog ──────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x0a0812, 0.05);

    // ── Perspective Camera ────────────────────────────────────────────
    const camera = new THREE.PerspectiveCamera(
      28,
      mount.clientWidth / mount.clientHeight,
      0.1,
      50
    );
    camera.position.set(0.0, 0.88, 2.75);
    camera.lookAt(0, 0.78, 0);

    // ── Orbit Controls (360° Horizontal Rotation with Inertia) ────────
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.enableDamping = true;
    orbit.dampingFactor = 0.08;
    orbit.enablePan = false;
    orbit.enableZoom = false;
    orbit.minPolarAngle = Math.PI * 0.12;
    orbit.maxPolarAngle = Math.PI * 0.82;
    orbit.target.set(0, 0.78, 0);
    orbit.mouseButtons = {
      LEFT: THREE.MOUSE.ROTATE,
      MIDDLE: THREE.MOUSE.DOLLY,
      RIGHT: THREE.MOUSE.ROTATE,
    };
    orbitRef.current = orbit;

    // ── Multi-Point Studio Lighting Rig ───────────────────────────────
    const ambient = new THREE.AmbientLight(0x22183a, 0.85);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xffecd6, 1.45);
    keyLight.position.set(-1.8, 2.2, 2.0);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x38bdf8, 2.2);
    rimLight.position.set(2.2, 1.4, -2.0);
    scene.add(rimLight);

    const fillLight = new THREE.DirectionalLight(0xffaacc, 0.45);
    fillLight.position.set(0.8, -0.4, 1.6);
    scene.add(fillLight);

    const hairLight = new THREE.DirectionalLight(0xc084fc, 1.2);
    hairLight.position.set(0, 3.6, 0.4);
    scene.add(hairLight);

    // ── Ground Platform & Contact Shadow Base (Eliminates Floating) ───
    const groundGroup = new THREE.Group();
    scene.add(groundGroup);

    // Dark soft contact shadow directly beneath feet
    const shadowGeo = new THREE.CircleGeometry(0.72, 48);
    const shadowMat = new THREE.MeshBasicMaterial({
      color: 0x05030c,
      transparent: true,
      opacity: 0.85,
    });
    const contactShadow = new THREE.Mesh(shadowGeo, shadowMat);
    contactShadow.rotation.x = -Math.PI / 2;
    contactShadow.position.y = 0.002;
    groundGroup.add(contactShadow);

    // Glowing Inner Ground Ring
    const ringGeo = new THREE.RingGeometry(0.68, 0.70, 64);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0x7c5cfc,
      transparent: true,
      opacity: 0.45,
      side: THREE.DoubleSide,
    });
    const groundRing = new THREE.Mesh(ringGeo, ringMat);
    groundRing.rotation.x = -Math.PI / 2;
    groundRing.position.y = 0.003;
    groundGroup.add(groundRing);

    // Glowing Outer Cyber Ring
    const outerRingGeo = new THREE.RingGeometry(0.88, 0.895, 64);
    const outerRingMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.25,
      side: THREE.DoubleSide,
    });
    const outerGroundRing = new THREE.Mesh(outerRingGeo, outerRingMat);
    outerGroundRing.rotation.x = -Math.PI / 2;
    outerGroundRing.position.y = 0.003;
    groundGroup.add(outerGroundRing);

    // ── Load VRM Avatar ───────────────────────────────────────────────
    const loader = new GLTFLoader();
    loader.register((p) => new VRMLoaderPlugin(p));

    let isDisposed = false;

    loader.load(
      "/avatar.vrm",
      (gltf) => {
        if (isDisposed) return;
        const vrm: VRM = gltf.userData.vrm;
        VRMUtils.rotateVRM0(vrm);
        scene.add(vrm.scene);
        vrmRef.current = vrm;

        // Initialize Central Animation Controller
        const controller = new AnimationController(vrm);
        controller.setVoiceState(voiceRef.current);
        animControllerRef.current = controller;

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

    // ── Mouse Tracking for Dynamic Gaze ───────────────────────────────
    const onMouseMove = (e: MouseEvent) => {
      const rect = mount.getBoundingClientRect();
      mouseNX.current = ((e.clientX - rect.left) / rect.width - 0.5) * 2;
      mouseNY.current = ((e.clientY - rect.top) / rect.height - 0.5) * 2;
    };
    mount.addEventListener("mousemove", onMouseMove);

    const onMouseLeave = () => {
      mouseNX.current = 0;
      mouseNY.current = 0;
    };
    mount.addEventListener("mouseleave", onMouseLeave);

    // ── Pointer Events (Click vs Drag Detection) ──────────────────────
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
    renderer.domElement.addEventListener("pointerup", onPointerUp);

    // ── Responsive Resize Observer ───────────────────────────────────
    const handleResize = () => {
      if (!mount) return;
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      if (width === 0 || height === 0) return;
      renderer.setSize(width, height);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(mount);
    window.addEventListener("resize", handleResize);

    // ── 60 FPS RequestAnimationFrame Render Loop ─────────────────────
    const clock = new THREE.Clock();
    let debugUpdateTimer = 0;

    const tick = () => {
      rafRef.current = requestAnimationFrame(tick);
      const dt = clock.getDelta();
      const state = voiceRef.current;
      const controller = animControllerRef.current;

      orbit.update();

      // Subtle ground ring rotation
      groundRing.rotation.z += dt * 0.12;
      outerGroundRing.rotation.z -= dt * 0.08;

      // Dynamic studio light hues
      const tKeyR = state === "thinking" ? 0.7 : state === "speaking" ? 1.0 : 0.95;
      const tKeyG = state === "thinking" ? 0.7 : state === "speaking" ? 0.9 : 0.85;
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

      if (controller) {
        controller.setVoiceState(state);
        controller.setMouse(mouseNX.current, mouseNY.current);
        controller.update(dt);

        // Throttle debug UI state updates to 4Hz (every 250ms) to avoid React re-renders
        debugUpdateTimer += dt;
        if (debugUpdateTimer >= 0.25) {
          debugUpdateTimer = 0;
          setDebugInfo(controller.getDebugInfo());
        }
      }

      renderer.render(scene, camera);
    };

    tick();

    return () => {
      isDisposed = true;
      resizeObserver.disconnect();
      window.removeEventListener("resize", handleResize);
      mount.removeEventListener("mousemove", onMouseMove);
      mount.removeEventListener("mouseleave", onMouseLeave);
      renderer.domElement.removeEventListener("pointerdown", onPointerDown);
      renderer.domElement.removeEventListener("pointermove", onPointerMove);
      renderer.domElement.removeEventListener("pointerup", onPointerUp);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      orbit.dispose();
      const vrm = vrmRef.current;
      if (vrm) {
        scene.remove(vrm.scene);
        VRMUtils.deepDispose(vrm.scene);
        vrmRef.current = null;
      }
      animControllerRef.current = null;
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
        title={
          !connected
            ? "Voice server disconnected"
            : isBusy
            ? "Click to stop"
            : "Drag to rotate 360° · Click to speak"
        }
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

        {/* Optional Debug Mode Toggle Button */}
        <button
          className={`vrm-debug-toggle ${showDebug ? "active" : ""}`}
          onClick={(e) => {
            e.stopPropagation();
            setShowDebug((prev) => !prev);
          }}
          title="Toggle Animation Debug HUD (Shift+D)"
        >
          {showDebug ? "HUD ON" : "HUD"}
        </button>

        {/* Animation Debug Overlay HUD */}
        {showDebug && debugInfo && (
          <div className="vrm-debug-hud glass" onClick={(e) => e.stopPropagation()}>
            <div className="vrm-debug-header">
              <span>🎭 Animation HUD</span>
              <span className="vrm-debug-fps">{debugInfo.fps} FPS</span>
            </div>
            <div className="vrm-debug-grid">
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">State:</span>
                <span className="vrm-debug-value highlight">{debugInfo.state.toUpperCase()}</span>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">Emotion:</span>
                <span className="vrm-debug-value">{debugInfo.emotion}</span>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">Gesture:</span>
                <span className="vrm-debug-value accent">{debugInfo.gesture} ({debugInfo.gesturePhase})</span>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">Progress:</span>
                <div className="vrm-debug-bar-wrap">
                  <div
                    className="vrm-debug-bar"
                    style={{ width: `${Math.round(debugInfo.gestureProgress * 100)}%` }}
                  />
                </div>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">Intensity:</span>
                <span className="vrm-debug-value">{debugInfo.gestureIntensity}</span>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">Weight Leg:</span>
                <span className="vrm-debug-value">{debugInfo.weightLeg.toUpperCase()}</span>
              </div>
              <div className="vrm-debug-row">
                <span className="vrm-debug-label">IK Active:</span>
                <span className={`vrm-debug-value ${debugInfo.ikActive ? "active-ik" : ""}`}>
                  {debugInfo.ikActive ? "ACTIVE" : "STANDBY"}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
