"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Option, type Question, type TurnResponse } from "@/lib/api";
import { t } from "@/lib/i18n";
import { useLang } from "@/lib/lang";
import { browserRecognitionAvailable, listenOnce, playWav, recordAvailable, speakBrowser, stopSpeaking, WavRecorder } from "@/lib/voice";
import { CheckIcon, KeyboardIcon, MicIcon, SpeakerIcon, StopIcon } from "./Icons";

type Mode = "bhashini" | "browser" | "none";
type Phase = "idle" | "listening" | "thinking";

export function Conversation({ profileId }: { profileId: string }) {
  const { lang } = useLang();
  const [mode, setMode] = useState<Mode | null>(null);
  const [bhashiniOk, setBhashiniOk] = useState(false);
  const [phase, setPhase] = useState<Phase>("idle");
  const [say, setSay] = useState<string>("");
  const [heard, setHeard] = useState<string | null>(null);
  const [question, setQuestion] = useState<Question | null>(null);
  const [done, setDone] = useState(false);
  const [answeredAny, setAnsweredAny] = useState(false);
  const [eligibleCount, setEligibleCount] = useState(0);
  const [typing, setTyping] = useState(false);
  const [draft, setDraft] = useState("");
  const [picked, setPicked] = useState<Option[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [voiceOutMissing, setVoiceOutMissing] = useState(false);
  const recorder = useRef<WavRecorder | null>(null);
  const stopBrowser = useRef<(() => void) | null>(null);

  const speak = useCallback(
    async (text: string, audio?: string | null) => {
      if (audio) return playWav(audio);
      if (bhashiniOk) {
        try {
          const r = await api.tts(text, lang);
          return playWav(r.audio_base64);
        } catch {
          /* fall through to the browser voice */
        }
      }
      if (!speakBrowser(text, lang)) setVoiceOutMissing(true);
    },
    [bhashiniOk, lang],
  );

  // voice capability + opening line
  useEffect(() => {
    let live = true;
    (async () => {
      let ok = false;
      try {
        ok = (await api.health()).bhashini === "ok";
      } catch {
        /* offline handled by the shell */
      }
      const m: Mode = ok && recordAvailable() ? "bhashini" : browserRecognitionAvailable() ? "browser" : "none";
      if (!live) return;
      setBhashiniOk(ok);
      setMode(m);
      if (m === "none") setTyping(true);
      const c = await api.conversation(profileId);
      if (!live) return;
      const last = [...c.turns].reverse().find((x) => x.role === "assistant");
      const text = c.question && c.turns.length ? c.question.text : last && !c.question ? last.text : c.greeting;
      setSay(text);
      setQuestion(c.question);
      setAnsweredAny(c.turns.length > 0);
      setDone(c.turns.length > 0 && !c.question);
    })().catch(() => setNotice(t("error", lang)));
    return () => {
      live = false;
      stopSpeaking();
    };
  }, [profileId, lang]);

  const handle = (r: TurnResponse) => {
    setSay(r.reply_text);
    setQuestion(r.question);
    setDone(r.done);
    setEligibleCount(r.eligible_count);
    setAnsweredAny(true);
    setPicked([]);
    speak(r.reply_text, r.reply_audio_base64);
  };

  const send = async (payload: { text?: string; answers?: { field: string; value: unknown; label?: string }[] }) => {
    stopSpeaking();
    setPhase("thinking");
    setNotice(null);
    try {
      handle(await api.chat(profileId, lang, payload));
      if (payload.text) setHeard(payload.text);
    } catch (e) {
      setNotice(e instanceof ApiError && e.code === "offline" ? t("offline", lang) : (e as Error).message);
    } finally {
      setPhase("idle");
    }
  };

  const startListening = async () => {
    stopSpeaking();
    setNotice(null);
    if (mode === "bhashini") {
      try {
        recorder.current = new WavRecorder();
        await recorder.current.start(30, () => stopListening());
        setPhase("listening");
      } catch {
        setNotice(t("micDenied", lang));
      }
    } else if (mode === "browser") {
      try {
        const l = listenOnce(lang);
        stopBrowser.current = l.stop;
        setPhase("listening");
        const text = await l.promise;
        stopBrowser.current = null;
        if (text) {
          setHeard(text);
          await send({ text });
        } else setPhase("idle");
      } catch (e) {
        setPhase("idle");
        const msg = (e as Error).message;
        setNotice(msg === "not-allowed" || msg === "service-not-allowed" ? t("micDenied", lang) : msg === "no-speech" ? t("tapToSpeak", lang) : t("noMic", lang));
      }
    }
  };

  const stopListening = async () => {
    if (mode === "browser") {
      stopBrowser.current?.();
      return;
    }
    if (!recorder.current) return;
    setPhase("thinking");
    try {
      const audio = await recorder.current.stop();
      recorder.current = null;
      const r = await api.voice(profileId, lang, audio);
      setHeard(r.transcript);
      handle(r);
    } catch (e) {
      if (e instanceof ApiError && e.fallback === "browser") {
        setBhashiniOk(false);
        setMode(browserRecognitionAvailable() ? "browser" : "none");
        if (!browserRecognitionAvailable()) setTyping(true);
      }
      setNotice(e instanceof ApiError && e.code === "no_speech" ? e.message : e instanceof ApiError && e.fallback ? t("noMic", lang) : t("error", lang));
    } finally {
      setPhase("idle");
    }
  };

  const tapOption = (o: Option) => {
    if (question?.multi) {
      setPicked((p) => (p.some((x) => x.field === o.field && x.value === o.value) ? p.filter((x) => !(x.field === o.field && x.value === o.value)) : [...p.filter((x) => x.field !== o.field), o]));
      return;
    }
    setHeard(o.label);
    send({ answers: [{ field: o.field, value: o.value, label: o.label }] });
  };

  const inputMode = question?.input === "int" ? "numeric" : "text";

  return (
    <div className="flex flex-1 flex-col pt-5">
      {heard && (
        <p className="mb-3 self-end rounded-2xl rounded-br-md bg-stamp-soft px-4 py-2 text-right text-ink">
          <span className="block text-sm text-muted">{t("heard", lang)}</span>
          {heard}
        </p>
      )}

      <section className="rounded-3xl border border-line bg-card p-5" aria-live="polite">
        <p className={`text-xl font-semibold leading-snug ${phase === "thinking" ? "opacity-50" : ""}`}>{say}</p>
        <button onClick={() => speak(say)} className="mt-3 flex min-h-[44px] items-center gap-2 rounded-xl px-1 font-semibold text-stamp" aria-label={t("listen", lang)}>
          <SpeakerIcon /> {t("listen", lang)}
        </button>
        {voiceOutMissing && <p className="text-sm text-muted">{t("noVoiceOut", lang)}</p>}
      </section>

      {question && question.options.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2.5" role="group" aria-label={question.text}>
          {question.options.map((o) => {
            const on = picked.some((x) => x.field === o.field && x.value === o.value);
            return (
              <button key={`${o.field}-${String(o.value)}`} onClick={() => tapOption(o)} disabled={phase !== "idle"} aria-pressed={question.multi ? on : undefined}
                className={`min-h-[52px] rounded-2xl border-2 px-4 py-2 text-left text-[1.05rem] font-semibold disabled:opacity-50 ${on ? "border-stamp bg-stamp text-white" : "border-stamp/40 bg-card text-stamp-deep"}`}>
                {question.multi && <span className={`mr-2 inline-grid h-5 w-5 place-items-center rounded border-2 align-[-3px] ${on ? "border-white" : "border-stamp/50"}`}>{on && <CheckIcon className="h-3.5 w-3.5" />}</span>}
                {o.label}
              </button>
            );
          })}
          {question.multi && (
            <div className="mt-1 flex w-full gap-2.5">
              <button onClick={() => send({ answers: picked.map((p) => ({ field: p.field, value: p.value, label: p.label })) })} disabled={phase !== "idle" || picked.length === 0}
                className="min-h-[52px] flex-1 rounded-2xl bg-stamp px-4 font-bold text-white disabled:opacity-40">{t("done", lang)}</button>
              <button onClick={() => { setHeard(question.none_label ?? t("noneOfThese", lang)); send({ answers: [] }); }} disabled={phase !== "idle"}
                className="min-h-[52px] flex-1 rounded-2xl border-2 border-ink/20 bg-card px-4 font-bold text-ink disabled:opacity-40">{question.none_label ?? t("noneOfThese", lang)}</button>
            </div>
          )}
        </div>
      )}

      {notice && <p className="mt-4 rounded-xl bg-turmeric-soft px-4 py-3 text-turmeric" role="status">{notice}</p>}

      {done && (
        <Link href="/results/" className="mt-6 block rounded-2xl bg-leaf px-5 py-4 text-center text-xl font-bold text-white">
          {t("seeSchemes", lang)}
        </Link>
      )}
      {!done && answeredAny && (
        <Link href="/results/" className="mt-5 self-start text-[1.02rem] font-semibold text-stamp underline underline-offset-4">
          {t("seeSchemesSoFar", lang)}{eligibleCount > 0 ? ` (${eligibleCount})` : ""}
        </Link>
      )}

      <div className="flex-1" />

      {/* input dock */}
      <div className="sticky bottom-0 -mx-4 mt-6 border-t border-line bg-paper/95 px-4 pb-4 pt-3 backdrop-blur no-print">
        {typing ? (
          <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); if (draft.trim()) { setHeard(draft.trim()); send({ text: draft.trim() }); setDraft(""); } }}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} inputMode={inputMode} autoFocus placeholder={t("typeHere", lang)} aria-label={t("typeHere", lang)}
              className="min-h-[56px] min-w-0 flex-1 rounded-2xl border-2 border-line bg-card px-4 text-lg focus:border-stamp" />
            <button type="submit" disabled={phase !== "idle"} className="min-h-[56px] rounded-2xl bg-stamp px-5 font-bold text-white disabled:opacity-50">{t("send", lang)}</button>
            {mode !== "none" && (
              <button type="button" onClick={() => setTyping(false)} className="grid min-h-[56px] w-14 place-items-center rounded-2xl border-2 border-line text-stamp" aria-label={t("speakInstead", lang)}>
                <MicIcon className="h-6 w-6" />
              </button>
            )}
          </form>
        ) : (
          <div className="flex items-center justify-center gap-5">
            <span className="w-14" />
            <button onClick={phase === "listening" ? stopListening : startListening} disabled={phase === "thinking" || mode === null}
              className={`grid h-24 w-24 place-items-center rounded-full text-white shadow-lg disabled:opacity-60 ${phase === "listening" ? "listening bg-brick" : "bg-stamp"}`}
              aria-label={phase === "listening" ? t("listening", lang) : t("tapToSpeak", lang)}>
              {phase === "listening" ? <StopIcon /> : <MicIcon className="h-11 w-11" />}
            </button>
            <button onClick={() => setTyping(true)} className="grid h-14 w-14 place-items-center rounded-full border-2 border-line bg-card text-ink" aria-label={t("typeInstead", lang)}>
              <KeyboardIcon />
            </button>
          </div>
        )}
        {!typing && (
          <p className="mt-2 text-center font-semibold text-muted">
            {phase === "listening" ? t("listening", lang) : phase === "thinking" ? t("thinking", lang) : t("tapToSpeak", lang)}
          </p>
        )}
      </div>
    </div>
  );
}
