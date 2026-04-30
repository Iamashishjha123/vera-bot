AUTO_REPLY_HINTS = [
    "thank you for contacting", "we will get back", "business account",
    "auto reply", "automated", "thanks for contacting"
]


def pct(x):
    try:
        return f"{x * 100:.0f}%"
    except Exception:
        return "N/A"


def money(x):
    try:
        return f"₹{int(x):,}"
    except Exception:
        return str(x)


def active_offer(merchant):
    for offer in merchant.get("offers", []):
        if offer.get("status") == "active":
            return offer.get("title")
    return None


def can_message_customer(customer, scope):
    if not customer:
        return False

    prefs = customer.get("preferences", {})
    scopes = customer.get("consent", {}).get("scope", [])

    if prefs.get("reminder_opt_in") is False:
        return False

    return scope in scopes


def category_fix(category_slug, merchant):
    offer = active_offer(merchant)

    if category_slug == "dentists":
        return offer or "Dental Cleaning @ ₹299"
    if category_slug == "salons":
        return offer or "Haircut @ ₹99"
    if category_slug == "restaurants":
        return offer or "Meal combo / thali offer"
    if category_slug == "gyms":
        return offer or "3 FREE Trial Classes"
    if category_slug == "pharmacies":
        return offer or "Free Home Delivery > ₹499"

    return offer or "service+price offer"


