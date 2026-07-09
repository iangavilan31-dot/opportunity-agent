"""
Sender profile — the operator's real name, positioning line, and calendar link.

Applied at RENDER time (not generation) so editing the profile instantly updates
every existing draft. Replaces the "[Your name]" placeholder with a real
signature block, which both removes per-email editing friction at scale and adds
the trust signal cold emails need.
"""
import json
import os

SETTINGS_PATH = os.path.join(os.path.dirname(__file__), "sender_profile.json")

DEFAULTS = {
    "sender_name": "",          # e.g. "Ian Gavilan"
    "positioning": "",          # e.g. "I automate back-office workflows for small teams"
    "calendar_link": "",        # e.g. "cal.com/ian/15min"
    "sender_email": "",         # reply-to / from address (info only)
    # CAN-SPAM requires a physical postal address in every commercial email.
    # A PO Box counts (and keeps a home address off cold emails).
    "postal_address": "",       # e.g. "Gavika · PO Box 123, Phoenix, AZ 85001"
}


def load_settings() -> dict:
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {**DEFAULTS, **data}
        except Exception:
            pass
    return dict(DEFAULTS)


def save_settings(data: dict) -> dict:
    current = load_settings()
    for k in DEFAULTS:
        if k in data and data[k] is not None:
            current[k] = data[k].strip() if isinstance(data[k], str) else data[k]
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return current


def build_signature(settings: dict | None = None) -> str:
    """The signature block that replaces '[Your name]'."""
    s = settings or load_settings()
    name = s.get("sender_name", "").strip()
    positioning = s.get("positioning", "").strip()
    calendar = s.get("calendar_link", "").strip()

    if not name:
        return "[Your name]"  # not configured yet — leave the prompt visible

    lines = [name]
    if positioning:
        lines[0] = f"{name} · {positioning}"
    if calendar:
        cal = calendar if calendar.startswith("http") else f"https://{calendar}"
        lines.append(f"Grab 15 min whenever: {cal}")
    return "\n".join(lines)


def apply_signature(text: str | None, settings: dict | None = None) -> str:
    """Replace the [Your name] / [Mailing address] placeholders with real values."""
    if not text:
        return text or ""
    s = settings or load_settings()
    sig = build_signature(s)
    # Handle both "— [Your name]" and bare "[Your name]"
    out = text.replace("[Your name]", sig)
    addr = s.get("postal_address", "").strip()
    if addr:
        out = out.replace("[Mailing address]", addr)
    return out


def is_configured() -> bool:
    return bool(load_settings().get("sender_name", "").strip())
