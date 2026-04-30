from typing import Optional
from conversation_handlers import respond

# ---------- HELPERS ----------

def get_name(merchant):
    return merchant.get("identity", {}).get("name", "there")


def get_lang(merchant):
    langs = merchant.get("identity", {}).get("languages", [])
    return langs[0] if langs else "en"


def get_offer(category, merchant):
    offers = merchant.get("offers", [])
    if offers:
        return offers[0].get("title") or offers[0].get("name")

    catalog = category.get("offer_catalog", [])
    return catalog[0] if catalog else None


def can_message_customer(customer, purpose):
    consent = customer.get("consent", {})
    return purpose in consent.get("scope", [])


# ---------- MAIN COMPOSE ----------

def compose(category: dict, merchant: dict, trigger: dict, customer: Optional[dict] = None) -> dict:
    kind = trigger.get("kind")
    payload = trigger.get("payload", {})
    suppression_key = trigger.get("suppression_key")

    name = get_name(merchant)
    lang = get_lang(merchant)
    offer = get_offer(category, merchant)

    perf = merchant.get("performance", {})
    signals = merchant.get("signals", [])

    # ---------- 1. PERFORMANCE DIP ----------
    if kind == "perf_dip":
        metric = payload.get("metric", "calls")
        delta = payload.get("delta_pct", -0.3)
        window = payload.get("window", "7d")

        views = perf.get("views", 0)
        calls = perf.get("calls", 0)
        ctr = perf.get("ctr", 0)

        body = f"{name}, your {metric} dropped {abs(int(delta*100))}% in the last {window}.\n"
        body += f"Current: {views} views → {calls} calls (CTR {int(ctr*100)}%)."

        if "no_active_offers" in signals:
            body += "\nIssue: no active offer."

        if "unverified_gbp" in signals:
            body += "\nAlso, profile is unverified."

        if offer:
            body += f"\n\nQuick fix: launch '{offer}' + 1 fresh post."

        body += "\nReply YES — I’ll draft it for you."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance dip using real metrics, signals, and actionable fix."
        }

    # ---------- 2. RESEARCH DIGEST ----------
    if kind in ["research_digest", "research_digest_release"]:
        top_item = payload.get("top_item", {})

        title = top_item.get("title", "a useful update")
        source = top_item.get("source")
        trial_n = top_item.get("trial_n")
        segment = top_item.get("patient_segment")

        body = f"{name}, {title}."

        if trial_n:
            body += f" ({trial_n:,} cases)"

        if segment:
            body += f"\nRelevant for your {segment.replace('_',' ')} patients."

        if source:
            body += f"\n— {source}"

        body += "\n\nWant me to draft a patient WhatsApp for this?"

        return {
            "body": body,
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Research-based curiosity + value."
        }

    # ---------- 3. COMPETITOR ----------
    if kind == "competitor_opened":
        comp = payload.get("competitor_name", "a new competitor")
        dist = payload.get("distance_km", "")
        their_offer = payload.get("their_offer", "")

        body = f"{name}, {comp} just opened {dist} km away."

        if their_offer:
            body += f"\nThey’re running '{their_offer}'."

        if offer:
            body += f"\n\nWe can counter with '{offer}' + visibility push."

        body += "\nWant me to draft your counter strategy?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Competition-based urgency + action."
        }

    # ---------- 4. CUSTOMER RECALL ----------
    if kind == "recall_due" and customer:
        if not can_message_customer(customer, "recall_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        lang = customer.get("identity", {}).get("language_pref", "")
        relationship = customer.get("relationship", {})

        last_visit = relationship.get("last_visit")
        service = payload.get("service_due", "follow-up")
        slots = payload.get("available_slots", [])

        slot_text = " / ".join([s.get("label", "") for s in slots[:2] if s.get("label")])

        body = f"Hi {cname}, {name} here 👋\n\n"

        if last_visit:
            body += f"It’s been a while since your last visit ({last_visit}). "

        body += f"Your {service} is due."

        if slot_text:
            if "hi" in lang:
                body += f"\nApke liye slots ready hain: {slot_text}."
            else:
                body += f"\nAvailable slots: {slot_text}."

        if offer:
            body += f"\nOffer: {offer}."

        body += "\n\nReply YES to book or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Customer recall using consent, slots, and personalization."
        }

    # ---------- DEFAULT ----------
    return {
        "body": f"{name}, I found a quick growth opportunity for you. Want me to show it?",
        "cta": "YES/NO",
        "send_as": "vera",
        "suppression_key": suppression_key,
        "rationale": "Fallback message."
    }