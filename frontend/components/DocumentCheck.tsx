"use client";

import { useRef, useState } from "react";
import { api, ApiError, type Issue } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { CameraIcon, CheckIcon } from "./Icons";

/** Consent, photo, result — with manual entry when the photo cannot be read. */
export function DocumentCheck({ profileId, docType, onDone }: { profileId: string; docType?: string; onDone?: () => void }) {
  const { lang } = useLang();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [issues, setIssues] = useState<Issue[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [manual, setManual] = useState(false);
  const [fields, setFields] = useState({ name: "", issue_date: "", valid_until: "" });
  const fileRef = useRef<HTMLInputElement>(null);

  const submit = async (form: FormData) => {
    setBusy(true);
    setErr(null);
    form.set("consent", "true");
    if (docType) form.set("doc_type", docType);
    try {
      const r = await api.upload(profileId, form);
      setIssues(r.issues);
      if (r.saved && !r.issues.some((i) => i.severity === "blocking")) setTimeout(() => onDone?.(), 1600);
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : t("error", lang));
      if (e instanceof ApiError && e.fallback === "manual") setManual(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="w-full rounded-2xl bg-stamp-soft p-4">
      <label className="flex gap-3 text-[1.02rem]">
        <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-1 h-6 w-6 shrink-0 accent-stamp" />
        <span>{t("docConsent", lang)}</span>
      </label>

      {!manual ? (
        <>
          <input ref={fileRef} type="file" accept="image/*" capture="environment" className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) { const fd = new FormData(); fd.set("file", f); submit(fd); } e.target.value = ""; }} />
          <button disabled={!agreed || busy} onClick={() => fileRef.current?.click()}
            className="mt-3 flex min-h-[52px] w-full items-center justify-center gap-2 rounded-xl bg-stamp px-4 text-lg font-bold text-white disabled:opacity-40">
            <CameraIcon /> {busy ? t("checking", lang) : t("takePhoto", lang)}
          </button>
          <button onClick={() => setManual(true)} className="mt-2 min-h-[44px] text-sm font-semibold text-stamp underline underline-offset-4">{t("enterByHand", lang)}</button>
        </>
      ) : (
        <form className="mt-3 space-y-2" onSubmit={(e) => {
          e.preventDefault();
          const fd = new FormData();
          fd.set("manual_fields", JSON.stringify(Object.fromEntries(Object.entries(fields).filter(([, v]) => v.trim()))));
          submit(fd);
        }}>
          {([["name", "nameOnDoc"], ["issue_date", "issueDate"], ["valid_until", "validUntil"]] as const).map(([k, label]) => (
            <label key={k} className="block">
              <span className="text-sm font-semibold">{t(label, lang)}</span>
              <input value={fields[k]} onChange={(e) => setFields({ ...fields, [k]: e.target.value })} inputMode={k === "name" ? "text" : "numeric"}
                className="mt-1 min-h-[48px] w-full rounded-xl border-2 border-line bg-card px-3" />
            </label>
          ))}
          <button disabled={!agreed || busy || !docType} className="min-h-[52px] w-full rounded-xl bg-stamp font-bold text-white disabled:opacity-40">{t("save", lang)}</button>
        </form>
      )}

      {err && <p className="mt-3 text-brick" role="alert">{err}</p>}
      {issues && (
        <div className="mt-3" role="status">
          {issues.length === 0 ? (
            <p className="flex items-center gap-2 font-semibold text-leaf"><CheckIcon /> {t("allGood", lang)}</p>
          ) : (
            issues.map((i) => <p key={i.code} className={`mt-1 rounded-lg px-3 py-2 ${i.severity === "blocking" ? "bg-brick-soft text-brick" : "bg-turmeric-soft text-turmeric"}`}>{i.message}</p>)
          )}
        </div>
      )}
    </div>
  );
}
