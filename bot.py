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
    consent = customer.get("consent", {})
    scopes = consent.get("scope", [])

    if prefs.get("reminder_opt_in") is False:
        return False

    return scope in scopes or "promotional_offers" in scopes


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

    send_as = "merchant_on_behalf" if trigger.get("scope") == "customer" else "vera"

    # ---------------- MERCHANT-FACING ----------------

    if kind == "perf_dip":
        metric = payload.get("metric", "performance")
        delta = payload.get("delta_pct")
        window = payload.get("window", "recently")

        blockers = []
        if "no_active_offers" in signals:
            blockers.append("no active offer")
        if "unverified_gbp" in signals:
            blockers.append("GBP not verified")
        if "dormant_with_vera_14d" in signals or "dormant_with_vera_38d" in signals:
            blockers.append("no recent Vera action")

        blocker_text = ", ".join(blockers) if blockers else "conversion weakness"

        body = (
            f"{name}, {metric} is down {pct(abs(delta)) if delta else 'recently'} over {window}.\n\n"
            f"Snapshot: {perf.get('views')} views, {perf.get('calls')} calls, CTR {pct(perf.get('ctr'))}.\n"
            f"Likely blocker: {blocker_text}.\n\n"
            f"Want me to create one service+price offer + one fresh post for {locality}?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance dip handled using metric drop, merchant performance, and merchant signals."
        }

    if kind == "perf_spike":
        body = (
            f"{name}, good momentum — {payload.get('metric', 'calls')} is up {pct(payload.get('delta_pct'))}.\n"
            f"Likely driver: {payload.get('likely_driver', 'recent activity')}.\n\n"
            "Want me to turn this into a fresh GBP post + WhatsApp campaign?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance spike converted into momentum-capture campaign."
        }

    if kind == "renewal_due":
        days = payload.get("days_remaining", subscription.get("days_remaining"))
        amount = payload.get("renewal_amount")
        plan = payload.get("plan", subscription.get("plan", "plan"))

        body = (
            f"{name}, your {plan} plan expires in {days} days.\n\n"
            f"You got {perf.get('views')} views and {perf.get('calls')} calls in the last {perf.get('window_days', 30)} days."
        )

        if amount:
            body += f"\nRenewal amount: {money(amount)}."

        body += "\n\nWant me to help you renew before growth actions pause?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Renewal reminder tied to actual merchant performance."
        }

    if kind == "research_digest":
        top_id = payload.get("top_item_id")
        digest = category.get("digest", [])
        item = next((d for d in digest if d.get("id") == top_id), digest[0] if digest else {})

        body = (
            f"{name}, new {category_slug} insight: {item.get('title', 'a useful category update')}.\n"
        )

        if item.get("source"):
            body += f"Source: {item.get('source')}.\n"

        body += "\nWant me to convert this into a customer-friendly WhatsApp message?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Research trigger grounded in category digest item."
        }

    if kind in ["regulation_change", "supply_alert"]:
        if kind == "supply_alert":
            body = (
                f"{name}, urgent supply alert.\n\n"
                f"Molecule: {payload.get('molecule')}\n"
                f"Affected batches: {', '.join(payload.get('affected_batches', []))}\n\n"
                "Want me to prepare a customer filter + recall message draft?"
            )
        else:
            body = (
                f"{name}, compliance update for {category_slug}.\n\n"
                f"Deadline: {payload.get('deadline_iso')}.\n"
                "Want me to create a short action checklist?"
            )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "High-priority compliance/supply trigger handled with operational next step."
        }

    if kind == "review_theme_emerged":
        body = (
            f"{name}, review pattern detected: {payload.get('theme')} came up "
            f"{payload.get('occurrences_30d')} times in 30 days.\n\n"
        )

        if payload.get("common_quote"):
            body += f"Customer wording: “{payload.get('common_quote')}”\n\n"

        body += "Want me to draft a reply + one fix message for your team?"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Review theme converted into a reputation-management action."
        }

    if kind == "competitor_opened":
        body = (
            f"{name}, competitor alert — {payload.get('competitor_name')} opened "
            f"{payload.get('distance_km')} km away.\n"
            f"Their offer: {payload.get('their_offer')}.\n\n"
            f"Your current offer: {offer or 'no active offer'}.\n"
            "Want me to draft a stronger counter-offer without sounding cheap?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Competitor trigger uses distance, competitor offer, and merchant offer state."
        }

    if kind == "gbp_unverified":
        body = (
            f"{name}, your Google profile is still unverified.\n\n"
            f"Estimated upside after verification: {pct(payload.get('estimated_uplift_pct'))} more trust/actions.\n"
            "Want me to guide you through postcard/phone verification?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "GBP verification trigger with uplift from payload."
        }

    if kind in ["festival_upcoming", "ipl_match_today", "category_seasonal"]:
        if kind == "ipl_match_today":
            body = (
                f"{name}, {payload.get('match')} is today in {city}.\n\n"
                "For restaurants, match-night combos usually work better than flat discounts.\n"
                "Want me to draft a WhatsApp + listing post for tonight?"
            )
        elif kind == "festival_upcoming":
            body = (
                f"{name}, {payload.get('festival')} is coming on {payload.get('date')}.\n\n"
                f"For {category_slug}, a service+price campaign works better than generic discounting.\n"
                "Want me to draft one campaign?"
            )
        else:
            trends = payload.get("trends", [])
            body = (
                f"{name}, seasonal demand is shifting.\n\n"
                f"Signals: {', '.join(trends[:3])}.\n"
                "Want me to turn this into a shelf/campaign action plan?"
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
            "1) one clear package name\n"
            "2) one starter price\n"
            "3) one GBP post + one WhatsApp message\n\n"
            "Want me to draft both now?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Intent-handoff handled directly without repetitive qualification."
        }

    if kind in ["milestone_reached", "dormant_with_vera", "winback_eligible", "cde_opportunity", "seasonal_perf_dip"]:
        body = (
            f"{name}, quick update: {kind.replace('_', ' ')}.\n\n"
            f"Context: {payload}.\n"
            "Want me to suggest the best next action?"
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Supported lower-frequency merchant trigger handled with contextual fallback."
        }

    # ---------------- CUSTOMER-FACING ----------------

    if kind == "recall_due" and customer:
        if not can_message_customer(customer, "recall_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        service = payload.get("service_due", "follow-up").replace("_", " ")
        slots = payload.get("available_slots", [])
        slot_text = " / ".join([s.get("label", "") for s in slots[:2]])

        body = (
            f"Hi {cname}, {name} here 👋\n\n"
            f"Your {service} is due."
        )

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
            "rationale": "Customer recall uses consent, service due, slots, and offer."
        }

    if kind in ["customer_lapsed_hard", "customer_lapsed_soft"] and customer:
        if not can_message_customer(customer, "winback_offers"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        days = payload.get("days_since_last_visit")

        body = (
            f"Hi {cname}, {name} here 👋\n\n"
            f"It’s been {days} days since your last visit."
        )

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
            "rationale": "Customer winback based on lapse state and prior focus."
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