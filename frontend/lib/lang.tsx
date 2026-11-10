"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { getItem, K, setItem } from "./store";
import type { Lang } from "./i18n";

type Ctx = { lang: Lang; chosen: boolean; setLang: (l: Lang) => void; ready: boolean };
const LangCtx = createContext<Ctx>({ lang: "en", chosen: false, setLang: () => {}, ready: false });

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setL] = useState<Lang>("en");
  const [chosen, setChosen] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    const saved = getItem(K.lang) as Lang | null;
    if (saved === "ta" || saved === "hi" || saved === "en") {
      setL(saved);
      setChosen(true);
    }
    setReady(true);
  }, []);
  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);
  const setLang = (l: Lang) => {
    setItem(K.lang, l);
    setL(l);
    setChosen(true);
  };
  return <LangCtx.Provider value={{ lang, chosen, setLang, ready }}>{children}</LangCtx.Provider>;
}

export const useLang = () => useContext(LangCtx);
