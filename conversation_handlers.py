AUTO_REPLY_HINTS = [
    "thank you for contacting",
    "thanks for contacting",
    "we will get back",
    "automated assistant",
    "auto reply",
    "team tak",
    "hamari team",
    "main ek automated assistant"
]


def respond(state, merchant_message: str) -> dict:
    msg = (merchant_message or "").lower().strip()

    if any(x in msg for x in AUTO_REPLY_HINTS):
        return {
            "action": "wait",
            "wait_seconds": 900,
            "rationale": "Likely WhatsApp Business auto-reply detected; backing off."
        }

    if any(x in msg for x in ["yes", "haan", "ok", "okay", "sure", "go ahead", "kar do", "send", "do it"]):
        return {
            "action": "send",
            "body": "Done 👍 I’ll prepare the draft/action now. You can review before it goes live.",
            "cta": "none",
            "rationale": "User accepted; moving directly to action."
        }

    if any(x in msg for x in ["join", "judna", "register", "start", "onboard"]):
        return {
            "action": "send",
            "body": "Great — I’ll start onboarding directly. Please share business name, city, and phone number.",
            "cta": "open_ended",
            "rationale": "Detected onboarding intent; avoided repeated qualification."
        }

    if any(x in msg for x in ["no", "not now", "stop", "later", "nahi", "not interested"]):
        return {
            "action": "end",
            "rationale": "User declined or opted out."
        }

    return {
        "action": "send",
        "body": "Got it. I’ll keep this simple: one clear next action, no extra steps. Reply YES and I’ll draft it.",
        "cta": "YES/NO",
        "rationale": "Unclear reply; nudging toward one low-friction action."
    }