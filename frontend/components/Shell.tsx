"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "@/lib/api";
import { LANGS, t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { clearAll, getItem, K } from "@/lib/store";
import { CloseIcon, MenuIcon } from "./Icons";

export function Shell({ children, title }: { children: ReactNode; title?: string }) {
  const { lang, setLang } = useLang();
  const [open, setOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleted, setDeleted] = useState(false);
  const [role, setRole] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const router = useRouter();

  useEffect(() => {
    setRole(getItem(K.role));
    const on = () => setOffline(!navigator.onLine);
    on();
    window.addEventListener("online", on);
    window.addEventListener("offline", on);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", on);
    };
  }, []);

  const changeLang = async (l: typeof lang) => {
    setLang(l);
    const pid = getItem(K.profile);
    if (pid) api.patchProfile(pid, { language: l }).catch(() => {});
  };

  const deleteAll = async () => {
    try {
      await api.deleteSession();
    } catch {
      /* already gone is fine */
    }
    clearAll();
    setConfirmDelete(false);
    setOpen(false);
    setDeleted(true);
  };

  const links: [string, Parameters<typeof t>[0]][] = [
    ["/", "talk"],
    ["/results/", "seeSchemes"],
    ["/documents/", "docDoctor"],
    ["/answers/", "myAnswers"],
    ...(role === "sahayak" ? ([["/sahayak/", "families"]] as [string, Parameters<typeof t>[0]][]) : []),
    ["/privacy/", "privacy"],
  ];

  return (
    <div className="mx-auto flex min-h-dvh max-w-xl flex-col">
      <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-line bg-paper/95 px-4 py-2 backdrop-blur">
        <Link href="/" className="mr-auto flex items-center gap-2 rounded-lg py-1 pr-2 font-bold text-stamp" aria-label={t("appName", lang)}>
          <span className="grid h-9 w-9 place-items-center rounded-full border-2 border-stamp text-[0.95rem] leading-none">ஸ</span>
          <span className="whitespace-nowrap text-base">{title ?? t("appName", lang)}</span>
        </Link>
        <div className="flex rounded-full border border-line bg-card p-0.5" role="group" aria-label={t("chooseLanguage", lang)}>
          {LANGS.map((l) => (
            <button key={l.id} onClick={() => changeLang(l.id)} aria-pressed={lang === l.id}
              className={`min-h-[40px] rounded-full px-2.5 text-sm font-semibold ${lang === l.id ? "bg-stamp text-white" : "text-muted"}`}>
              {l.id === "en" ? "En" : l.name}
            </button>
          ))}
        </div>
        <button onClick={() => setOpen(true)} className="grid h-12 w-12 place-items-center rounded-full text-ink" aria-label={t("menu", lang)}>
          <MenuIcon />
        </button>
      </header>

      {offline && <p className="bg-turmeric-soft px-4 py-2 text-sm text-turmeric" role="status">{t("offline", lang)}</p>}

      <main className="flex flex-1 flex-col px-4 pb-6">{deleted ? <Deleted onRestart={() => { setDeleted(false); router.push("/"); window.location.reload(); }} /> : children}</main>

      {open && (
        <div className="fixed inset-0 z-40 bg-ink/40" onClick={() => setOpen(false)}>
          <nav className="absolute right-0 top-0 flex h-full w-[min(88vw,22rem)] flex-col bg-card p-4 shadow-xl" onClick={(e) => e.stopPropagation()} aria-label={t("menu", lang)}>
            <button onClick={() => setOpen(false)} className="mb-2 grid h-12 w-12 place-items-center self-end rounded-full" aria-label={t("cancel", lang)}>
              <CloseIcon />
            </button>
            {links.map(([href, key]) => (
              <Link key={href} href={href} onClick={() => setOpen(false)} className="rounded-xl px-3 py-3.5 text-lg font-semibold text-ink hover:bg-stamp-soft">
                {t(key, lang)}
              </Link>
            ))}
            <div className="mt-auto border-t border-line pt-4">
              {!confirmDelete ? (
                <button onClick={() => setConfirmDelete(true)} className="w-full rounded-xl border-2 border-brick px-4 py-3 text-left font-semibold text-brick">
                  {t("deleteAll", lang)}
                </button>
              ) : (
                <div className="rounded-xl bg-brick-soft p-3">
                  <p className="mb-3 text-sm text-ink">{t("deleteConfirm", lang)}</p>
                  <div className="flex gap-2">
                    <button onClick={deleteAll} className="flex-1 rounded-lg bg-brick px-3 py-3 font-semibold text-white">{t("deleteYes", lang)}</button>
                    <button onClick={() => setConfirmDelete(false)} className="rounded-lg border border-line bg-card px-3 py-3 font-semibold">{t("cancel", lang)}</button>
                  </div>
                </div>
              )}
            </div>
          </nav>
        </div>
      )}
    </div>
  );
}

function Deleted({ onRestart }: { onRestart: () => void }) {
  const { lang } = useLang();
  return (
    <div className="my-auto py-16 text-center">
      <p className="mb-6 text-xl font-semibold">{t("deleted", lang)}</p>
      <button onClick={onRestart} className="rounded-xl bg-stamp px-6 py-3.5 text-lg font-semibold text-white">{t("startAgain", lang)}</button>
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-3 py-8 text-muted" role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-stamp border-t-transparent motion-reduce:animate-none" />
      {label}
    </p>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return <p className="my-3 rounded-xl bg-brick-soft px-4 py-3 text-brick" role="alert">{message}</p>;
}
