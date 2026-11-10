"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { DocumentCheck } from "@/components/DocumentCheck";
import { AlertIcon, BackIcon, CheckIcon, CrossIcon, SpeakerIcon } from "@/components/Icons";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { api, API_BASE, type ChecklistItem, type ClauseView, type SchemeView, type Source } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { useProfileId } from "@/lib/useProfile";
import { speakBrowser } from "@/lib/voice";

export default function SchemePage() {
  return (
    <Suspense fallback={null}>
      <SchemeInner />
    </Suspense>
  );
}

function SchemeInner() {
  const sid = useSearchParams().get("id") ?? "";
  const { lang } = useLang();
  const { id, error } = useProfileId();
  const [data, setData] = useState<{ scheme: SchemeView; checklist: ChecklistItem[] } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [checking, setChecking] = useState<string | null>(null);

  const load = () => id && api.checklist(id, sid, lang).then(setData).catch(() => setErr(t("error", lang)));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [id, sid, lang]);

  const download = async () => {
    if (!id) return;
    const { url } = await api.packet(id, sid);
    // Navigate rather than window.open: a new tab opened after an await is popup-blocked on phones.
    window.location.assign(`${API_BASE}${url}`);
  };

  const s = data?.scheme;
  return (
    <Shell>
      {(error || err) && <ErrorNote message={(error || err)!} />}
      {!data && !error && !err && <Spinner label={t("thinking", lang)} />}
      {s && data && (
        <article className="pt-4">
          <Link href="/results/" className="no-print mb-3 inline-flex min-h-[44px] items-center gap-1 font-semibold text-stamp"><BackIcon /> {t("back", lang)}</Link>
          <h1 className="text-2xl font-bold leading-tight">{s.name}</h1>
          <span className={`stamp mt-3 ${s.status === "eligible" ? "border-leaf text-leaf" : s.status === "needs_info" ? "border-turmeric text-turmeric" : "border-muted text-muted"}`}>
            {s.status === "eligible" ? t("likelyEligible", lang) : s.status === "needs_info" ? t("needInfo", lang) : t("whyNot", lang)}
          </span>

          <Block title={t("benefit", lang)}>
            <p className="text-lg">{s.benefit}</p>
            <button onClick={() => speakBrowser(`${s.name}. ${s.benefit}. ${t("whereToApply", lang)}: ${s.apply_at}`, lang)} className="no-print mt-2 flex min-h-[44px] items-center gap-2 font-semibold text-stamp">
              <SpeakerIcon /> {t("listen", lang)}
            </button>
          </Block>

          <Block title={s.status === "eligible" ? t("why", lang) : t("whyNot", lang)}>
            <ul className="space-y-3">
              {s.passed.map((c) => <Clause key={c.id} c={c} ok />)}
              {s.failed.map((c) => <Clause key={c.id} c={c} ok={false} />)}
            </ul>
            {s.missing.length > 0 && <Link href="/" className="no-print mt-3 inline-block font-semibold text-stamp underline underline-offset-4">{t("answerMore", lang)}</Link>}
          </Block>

          <Block title={t("whereToApply", lang)}><p className="text-lg">{s.apply_at}</p></Block>

          {s.office_checks.length > 0 && (
            <Block title={t("officeChecks", lang)}>
              <ul className="list-disc space-y-1 pl-5">{s.office_checks.map((o) => <li key={o}>{o}</li>)}</ul>
            </Block>
          )}

          <Block title={t("documents", lang)}>
            <ul className="space-y-2.5">
              {data.checklist.map((c) => (
                <li key={c.doc_type} className="rounded-2xl border border-line bg-card p-3.5">
                  <div className="flex items-start gap-3">
                    <StatusDot status={c.status} />
                    <div className="flex-1">
                      <p className="font-semibold">{c.label}</p>
                      <p className={`text-sm ${c.status === "ok" ? "text-leaf" : c.status === "problem" ? "text-brick" : "text-muted"}`}>
                        {c.status === "ok" ? t("docOk", lang) : c.status === "problem" ? t("docProblem", lang) : t("docMissing", lang)}
                      </p>
                      {c.issues.map((i) => <p key={i.code} className={`mt-1 text-sm ${i.severity === "blocking" ? "text-brick" : "text-turmeric"}`}>{i.message}</p>)}
                    </div>
                  </div>
                  {c.status !== "ok" && id && (
                    <div className="no-print mt-3 flex flex-wrap gap-2">
                      {checking === c.doc_type ? (
                        <DocumentCheck profileId={id} docType={c.doc_type} onDone={() => { setChecking(null); load(); }} />
                      ) : (
                        <>
                          {c.ocr_supported && <button onClick={() => setChecking(c.doc_type)} className="min-h-[44px] rounded-xl bg-stamp px-4 font-semibold text-white">{t("checkPhoto", lang)}</button>}
                          <button onClick={async () => { const f = new FormData(); f.set("consent", "true"); f.set("doc_type", c.doc_type); await api.upload(id, f); load(); }}
                            className="min-h-[44px] rounded-xl border-2 border-stamp/40 px-4 font-semibold text-stamp">{t("iHaveIt", lang)}</button>
                        </>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Block>

          <div className="no-print mt-6 space-y-3">
            <button onClick={download} className="w-full rounded-2xl bg-stamp px-5 py-4 text-lg font-bold text-white">{t("downloadPdf", lang)}</button>
            <button onClick={() => window.print()} className="w-full rounded-2xl border-2 border-stamp px-5 py-3.5 text-lg font-bold text-stamp">{t("print", lang)}</button>
          </div>

          <Ask schemeId={sid} />
          <p className="mt-8 text-sm text-muted">{t("finalDecision", lang)}</p>
        </article>
      )}
    </Shell>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-6">
      <h2 className="mb-2 text-lg font-bold text-stamp-deep">{title}</h2>
      {children}
    </section>
  );
}

function SourceLink({ src }: { src: Source }) {
  const { lang } = useLang();
  return (
    <a href={src.url} target="_blank" rel="noopener noreferrer" className="text-sm text-stamp underline underline-offset-2">
      {src.quality === "official" ? t("source", lang) : t("sourceSecondary", lang)}: {src.title.replace(/\s*\(.*?\)/g, "").replace(/\s+—.*$/, "")}{src.locator ? `, ${src.locator}` : ""}
    </a>
  );
}

function Clause({ c, ok }: { c: ClauseView; ok: boolean }) {
  return (
    <li className="flex gap-2.5">
      <span className={`mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full ${ok ? "bg-leaf-soft text-leaf" : "bg-brick-soft text-brick"}`}>
        {ok ? <CheckIcon className="h-4 w-4" /> : <CrossIcon className="h-4 w-4" />}
      </span>
      <div>
        <p>{c.text}</p>
        <SourceLink src={c.source} />
      </div>
    </li>
  );
}

function StatusDot({ status }: { status: ChecklistItem["status"] }) {
  if (status === "ok") return <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-leaf text-white"><CheckIcon className="h-4 w-4" /></span>;
  if (status === "problem") return <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-brick text-white"><AlertIcon className="h-4 w-4" /></span>;
  return <span className="h-7 w-7 shrink-0 rounded-full border-2 border-dashed border-muted" />;
}

function Ask({ schemeId }: { schemeId: string }) {
  const { lang } = useLang();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [a, setA] = useState<{ answer: string; citations: { text: string; source: Source }[] } | null>(null);
  return (
    <section className="no-print mt-8 rounded-2xl border border-line bg-card p-4">
      <h2 className="mb-2 text-lg font-bold">{t("askQuestion", lang)}</h2>
      <form className="flex gap-2" onSubmit={async (e) => { e.preventDefault(); if (!q.trim()) return; setBusy(true); try { setA(await api.ask(schemeId, q, lang)); } finally { setBusy(false); } }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("askPlaceholder", lang)} aria-label={t("askQuestion", lang)}
          className="min-h-[52px] min-w-0 flex-1 rounded-xl border-2 border-line px-3 text-[1.02rem] focus:border-stamp" />
        <button disabled={busy} className="min-h-[52px] rounded-xl bg-stamp px-4 font-bold text-white disabled:opacity-50">{t("ask", lang)}</button>
      </form>
      {a && (
        <div className="mt-3">
          <p className="text-lg">{a.answer}</p>
          {a.citations.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="text-sm text-muted">{t("basedOn", lang)}:</p>
              {[...new Map(a.citations.map((c) => [c.source.url, c.source])).values()].map((s) => <div key={s.url}><SourceLink src={s} /></div>)}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
