from typing import Optional
from datetime import datetime
from conversation_handlers import respond


# ---------- HELPERS ----------

def pct(value):
    try:
        return f"{abs(float(value) * 100):.0f}%"
    except Exception:
        return None


def human_datetime(value):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%d %b, %I:%M %p").lstrip("0")
    except Exception:
        return str(value)


def get_name(merchant):
    return merchant.get("identity", {}).get("name", "there")


def get_offer(category, merchant):
    offers = merchant.get("offers", [])

    for offer in offers:
        if offer.get("status") == "active":
            return offer.get("title") or offer.get("name")

    if offers:
        return offers[0].get("title") or offers[0].get("name")

    catalog = category.get("offer_catalog", [])
    if catalog:
        first = catalog[0]
        if isinstance(first, dict):
            return first.get("title")
        return str(first)

    return None


def can_message_customer(customer, purpose):
    consent = customer.get("consent", {})
    return purpose in consent.get("scope", [])


def get_peer_ctr(category):
    return category.get("peer_stats", {}).get("avg_ctr")


def category_voice(category, merchant):
    slug = merchant.get("category_slug") or category.get("slug", "")

    if slug == "dentists":
        return "clinical-peer"
    if slug == "salons":
        return "warm-practical"
    if slug == "restaurants":
        return "operator-focused"
    if slug == "gyms":
        return "coach-like"
    if slug == "pharmacies":
        return "precise-trustworthy"

    return "peer"


def merchant_place(merchant):
    identity = merchant.get("identity", {})
    locality = identity.get("locality")
    city = identity.get("city")

    if locality and city:
        return f"{locality}, {city}"
    if locality:
        return locality
    if city:
        return city
    return None


def category_label(category, merchant):
    slug = merchant.get("category_slug") or category.get("slug", "business")
    return slug.replace("_", " ").replace("-", " ")


def merchant_context_line(merchant, category):
    parts = []

    place = merchant_place(merchant)
    if place:
        parts.append(place)

    cat = category_label(category, merchant)
    if cat:
        parts.append(cat)

    subscription = merchant.get("subscription", {})
    plan = subscription.get("plan")
    days = subscription.get("days_remaining")

    if plan and days is not None:
        parts.append(f"{plan} plan, {days} days left")

    if parts:
        return "Context: " + " • ".join(parts) + "."

    return ""


def customer_aggregate_line(merchant):
    agg = merchant.get("customer_aggregate", {})
    total = agg.get("total_unique_ytd")
    lapsed = agg.get("lapsed_180d_plus")
    retention = agg.get("retention_6mo_pct")

    facts = []

    if total:
        facts.append(f"{total} customers YTD")
    if lapsed:
        facts.append(f"{lapsed} lapsed 180d+")
    if retention is not None:
        facts.append(f"{int(float(retention) * 100)}% 6mo retention")

    if facts:
        return "Customer base: " + ", ".join(facts) + "."

    return ""


def voice_line(category, merchant):
    voice = category_voice(category, merchant)

    if voice == "clinical-peer":
        return "Tone: clinical, factual, no overclaims."
    if voice == "warm-practical":
        return "Tone: warm, practical, service-first."
    if voice == "operator-focused":
        return "Tone: direct, demand and revenue focused."
    if voice == "coach-like":
        return "Tone: motivating, action-oriented."
    if voice == "precise-trustworthy":
        return "Tone: precise, trust-first, no exaggeration."

    return ""


def get_digest_item(category, trigger):
    payload = trigger.get("payload", {})

    if payload.get("top_item"):
        return payload["top_item"]

    top_id = payload.get("top_item_id")
    digest = category.get("digest", [])

    if top_id:
        for item in digest:
            if item.get("id") == top_id:
                return item

    return digest[0] if digest else {}


