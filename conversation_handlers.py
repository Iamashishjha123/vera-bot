AUTO_REPLY_HINTS = [
    "thank you for contacting",
    "thanks for contacting",
    "we will get back",
    "automated assistant",
    "auto reply",
    "hamari team",
    "team tak",
    "main ek automated assistant",
    "aapki jaankari ke liye",
]


def respond(state, merchant_message: str) -> dict:
    msg = (merchant_message or "").lower().strip()
    turns = state.get("turns", [])
    trigger_kind = state.get("trigger_kind", "")

    auto_count = 0
    for t in turns:
        text = t.get("body", "").lower().strip()
        if t.get("from") in ["merchant", "customer"] and any(x in text for x in AUTO_REPLY_HINTS):
            auto_count += 1

    if any(x in msg for x in AUTO_REPLY_HINTS):
        if auto_count >= 2:
            return {
                "action": "end",
                "rationale": "Repeated WhatsApp Business auto-replies detected; exiting gracefully."
            }
        return {
            "action": "wait",
            "wait_seconds": 900,
            "rationale": "Likely WhatsApp Business auto-reply detected; backing off once."
        }

    if any(x in msg for x in ["stop", "not interested", "no", "nahi", "later", "not now"]):
        return {
            "action": "end",
            "rationale": "User declined or opted out."
        }

    if any(x in msg for x in ["book", "slot", "appointment", "confirm", "wed", "thu", "6pm", "5pm"]):
        return {
            "action": "send",
            "body": "Confirmed 👍 I’ll mark this as the preferred slot and prepare the booking note for review.",
            "cta": "none",
            "rationale": "Customer showed booking intent; moved directly to confirmation."
        }

    if any(x in msg for x in ["audit", "x-ray", "xray", "setup", "checklist", "compliance"]):
        return {
            "action": "send",
            "body": "Got it. I’ll create a 5-point compliance checklist: equipment, shielding, signage, staff safety, and documentation. Reply YES — I’ll draft it.",
            "cta": "YES/NO",
            "rationale": "Specific compliance follow-up handled with domain-relevant next step."
        }

    if any(x in msg for x in ["yes", "haan", "ok", "okay", "sure", "go ahead", "kar do", "send", "do it", "let's do it"]):
        if trigger_kind in ["regulation_change", "supply_alert"]:
            body = "Done — I’ll draft the checklist/action note using the provided deadline and payload details."
        elif trigger_kind in ["recall_due", "customer_lapsed_soft", "customer_lapsed_hard"]:
            body = "Done — I’ll prepare the customer message with consent-safe wording and booking CTA."
        elif trigger_kind in ["perf_dip", "perf_spike"]:
            body = "Done — I’ll draft the campaign using the latest views, calls, CTR, and active offer."
        elif trigger_kind in ["research_digest", "research_digest_release", "category_research_digest_release"]:
            body = "Done — I’ll convert the digest into a short, source-backed WhatsApp message."
        else:
            body = "Done 👍 I’ll prepare the draft/action now. You can review before it goes live."

        return {
            "action": "send",
            "body": body,
            "cta": "none",
            "rationale": "User accepted; routed directly to trigger-specific action."
        }

    if any(x in msg for x in ["join", "judna", "register", "start", "onboard", "magicpin"]):
        return {
            "action": "send",
            "body": "Great — I’ll start onboarding directly. Please share business name, city, and phone number.",
            "cta": "open_ended",
            "rationale": "Detected onboarding intent; avoided repeated qualification."
        }

    if any(x in msg for x in ["gst", "tax", "loan"]):
        return {
            "action": "send",
            "body": "I can’t handle GST filing, but I can help with growth actions: profile, offers, reviews, posts, and customer reminders. Want me to draft the next best one?",
            "cta": "YES/NO",
            "rationale": "Off-topic request handled politely while staying on Vera’s scope."
        }

    return {
        "action": "send",
        "body": "Got it. Tell me one detail — offer, review, post, or customer reminder — and I’ll turn it into the next best action.",
        "cta": "open_ended",
        "rationale": "Unclear reply handled with a useful clarifying prompt instead of generic repetition."
    }