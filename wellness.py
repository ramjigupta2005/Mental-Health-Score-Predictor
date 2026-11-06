"""
MindWell AI - wellness assistant layer.

Sits on top of the existing ML model. It never changes the prediction; it only
interprets it, builds recommendations / a 7-day plan, and powers the chat.

Design rules (from the project brief):
  * Non-clinical. No diagnosis. Score bands live in interpretation_config.json
    and are flagged `approved: false` until the project owner signs them off.
  * Nothing is attributed to the reference documents unless it really came
    from a file in ./knowledge (see KnowledgeBase).
  * Each student's data lives only inside their own server-side session.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import httpx

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "interpretation_config.json"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"

BUILTIN_SOURCE = "General wellness guidance (built in, not from your reference documents)"


# --------------------------------------------------------------------------
# Config (score bands) - non-clinical, needs approval
# --------------------------------------------------------------------------
def load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()


def band_for(score: float) -> dict:
    for b in CONFIG["bands"]:
        if score < b["max"]:
            return b
    return CONFIG["bands"][-1]


# --------------------------------------------------------------------------
# Knowledge base: keyword retrieval over files the owner drops in ./knowledge
# --------------------------------------------------------------------------
class KnowledgeBase:
    def __init__(self, directory: Path):
        self.chunks: list[dict] = []
        self.files: list[str] = []
        self._load(directory)

    def _load(self, directory: Path) -> None:
        if not directory.exists():
            return
        for p in sorted(directory.glob("**/*")):
            if p.suffix.lower() not in {".md", ".txt"} or p.name.lower() == "readme.md":
                continue
            self.files.append(p.name)
            text = p.read_text(encoding="utf-8", errors="ignore")
            for para in re.split(r"\n\s*\n", text):
                para = para.strip()
                if len(para) > 40:
                    self.chunks.append({"source": p.name, "text": para[:900]})

    @staticmethod
    def _tok(s: str) -> set[str]:
        return {w for w in re.findall(r"[a-z]{4,}", s.lower())}

    def search(self, query: str, k: int = 3) -> list[dict]:
        q = self._tok(query)
        if not q or not self.chunks:
            return []
        scored = []
        for c in self.chunks:
            s = len(q & self._tok(c["text"]))
            if s:
                scored.append((s, c))
        scored.sort(key=lambda x: -x[0])
        return [c for _, c in scored[:k]]


KB = KnowledgeBase(KNOWLEDGE_DIR)


# --------------------------------------------------------------------------
# Assessment analysis
# --------------------------------------------------------------------------
def analyse_habits(a: dict) -> dict:
    """Split habits into strengths and focus areas using simple, transparent thresholds."""
    t = CONFIG["thresholds"]
    strengths, focus = [], []

    def add(ok: bool, key: str, good: str, bad: str):
        (strengths if ok else focus).append({"key": key, "text": good if ok else bad})

    add(a["sleep_hours_per_night"] >= t["sleep_min"], "sleep",
        f"Sleep of {a['sleep_hours_per_night']:g} h/night is within the commonly recommended range.",
        f"Sleep of {a['sleep_hours_per_night']:g} h/night is below the {t['sleep_min']:g}+ h usually recommended.")
    add(a["avg_daily_usage_hours"] <= t["usage_high"], "social",
        f"Social media time ({a['avg_daily_usage_hours']:g} h/day) is moderate.",
        f"Social media time ({a['avg_daily_usage_hours']:g} h/day) is on the high side.")
    add(a["daily_unlocks"] <= t["unlocks_high"], "unlocks",
        f"{a['daily_unlocks']} phone unlocks/day is a fairly calm checking pattern.",
        f"{a['daily_unlocks']} phone unlocks/day suggests frequent checking.")
    add(a["physical_activity_hours"] >= t["activity_min"], "activity",
        f"{a['physical_activity_hours']:g} h/day of physical activity is a good habit.",
        f"{a['physical_activity_hours']:g} h/day of physical activity is on the low side.")
    add(a["study_hours"] <= t["study_high"], "study",
        f"Study load ({a['study_hours']:g} h/day) looks manageable.",
        f"Study load ({a['study_hours']:g} h/day) is heavy - breaks and boundaries matter.")
    add(a["stress_level"] in ("Low", "Medium"), "stress",
        f"Perceived stress is {a['stress_level'].lower()}.",
        f"Perceived stress is {a['stress_level'].lower()}.")
    return {"strengths": [s["text"] for s in strengths],
            "focus_areas": [f["text"] for f in focus],
            "focus_keys": [f["key"] for f in focus]}


def what_if(a: dict, predict_fn: Callable[[dict], float], base: float) -> list[dict]:
    """
    Ask the trained model how the score would change if one habit moved to a
    healthier value. This explains the *model's* learned pattern; it is an
    association in the training data, not proof of cause.
    """
    t = CONFIG["thresholds"]
    trials = []
    if a["sleep_hours_per_night"] < t["sleep_target"]:
        trials.append(("sleep_hours_per_night", t["sleep_target"],
                       f"sleeping {t['sleep_target']:g} h/night"))
    if a["avg_daily_usage_hours"] > t["usage_target"]:
        trials.append(("avg_daily_usage_hours", t["usage_target"],
                       f"social media at {t['usage_target']:g} h/day"))
    if a["daily_unlocks"] > t["unlocks_target"]:
        trials.append(("daily_unlocks", t["unlocks_target"],
                       f"about {t['unlocks_target']} phone unlocks/day"))
    if a["physical_activity_hours"] < t["activity_target"]:
        trials.append(("physical_activity_hours", t["activity_target"],
                       f"{t['activity_target']:g} h/day of activity"))
    if a["stress_level"] in ("High", "Very High"):
        trials.append(("stress_level", "Medium", "perceived stress at Medium"))

    out = []
    for key, val, label in trials:
        try:
            new = predict_fn({**a, key: val})
        except Exception:
            continue
        if abs(new - base) >= 0.05:  # hide changes the model barely reacts to
            out.append({"change": label, "delta": round(new - base, 2)})
    out.sort(key=lambda x: -x["delta"])
    return out


def interpret(a: dict, score: float, predict_fn: Callable[[dict], float]) -> dict:
    band = band_for(score)
    habits = analyse_habits(a)
    sens = what_if(a, predict_fn, score)
    approved = bool(CONFIG.get("approved", False))
    low, high = CONFIG["dataset_reference"]["p25"], CONFIG["dataset_reference"]["p75"]

    simple = (
        f"Your predicted score is {score:.2f} out of 10. In the data this model learned from, "
        f"higher scores went with more sleep, less screen time and lower stress, so a higher number "
        f"generally reflects a more supportive daily rhythm. "
        f"Most students in that dataset scored between {low:g} and {high:g}."
    )
    return {
        "score": score,
        "band_label": band["label"],
        "band_text": band["text"],
        "band_config_approved": approved,
        "disclaimer": CONFIG["disclaimer"],
        "plain_language": simple,
        "strengths": habits["strengths"],
        "focus_areas": habits["focus_areas"],
        "focus_keys": habits["focus_keys"],
        "what_if": sens,
        "what_if_note": ("These are patterns the model learned from survey data. "
                         "They show association, not guaranteed cause and effect."),
    }


# --------------------------------------------------------------------------
# Recommendations
# --------------------------------------------------------------------------
TIPS = {
    "sleep": [
        "Keep a consistent sleep and wake time, even on weekends.",
        "Wind down for 30-60 minutes before bed: dim lights, no study, no scrolling.",
        "Keep your phone out of reach of the bed or on Do Not Disturb overnight.",
        "Limit caffeine in the afternoon and evening.",
    ],
    "social": [
        "Set a daily limit with your phone's screen-time tool and aim to lower it gradually.",
        "Schedule 2-3 short social-media windows instead of checking all day.",
        "Turn off non-essential notifications.",
        "Replace some scrolling time with something offline: a walk, a call, a hobby.",
    ],
    "unlocks": [
        "Move distracting apps off your home screen and use grayscale in study hours.",
        "Charge the phone across the room while studying.",
    ],
    "activity": [
        "Start with a 15-20 minute daily walk, then build up to about an hour of movement.",
        "Stack movement onto routines: walk between classes, stretch each study break.",
    ],
    "study": [
        "Study in focused blocks (e.g. 45-50 min) with 10 min breaks.",
        "Set a hard stop time each evening and protect it for rest and people.",
        "Plan one non-academic activity every day.",
    ],
    "stress": [
        "Try 5 minutes of slow breathing (inhale 4s, exhale 6s) when stress spikes.",
        "Break big tasks into small next steps so the workload feels smaller.",
        "Talk to a friend, family member, tutor or counsellor, especially if stress feels constant.",
    ],
}


def recommendations(focus_keys: list[str], strengths_present: bool = True) -> list[dict]:
    recs = [{"area": k, "tips": TIPS[k], "source": BUILTIN_SOURCE} for k in focus_keys if k in TIPS]
    if not recs:
        recs.append({"area": "maintain",
                     "tips": ["Your habits look balanced. Keep your routines and check in with yourself regularly."],
                     "source": BUILTIN_SOURCE})
    return recs


# --------------------------------------------------------------------------
# 7-day plan
# --------------------------------------------------------------------------
def _fmt_h(h: float) -> str:
    mins = int(round(h * 60))
    return f"{mins // 60} h {mins % 60:02d} min" if mins % 60 else f"{mins // 60} h"


def seven_day_plan(a: dict) -> list[dict]:
    t = CONFIG["thresholds"]
    sleep0, usage0 = a["sleep_hours_per_night"], a["avg_daily_usage_hours"]
    act0, study0 = a["physical_activity_hours"], a["study_hours"]
    high_stress = a["stress_level"] in ("High", "Very High")

    sleep_goal = min(max(sleep0, t["sleep_min"]), t["sleep_target"]) if sleep0 < t["sleep_target"] else sleep0
    usage_goal = min(usage0, max(t["usage_target"], usage0 * 0.6))
    act_goal = max(act0, t["activity_target"]) if act0 < t["activity_target"] else act0

    breathing = ["5 min slow breathing", "10 min walk without phone", "Write 3 things that went okay",
                 "5 min stretching", "Call or message someone you trust", "10 min of a hobby you enjoy",
                 "Short reflection: what helped this week?"]
    days = []
    for i in range(7):
        f = (i + 1) / 7  # progressive ramp
        sleep_t = sleep0 + (sleep_goal - sleep0) * f
        usage_t = usage0 - (usage0 - usage_goal) * f
        act_t = act0 + (act_goal - act0) * f
        study_t = min(study0, 4.5)
        blocks = max(1, round(study_t * 60 / 50))
        days.append({
            "day": i + 1,
            "theme": ["Baseline", "Wind-down", "Move more", "Screen reset", "Balance", "Recover", "Review"][i],
            "daily_goal": f"Day {i+1}: " + breathing[i],
            "sleep": f"Aim for about {_fmt_h(sleep_t)} in bed; same wake time daily.",
            "activity": f"About {int(round(act_t*60))} min of movement (walking counts).",
            "study": (f"{blocks} focused blocks of ~50 min with 10 min breaks; stop by a fixed evening time."
                      if study_t >= 1 else "Light study; keep a regular slot."),
            "social_media": f"Try to stay near {usage_t:.1f} h of social media; one phone-free hour before bed.",
            "stress_note": ("Take one proper break from studying; reach out to someone if stress stays high."
                            if high_stress else "Do one thing today purely for enjoyment."),
        })
    return days


# --------------------------------------------------------------------------
# Safety
# --------------------------------------------------------------------------
CRISIS_RE = re.compile(
    r"\b(suicid\w*|kill myself|end my life|want to die|don'?t want to live|self[- ]?harm|"
    r"hurt myself|cut myself|no reason to live|better off dead)\b", re.I)

HELPLINES = {
    "india": "Tele-MANAS: 14416 (free, 24/7)",
    "usa": "988 Suicide & Crisis Lifeline: call or text 988",
    "uk": "Samaritans: 116 123 (free, 24/7)",
    "canada": "9-8-8 Suicide Crisis Helpline: call or text 988",
    "australia": "Lifeline: 13 11 14",
}


def crisis_message(country: str) -> str:
    line = HELPLINES.get((country or "").strip().lower())
    extra = f" Here is a line for your country: {line}." if line else ""
    return (
        "I'm really glad you told me, and I'm sorry things feel this heavy. I'm an AI wellness assistant "
        "and can't give the support you deserve right now. If you might act on these thoughts or are in "
        "danger, please contact your local emergency number now, or go to someone near you."
        f"{extra} You can also find a helpline in any country at findahelpline.com. "
        "If you can, tell a trusted person near you what you're feeling today. You don't have to handle this alone."
    )


# --------------------------------------------------------------------------
# Sessions: strictly per-student, server-side, expiring
# --------------------------------------------------------------------------
class SessionStore:
    def __init__(self, ttl: int = 7200, max_sessions: int = 2000):
        self._d: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.ttl, self.max = ttl, max_sessions

    def _gc(self):
        now = time.time()
        for k in [k for k, v in self._d.items() if now - v["ts"] > self.ttl]:
            del self._d[k]
        while len(self._d) > self.max:
            del self._d[min(self._d, key=lambda k: self._d[k]["ts"])]

    def create(self, data: dict) -> str:
        sid = secrets.token_urlsafe(24)
        with self._lock:
            self._gc()
            self._d[sid] = {"ts": time.time(), "history": [], "msgs": 0, **data}
        return sid

    def get(self, sid: str) -> Optional[dict]:
        with self._lock:
            s = self._d.get(sid)
            if s and time.time() - s["ts"] <= self.ttl:
                s["ts"] = time.time()
                return s
            self._d.pop(sid, None)
            return None


SESSIONS = SessionStore()
MAX_MSGS_PER_SESSION = 60


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
def _intent(msg: str) -> str:
    m = msg.lower()
    if re.search(r"7[- ]?day|seven[- ]?day|wellness plan|weekly plan", m): return "plan"
    if re.search(r"routine|timetable|schedule|study.?life|balance", m): return "routine"
    if re.search(r"why|influence|affect|factor", m): return "why"
    if re.search(r"sleep|insomnia|bed|tired", m): return "sleep"
    if re.search(r"social|scroll|instagram|tiktok|screen|phone|unlock", m): return "social"
    if re.search(r"stress|anxi|overwhelm|pressure|relax|calm", m): return "stress"
    if re.search(r"exercise|activity|walk|move|workout", m): return "activity"
    if re.search(r"score|mean|result|number", m): return "score"
    return "general"


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {i}" for i in items)


def rule_based_reply(sess: dict, msg: str) -> dict:
    a, ins = sess["assessment"], sess["insights"]
    intent = _intent(msg)
    snippets = KB.search(msg, 2)
    sources = [BUILTIN_SOURCE]

    if intent == "score":
        txt = (f"{ins['plain_language']}\n\nIndicative band: **{ins['band_label']}**. {ins['band_text']} "
               f"This is a non-clinical estimate from habits, not a diagnosis.")
    elif intent == "why":
        lines = [f"- If {w['change']}, the model's estimate moves by {w['delta']:+.2f}." for w in ins["what_if"][:4]]
        txt = ("Here is what the model picked up from your answers:\n"
               + ("\n".join(lines) if lines else "- Your habits already sit near the healthier end, so there is little left that the model expects to move your score.")
               + f"\n\nWorking in your favour: {'; '.join(ins['strengths'][:2]) or 'no clear strengths stood out in this set of answers'}\n"
               f"{ins['what_if_note']}")
    elif intent == "plan":
        plan = sess["plan"]
        txt = "Here is your 7-day plan (it's also shown in the Plan tab):\n" + "\n".join(
            f"- Day {d['day']} ({d['theme']}): {d['sleep']} {d['activity']} {d['social_media']}" for d in plan)
    elif intent == "routine":
        txt = ("A simple study-life routine based on your answers:\n" + _bullets([
            f"Wake at a fixed time; protect about {_fmt_h(max(a['sleep_hours_per_night'], 7))} of sleep.",
            "Two or three 50-minute study blocks with 10-minute breaks.",
            f"{int(max(a['physical_activity_hours'], 0.75)*60)} minutes of movement, ideally before the evening.",
            "A fixed finish time for study, then a phone-light evening.",
            "One social or enjoyable offline activity each day."]))
    elif intent in TIPS:
        txt = f"Based on your answers, here are some ideas for {intent.replace('social','social media')}:\n" + _bullets(TIPS[intent][:4])
    else:
        txt = ("I can explain your score, suggest ways to improve sleep, manage stress, or cut down screen time, "
               "build a study-life routine, or give you a 7-day plan. What would you like to start with?")
    if intent == "stress" and a["stress_level"] in ("High", "Very High"):
        txt += "\n\nSince you report high stress, consider talking to someone you trust or a counsellor."
    for s in snippets:
        txt += f"\n\nFrom your reference material ({s['source']}): {s['text'][:300]}"
        sources.append(s["source"])
    return {"reply": txt, "mode": "rules", "sources": sources}


SYSTEM_PROMPT = """You are "MindWell AI - Your Student Wellness Assistant".
You help ONE student understand a machine-learning estimate of a wellbeing score and make healthy habit changes.
Rules:
- You are NOT a clinician. Never diagnose, never claim the score is a clinical measure.
- Do not claim higher or lower is clinically better; say only what the dataset pattern shows (higher scores went with more sleep, less screen time, lower stress).
- Only cite "reference material" if it appears in the REFERENCE EXCERPTS block below; otherwise treat advice as general wellness guidance.
- Use only this student's data below. Be warm, concise, practical, specific.
- If the student mentions self-harm or crisis, urge contacting local emergency services or a trusted person.
- Suggest professional help when stress is persistently high.
STUDENT DATA (private):
{student}
REFERENCE EXCERPTS:
{refs}
"""


def llm_reply(sess: dict, msg: str) -> Optional[dict]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    ins = sess["insights"]
    student = json.dumps({"inputs": sess["assessment"], "predicted_score": ins["score"],
                          "band": ins["band_label"], "strengths": ins["strengths"],
                          "focus_areas": ins["focus_areas"], "what_if": ins["what_if"]})
    snippets = KB.search(msg + " " + " ".join(ins["focus_areas"]), 3)
    refs = "\n".join(f"[{s['source']}] {s['text']}" for s in snippets) or "(none provided)"
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.getenv("WELLNESS_LLM_MODEL", "claude-sonnet-5-5"),
                  "max_tokens": 900,
                  "system": SYSTEM_PROMPT.format(student=student, refs=refs),
                  "messages": sess["history"][-12:] + [{"role": "user", "content": msg}]},
            timeout=40)
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"] if b.get("type") == "text")
        if not text.strip():
            return None
        return {"reply": text, "mode": "llm",
                "sources": [s["source"] for s in snippets] or [BUILTIN_SOURCE]}
    except Exception:
        return None  # fall back to rules


def chat(sid: str, msg: str) -> Optional[dict]:
    sess = SESSIONS.get(sid)
    if sess is None:
        return None
    if sess["msgs"] >= MAX_MSGS_PER_SESSION:
        return {"reply": "This session has reached its message limit. Please start a new assessment.",
                "mode": "limit", "sources": []}
    sess["msgs"] += 1
    if CRISIS_RE.search(msg):
        out = {"reply": crisis_message(sess["assessment"].get("country", "")), "mode": "safety", "sources": []}
    else:
        out = llm_reply(sess, msg) or rule_based_reply(sess, msg)
    sess["history"] += [{"role": "user", "content": msg}, {"role": "assistant", "content": out["reply"]}]
    return out
