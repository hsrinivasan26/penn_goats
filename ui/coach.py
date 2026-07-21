"""The results-screen AI coach.

Generates ONE short debrief of the finished run, grounded strictly in the game's own
figures (so it can't invent numbers), and falls back to a written line when there's no
GEMINI_API_KEY or the call fails. The Gemini SDK is imported lazily, so this module is
import-safe without the package installed.
"""

import os

MODEL = "gemini-3.1-flash-lite"          # same model the MCQ backend uses

_FALLBACK = {
    "win": "You built a real head start — that's the whole game. From here, you're not living "
           "paycheck to paycheck.",
    "bankruptcy": "The essentials caught up with you. Next run, keep a bigger cushion before "
                  "investing so one bad month doesn't spiral.",
    "burnout": "You ran yourself into the ground. A little fun each month keeps happiness up — "
               "it's part of the budget too.",
    "timeout": "You survived the five years but didn't reach the goal. Steady saving and "
               "clearing high-interest debt gets you there.",
}


def fallback_line(outcome: str) -> str:
    return _FALLBACK.get(outcome, _FALLBACK["timeout"])


def _facts(state, outcome: str) -> str:
    """A compact, factual summary the model must stay inside of (never invent numbers)."""
    hist = state.history or []
    start_nw = hist[0]["net_worth"] if hist else state.net_worth()
    shortfalls = sum(1 for h in hist if h.get("shortfall"))
    reached = state.net_worth() >= state.target
    import jobs                                            # sibling ui module (persona ages)
    start_age = jobs.START_AGE.get(state.path, 18)
    return (
        f"outcome={outcome}; months_played={state.turn}; "
        f"starting_net_worth={start_nw}; final_net_worth={state.net_worth()}; "
        f"goal={state.target}; reached_goal={reached}; "
        f"final_happiness={state.happiness}/100; shortfall_months={shortfalls}; "
        f"started_at_age={start_age}; age_now={start_age + (state.turn - 1) // 12}; "
        f"path={'graduate with a student loan' if state.path == 'B' else 'no degree, no debt'}"
    )


def _build_prompt(state, outcome: str) -> str:
    return (
        "You are a warm, plain-spoken financial coach debriefing a player's 5-year run in a "
        "budgeting game. Write 2 sentences, second person, encouraging and specific. Use ONLY "
        "the figures below — never invent a number, name, or event. No lists, no preamble.\n\n"
        f"Figures: {_facts(state, outcome)}"
    )


def _gemini_generate(prompt: str) -> str:
    """Plain-text Gemini call (no JSON mode). Lazy import keeps this module load-safe."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    resp = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(max_output_tokens=200, temperature=0.7),
    )
    return resp.text or ""


def overview(state, outcome: str, generator=None):
    """Return (text, is_ai). Uses Gemini when a key is set; otherwise the written fallback.

    `generator` is an injectable prompt->str (a fake in tests). If it or Gemini fails or
    returns nothing, we fall back to the written line so results never break.
    """
    gen = generator
    if gen is None:
        if not os.getenv("GEMINI_API_KEY"):
            return fallback_line(outcome), False
        gen = _gemini_generate
    try:
        text = (gen(_build_prompt(state, outcome)) or "").strip()
    except Exception:
        return fallback_line(outcome), False
    return (text, True) if text else (fallback_line(outcome), False)
