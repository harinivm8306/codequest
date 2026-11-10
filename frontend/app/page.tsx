"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Conversation } from "@/components/Conversation";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { SpeakerIcon } from "@/components/Icons";
import { api, ApiError, ensureProfile } from "@/lib/api";
import { LANGS, t, type Lang } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { getItem, K, setItem } from "@/lib/store";
import { speakBrowser, stopSpeaking } from "@/lib/voice";

export default function Home() {
  const { lang, chosen, setLang, ready } = useLang();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [consent, setConsent] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    if (!ready || !chosen) return;
    let live = true;
    ensureProfile(lang)
      .then(async (id) => {
        const p = await api.getProfile(id);
        if (!live) return;
        setProfileId(id);
        setConsent(p.consent_given);
        if (p.language !== lang) api.patchProfile(id, { language: lang }).catch(() => {});
      })
      .catch((e) => setError(e instanceof ApiError && e.code === "offline" ? t("offline", lang) : t("error", lang)));
    return () => {
      live = false;
    };
  }, [ready, chosen, lang]);

  if (!ready) return null;

  if (!chosen) return <LanguagePicker onPick={(l) => setLang(l)} onHelper={(l) => { setItem(K.role, "sahayak"); setLang(l); router.push("/sahayak/"); }} />;

  return (
    <Shell>
      {error && <ErrorNote message={error} />}
      {!error && consent === null && <Spinner label={t("thinking", lang)} />}
      {consent === false && profileId && (
        <Consent
          onAgree={async () => {
            stopSpeaking();
            await api.patchProfile(profileId, { consent_given: true, language: lang });
            setConsent(true);
          }}
        />
      )}
      {consent && profileId && <Conversation profileId={profileId} />}
    </Shell>
  );
}

function LanguagePicker({ onPick, onHelper }: { onPick: (l: Lang) => void; onHelper: (l: Lang) => void }) {
  const [helperFor, setHelperFor] = useState(false);
  const role = typeof window !== "undefined" ? getItem(K.role) : null;
  return (
    <main className="mx-auto flex min-h-dvh max-w-xl flex-col px-5 pb-8 pt-10">
      <div className="mb-8 flex items-center gap-3 text-stamp">
        <span className="grid h-14 w-14 place-items-center rounded-full border-[3px] border-stamp text-2xl font-bold">ஸ</span>
        <div>
          <p className="text-2xl font-bold leading-tight">SchemeSathi</p>
          <p className="text-muted">திட்டச் சாதி · स्कीम साथी</p>
        </div>
      </div>
      <h1 className="mb-2 text-2xl font-bold leading-snug">
        உங்களுக்குக் கிடைக்கும் அரசுத் திட்டங்களைக் கண்டறியுங்கள்.
      </h1>
      <p className="mb-1 text-lg text-muted">जानिए कौन सी सरकारी योजनाएँ आपको मिल सकती हैं।</p>
      <p className="mb-8 text-lg text-muted">Find the government schemes you can get. Just speak.</p>

      <div className="space-y-3">
        {LANGS.map((l) => (
          <button key={l.id} onClick={() => (helperFor ? onHelper(l.id) : onPick(l.id))}
            className="flex w-full items-center justify-between rounded-2xl border-2 border-stamp bg-card px-5 py-4 text-left text-2xl font-bold text-stamp active:bg-stamp active:text-white">
            {l.name}
            <span className="text-base font-semibold text-muted">{l.id === "ta" ? "Tamil" : l.id === "hi" ? "Hindi" : ""}</span>
          </button>
        ))}
      </div>
      <button onClick={() => setHelperFor((v) => !v)} aria-pressed={helperFor}
        className={`mt-8 self-start rounded-xl px-4 py-3 text-left font-semibold ${helperFor ? "bg-stamp-soft text-stamp" : "text-muted underline underline-offset-4"}`}>
        {helperFor ? "✓ " : ""}
        {role === "sahayak" ? "Sahayak / சகாயக் / सहायक" : "I am helping others · நான் மற்றவர்களுக்கு உதவுகிறேன் · मैं दूसरों की मदद करता हूँ"}
      </button>
    </main>
  );
}

function Consent({ onAgree }: { onAgree: () => void }) {
  const { lang } = useLang();
  const [noVoice, setNoVoice] = useState(false);
  useEffect(() => {
    const id = window.setTimeout(() => setNoVoice(!speakBrowser(t("consentBody", lang), lang)), 400);
    return () => {
      window.clearTimeout(id);
      stopSpeaking();
    };
  }, [lang]);
  return (
    <section className="py-6">
      <h1 className="mb-4 text-2xl font-bold">{t("consentTitle", lang)}</h1>
      <div className="rounded-2xl border border-line bg-card p-5">
        <p className="text-lg leading-relaxed">{t("consentBody", lang)}</p>
        <button onClick={() => setNoVoice(!speakBrowser(t("consentBody", lang), lang))}
          className="mt-4 flex min-h-[48px] items-center gap-2 rounded-xl border border-stamp px-4 font-semibold text-stamp">
          <SpeakerIcon /> {t("listen", lang)}
        </button>
        {noVoice && <p className="mt-2 text-sm text-muted">{t("noVoiceOut", lang)}</p>}
      </div>
      <button onClick={onAgree} className="mt-6 w-full rounded-2xl bg-stamp px-5 py-4 text-xl font-bold text-white">
        {t("agree", lang)}
      </button>
    </section>
  );
}
