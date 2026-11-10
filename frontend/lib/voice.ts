// Voice in and out, with graceful fallbacks:
//   speech in : Bhashini (16 kHz WAV recorded here)  -> browser SpeechRecognition -> typing
//   speech out: Bhashini audio from the server        -> browser speechSynthesis   -> text only

import { speechLang, type Lang } from "./i18n";

// ---------------------------------------------------------------- WAV recorder (for Bhashini)
export class WavRecorder {
  private ctx?: AudioContext;
  private stream?: MediaStream;
  private node?: ScriptProcessorNode;
  private chunks: Float32Array[] = [];
  private timer?: number;

  async start(maxSeconds = 30, onAutoStop?: () => void) {
    this.stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true } });
    this.ctx = new AudioContext();
    const src = this.ctx.createMediaStreamSource(this.stream);
    // ScriptProcessor is deprecated but is the most widely supported option on older Android Chrome.
    this.node = this.ctx.createScriptProcessor(4096, 1, 1);
    this.chunks = [];
    this.node.onaudioprocess = (e) => this.chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    src.connect(this.node);
    this.node.connect(this.ctx.destination);
    this.timer = window.setTimeout(() => onAutoStop?.(), maxSeconds * 1000);
  }

  async stop(): Promise<string> {
    window.clearTimeout(this.timer);
    this.node?.disconnect();
    this.stream?.getTracks().forEach((t) => t.stop());
    const rate = this.ctx?.sampleRate ?? 48000;
    await this.ctx?.close();
    const merged = new Float32Array(this.chunks.reduce((n, c) => n + c.length, 0));
    let off = 0;
    for (const c of this.chunks) {
      merged.set(c, off);
      off += c.length;
    }
    return toBase64(encodeWav(downsample(merged, rate, 16000), 16000));
  }
}

function downsample(buf: Float32Array, from: number, to: number): Float32Array {
  if (from === to) return buf;
  const ratio = from / to;
  const out = new Float32Array(Math.floor(buf.length / ratio));
  for (let i = 0; i < out.length; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.min(buf.length, Math.floor((i + 1) * ratio));
    let sum = 0;
    for (let j = start; j < end; j++) sum += buf[j];
    out[i] = sum / Math.max(1, end - start);
  }
  return out;
}

function encodeWav(samples: Float32Array, rate: number): Uint8Array {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buffer);
  const w = (o: number, s: string) => [...s].forEach((ch, i) => v.setUint8(o + i, ch.charCodeAt(0)));
  w(0, "RIFF"); v.setUint32(4, 36 + samples.length * 2, true); w(8, "WAVE"); w(12, "fmt ");
  v.setUint32(16, 16, true); v.setUint16(20, 1, true); v.setUint16(22, 1, true); v.setUint32(24, rate, true);
  v.setUint32(28, rate * 2, true); v.setUint16(32, 2, true); v.setUint16(34, 16, true); w(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Uint8Array(buffer);
}

function toBase64(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return btoa(s);
}

// ---------------------------------------------------------------- browser speech recognition
type SR = {
  lang: string; interimResults: boolean; maxAlternatives: number; continuous: boolean;
  start(): void; stop(): void; abort(): void;
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
};

export function browserRecognitionAvailable(): boolean {
  return typeof window !== "undefined" && !!((window as unknown as Record<string, unknown>).SpeechRecognition || (window as unknown as Record<string, unknown>).webkitSpeechRecognition);
}

export function recordAvailable(): boolean {
  return typeof navigator !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof AudioContext !== "undefined";
}

export function listenOnce(lang: Lang): { promise: Promise<string>; stop: () => void } {
  const W = window as unknown as Record<string, new () => SR>;
  const Ctor = W.SpeechRecognition || W.webkitSpeechRecognition;
  const rec = new Ctor();
  rec.lang = speechLang(lang);
  rec.interimResults = false;
  rec.maxAlternatives = 1;
  rec.continuous = false;
  let text = "";
  const promise = new Promise<string>((resolve, reject) => {
    rec.onresult = (e) => {
      text = Array.from(e.results).map((r) => r[0].transcript).join(" ");
    };
    rec.onerror = (e) => reject(new Error(e.error));
    rec.onend = () => resolve(text.trim());
  });
  rec.start();
  return { promise, stop: () => rec.stop() };
}

// ---------------------------------------------------------------- speaking
let current: HTMLAudioElement | null = null;

export function stopSpeaking() {
  current?.pause();
  current = null;
  if (typeof speechSynthesis !== "undefined") speechSynthesis.cancel();
}

export function playWav(b64: string): Promise<void> {
  stopSpeaking();
  return new Promise((resolve) => {
    current = new Audio(`data:audio/wav;base64,${b64}`);
    current.onended = () => resolve();
    current.onerror = () => resolve();
    current.play().catch(() => resolve());
  });
}

export function browserVoiceFor(lang: Lang): SpeechSynthesisVoice | null {
  if (typeof speechSynthesis === "undefined") return null;
  const want = speechLang(lang).toLowerCase();
  const voices = speechSynthesis.getVoices();
  return voices.find((v) => v.lang.toLowerCase() === want) ?? voices.find((v) => v.lang.toLowerCase().startsWith(want.slice(0, 2))) ?? null;
}

/** Speak with the browser. Returns false if this device has no voice for the language. */
export function speakBrowser(text: string, lang: Lang): boolean {
  if (typeof speechSynthesis === "undefined") return false;
  const voice = browserVoiceFor(lang);
  if (!voice && lang !== "en") return false;
  stopSpeaking();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = speechLang(lang);
  if (voice) u.voice = voice;
  u.rate = 0.95;
  speechSynthesis.speak(u);
  return true;
}
