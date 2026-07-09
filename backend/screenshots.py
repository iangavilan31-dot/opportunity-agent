"""
Screenshot pipeline — the "See" stage, automated.

After ranking, capture mobile + desktop screenshots of every selected lead's
site into backend/screenshots/YYYY-MM-DD/ and build a contact-sheet HTML so a
human (or a vision pass) can kill false positives in a 5-minute skim instead of
opening 40 tabs. Runs headless via Playwright; every failure is per-site and
non-fatal. Zero API keys.
"""
from __future__ import annotations

import os
import re
from datetime import date

_HERE = os.path.dirname(__file__)
SHOTS_ROOT = os.path.join(_HERE, "screenshots")

_MOBILE = {"viewport": {"width": 390, "height": 844}, "is_mobile": True,
           "device_scale_factor": 2,
           "user_agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")}
_DESKTOP = {"viewport": {"width": 1366, "height": 900}}


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "site").lower()).strip("-")[:60] or "site"


def capture(items: list[dict], max_shots: int = 40, log=print) -> tuple[str | None, str | None]:
    """items: [{company, url, issues}] — each gets item['shots']={mobile,desktop}
    filenames populated in place. Returns (contact_sheet_path, out_dir)."""
    items = [i for i in items if i.get("url")][:max_shots]
    if not items:
        return None, None
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        log("[screenshots] playwright not installed — skipping (pip install playwright)")
        return None, None

    out_dir = os.path.join(SHOTS_ROOT, date.today().isoformat())
    os.makedirs(out_dir, exist_ok=True)
    cards, done = [], 0

    try:
        with sync_playwright() as pw:
            try:
                browser = pw.chromium.launch(headless=True)
            except Exception as e:
                log(f"[screenshots] chromium unavailable ({e}) — run: playwright install chromium")
                return None, None
            for kind, opts in (("mobile", _MOBILE), ("desktop", _DESKTOP)):
                ctx = browser.new_context(**opts)
                ctx.set_default_timeout(15000)
                page = ctx.new_page()
                for it in items:
                    slug = _slug(it["company"])
                    fname = f"{slug}_{kind}.png"
                    try:
                        page.goto(it["url"], wait_until="domcontentloaded", timeout=20000)
                        # Wait for the page to actually paint — JS-heavy sites are
                        # blank at domcontentloaded, and a blank frame makes the
                        # vision auditor hallucinate. Give the network a moment to
                        # settle, then confirm the body has real content.
                        try:
                            page.wait_for_load_state("networkidle", timeout=8000)
                        except Exception:
                            pass
                        try:
                            page.wait_for_function(
                                "document.body && document.body.innerText.trim().length > 40",
                                timeout=6000)
                        except Exception:
                            pass
                        page.wait_for_timeout(1500)  # settle fonts/hero images
                        page.screenshot(path=os.path.join(out_dir, fname))
                        it.setdefault("shots", {})[kind] = fname
                        done += 1
                    except Exception:
                        pass  # dead/hostile site — the audit already caught it
                ctx.close()
            browser.close()
    except Exception as e:
        log(f"[screenshots] batch failed: {e}")
        return None, out_dir

    for it in items:
        shots = it.get("shots", {})
        imgs = "".join(
            f'<a href="{it["url"]}" target="_blank"><img src="{shots[k]}" class="{k}" loading="lazy"></a>'
            for k in ("mobile", "desktop") if k in shots)
        if not imgs:
            imgs = '<div class="dead">did not render</div>'
        issues = "".join(f"<li>{x}</li>" for x in (it.get("issues") or [])[:3])
        cards.append(f'<div class="card"><h3>{it["company"]}</h3>'
                     f'<p class="url">{it["url"]}</p><div class="imgs">{imgs}</div>'
                     f"<ul>{issues}</ul></div>")

    sheet = os.path.join(out_dir, "contact_sheet.html")
    with open(sheet, "w", encoding="utf-8") as f:
        f.write(f"""<!doctype html><meta charset="utf-8"><title>Lead sites — {date.today()}</title>
<style>
 body{{font-family:system-ui;background:#111;color:#eee;margin:24px}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(430px,1fr));gap:20px}}
 .card{{background:#1a1a1a;border-radius:10px;padding:14px}}
 .card h3{{margin:0 0 2px;font-size:15px}} .url{{color:#8ab;font-size:12px;margin:0 0 8px;word-break:break-all}}
 .imgs{{display:flex;gap:8px}} img{{border-radius:6px;background:#000;object-fit:cover;object-position:top}}
 img.mobile{{width:120px;height:260px}} img.desktop{{width:280px;height:260px}}
 ul{{font-size:12px;color:#caa;margin:8px 0 0;padding-left:18px}}
 .dead{{color:#a66;font-size:13px;padding:40px 10px}}
</style>
<h1>Shortlisted lead sites — {date.today()} ({done // 2 if done else 0} captured)</h1>
<div class="grid">{"".join(cards)}</div>""")
    log(f"[screenshots] {done} shots -> {sheet}")
    return sheet, out_dir
