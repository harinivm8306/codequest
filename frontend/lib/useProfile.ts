"use client";

import { useEffect, useState } from "react";
import { ApiError, ensureProfile } from "./api";
import { t } from "./i18n";
import { useLang } from "./lang";

/** Resolve the active profile id for pages other than the conversation. */
export function useProfileId(): { id: string | null; error: string | null } {
  const { lang, ready } = useLang();
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (!ready) return;
    ensureProfile(lang)
      .then(setId)
      .catch((e) => setError(e instanceof ApiError && e.code === "offline" ? t("offline", lang) : t("error", lang)));
  }, [ready, lang]);
  return { id, error };
}
