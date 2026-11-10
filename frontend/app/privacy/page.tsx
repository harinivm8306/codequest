"use client";

import { Shell } from "@/components/Shell";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";

export default function Privacy() {
  const { lang } = useLang();
  return (
    <Shell>
      <div className="pt-5">
        <h1 className="text-2xl font-bold">{t("privacy", lang)}</h1>
        <p className="mt-3 text-lg leading-relaxed">{t("privacyBody", lang)}</p>
        <p className="mt-4 text-lg">{t("finalDecision", lang)}</p>
        <p className="mt-6 text-muted">{t("deleteAll", lang)}: {t("menu", lang)} ☰</p>
      </div>
    </Shell>
  );
}