def cta_for(kind):
    ctas = {
        "perf_dip": "Reply YES — I’ll draft a recovery post now.",
        "perf_spike": "Reply YES — I’ll capture this demand today.",
        "competitor_opened": "Reply YES — I’ll draft your counter-offer.",
        "review_theme_emerged": "Reply YES — I’ll draft the reply + fix note.",
        "regulation_change": "Reply YES — I’ll make the checklist.",
        "supply_alert": "Reply YES — I’ll draft the recall note.",
        "festival_upcoming": "Reply YES — I’ll draft the campaign.",
        "ipl_match_today": "Reply YES — I’ll draft tonight’s post.",
        "research_digest": "Reply YES — I’ll convert this into a shareable WhatsApp.",
        "research_digest_release": "Reply YES — I’ll convert this into a shareable WhatsApp.",
        "category_research_digest_release": "Reply YES — I’ll convert this into a shareable WhatsApp.",
        "milestone_reached": "Reply YES — I’ll draft the milestone post.",
        "gbp_unverified": "Reply YES — I’ll guide the verification steps.",
        "category_trend_movement": "Reply YES — I’ll draft a timely post.",
        "weather_heatwave": "Reply YES — I’ll draft a timely customer message.",
        "local_news_event": "Reply YES — I’ll draft the local update.",
        "category_seasonal": "Reply YES — I’ll draft the seasonal campaign.",
        "active_planning_intent": "Reply YES — I’ll draft the offer and post.",
        "dormant_with_vera": "Reply YES — I’ll suggest one quick growth action.",
        "winback_eligible": "Reply YES — I’ll draft a restart plan.",
    }
    return ctas.get(kind, "Reply YES — I’ll draft it now.")


# ---------- MAIN COMPOSE ----------

