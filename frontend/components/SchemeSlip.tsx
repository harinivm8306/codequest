"use client";

import Link from "next/link";
import type { SchemeView } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { CheckIcon, ChevronIcon } from "./Icons";

const TONE = {
  eligible: { edge: "bg-leaf", stamp: "border-leaf text-leaf", key: "likelyEligible" },
  almost: { edge: "bg-turmeric-bright", stamp: "border-turmeric text-turmeric", key: "almost" },
  needs_info: { edge: "bg-turmeric-bright", stamp: "border-turmeric text-turmeric", key: "needInfo" },
  not_eligible: { edge: "bg-line", stamp: "border-muted text-muted", key: "whyNot" },
} as const;

/**
 * A scheme as a perforated counterfoil slip — the kind of stamped receipt a citizen
 * gets at a government counter. The tear-off stub carries the verdict stamp.
 */
export function SchemeSlip({ s, tone }: { s: SchemeView; tone: keyof typeof TONE }) {
  const { lang } = useLang();
  const k = TONE[tone];
  const reasons = tone === "eligible" ? s.passed : s.failed;
  return (
    <Link href={`/scheme/?id=${s.id}`} className="slip group block">
      <div className={`slip-stub ${k.edge}`} aria-hidden />
      <div className="slip-body">
        <div className="flex items-start gap-3">
          <h3 className="flex-1 text-lg font-bold leading-snug text-ink">{s.name}</h3>
          <ChevronIcon className="mt-1 h-5 w-5 shrink-0 text-muted" />
        </div>
        <p className="mt-1 text-[1.02rem] text-ink">{s.benefit}</p>
        {tone !== "needs_info" && reasons.length > 0 && (
          <ul className="mt-2 space-y-1 text-sm text-muted">
            {reasons.slice(0, tone === "eligible" ? 3 : 2).map((c) => (
              <li key={c.id} className="flex gap-1.5">
                {tone === "eligible" ? <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-leaf" /> : <span className="mt-0.5 shrink-0 text-turmeric">•</span>}
                <span>{c.text}</span>
              </li>
            ))}
          </ul>
        )}
        <span className={`stamp mt-3 ${k.stamp}`}>{t(k.key, lang)}</span>
      </div>
    </Link>
  );
}
