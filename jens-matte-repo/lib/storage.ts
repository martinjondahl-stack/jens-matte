"use client";

import type { PlayerProfile } from "@/lib/types";

const PROFILE_KEY = "jens-matte-profile-v1";
const SOUND_KEY = "jens-matte-sound-v1";

export function loadProfile(): PlayerProfile | null {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PlayerProfile;
    if (!parsed?.name || !parsed?.id) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function saveProfile(profile: PlayerProfile): void {
  try {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile));
  } catch {
    // Private mode or storage restrictions should not break the game.
  }
}

export function clearProfile(): void {
  try {
    localStorage.removeItem(PROFILE_KEY);
  } catch {
    // Ignore.
  }
}

export function loadSoundPreference(): boolean {
  try {
    return localStorage.getItem(SOUND_KEY) !== "off";
  } catch {
    return true;
  }
}

export function saveSoundPreference(enabled: boolean): void {
  try {
    localStorage.setItem(SOUND_KEY, enabled ? "on" : "off");
  } catch {
    // Ignore.
  }
}