def compose(
    category: dict,
    merchant: dict,
    trigger: dict,
    customer: Optional[dict] = None
) -> Optional[dict]:

    kind = trigger.get("kind", "")
    payload = trigger.get("payload", {})
    suppression_key = trigger.get("suppression_key") or f"{kind}:{trigger.get('id', 'unknown')}"

    name = get_name(merchant)
    offer = get_offer(category, merchant)
    voice = category_voice(category, merchant)
    peer_ctr = get_peer_ctr(category)

    context_line = merchant_context_line(merchant, category)
    customer_line = customer_aggregate_line(merchant)
    tone_line = voice_line(category, merchant)

    perf = merchant.get("performance", {})
    signals = merchant.get("signals", [])

    views = perf.get("views")
    calls = perf.get("calls")
    ctr = perf.get("ctr")

    # ---------- PERFORMANCE DIP ----------
    if kind == "perf_dip":
        metric = payload.get("metric", "calls")
        delta = payload.get("delta_pct")
        window = payload.get("window", "recently")

        body = f"{name}, your {metric} dropped"

        if delta is not None:
            body += f" {pct(delta)}"

        body += f" in the last {window}."

        if context_line:
            body += f"\n{context_line}"

        facts = []
        if views is not None:
            facts.append(f"{views} views")
        if calls is not None:
            facts.append(f"{calls} calls")
        if ctr is not None:
            facts.append(f"CTR {pct(ctr)}")

        if facts:
            body += "\nCurrent: " + " → ".join(facts) + "."

        if peer_ctr:
            body += f"\nPeer benchmark CTR: {pct(peer_ctr)}."

        blockers = []
        if "no_active_offers" in signals:
            blockers.append("no active offer")
        if "unverified_gbp" in signals:
            blockers.append("unverified Google profile")
        if any("stale_posts" in s for s in signals):
            blockers.append("stale posts")

        if blockers:
            body += "\nLikely blocker: " + ", ".join(blockers) + "."

        if offer:
            body += f"\n\nQuick fix: promote “{offer}” + one fresh post."

        body += "\nThis is likely costing you calls/walk-ins right now."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Performance dip using merchant metrics, location/category context, peer benchmark, offer context, and {voice} tone."
        }

    # ---------- PERFORMANCE SPIKE ----------
    if kind == "perf_spike":
        metric = payload.get("metric", "performance")
        delta = payload.get("delta_pct")
        driver = payload.get("likely_driver")

        body = f"{name}, good momentum — {metric} is improving"

        if delta is not None:
            body += f" by {pct(delta)}"

        body += "."

        if context_line:
            body += f"\n{context_line}"

        if driver:
            body += f"\nLikely driver: {driver}."

        if offer:
            body += f"\nBest next step: push “{offer}” while demand is warm."

        body += "\nThis warm demand should be converted before it cools."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Performance spike converted into a timely campaign using merchant context and {voice} tone."
        }

    # ---------- RESEARCH DIGEST ----------
    if kind in ["research_digest", "research_digest_release", "category_research_digest_release"]:
        item = get_digest_item(category, trigger)

        title = item.get("title") or payload.get("title") or "a new category update"
        source = item.get("source") or payload.get("source")
        trial_n = item.get("trial_n") or payload.get("trial_n")
        segment = item.get("patient_segment") or payload.get("patient_segment")

        body = f"{name}, {title}."

        if tone_line:
            body += f"\n{tone_line}"

        if customer_line:
            body += f"\n{customer_line}"

        if trial_n:
            body += f"\nIt covers {int(trial_n):,} cases."

        if segment:
            body += f"\nRelevant for your {str(segment).replace('_', ' ')} cohort."

        if source:
            body += f"\n— {source}"

        body += "\nThis is useful content your customers can understand."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Research digest grounded in category source, customer aggregate, and {voice} tone."
        }

    # ---------- COMPETITOR ----------
    if kind == "competitor_opened":
        comp = payload.get("competitor_name", "a new competitor")
        dist = payload.get("distance_km")
        their_offer = payload.get("their_offer")

        body = f"{name}, {comp} opened nearby"

        if dist is not None:
            body += f" ({dist} km away)"

        body += "."

        if context_line:
            body += f"\n{context_line}"

        if their_offer:
            body += f"\nThey’re pushing: “{their_offer}”."

        if offer:
            body += f"\nYour counter can be: “{offer}” + fresh visibility post."

        body += "\nThis is the moment to protect nearby demand."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Competitor trigger uses competitor payload, location/category context, and merchant offer."
        }

    # ---------- REVIEW THEME ----------
    if kind == "review_theme_emerged":
        theme = payload.get("theme", "customer feedback")
        count = payload.get("occurrences_30d")
        quote = payload.get("common_quote")

        body = f"{name}, customers are repeatedly mentioning “{theme}”"

        if count:
            body += f" — {count} times in 30 days"

        body += "."

        if context_line:
            body += f"\n{context_line}"

        if quote:
            body += f"\nExample: “{quote}”."

        body += "\nFixing this early protects rating and future clicks."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Review theme converted into reputation action using merchant context and {voice} tone."
        }

    # ---------- REGULATION CHANGE ----------
    if kind == "regulation_change":
        deadline = payload.get("deadline_iso")
        category_name = payload.get("category") or merchant.get("category_slug", "your category")

        body = f"{name}, there is a compliance update for {category_name}."

        if tone_line:
            body += f"\n{tone_line}"

        if context_line:
            body += f"\n{context_line}"

        if deadline:
            body += f"\nDeadline: {human_datetime(deadline)}."

        body += "\nMissing this can create avoidable operational risk."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Regulation trigger handled with category voice, merchant context, deadline, and checklist action."
        }

    # ---------- SUPPLY ALERT ----------
    if kind == "supply_alert":
        molecule = payload.get("molecule")
        batches = payload.get("affected_batches", [])
        manufacturer = payload.get("manufacturer")

        body = f"{name}, urgent supply alert."

        if context_line:
            body += f"\n{context_line}"

        if molecule:
            body += f"\nMolecule: {molecule}."

        if manufacturer:
            body += f"\nManufacturer: {manufacturer}."

        if batches:
            body += f"\nAffected batches: {', '.join(batches)}."

        body += "\nThis needs quick filtering before customers are affected."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Supply alert handled with provided product/batch details and merchant context."
        }

    # ---------- FESTIVAL ----------
    if kind == "festival_upcoming":
        festival = payload.get("festival", "festival")
        date = payload.get("date")
        days = payload.get("days_until")

        body = f"{name}, {festival} is coming"

        if date:
            body += f" on {date}"

        if days is not None:
            body += f" ({days} days away)"

        body += "."

        if context_line:
            body += f"\n{context_line}"

        if offer:
            body += f"\nBest move: promote “{offer}” with a timely post."

        body += "\nThis window is short, so timing matters."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"Festival trigger turned into timely category campaign using merchant context and offer."
        }

    # ---------- IPL MATCH ----------
    if kind == "ipl_match_today":
        match = payload.get("match", "today’s match")
        venue = payload.get("venue")
        match_time = payload.get("match_time_iso")

        body = f"{name}, {match} is today."

        if context_line:
            body += f"\n{context_line}"

        if venue:
            body += f"\nVenue: {venue}."

        if match_time:
            body += f"\nMatch time: {human_datetime(match_time)}."

        body += "\nMatch-night demand is time-sensitive."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "IPL trigger uses human-readable time, merchant context, and timely campaign framing."
        }

    # ---------- CATEGORY SEASONAL / TREND / WEATHER / LOCAL EVENT ----------
    if kind in ["category_seasonal", "category_trend_movement", "weather_heatwave", "local_news_event"]:
        if kind == "category_trend_movement":
            query = payload.get("query", "category search")
            delta = payload.get("delta_yoy")
            body = f"{name}, “{query}” searches are moving"
            if delta:
                body += f" by {pct(delta)}"
            body += "."
        elif kind == "weather_heatwave":
            body = f"{name}, heatwave conditions are active in your market."
        elif kind == "local_news_event":
            body = f"{name}, local update: {payload.get('headline', 'a nearby event may affect demand')}."
        else:
            trends = payload.get("trends", [])
            body = f"{name}, seasonal demand is shifting."
            if trends:
                body += f"\nSignals: {', '.join(trends[:3])}."

        if context_line:
            body += f"\n{context_line}"

        if offer:
            body += f"\nBest move: promote “{offer}” with a timely post."

        body += "\nThis is a good moment to act before demand moves elsewhere."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": f"External trigger converted into timely action with category and merchant context."
        }

    # ---------- MILESTONE ----------
    if kind == "milestone_reached":
        metric = payload.get("metric", "milestone")
        value = payload.get("value_now")
        milestone = payload.get("milestone_value")

        body = f"{name}, quick milestone: {metric}"

        if value:
            body += f" is now {value}"

        if milestone:
            body += f" — close to {milestone}"

        body += "."

        if context_line:
            body += f"\n{context_line}"

        body += "\nThis is useful social proof for your profile."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Milestone trigger converted into social-proof content with merchant context."
        }

    # ---------- GBP UNVERIFIED ----------
    if kind == "gbp_unverified":
        uplift = payload.get("estimated_uplift_pct")

        body = f"{name}, your Google profile is still unverified."

        if context_line:
            body += f"\n{context_line}"

        if uplift:
            body += f"\nEstimated upside after verification: {pct(uplift)}."

        body += "\nUnverified profiles often lose trust at the decision point."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "GBP verification trigger handled with merchant context and direct next step."
        }

    # ---------- ACTIVE PLANNING / DORMANT / CURIOUS ----------
    if kind in ["active_planning_intent", "curious_ask_due", "scheduled_recurring", "dormant_with_vera", "winback_eligible"]:
        topic = payload.get("intent_topic") or payload.get("ask_template") or payload.get("last_topic") or "growth action"
        last_msg = payload.get("merchant_last_message")

        if kind == "active_planning_intent" and last_msg:
            body = f"{name}, continuing from your message: “{last_msg}”."
        elif kind in ["curious_ask_due", "scheduled_recurring"]:
            body = f"{name}, quick question: what’s the most asked service this week?"
            if context_line:
                body += f"\n{context_line}"
            body += "\nTell me in one line — I’ll turn it into a post or offer."
            return {
                "body": body,
                "cta": "open_ended",
                "send_as": "vera",
                "suppression_key": suppression_key,
                "rationale": "Curiosity-driven engagement using merchant/category context."
            }
        else:
            body = f"{name}, this is a good moment to restart growth."

        if context_line:
            body += f"\n{context_line}"

        body += f"\nI can turn “{topic}” into one clear action."
        body += f"\n{cta_for(kind)}"

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Planning/dormancy trigger handled with low-friction action and merchant context."
        }

    # ---------- CUSTOMER RECALL ----------
    if kind == "recall_due" and customer:
        if not can_message_customer(customer, "recall_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        lang = customer.get("identity", {}).get("language_pref", "")
        relationship = customer.get("relationship", {})
        last_visit = relationship.get("last_visit")
        service = payload.get("service_due", "follow-up").replace("_", " ")
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
            "rationale": "Customer recall uses consent, last visit, service due, slots, language preference, and merchant offer."
        }

    # ---------- CUSTOMER LAPSED ----------
    if kind in ["customer_lapsed_soft", "customer_lapsed_hard"] and customer:
        if not can_message_customer(customer, "winback_offers"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        days = payload.get("days_since_last_visit")
        focus = payload.get("previous_focus")

        body = f"Hi {cname}, {name} here 👋\n\n"

        if days:
            body += f"It’s been {days} days since your last visit."
        else:
            body += "We haven’t seen you in a while."

        if focus:
            body += f"\nWe can help you restart your {focus.replace('_', ' ')} plan."

        if offer:
            body += f"\nOffer: {offer}."

        body += "\n\nReply YES to pick a slot or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Customer winback uses lapse state, consent, previous focus, and offer."
        }

    # ---------- TRIAL FOLLOWUP ----------
    if kind == "trial_followup" and customer:
        if not can_message_customer(customer, "kids_program_updates"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        options = payload.get("next_session_options", [])
        slot = options[0].get("label") if options else "this week"

        body = (
            f"Hi {cname}, {name} here 👋\n\n"
            f"Hope the trial went well. Next available session: {slot}.\n"
            "Reply YES to confirm or STOP to opt out."
        )

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Trial follow-up uses next-session option and consent."
        }

    # ---------- WEDDING PACKAGE FOLLOWUP ----------
    if kind == "wedding_package_followup" and customer:
        if not can_message_customer(customer, "bridal_package_followup"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        wedding_date = payload.get("wedding_date")
        next_step = payload.get("next_step_window_open")

        body = f"Hi {cname}, {name} here 👋\n\n"

        if wedding_date:
            body += f"Your wedding is on {wedding_date}. "

        if next_step:
            body += f"This is a good time for {next_step.replace('_', ' ')}."

        body += "\nReply YES and we’ll share package options. STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Wedding follow-up uses customer stage, timing, and consent."
        }

    # ---------- CHRONIC REFILL ----------
    if kind == "chronic_refill_due" and customer:
        if not can_message_customer(customer, "refill_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")
        meds = payload.get("molecule_list", [])
        stock_runs_out = payload.get("stock_runs_out_iso")
        delivery_saved = payload.get("delivery_address_saved")

        body = f"Hi {cname}, {name} here.\n\n"

        if meds:
            body += f"Your refill may be due for: {', '.join(meds)}."

        if stock_runs_out:
            body += f"\nStock may run out around: {human_datetime(stock_runs_out)}."

        if delivery_saved:
            body += "\nYour delivery address is saved."

        body += "\n\nReply YES for refill support or STOP to opt out."

        return {
            "body": body,
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Chronic refill reminder uses consent, medicine list, stock date, and delivery context."
        }

    # ---------- APPOINTMENT ----------
    if kind == "appointment_tomorrow" and customer:
        if not can_message_customer(customer, "appointment_reminders"):
            return None

        cname = customer.get("identity", {}).get("name", "there")

        return {
            "body": f"Hi {cname}, reminder from {name} 👋\n\nYour appointment is tomorrow. Reply YES to confirm or STOP to opt out.",
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": suppression_key,
            "rationale": "Appointment reminder sent only with appointment-reminder consent."
        }

    # ---------- HIGH URGENCY SAFE FALLBACK ----------
    if trigger.get("urgency", 0) >= 4:
        return {
            "body": f"{name}, high-priority update: {kind.replace('_', ' ')}.\n{cta_for(kind)}",
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Safe fallback without inventing details."
        }

    return None