def compose(category, merchant, trigger, customer=None):
    identity = merchant.get("identity", {})
    name = identity.get("name", "there")
    city = identity.get("city", "")
    locality = identity.get("locality", "")
    category_slug = merchant.get("category_slug", category.get("slug", "business"))

    kind = trigger.get("kind", "")
    payload = trigger.get("payload", {})
    suppression_key = trigger.get("suppression_key", f"{kind}:{merchant.get('merchant_id')}")

    perf = merchant.get("performance", {})
    signals = merchant.get("signals", [])
    subscription = merchant.get("subscription", {})
    offer = active_offer(merchant)
    suggested_offer = category_fix(category_slug, merchant)

    # ---------- MERCHANT TRIGGERS ----------

    if kind in ["perf_dip", "seasonal_perf_dip"]:
        metric = payload.get("metric", "performance")
        delta = payload.get("delta_pct")
        window = payload.get("window", "recently")

        blockers = []
        if "no_active_offers" in signals:
            blockers.append("no active offer")
        if "unverified_gbp" in signals:
            blockers.append("GBP not verified")
        if any("dormant_with_vera" in s for s in signals):
            blockers.append("no recent Vera action")

        body = (
            f"{name}, {metric} is down {pct(abs(delta)) if delta else 'recently'} over {window}.\n\n"
            f"Snapshot: {perf.get('views')} views, {perf.get('calls')} calls, CTR {pct(perf.get('ctr'))}.\n"
            f"Likely blocker: {', '.join(blockers) if blockers else 'conversion weakness'}.\n\n"
            f"Best fix: push “{suggested_offer}” + one fresh post for {locality}. "
            f"Reply YES — I’ll draft it now."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance dip handled using metric drop, merchant performance, signals, and category-correct offer."
        }

    if kind == "perf_spike":
        body = (
            f"{name}, good momentum — {payload.get('metric', 'calls')} is up {pct(payload.get('delta_pct'))}.\n"
            f"Likely driver: {payload.get('likely_driver', 'recent activity')}.\n\n"
            f"Let’s capture this while demand is warm. Want me to create a post + WhatsApp campaign around “{suggested_offer}”?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance spike converted into a momentum-capture action."
        }

    if kind == "renewal_due":
        days = payload.get("days_remaining", subscription.get("days_remaining"))
        amount = payload.get("renewal_amount")
        plan = payload.get("plan", subscription.get("plan", "plan"))

        body = (
            f"{name}, your {plan} plan expires in {days} days.\n\n"
            f"Current value: {perf.get('views')} views, {perf.get('calls')} calls, {perf.get('directions')} directions in "
            f"{perf.get('window_days', 30)} days."
        )

        if amount:
            body += f"\nRenewal amount: {money(amount)}."

        body += "\n\nReply YES and I’ll help renew before growth actions pause."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Renewal reminder tied to actual merchant performance and plan value."
        }

    if kind == "research_digest":
        top_id = payload.get("top_item_id")
        digest = category.get("digest", [])
        item = next((d for d in digest if d.get("id") == top_id), digest[0] if digest else {})

        body = f"{name}, new {category_slug} insight: {item.get('title', 'a useful category update')}.\n"

        if item.get("source"):
            body += f"Source: {item.get('source')}.\n"

        body += "\nWant me to turn this into a customer-friendly WhatsApp + GBP post?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Research trigger grounded in category digest item and converted into merchant action."
        }

    if kind == "review_theme_emerged":
        body = (
            f"{name}, review pattern detected: “{payload.get('theme')}” came up "
            f"{payload.get('occurrences_30d')} times in 30 days.\n\n"
        )

        if payload.get("common_quote"):
            body += f"Customer wording: “{payload.get('common_quote')}”\n\n"

        body += "Want me to draft: 1) polite public reply, 2) internal fix note, 3) follow-up message?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Review trend converted into reputation and operations action."
        }

    if kind == "competitor_opened":
        body = (
            f"{name}, competitor alert — {payload.get('competitor_name')} opened "
            f"{payload.get('distance_km')} km away.\n"
            f"Their offer: {payload.get('their_offer')}.\n\n"
            f"Your current offer: {offer or 'no active offer'}.\n"
            f"Recommended counter: “{suggested_offer}” with better positioning, not deeper discount.\n\n"
            "Reply YES and I’ll draft it."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Competitor trigger uses distance, competitor offer, and merchant offer state."
        }

    if kind in ["regulation_change", "supply_alert"]:
        if kind == "supply_alert":
            body = (
                f"{name}, urgent supply alert.\n\n"
                f"Molecule: {payload.get('molecule')}\n"
                f"Affected batches: {', '.join(payload.get('affected_batches', []))}\n\n"
                "Reply YES and I’ll prepare customer filter + recall message draft."
            )
        else:
            body = (
                f"{name}, compliance update for {category_slug}.\n\n"
                f"Deadline: {payload.get('deadline_iso')}.\n"
                "Reply YES and I’ll create a short action checklist."
            )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "High-priority compliance/supply trigger handled with precise next step."
        }

    if kind == "gbp_unverified":
        body = (
            f"{name}, your Google profile is still unverified.\n\n"
            f"Estimated upside after verification: {pct(payload.get('estimated_uplift_pct'))} more trust/actions.\n"
            "Reply YES and I’ll guide you through phone/postcard verification."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "GBP verification trigger with estimated uplift from payload."
        }

    if kind in ["festival_upcoming", "ipl_match_today", "category_seasonal"]:
        if kind == "ipl_match_today":
            body = (
                f"{name}, {payload.get('match')} is today in {city}.\n\n"
                f"For restaurants, match-night combos work better than flat discounts. Suggested: “{suggested_offer}”.\n"
                "Reply YES and I’ll draft tonight’s WhatsApp + listing post."
            )
        elif kind == "festival_upcoming":
            body = (
                f"{name}, {payload.get('festival')} is coming on {payload.get('date')}.\n\n"
                f"For {category_slug}, service+price campaigns work better than generic discounting. Suggested: “{suggested_offer}”.\n"
                "Reply YES and I’ll draft one campaign."
            )
        else:
            trends = payload.get("trends", [])
            body = (
                f"{name}, seasonal demand is shifting in {city}.\n\n"
                f"Signals: {', '.join(trends[:3])}.\n"
                "Reply YES and I’ll turn this into a shelf/campaign action plan."
            )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "External event/seasonality converted into timely merchant action."
        }

    if kind in ["active_planning_intent", "curious_ask_due"]:
        topic = payload.get("intent_topic", payload.get("ask_template", "growth idea"))
        last_msg = payload.get("merchant_last_message", "")

        body = f"{name}, "
        if last_msg:
            body += f"continuing from your message: “{last_msg}”\n\n"

        body += (
            f"For {topic}, I suggest:\n"
            "1) clear package name\n"
            "2) starter price\n"
            "3) GBP post\n"
            "4) WhatsApp message\n\n"
            "Reply YES and I’ll draft both now."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Intent-handoff handled directly without repetitive qualification."
        }

    if kind in ["milestone_reached", "dormant_with_vera", "winback_eligible", "cde_opportunity"]:
        body = (
            f"{name}, quick opportunity: {kind.replace('_', ' ')}.\n\n"
            f"Context: {payload}.\n\n"
            "Reply YES and I’ll suggest the best next action."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Lower-frequency merchant trigger handled with contextual fallback."
        }

    # ---------- CUSTOMER TRIGGERS ----------

    if kind == "recall_due" and customer:
        if not can_message_customer(customer, "recall_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        service = payload.get("service_due", "follow-up").replace("_", " ")
        slots = payload.get("available_slots", [])
        slot_text = " / ".join([s.get("label", "") for s in slots[:2] if s.get("label")])

        body = f"Hi {cname}, {name} here 👋\n\nYour {service} is due."

        if offer:
            body += f"\nCurrent offer: {offer}."

        if slot_text:
            body += f"\nAvailable slots: {slot_text}."

        body += "\n\nReply YES to book or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Customer recall uses consent, service due, slots, and merchant offer."
        }

    if kind in ["customer_lapsed_hard", "customer_lapsed_soft"] and customer:
        scope = "winback_offers"
        if not can_message_customer(customer, scope):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        days = payload.get("days_since_last_visit")

        body = f"Hi {cname}, {name} here 👋\n\nIt’s been {days} days since your last visit."

        if payload.get("previous_focus"):
            body += f"\nWe can help you restart your {payload.get('previous_focus').replace('_', ' ')} plan."

        if offer:
            body += f"\nOffer available: {offer}."

        body += "\n\nReply YES to pick a slot or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Customer winback based on lapse state, consent, and previous focus."
        }

    if kind in ["trial_followup", "wedding_package_followup"] and customer:
        cname = customer.get("identity", {}).get("name", "there")

        if kind == "trial_followup":
            if not can_message_customer(customer, "kids_program_updates"):
                return None
            slot = payload.get("next_session_options", [{}])[0].get("label", "this week")
            body = (
                f"Hi {cname}, {name} here 👋\n\n"
                f"Hope the trial went well. Next available session: {slot}.\n"
                "Reply YES to confirm or STOP to opt out."
            )
        else:
            if not can_message_customer(customer, "bridal_package_followup"):
                return None
            body = (
                f"Hi {cname}, {name} here 👋\n\n"
                f"Your wedding is on {payload.get('wedding_date')}. "
                f"This is a good time to start the {payload.get('next_step_window_open')}.\n"
                "Reply YES and we’ll share package options. STOP to opt out."
            )

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Customer follow-up based on specific journey stage and consent."
        }

    if kind == "chronic_refill_due" and customer:
        if not can_message_customer(customer, "refill_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        meds = ", ".join(payload.get("molecule_list", []))

        body = (
            f"Hi {cname}, {name} here.\n\n"
            f"Your refill may be due for: {meds}.\n"
            f"Stock may run out around: {payload.get('stock_runs_out_iso')}."
        )

        if payload.get("delivery_address_saved"):
            body += "\nYour delivery address is saved."

        body += "\n\nReply YES for refill support or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Chronic refill reminder respects consent and uses refill payload."
        }

    if kind == "appointment_tomorrow" and customer:
        if not can_message_customer(customer, "appointment_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")

        return {
            "body": (
                f"Hi {cname}, reminder from {name} 👋\n\n"
                "Your appointment is tomorrow. Reply YES to confirm or STOP to opt out."
            ),
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Appointment reminder sent only with appointment-reminder consent."
        }

    return None


