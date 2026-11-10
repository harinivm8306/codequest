"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ErrorNote, Shell, Spinner } from "@/components/Shell";
import { api, ApiError, type ProfileView } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { getItem, K, setItem } from "@/lib/store";

/** Sahayak (helper) mode: one helper, many families, data never mixed. */
export default function Sahayak() {
  const { lang } = useLang();
  const router = useRouter();
  const [profiles, setProfiles] = useState<ProfileView[] | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [label, setLabel] = useState("");
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    setItem(K.role, "sahayak");
    if (!getItem(K.token)) setItem(K.token, (await api.startSession("sahayak")).token);
    else await api.setRole("sahayak");
    setProfiles((await api.listProfiles()).profiles);
    setActive(getItem(K.profile));
  };
  useEffect(() => {
    load().catch((e) => setErr(e instanceof ApiError && e.code === "offline" ? t("offline", lang) : t("error", lang)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const use = (id: string, to: string) => {
    setItem(K.profile, id);
    setActive(id);
    router.push(to);
  };

  return (
    <Shell>
      {err && <ErrorNote message={err} />}
      {!profiles && !err && <Spinner label={t("thinking", lang)} />}
      {profiles && (
        <div className="pt-5">
          <h1 className="text-2xl font-bold">{t("families", lang)}</h1>
          <form className="mt-4 flex gap-2" onSubmit={async (e) => {
            e.preventDefault();
            const p = await api.createProfile(lang, label.trim());
            await api.patchProfile(p.id, { consent_given: false });
            setLabel("");
            use(p.id, "/");
          }}>
            <input value={label} onChange={(e) => setLabel(e.target.value)} placeholder={t("personName", lang)} aria-label={t("personName", lang)}
              className="min-h-[52px] min-w-0 flex-1 rounded-xl border-2 border-line bg-card px-3 text-lg focus:border-stamp" />
            <button className="min-h-[52px] rounded-xl bg-stamp px-4 font-bold text-white">{t("addFamily", lang)}</button>
          </form>

          {profiles.length === 0 && <p className="mt-6 text-lg text-muted">{t("noFamilies", lang)}</p>}
          <ul className="mt-6 space-y-3">
            {profiles.map((p) => (
              <li key={p.id} className={`rounded-2xl border-2 bg-card p-4 ${p.id === active ? "border-stamp" : "border-line"}`}>
                <div className="flex items-baseline gap-2">
                  <p className="flex-1 text-lg font-bold">{p.label || p.id}</p>
                  {p.id === active && <span className="stamp border-stamp text-stamp">{t("helping", lang)}</span>}
                </div>
                <p className="text-sm text-muted">
                  {[p.facts.age && `${p.facts.age}`, p.facts.district as string].filter(Boolean).join(", ")}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={() => use(p.id, "/")} className="min-h-[44px] rounded-xl bg-stamp px-4 font-semibold text-white">{t("talk", lang)}</button>
                  <button onClick={() => use(p.id, "/answers/")} className="min-h-[44px] rounded-xl border-2 border-stamp/40 px-4 font-semibold text-stamp">{t("quickEntry", lang)}</button>
                  <button onClick={() => use(p.id, "/results/")} className="min-h-[44px] rounded-xl border-2 border-stamp/40 px-4 font-semibold text-stamp">{t("seeSchemes", lang)}</button>
                </div>
              </li>
            ))}
          </ul>
          <Link href="/privacy/" className="mt-8 inline-block text-muted underline underline-offset-4">{t("privacy", lang)}</Link>
        </div>
      )}
    </Shell>
  );
}
