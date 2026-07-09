"""
Visual UI audit — GPT-4o-mini reads a real screenshot of the prospect's homepage
and returns the concrete, visible problems a human would notice.

This is the sharpest, cheapest reply-rate lever: it turns weak platform-guess
openers ("you're on Wix") into undeniable, specific observations ("the phone
number is below three scrolls, the hero is a stock photo, three different
fonts"). ~$0.0004/site on gpt-4o-mini — cents a day for the shortlist.

Grounded, not generative: the model only describes what's IN the screenshot.
Prompted hard for restraint (no praise, no guessing, no invented content) so
the lines are safe to put in a real cold email. Any failure -> [] and the
caller falls back to the heuristic opener. Skips entirely without OPENAI_API_KEY.
"""
from __future__ import annotations

import base64
import json
import os

import config

# Vision is used as a conservative QUALITY GATE, not a problem generator. A
# generator hallucinates flaws to satisfy the task — confirmed 2026-07-09, it
# invented 3 false problems for a genuinely good dental site. So the model's job
# is to JUDGE: is this already a modern, well-built site (skip it) or clearly
# dated/amateur (a real prospect)? It must default to 'modern' when unsure — a
# wrong 'dated' fabricates a pitch; a wrong 'modern' only costs us one lead.
_SYS = (
    "You are a senior web designer grading ONE screenshot of a local business "
    "homepage. Decide if it is already a modern, professionally designed site or "
    "clearly dated / amateur / template-looking. Judge only what is visible. Be "
    "CONSERVATIVE: if it looks clean, current, and competently designed — even if "
    "not fancy — call it 'modern'. Only call it 'dated' when it is obviously old "
    "or amateur (tiny cramped text, clip-art, default template look, no real "
    "photos, broken layout, 2000s styling). When 'dated', list only the specific "
    "flaws you can actually SEE. When 'modern', problems MUST be empty. "
    "Return STRICT JSON: {\"verdict\": \"modern\"|\"dated\", "
    "\"problems\": [\"short lowercase phrase under 12 words\", ...]} (<=3 problems)."
)


def _is_blank(path: str) -> bool:
    """True if the screenshot is blank / near-uniform (page didn't render).
    CRITICAL: vision models confidently HALLUCINATE UI problems on a blank white
    image (confirmed 2026-07-09 — an unrendered page got 'tiny text, cluttered
    nav' invented for it). Never send a blank frame to the model."""
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            g = im.convert("L").resize((64, 64))
        st = ImageStat.Stat(g)
        stdev = st.stddev[0]
        mean = st.mean[0]
        # Near-zero variance = one flat color; near-white mean = empty page.
        return stdev < 6.0 or mean > 250.0
    except Exception:
        # Can't inspect it -> treat as blank (safe: abstain over fabricate).
        return True


def _client():
    key = getattr(config, "OPENAI_API_KEY", "")
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key)
    except Exception:
        return None


def assess(screenshot_path: str) -> dict:
    """Grade a homepage screenshot. Returns:
        {"verdict": "modern"|"dated"|"unknown", "problems": [str, ...]}
    'modern'  -> already a good site; caller should DROP the lead.
    'dated'   -> a real prospect; problems are visible flaws for the opener.
    'unknown' -> blank/failed/no-key; caller falls back to deterministic signals.
    """
    if not getattr(config, "VISION_ENABLED", True):
        return {"verdict": "unknown", "problems": []}
    client = _client()
    if client is None or not screenshot_path or not os.path.exists(screenshot_path):
        return {"verdict": "unknown", "problems": []}
    if _is_blank(screenshot_path):
        return {"verdict": "unknown", "problems": []}  # didn't render — never guess
    try:
        with open(screenshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        model = getattr(config, "VISION_MODEL", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model, temperature=0, max_tokens=200,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYS},
                {"role": "user", "content": [
                    {"type": "text", "text": "Grade this homepage screenshot."},
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{b64}", "detail": "low"}},
                ]},
            ],
        )
        data = json.loads(resp.choices[0].message.content or "{}")
        verdict = "dated" if str(data.get("verdict")).lower() == "dated" else "modern"
        problems = []
        if verdict == "dated":
            for p in (data.get("problems") or [])[:3]:
                p = str(p).strip().rstrip(".")
                if 3 < len(p) < 90:
                    problems.append(p)
        return {"verdict": verdict, "problems": problems}
    except Exception as e:
        print(f"[vision_audit] {os.path.basename(screenshot_path)}: {e}")
        return {"verdict": "unknown", "problems": []}


def analyze(screenshot_path: str) -> list[str]:
    """Opener problems, only for a confidently 'dated' verdict; else []."""
    a = assess(screenshot_path)
    return a["problems"] if a["verdict"] == "dated" else []
