"use client";

import { useEffect, useState } from "react";
import { DocumentCheck } from "@/components/DocumentCheck";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { api, type Doc } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { useProfileId } from "@/lib/useProfile";

export default function Documents() {
  const { lang } = useLang();
  const { id, error } = useProfileId();
  const [docs, setDocs] = useState<Doc[] | null>(null);
  const [types, setTypes] = useState<{ id: string; label: string; ocr: boolean }[]>([]);
  const [docType, setDocType] = useState("");
  const [name, setName] = useState("");
  const [savedName, setSavedName] = useState("");
  const [round, setRound] = useState(0);

  const load = async () => {
    if (!id) return;
    const [d, p] = await Promise.all([api.documents(id), api.getProfile(id)]);
    setDocs(d.documents);
    setTypes(d.types);
    const n = String(p.facts.name ?? "");
    setName(n);
    setSavedName(n);
  };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [id, lang]);

  return (
    <Shell>
      {error && <ErrorNote message={error} />}
      {!docs && !error && <Spinner label={t("thinking", lang)} />}
      {docs && id && (
        <div className="pt-5">
          <h1 className="text-2xl font-bold">{t("docDoctor", lang)}</h1>
          <p className="mt-1 text-lg text-muted">{t("docDoctorIntro", lang)}</p>

          <form className="mt-5" onSubmit={async (e) => { e.preventDefault(); await api.patchProfile(id, { facts: { name: name.trim() || null } }); setSavedName(name.trim()); }}>
            <label className="block font-semibold" htmlFor="nm">{t("yourName", lang)}</label>
            <div className="mt-1 flex gap-2">
              <input id="nm" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name"
                className="min-h-[52px] min-w-0 flex-1 rounded-xl border-2 border-line bg-card px-3 text-lg focus:border-stamp" />
              <button disabled={name.trim() === savedName} className="min-h-[52px] rounded-xl border-2 border-stamp px-4 font-semibold text-stamp disabled:opacity-40">{t("save", lang)}</button>
            </div>
          </form>

          <label className="mt-5 block font-semibold" htmlFor="dt">{t("docType", lang)}</label>
          <select id="dt" value={docType} onChange={(e) => setDocType(e.target.value)} className="mt-1 min-h-[52px] w-full rounded-xl border-2 border-line bg-card px-3 text-lg">
            <option value="">{t("detectAuto", lang)}</option>
            {types.map((ty) => <option key={ty.id} value={ty.id}>{ty.label}</option>)}
          </select>
          <div className="mt-3">
            <DocumentCheck key={`${docType}-${round}`} profileId={id} docType={docType || undefined} onDone={() => { setRound((r) => r + 1); load(); }} />
          </div>

          {docs.length > 0 && (
            <section className="mt-8">
              <h2 className="mb-3 text-xl font-bold">{t("yourDocs", lang)}</h2>
              <ul className="space-y-3">
                {docs.map((d) => (
                  <li key={d.id} className="rounded-2xl border border-line bg-card p-4">
                    <p className="font-bold">{d.label}</p>
                    {"name" in d.extracted && <p className="text-muted">{String(d.extracted.name)}</p>}
                    {d.issues.length === 0 ? <p className="text-leaf">{t("allGood", lang)}</p> :
                      d.issues.map((i) => <p key={i.code} className={i.severity === "blocking" ? "text-brick" : "text-turmeric"}>{i.message}</p>)}
                    <p className="mt-2 text-sm text-muted">{d.expires_at ? t("deletesIn24", lang) : t("kept", lang)}</p>
                    <div className="mt-2 flex gap-2">
                      {d.expires_at && <button onClick={async () => { await api.keepDoc(id, d.id); load(); }} className="min-h-[44px] rounded-xl border border-line px-4 font-semibold">{t("keep", lang)}</button>}
                      <button onClick={async () => { await api.deleteDoc(id, d.id); load(); }} className="min-h-[44px] rounded-xl border border-brick/40 px-4 font-semibold text-brick">{t("remove", lang)}</button>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </Shell>
  );
}
