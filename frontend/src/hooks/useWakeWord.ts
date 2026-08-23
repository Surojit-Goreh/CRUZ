import { useEffect, useRef, useState, useCallback } from "react";
import type { VoiceState } from "./useChat";

// Declare global types for browser SpeechRecognition
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  resultIndex: number;
}

interface SpeechRecognitionErrorEvent extends Event {
  error: string;
  message?: string;
}

interface ISpeechRecognition extends EventTarget {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
}

declare global {
  interface Window {
    SpeechRecognition?: { new (): ISpeechRecognition };
    webkitSpeechRecognition?: { new (): ISpeechRecognition };
  }
}

// Broad phonetic keywords for "Cruz"
const WAKE_KEYWORDS = [
  "cruz", "cruise", "cruze", "cruse", "crooz", "kruz", "kruze", "crews", "crew", "cross", "crows", "cuz"
];

const GREETINGS = [
  "hey", "hi", "hello", "ok", "okay", "yo", "listen", "wake", "a", "the", "sup"
];

// Regex matching any greeting + wake sound, or standalone wake keyword
const WAKE_WORD_REGEX = new RegExp(
  `\\b(?:(?:${GREETINGS.join("|")})\\s+)?(?:${WAKE_KEYWORDS.join("|")}|chris|bruce|choose|clues|truth|groos)\\b`,
  "i"
);

export interface WakeDetectionResult {
  matched: boolean;
  prompt: string;
}

export function parseWakeWord(transcript: string): WakeDetectionResult {
  if (!transcript) return { matched: false, prompt: "" };

  // Normalize punctuation and collapse whitespace
  const clean = transcript
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();

  const match = WAKE_WORD_REGEX.exec(clean);
  if (match) {
    const prompt = clean.slice(match.index + match[0].length).trim();
    return { matched: true, prompt };
  }

  return { matched: false, prompt: "" };
}

interface UseWakeWordOptions {
  enabled?: boolean;
  voiceState: VoiceState;
  connected: boolean;
  onWakeWord: (prompt?: string) => void;
}

export default function useWakeWord({
  enabled = true,
  voiceState,
  connected,
  onWakeWord,
}: UseWakeWordOptions) {
  const [isSupported] = useState(
    () => Boolean(typeof window !== "undefined" && (window.SpeechRecognition || window.webkitSpeechRecognition))
  );
  const [isActive, setIsActive] = useState(false);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [lastDetected, setLastDetected] = useState<number | null>(null);

  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const isRunningRef = useRef(false);
  const cooldownRef = useRef(false);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Synchronously evaluate shouldRun state
  const shouldRun = enabled && connected && voiceState === "idle";
  const shouldRunRef = useRef(shouldRun);
  shouldRunRef.current = shouldRun;

  // Pre-authorize microphone permission on mount
  useEffect(() => {
    if (typeof navigator !== "undefined" && navigator.mediaDevices?.getUserMedia) {
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          setHasPermission(true);
          // Release immediately so browser audio stack is unlocked
          stream.getTracks().forEach((track) => track.stop());
        })
        .catch((err) => {
          console.warn("Microphone permission check:", err);
          setHasPermission(false);
        });
    }
  }, []);

  const handleWakeWordTrigger = useCallback(
    (prompt?: string) => {
      if (cooldownRef.current) return;
      cooldownRef.current = true;
      setLastDetected(Date.now());

      console.log(`🎤 Wake word detected instantly! Prompt: "${prompt || '(none)'}"`);

      // Immediately stop recognition to free microphone for backend VAD recording
      try {
        recognitionRef.current?.abort();
      } catch {
        // ignore
      }

      onWakeWord(prompt);

      // Short 2-second cooldown to prevent double triggering
      setTimeout(() => {
        cooldownRef.current = false;
      }, 2000);
    },
    [onWakeWord]
  );

  // Start continuous, high-sensitivity SpeechRecognition
  const startRecognition = useCallback(() => {
    if (!isSupported || isRunningRef.current || !shouldRunRef.current || cooldownRef.current) {
      return;
    }

    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionClass) return;

    try {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }

      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true; // Ultra-low latency interim detection
      recognition.lang = "en-US";
      recognition.maxAlternatives = 5; // Evaluate top 5 phonetic hypotheses

      recognition.onstart = () => {
        isRunningRef.current = true;
        setIsActive(true);
      };

      recognition.onend = () => {
        isRunningRef.current = false;
        setIsActive(false);

        // Gapless, immediate restart (10ms)
        if (shouldRunRef.current && !cooldownRef.current) {
          if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
          restartTimerRef.current = setTimeout(() => {
            if (shouldRunRef.current && !isRunningRef.current && !cooldownRef.current) {
              startRecognition();
            }
          }, 10);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (event.error === "not-allowed") {
          console.warn("SpeechRecognition mic access denied.");
          setHasPermission(false);
        } else if (event.error !== "no-speech" && event.error !== "aborted") {
          console.warn("SpeechRecognition notice:", event.error);
        }
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        if (!shouldRunRef.current || cooldownRef.current) return;

        // Inspect all results and alternatives including interim hypotheses
        for (let i = 0; i < event.results.length; i++) {
          const res = event.results[i];
          for (let j = 0; j < res.length; j++) {
            const transcript = res[j]?.transcript || "";
            const { matched, prompt } = parseWakeWord(transcript);
            if (matched) {
              handleWakeWordTrigger(prompt);
              return;
            }
          }
        }
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (e) {
      console.warn("Failed to start SpeechRecognition:", e);
    }
  }, [isSupported, handleWakeWordTrigger]);

  const stopRecognition = useCallback(() => {
    if (restartTimerRef.current) clearTimeout(restartTimerRef.current);
    const recognition = recognitionRef.current;
    if (recognition && isRunningRef.current) {
      try {
        recognition.stop();
      } catch {
        // ignore
      }
    }
    isRunningRef.current = false;
    setIsActive(false);
  }, []);

  // Manage start/stop dynamically
  useEffect(() => {
    if (shouldRun) {
      startRecognition();
    } else {
      stopRecognition();
    }

    return () => {
      stopRecognition();
    };
  }, [shouldRun, startRecognition, stopRecognition]);

  return {
    isSupported,
    isActive,
    hasPermission,
    lastDetected,
  };
}
