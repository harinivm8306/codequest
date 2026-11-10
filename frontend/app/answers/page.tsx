"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { API_BASE, api, type Question } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { useProfileId } from "@/lib/useProfile";

/** Everything the person has told Sathi, editable. Doubles as Sahayak quick entry. */
export default function Answers() {
  const { lang } = useLang();
  const { id, error } = useProfileId();
  const [fields, setFields] = useState<Question[] | null>(null);
  const [facts, setFacts] = useState<Record<string, unknown>>({});
  const [label, setLabel] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([fetch(`${API_BASE}/api/v1/fields?lang=${lang}`).then((r) => r.json()), api.getProfile(id)]).then(([f, p]) => {
      setFields(f.fields);
      setFacts(p.facts);
      setLabel(p.label);
    });
  }, [id, lang]);

  const set = async (field: string, value: unknown) => {
    if (!id) return;
    const p = await api.patchProfile(id, { facts: { [field]: value } });
    setFacts(p.facts);
  };

  return (
    <Shell>
      {error && <ErrorNote message={error} />}
      {!fields && !error && <Spinner label={t("thinking", lang)} />}
      {fields && (
        <div className="pt-5">
          <h1 className="text-2xl font-bold">{t("myAnswers", lang)}{label ? `: ${label}` : ""}</h1>
          <p className="mb-5 mt-1 text-muted">{t("answersIntro", lang)}</p>
          <div className="space-y-4">
            {fields.map((q) => (
              <section key={q.key} className="rounded-2xl border border-line bg-card p-4">
                <h2 className="font-semibold">{q.text}</h2>
                {q.options.length === 0 ? (
                  <NumberField value={facts[q.key] as number | undefined} onSave={(v) => set(q.key, v)} />
                ) : (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {q.options.map((o) => {
                      const on = facts[o.field] === o.value;
                      return (
                        <button key={`${o.field}-${String(o.value)}`} aria-pressed={on}
                          onClick={() => set(o.field, q.multi && on ? (o.field === "family_govt_pension" ? "none" : false) : o.value)}
                          className={`min-h-[44px] rounded-xl border-2 px-3 py-1.5 text-left font-semibold ${on ? "border-stamp bg-stamp text-white" : "border-line text-ink"}`}>
                          {o.label}
                        </button>
                      );
                    })}
                    {q.multi && (
                      <button onClick={async () => { for (const o of q.options) if (facts[o.field] === undefined) await set(o.field, o.field === "family_govt_pension" ? "none" : false); }}
                        className="min-h-[44px] rounded-xl border-2 border-dashed border-line px-3 font-semibold text-muted">{q.none_label}</button>
                    )}
                  </div>
                )}
                {!q.multi && facts[q.key] === undefined && <p className="mt-1 text-sm text-muted">{t("notAnswered", lang)}</p>}
                {!q.multi && facts[q.key] !== undefined && <button onClick={() => set(q.key, null)} className="mt-1 text-sm text-muted underline">{t("clear", lang)}</button>}
              </section>
            ))}
          </div>
          <Link href="/results/" className="mt-6 block rounded-2xl bg-leaf px-5 py-4 text-center text-xl font-bold text-white">{t("seeSchemes", lang)}</Link>
        </div>
      )}
    </Shell>
  );
}

function NumberField({ value, onSave }: { value?: number; onSave: (v: number) => void }) {
  const { lang } = useLang();
  const [v, setV] = useState(value?.toString() ?? "");
  useEffect(() => setV(value?.toString() ?? ""), [value]);
  return (
    <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (v.trim()) onSave(Number(v)); }}>
      <input value={v} onChange={(e) => setV(e.target.value.replace(/\D/g, ""))} inputMode="numeric" className="min-h-[48px] w-28 rounded-xl border-2 border-line px-3 text-lg" aria-label="number" />
      <button disabled={v === (value?.toString() ?? "")} className="min-h-[48px] rounded-xl border-2 border-stamp px-4 font-semibold text-stamp disabled:opacity-40">{t("save", lang)}</button>
    </form>
  );
}
