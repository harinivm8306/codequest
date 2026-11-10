"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SchemeSlip } from "@/components/SchemeSlip";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { SpeakerIcon } from "@/components/Icons";
import { api, type Eligibility } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { useProfileId } from "@/lib/useProfile";
import { speakBrowser } from "@/lib/voice";

export default function Results() {
  const { lang } = useLang();
  const { id, error } = useProfileId();
  const [e, setE] = useState<Eligibility | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (id) api.eligibility(id, lang).then(setE).catch(() => setErr(t("error", lang)));
  }, [id, lang]);

  const readAloud = () => {
    if (!e) return;
    const names = e.eligible.map((s) => s.name).join(". ");
    speakBrowser(`${t("yourSchemes", lang)}. ${names}. ${e.disclaimer}`, lang);
  };

  const almostIds = new Set(e?.almost.map((s) => s.id));
  const others = e?.not_eligible.filter((s) => !almostIds.has(s.id)) ?? [];

  return (
    <Shell>
      {(error || err) && <ErrorNote message={(error || err)!} />}
      {!e && !error && !err && <Spinner label={t("thinking", lang)} />}
      {e && (
        <div className="pt-5">
          <div className="mb-4 flex items-start gap-3">
            <h1 className="flex-1 text-2xl font-bold leading-tight">{t("yourSchemes", lang)}</h1>
            <button onClick={readAloud} className="grid h-12 w-12 shrink-0 place-items-center rounded-full border border-line bg-card text-stamp" aria-label={t("listen", lang)}>
              <SpeakerIcon />
            </button>
          </div>

          {e.eligible.length === 0 && <p className="mb-4 rounded-2xl bg-card p-4 text-lg">{t("noneYet", lang)}</p>}
          <div className="space-y-3">
            {e.eligible.map((s) => <SchemeSlip key={s.id} s={s} tone="eligible" />)}
          </div>

          {e.conflicts.length > 0 && (
            <div className="mt-4 rounded-2xl border-2 border-turmeric-bright bg-turmeric-soft p-4">
              <p className="mb-1 font-bold text-turmeric">{t("heads_up", lang)}</p>
              {e.conflicts.slice(0, 2).map((c) => <p key={c.schemes.join()} className="text-ink">{c.note}</p>)}
            </div>
          )}

          {e.needs_info.length > 0 && (
            <section className="mt-8">
              <h2 className="mb-1 text-xl font-bold">{t("needInfo", lang)}</h2>
              <Link href="/" className="mb-3 inline-block font-semibold text-stamp underline underline-offset-4">{t("answerMore", lang)}</Link>
              <div className="space-y-3">{e.needs_info.map((s) => <SchemeSlip key={s.id} s={s} tone="needs_info" />)}</div>
            </section>
          )}

          {e.almost.length > 0 && (
            <section className="mt-8">
              <h2 className="mb-3 text-xl font-bold">{t("almost", lang)}</h2>
              <div className="space-y-3">{e.almost.map((s) => <SchemeSlip key={s.id} s={s} tone="almost" />)}</div>
            </section>
          )}

          {e.upcoming.length > 0 && (
            <section className="mt-8 rounded-2xl border border-line bg-card p-4">
              <h2 className="mb-2 text-lg font-bold">{t("comingUp", lang)}</h2>
              <ul className="space-y-1">
                {e.upcoming.map((u) => (
                  <li key={u.id}><span className="font-semibold">{u.name}</span> <span className="text-muted">— {t("inYears", lang, { age: u.at_age, n: u.in_years })}</span></li>
                ))}
              </ul>
            </section>
          )}

          {others.length > 0 && (
            <details className="mt-8">
              <summary className="cursor-pointer py-2 text-lg font-semibold text-muted">{t("notEligibleAll", lang)} ({others.length})</summary>
              <div className="mt-2 space-y-3">{others.map((s) => <SchemeSlip key={s.id} s={s} tone="not_eligible" />)}</div>
            </details>
          )}

          <p className="mt-8 text-sm text-muted">{e.disclaimer}</p>
        </div>
      )}
    </Shell>
  );
}
