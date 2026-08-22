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

// Patterns that trigger the wake word (including common STT misspellings)
const WAKE_WORD_PATTERNS = [
  /\bhey\s+cruz\b/i,
  /\bhi\s+cruz\b/i,
  /\bhello\s+cruz\b/i,
  /\bok\s+cruz\b/i,
  /\bokay\s+cruz\b/i,
  /\bcruz\b/i,
  /\bhey\s+cruise\b/i,
  /\bhi\s+cruise\b/i,
  /\bhello\s+cruise\b/i,
  /\bok\s+cruise\b/i,
  /\bokay\s+cruise\b/i,
  /\bcruise\b/i,
  /\bhey\s+crews\b/i,
  /\bcrews\b/i,
  /\bhey\s+kruz\b/i,
  /\bkruz\b/i,
  /\bhey\s+cross\b/i,
];

function containsWakeWord(transcript: string): boolean {
  const clean = transcript.trim().toLowerCase();
  return WAKE_WORD_PATTERNS.some((pattern) => pattern.test(clean));
}

interface UseWakeWordOptions {
  enabled?: boolean;
  voiceState: VoiceState;
  connected: boolean;
  onWakeWord: () => void;
}

export default function useWakeWord({
  enabled = true,
  voiceState,
  connected,
  onWakeWord,
}: UseWakeWordOptions) {
  const [isSupported] = useState(
    () => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
  );
  const [isActive, setIsActive] = useState(false);
  const [lastDetected, setLastDetected] = useState<number | null>(null);

  const recognitionRef = useRef<ISpeechRecognition | null>(null);
  const isRunningRef = useRef(false);
  const shouldRunRef = useRef(enabled);
  const cooldownRef = useRef(false);

  useEffect(() => {
    shouldRunRef.current = enabled && connected && voiceState === "idle";
  }, [enabled, connected, voiceState]);

  const handleWakeWordTrigger = useCallback(() => {
    if (cooldownRef.current) return;
    cooldownRef.current = true;
    setLastDetected(Date.now());

    console.log("🎤 Wake word 'Hey Cruz' detected! Starting voice turn...");

    // Stop current recognition immediately to release mic for backend VAD recording
    try {
      recognitionRef.current?.abort();
    } catch {
      // ignore
    }

    onWakeWord();

    // Reset cooldown after 3 seconds
    setTimeout(() => {
      cooldownRef.current = false;
    }, 3000);
  }, [onWakeWord]);

  // Initialize SpeechRecognition instance once
  useEffect(() => {
    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      console.warn("SpeechRecognition is not supported in this browser.");
      return;
    }

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "en-US";
      recognition.maxAlternatives = 3;

      recognition.onstart = () => {
        isRunningRef.current = true;
        setIsActive(true);
      };

      recognition.onend = () => {
        isRunningRef.current = false;
        setIsActive(false);

        // Auto-restart if we should still be running and voice is idle
        if (shouldRunRef.current && !cooldownRef.current) {
          setTimeout(() => {
            if (shouldRunRef.current && !isRunningRef.current) {
              try {
                recognition.start();
              } catch {
                // Ignore if already started
              }
            }
          }, 300);
        }
      };

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        // "no-speech" and "aborted" are normal lifecycle events
        if (event.error !== "no-speech" && event.error !== "aborted") {
          console.warn("SpeechRecognition error:", event.error);
        }
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        if (!shouldRunRef.current || cooldownRef.current) return;

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          for (let j = 0; j < result.length; j++) {
            const transcript = result[j].transcript;
            if (containsWakeWord(transcript)) {
              handleWakeWordTrigger();
              return;
            }
          }
        }
      };

      recognitionRef.current = recognition;
    } catch (e) {
      console.error("Failed to initialize SpeechRecognition:", e);
    }

    return () => {
      try {
        recognitionRef.current?.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    };
  }, [handleWakeWordTrigger]);

  // Manage start/stop based on voiceState & connection
  useEffect(() => {
    const recognition = recognitionRef.current;
    if (!recognition || !isSupported) return;

    if (shouldRunRef.current && !cooldownRef.current) {
      if (!isRunningRef.current) {
        try {
          recognition.start();
        } catch {
          // Ignore if already started
        }
      }
    } else {
      if (isRunningRef.current) {
        try {
          recognition.stop();
        } catch {
          // ignore
        }
      }
    }
  }, [voiceState, connected, enabled, isSupported]);

  return {
    isSupported,
    isActive,
    lastDetected,
  };
}
