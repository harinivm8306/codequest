import { getItem, K, setItem } from "./store";
import type { Lang } from "./i18n";

// Same origin by default (backend serves the exported app); set NEXT_PUBLIC_API_URL when hosted separately.
export const API_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public fallback?: string) {
    super(message);
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getItem(K.token);
  const headers: Record<string, string> = { ...(init.headers as Record<string, string>) };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (init.body && !(init.body instanceof FormData)) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${API_BASE}/api/v1${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "offline", "offline");
  }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = body?.error ?? {};
    throw new ApiError(res.status, e.code ?? "error", e.message ?? res.statusText, e.fallback);
  }
  return body as T;
}

export type Option = { field: string; value: unknown; label: string };
export type Question = { key: string; text: string; multi: boolean; input?: string; options: Option[]; none_label?: string };
export type TurnResponse = {
  transcript: string | null;
  facts_added: Record<string, unknown>;
  reply_text: string;
  reply_audio_base64?: string | null;
  question: Question | null;
  next_field: string | null;
  done: boolean;
  eligible_count: number;
  facts: Record<string, unknown>;
};
export type Source = { title: string; url: string; locator: string; quality: "official" | "secondary" };
export type ClauseView = { id: string; text: string; source: Source };
export type SchemeView = {
  id: string; status: "eligible" | "not_eligible" | "needs_info"; name: string; level: string; category: string;
  benefit: string; apply_at: string; source_url: string; verified_on: string; passed: ClauseView[]; failed: ClauseView[];
  missing: string[]; office_checks: string[]; required_documents: string[]; reason: string;
  documents?: { id: string; label: string }[];
};
export type Eligibility = {
  rules_version: string; eligible: SchemeView[]; needs_info: SchemeView[]; almost: SchemeView[]; not_eligible: SchemeView[];
  conflicts: { schemes: string[]; note: string }[]; upcoming: { id: string; name: string; in_years: number; at_age: number }[];
  next_question: string | null; disclaimer: string;
};
export type Issue = { code: string; severity: "blocking" | "warning"; message: string };
export type Doc = { id: string; doc_type: string; label: string; extracted: Record<string, unknown>; issues: Issue[]; source: string; created_at: string; expires_at: string | null };
export type ChecklistItem = { doc_type: string; label: string; status: "ok" | "problem" | "missing"; issues: Issue[]; ocr_supported: boolean };
export type ProfileView = { id: string; label: string; language: Lang; consent_given: boolean; facts: Record<string, unknown>; derived: Record<string, unknown>; updated_at: string; documents: number };
export type Health = { status: string; db: string; bhashini: "ok" | "unavailable" | "not_configured"; llm: string; ocr_languages: string; schemes: number };

export const api = {
  health: () => request<Health>("/health"),
  startSession: (role: "citizen" | "sahayak" = "citizen") =>
    request<{ token: string; role: string }>("/session", { method: "POST", body: JSON.stringify({ role }) }),
  setRole: (role: "citizen" | "sahayak") => request<{ role: string }>("/session/role", { method: "POST", body: JSON.stringify({ role }) }),
  deleteSession: () => request<{ deleted: boolean }>("/session", { method: "DELETE" }),
  createProfile: (language: Lang, label = "") => request<ProfileView>("/profiles", { method: "POST", body: JSON.stringify({ language, label }) }),
  listProfiles: () => request<{ role: string; profiles: ProfileView[] }>("/profiles"),
  getProfile: (id: string) => request<ProfileView>(`/profiles/${id}`),
  patchProfile: (id: string, body: Partial<{ facts: Record<string, unknown>; language: Lang; label: string; consent_given: boolean }>) =>
    request<ProfileView>(`/profiles/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteProfile: (id: string) => request<{ deleted: boolean }>(`/profiles/${id}`, { method: "DELETE" }),
  conversation: (id: string) =>
    request<{ turns: { role: string; text: string }[]; greeting: string; question: Question | null; language: Lang }>(`/profiles/${id}/conversation`),
  chat: (profile_id: string, language: Lang, payload: { text?: string; answers?: { field: string; value: unknown; label?: string }[] }) =>
    request<TurnResponse>("/chat/turn", { method: "POST", body: JSON.stringify({ profile_id, language, ...payload }) }),
  voice: (profile_id: string, language: Lang, audio_base64: string) =>
    request<TurnResponse>("/voice/turn", { method: "POST", body: JSON.stringify({ profile_id, language, audio_base64, mime: "audio/wav", sample_rate: 16000 }) }),
  tts: (text: string, language: Lang) => request<{ audio_base64: string }>("/voice/tts", { method: "POST", body: JSON.stringify({ text, language }) }),
  eligibility: (id: string, lang: Lang) => request<Eligibility>(`/profiles/${id}/eligibility?lang=${lang}`),
  checklist: (id: string, scheme: string, lang: Lang) => request<{ scheme: SchemeView; checklist: ChecklistItem[] }>(`/profiles/${id}/checklist/${scheme}?lang=${lang}`),
  ask: (scheme: string, question: string, language: Lang) =>
    request<{ answer: string; citations: { text: string; source: Source }[]; grounded: boolean }>(`/schemes/${scheme}/ask`, { method: "POST", body: JSON.stringify({ question, language }) }),
  documents: (id: string) => request<{ documents: Doc[]; types: { id: string; label: string; ocr: boolean }[] }>(`/profiles/${id}/documents`),
  upload: (id: string, form: FormData) => request<{ document: Doc | null; issues: Issue[]; preview: string; saved: boolean }>(`/profiles/${id}/documents`, { method: "POST", body: form }),
  keepDoc: (id: string, doc: string) => request<Doc>(`/profiles/${id}/documents/${doc}/keep`, { method: "POST" }),
  deleteDoc: (id: string, doc: string) => request<{ deleted: boolean }>(`/profiles/${id}/documents/${doc}`, { method: "DELETE" }),
  packet: (id: string, scheme: string) => request<{ url: string }>(`/profiles/${id}/packets/${scheme}`, { method: "POST" }),
};

/** Make sure this device has a session and an active profile; returns the profile id. */
export async function ensureProfile(lang: Lang): Promise<string> {
  if (!getItem(K.token)) {
    const s = await api.startSession((getItem(K.role) as "citizen" | "sahayak") ?? "citizen");
    setItem(K.token, s.token);
  }
  const existing = getItem(K.profile);
  if (existing) {
    try {
      await api.getProfile(existing);
      return existing;
    } catch (e) {
      if (!(e instanceof ApiError) || e.status === 0) throw e;
      if (e.code === "bad_session") {
        setItem(K.token, null);
        setItem(K.profile, null);
        return ensureProfile(lang);
      }
    }
  }
  const p = await api.createProfile(lang);
  setItem(K.profile, p.id);
  return p.id;
}
