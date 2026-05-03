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


def is_auto_reply(msg: str) -> bool:
    return any(x in msg for x in AUTO_REPLY_HINTS)


def respond(state, merchant_message: str) -> dict:
    msg = (merchant_message or "").lower().strip()
    turns = state.get("turns", [])
    trigger_kind = state.get("trigger_kind", "")
    from_role = state.get("last_from_role", "merchant")

    auto_count = 0
    for t in turns:
        text = t.get("body", "").lower().strip()
        if t.get("from") in ["merchant", "customer"] and is_auto_reply(text):
            auto_count += 1

    # 1. Auto-reply handling: wait once, then end
    if is_auto_reply(msg):
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

    # 2. STOP / refusal handling
    if any(x in msg for x in ["stop", "not interested", "no", "nahi", "later", "not now", "don't message"]):
        return {
            "action": "end",
            "rationale": "User declined or opted out."
        }

    # 3. Customer slot pick / booking confirmation
    slot_words = [
        "book", "slot", "appointment", "confirm",
        "wed", "wednesday", "thu", "thursday",
        "mon", "monday", "tue", "tuesday",
        "fri", "friday", "sat", "saturday",
        "sun", "sunday",
        "am", "pm", "6pm", "5pm", "7pm", "morning", "evening"
    ]

    if from_role == "customer" or trigger_kind in [
        "recall_due",
        "appointment_tomorrow",
        "customer_lapsed_soft",
        "customer_lapsed_hard",
        "trial_followup",
        "wedding_package_followup",
        "chronic_refill_due"
    ]:
        if any(x in msg for x in slot_words) or any(x in msg for x in ["yes", "haan", "ok", "okay", "sure"]):
            return {
                "action": "send",
                "body": "Confirmed 👍 I’ll mark this as your preferred slot and share it with the clinic/team for booking confirmation.",
                "cta": "none",
                "rationale": "Customer selected or accepted a slot; moved directly to booking confirmation."
            }

    # 4. Specific compliance follow-up
    if any(x in msg for x in ["audit", "x-ray", "xray", "setup", "checklist", "compliance", "d-speed"]):
        return {
            "action": "send",
            "body": "Got it. I’ll create a 5-point compliance checklist: equipment type, shielding, signage, operator safety, and documentation. Reply YES — I’ll draft it.",
            "cta": "YES/NO",
            "rationale": "Specific compliance follow-up handled with domain-relevant next step."
        }

    # 5. Acceptance handling
    if any(x in msg for x in ["yes", "haan", "ok", "okay", "sure", "go ahead", "kar do", "send", "do it", "let's do it"]):
        if trigger_kind in ["regulation_change", "supply_alert"]:
            body = "Done — I’ll draft the checklist/action note using the provided deadline and payload details."
        elif trigger_kind in ["perf_dip", "perf_spike"]:
            body = "Done — I’ll draft the campaign using the latest views, calls, CTR, and active offer."
        elif trigger_kind in ["research_digest", "research_digest_release", "category_research_digest_release"]:
            body = "Done — I’ll convert the digest into a short, source-backed WhatsApp message."
        elif trigger_kind in ["competitor_opened"]:
            body = "Done — I’ll draft a counter-offer and listing post to protect nearby demand."
        elif trigger_kind in ["review_theme_emerged"]:
            body = "Done — I’ll draft a polite review reply and a short internal fix note."
        else:
            body = "Done 👍 I’ll prepare the draft/action now. You can review before it goes live."

        return {
            "action": "send",
            "body": body,
            "cta": "none",
            "rationale": "User accepted; routed directly to trigger-specific action."
        }

    # 6. Onboarding intent
    if any(x in msg for x in ["join", "judna", "register", "start", "onboard", "magicpin"]):
        return {
            "action": "send",
            "body": "Great — I’ll start onboarding directly. Please share business name, city, and phone number.",
            "cta": "open_ended",
            "rationale": "Detected onboarding intent; avoided repeated qualification."
        }

    # 7. Off-topic but polite
    if any(x in msg for x in ["gst", "tax", "loan"]):
        return {
            "action": "send",
            "body": "I can’t handle GST filing, but I can help with growth actions: profile, offers, reviews, posts, and customer reminders. Want me to draft the next best one?",
            "cta": "YES/NO",
            "rationale": "Off-topic request handled politely while staying on Vera’s scope."
        }

    # 8. Non-generic fallback
    return {
        "action": "send",
        "body": "Got it. Tell me one detail — offer, review, post, or customer reminder — and I’ll turn it into the next best action.",
        "cta": "open_ended",
        "rationale": "Unclear reply handled with useful clarification instead of generic repetition."
    }