def respond(message):
    msg = (message or "").lower().strip()

    if any(x in msg for x in AUTO_REPLY_HINTS):
        return {
            "action": "wait",
            "wait_seconds": 900,
            "rationale": "Likely WhatsApp Business auto-reply detected; backing off."
        }

    if any(x in msg for x in ["yes", "haan", "ok", "okay", "sure", "go ahead", "send", "kar do"]):
        return {
            "action": "send",
            "body": "Done 👍 I’ll prepare the draft/action now. You can review before it goes live.",
            "cta": "none",
            "rationale": "Merchant/customer accepted the suggested action."
        }

    if any(x in msg for x in ["no", "not now", "stop", "later", "nahi"]):
        return {
            "action": "end",
            "rationale": "User declined or opted out."
        }

    if "price" in msg or "cost" in msg or "kitna" in msg:
        return {
            "action": "send",
            "body": "I’ll keep it simple: one clear offer, one price point, and no heavy discounting. Want me to draft 2 options?",
            "cta": "YES/NO",
            "rationale": "User asked about price; continue with low-friction option."
        }

    return {
        "action": "send",
        "body": "Got it. I can suggest the best next action based on your listing data. Reply YES and I’ll draft it.",
        "cta": "YES/NO",
        "rationale": "Unclear response; nudging toward a simple next step."
    }