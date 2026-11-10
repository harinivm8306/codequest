// Per-device conveniences: session token, active profile, language.
// Browser storage can be unavailable (private mode, blocked site data), so every access is guarded
// and the app still works for the length of the page visit.

const memory: Record<string, string> = {};

export function getItem(key: string): string | null {
  try {
    return window.localStorage.getItem(key) ?? memory[key] ?? null;
  } catch {
    return memory[key] ?? null;
  }
}

export function setItem(key: string, value: string | null) {
  if (value === null) delete memory[key];
  else memory[key] = value;
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* memory fallback already set */
  }
}

export const K = { token: "ss.token", profile: "ss.profile", lang: "ss.lang", role: "ss.role" } as const;

export function clearAll() {
  Object.values(K).forEach((k) => setItem(k, null));
}
