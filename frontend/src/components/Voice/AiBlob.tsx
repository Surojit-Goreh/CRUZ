import { useEffect, useRef } from "react";
import "./AiBlob.css";

export type VoiceState = "listening" | "transcribing" | "thinking" | "speaking" | "idle";

interface Props {
  voiceState: VoiceState;
  connected: boolean;
  onStartVoice: () => void;
}

export default function AiBlob({ voiceState, connected, onStartVoice }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // Smooth parameter lerp refs
  const currentAmpRef = useRef(6);
  const currentSpeedRef = useRef(0.012);
  const currentGlowRef = useRef(0.22);
  const currentRingAlphaRef = useRef(0.12);
  const currentRingsRef = useRef(2);

  // Background ambient light color lerp refs (RGB for inner & outer stops)
  const currentR1Ref = useRef(124);
  const currentG1Ref = useRef(92);
  const currentB1Ref = useRef(252);

  const currentR2Ref = useRef(0);
  const currentG2Ref = useRef(180);
  const currentB2Ref = useRef(255);

  // Per-point liquid physics arrays (120 points around circle)
  const POINTS_COUNT = 120;
  const currentRadiiRef = useRef<Float32Array>(new Float32Array(POINTS_COUNT));

  const targetStateRef = useRef<VoiceState>(voiceState);

  useEffect(() => {
    targetStateRef.current = voiceState;
  }, [voiceState]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId: number;
    let time = 0;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
    };

    resize();
    window.addEventListener("resize", resize);

    const radii = currentRadiiRef.current;

    const render = () => {
      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;
      const cx = width / 2;
      const cy = height / 2;
      const baseRadius = Math.min(width, height) * 0.28;

      ctx.clearRect(0, 0, width, height);

      // ── Target parameter & color calculations based on voiceState ──
      const state = targetStateRef.current;
      let targetAmp = 6;
      let targetSpeed = 0.012;
      let targetGlow = 0.22;
      let targetRingAlpha = 0.12;
      let targetRings = 2;

      // Color targets: [R1, G1, B1] (inner stop), [R2, G2, B2] (mid stop)
      let targetRGB1 = [124, 92, 252]; // Violet
      let targetRGB2 = [0, 180, 255];  // Cyan-blue

      if (state === "speaking") {
        targetAmp = 18;
        targetSpeed = 0.032;
        targetGlow = 0.48;
        targetRingAlpha = 0.25;
        targetRings = 3;
        targetRGB1 = [99, 102, 241];  // Electric Indigo
        targetRGB2 = [0, 210, 255];   // Bright Cyan
      } else if (state === "listening") {
        targetAmp = 14;
        targetSpeed = 0.024;
        targetGlow = 0.42;
        targetRingAlpha = 0.35;
        targetRings = 4;
        targetRGB1 = [0, 210, 255];   // Bright Cyan
        targetRGB2 = [124, 92, 252];  // Violet
      } else if (state === "thinking" || state === "transcribing") {
        targetAmp = 10;
        targetSpeed = 0.018;
        targetGlow = 0.32;
        targetRingAlpha = 0.2;
        targetRings = 3;
        targetRGB1 = [167, 139, 250]; // Light Violet/Purple
        targetRGB2 = [0, 210, 255];   // Cyan
      }

      // ── Continuous 3.5% Lerp Ease for smooth transitions ──
      const lerpFactor = 0.035;
      currentAmpRef.current += (targetAmp - currentAmpRef.current) * lerpFactor;
      currentSpeedRef.current += (targetSpeed - currentSpeedRef.current) * lerpFactor;
      currentGlowRef.current += (targetGlow - currentGlowRef.current) * lerpFactor;
      currentRingAlphaRef.current += (targetRingAlpha - currentRingAlphaRef.current) * lerpFactor;
      currentRingsRef.current += (targetRings - currentRingsRef.current) * lerpFactor;

      // RGB Color lerping for background light
      currentR1Ref.current += (targetRGB1[0] - currentR1Ref.current) * lerpFactor;
      currentG1Ref.current += (targetRGB1[1] - currentG1Ref.current) * lerpFactor;
      currentB1Ref.current += (targetRGB1[2] - currentB1Ref.current) * lerpFactor;

      currentR2Ref.current += (targetRGB2[0] - currentR2Ref.current) * lerpFactor;
      currentG2Ref.current += (targetRGB2[1] - currentG2Ref.current) * lerpFactor;
      currentB2Ref.current += (targetRGB2[2] - currentB2Ref.current) * lerpFactor;

      const amp = currentAmpRef.current;
      const speed = currentSpeedRef.current;
      const glowOpacity = currentGlowRef.current;
      const ringAlpha = currentRingAlphaRef.current;
      const activeRings = Math.round(currentRingsRef.current);

      const r1 = Math.round(currentR1Ref.current);
      const g1 = Math.round(currentG1Ref.current);
      const b1 = Math.round(currentB1Ref.current);

      const r2 = Math.round(currentR2Ref.current);
      const g2 = Math.round(currentG2Ref.current);
      const b2 = Math.round(currentB2Ref.current);

      time += speed;

      // ── Outer Glowing Energy Rings ──
      for (let r = 1; r <= activeRings; r++) {
        const ringRadius = baseRadius + r * 26 + Math.sin(time * 1.8 + r) * 5;
        const currentAlpha = (ringAlpha / r);
        ctx.beginPath();
        ctx.arc(cx, cy, ringRadius, 0, Math.PI * 2);
        ctx.strokeStyle = `rgba(${r2}, ${g2}, ${b2}, ${currentAlpha})`;
        ctx.lineWidth = 1.5;
        ctx.setLineDash([8, 12]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // ── Continuous Color-Lerped Ambient Outer Radial Glow ──
      const glowGrad = ctx.createRadialGradient(cx, cy, baseRadius * 0.3, cx, cy, baseRadius * 1.9);
      glowGrad.addColorStop(0, `rgba(${r1}, ${g1}, ${b1}, ${glowOpacity})`);
      glowGrad.addColorStop(0.5, `rgba(${r2}, ${g2}, ${b2}, ${glowOpacity * 0.5})`);
      glowGrad.addColorStop(1, "rgba(0, 0, 0, 0)");

      ctx.fillStyle = glowGrad;
      ctx.beginPath();
      ctx.arc(cx, cy, baseRadius * 1.9, 0, Math.PI * 2);
      ctx.fill();

      // ── Per-Point Liquid Spring Physics Engine ──
      ctx.beginPath();

      for (let i = 0; i < POINTS_COUNT; i++) {
        const angle = (i / POINTS_COUNT) * Math.PI * 2;

        const targetOffset1 = Math.sin(angle * 3 + time * 2) * amp;
        const targetOffset2 = Math.cos(angle * 5 - time * 1.5) * (amp * 0.55);
        const targetOffset3 = Math.sin(angle * 2 + time * 2.5) * (amp * 0.35);
        const targetR = baseRadius + targetOffset1 + targetOffset2 + targetOffset3;

        if (radii[i] === 0) {
          radii[i] = targetR;
        }

        radii[i] += (targetR - radii[i]) * 0.06;

        const currentR = radii[i];
        const x = cx + Math.cos(angle) * currentR;
        const y = cy + Math.sin(angle) * currentR;

        if (i === 0) {
          ctx.moveTo(x, y);
        } else {
          ctx.lineTo(x, y);
        }
      }
      ctx.closePath();

      // 3D Liquid Core Gradient
      const blobGrad = ctx.createRadialGradient(
        cx - baseRadius * 0.3,
        cy - baseRadius * 0.35,
        baseRadius * 0.1,
        cx,
        cy,
        baseRadius * 1.25
      );

      blobGrad.addColorStop(0, "#ffffff");
      blobGrad.addColorStop(0.2, "#e0f2fe");
      blobGrad.addColorStop(0.45, "#00d2ff");
      blobGrad.addColorStop(0.75, "#3b82f6");
      blobGrad.addColorStop(0.95, "#1e1b4b");
      blobGrad.addColorStop(1, "#0f172a");

      ctx.fillStyle = blobGrad;
      ctx.shadowColor = `rgba(${r2}, ${g2}, ${b2}, 0.5)`;
      ctx.shadowBlur = 30;
      ctx.fill();
      ctx.shadowBlur = 0;

      // ── Pearlescent Highlight Layer ──
      ctx.beginPath();
      const highlightR = baseRadius * 0.85;
      ctx.ellipse(cx - baseRadius * 0.25, cy - baseRadius * 0.3, highlightR * 0.45, highlightR * 0.25, -Math.PI / 4, 0, Math.PI * 2);
      const highlightGrad = ctx.createRadialGradient(
        cx - baseRadius * 0.25,
        cy - baseRadius * 0.3,
        0,
        cx - baseRadius * 0.25,
        cy - baseRadius * 0.3,
        highlightR * 0.45
      );
      highlightGrad.addColorStop(0, "rgba(255, 255, 255, 0.85)");
      highlightGrad.addColorStop(0.5, "rgba(255, 255, 255, 0.3)");
      highlightGrad.addColorStop(1, "rgba(255, 255, 255, 0)");
      ctx.fillStyle = highlightGrad;
      ctx.fill();

      // ── Orbiting Particle Dust ──
      const particleCount = 40;
      for (let p = 0; p < particleCount; p++) {
        const pAngle = (p / particleCount) * Math.PI * 2 + time * 0.4 * (p % 2 === 0 ? 1 : -1);
        const pDist = baseRadius * (1.1 + (p % 5) * 0.1) + Math.sin(time + p) * 8;
        const px = cx + Math.cos(pAngle) * pDist;
        const py = cy + Math.sin(pAngle) * pDist;
        const pSize = 1 + (p % 3) * 0.8;
        const pAlpha = 0.3 + Math.sin(time * 2 + p) * 0.3;

        ctx.beginPath();
        ctx.arc(px, py, pSize, 0, Math.PI * 2);
        ctx.fillStyle = p % 2 === 0 ? `rgba(${r2}, ${g2}, ${b2}, ${pAlpha})` : `rgba(${r1}, ${g1}, ${b1}, ${pAlpha})`;
        ctx.fill();
      }

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  const isBusy = voiceState !== "idle";

  return (
    <div className="ai-blob-container">
      {/* Clean 3D Canvas Orb Stage */}
      <div
        className={`blob-stage ${isBusy ? "busy" : ""}`}
        onClick={() => {
          if (connected && !isBusy) {
            onStartVoice();
          }
        }}
        title={!connected ? "Voice server disconnected" : "Click orb to speak with CRUZ"}
      >
        <canvas ref={canvasRef} className="blob-canvas" />
      </div>

      {/* Voice Status & Title */}
      <div className="blob-info">
        <h2 className="blob-title">CRUZ AI</h2>
        <p className="blob-status">
          {voiceState === "listening" && "Listening to your voice..."}
          {voiceState === "transcribing" && "Processing audio..."}
          {voiceState === "thinking" && "CRUZ is thinking..."}
          {voiceState === "speaking" && "CRUZ is speaking..."}
          {voiceState === "idle" && "Click orb or mic to talk"}
        </p>
      </div>
    </div>
  );
}
