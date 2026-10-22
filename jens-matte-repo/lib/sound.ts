"use client";

let context: AudioContext | null = null;

function audioContext(): AudioContext | null {
  if (typeof window === "undefined") return null;
  try {
    context ??= new AudioContext();
    return context;
  } catch {
    return null;
  }
}

function tone(frequency: number, duration: number, delay = 0, volume = 0.045): void {
  const ctx = audioContext();
  if (!ctx) return;
  const oscillator = ctx.createOscillator();
  const gain = ctx.createGain();
  const start = ctx.currentTime + delay;
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.015);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain);
  gain.connect(ctx.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.03);
}

export function playCorrect(): void {
  tone(523.25, 0.12);
  tone(659.25, 0.14, 0.1);
}

export function playWrong(): void {
  tone(220, 0.16, 0, 0.035);
  tone(185, 0.2, 0.13, 0.03);
}

export function playLevelUp(): void {
  tone(523.25, 0.12);
  tone(659.25, 0.12, 0.1);
  tone(783.99, 0.2, 0.2);
}
