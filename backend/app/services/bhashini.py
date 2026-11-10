"""Bhashini (ULCA) speech services: ASR, TTS and translation.

Flow (Bhashini "pipeline" API):
  1. getModelsPipeline with userID + ulcaApiKey -> serviceId per task, callback URL
     and an inference key. Cached per (task, language) for an hour.
  2. POST the inference request to the callback URL with that key.

Any error or a timeout (BHASHINI_TIMEOUT_S, default 6 s) raises BhashiniUnavailable;
callers then return text only and the browser speaks / listens instead.
"""

from __future__ import annotations

import time

import httpx

from app.config import settings

CONFIG_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
_cache: dict[tuple, tuple[float, dict]] = {}


class BhashiniUnavailable(RuntimeError):
    pass


def _pipeline(task: str, src: str, tgt: str | None = None) -> dict:
    if not settings.bhashini_enabled:
        raise BhashiniUnavailable("not configured")
    key = (task, src, tgt)
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < 3600:
        return hit[1]
    lang = {"sourceLanguage": src}
    if tgt:
        lang["targetLanguage"] = tgt
    body = {
        "pipelineTasks": [{"taskType": task, "config": {"language": lang}}],
        "pipelineRequestConfig": {"pipelineId": settings.bhashini_pipeline_id},
    }
    headers = {"userID": settings.bhashini_user_id, "ulcaApiKey": settings.bhashini_api_key}
    try:
        r = httpx.post(CONFIG_URL, json=body, headers=headers, timeout=settings.bhashini_timeout_s)
        r.raise_for_status()
        j = r.json()
        cfg = {
            "service_id": j["pipelineResponseConfig"][0]["config"][0]["serviceId"],
            "url": j["pipelineInferenceAPIEndPoint"]["callbackUrl"],
            "auth": {j["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"]: j["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]},
        }
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise BhashiniUnavailable(str(exc)) from exc
    _cache[key] = (time.time(), cfg)
    return cfg


def _infer(cfg: dict, task_config: dict, task: str, input_data: dict) -> dict:
    body = {"pipelineTasks": [{"taskType": task, "config": {**task_config, "serviceId": cfg["service_id"]}}], "inputData": input_data}
    try:
        r = httpx.post(cfg["url"], json=body, headers=cfg["auth"], timeout=settings.bhashini_timeout_s)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise BhashiniUnavailable(str(exc)) from exc


def asr(audio_b64: str, lang: str, audio_format: str = "wav", sample_rate: int = 16000) -> str:
    cfg = _pipeline("asr", lang)
    j = _infer(
        cfg, {"language": {"sourceLanguage": lang}, "audioFormat": audio_format, "samplingRate": sample_rate}, "asr", {"audio": [{"audioContent": audio_b64}]}
    )
    try:
        return j["pipelineResponse"][0]["output"][0]["source"].strip()
    except (KeyError, IndexError) as exc:
        raise BhashiniUnavailable("bad ASR response") from exc


def tts(text: str, lang: str, gender: str = "female") -> str:
    """Returns base64 WAV audio."""
    cfg = _pipeline("tts", lang)
    j = _infer(cfg, {"language": {"sourceLanguage": lang}, "gender": gender}, "tts", {"input": [{"source": text}]})
    try:
        return j["pipelineResponse"][0]["audio"][0]["audioContent"]
    except (KeyError, IndexError) as exc:
        raise BhashiniUnavailable("bad TTS response") from exc


def translate(text: str, src: str, tgt: str) -> str:
    if src == tgt:
        return text
    cfg = _pipeline("translation", src, tgt)
    j = _infer(cfg, {"language": {"sourceLanguage": src, "targetLanguage": tgt}}, "translation", {"input": [{"source": text}]})
    try:
        return j["pipelineResponse"][0]["output"][0]["target"]
    except (KeyError, IndexError) as exc:
        raise BhashiniUnavailable("bad NMT response") from exc


def status() -> str:
    if not settings.bhashini_enabled:
        return "not_configured"
    try:
        _pipeline("tts", "en")
        return "ok"
    except BhashiniUnavailable:
        return "unavailable"
