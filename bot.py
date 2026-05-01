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


def get_category_offer(category, merchant):
    active_offer = get_offer(category, merchant)
    if active_offer:
        return active_offer

    catalog = category.get("offer_catalog", [])
    if not catalog:
        return None

    first = catalog[0]
    if isinstance(first, dict):
        return first.get("title")
    return str(first)


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


# ---------- MAIN COMPOSE ----------

def compose(category: dict, merchant: dict, trigger: dict, customer: Optional[dict] = None) -> dict:
    kind = trigger.get("kind")
    payload = trigger.get("payload", {})
    suppression_key = trigger.get("suppression_key")

    name = get_name(merchant)
    lang = get_lang(merchant)
    offer = get_category_offer(category, merchant)
    voice = category_voice(category, merchant)
    peer_ctr = get_peer_ctr(category)

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
        if peer_ctr:
            body += f"\nPeer benchmark CTR: {int(peer_ctr * 100)}%."

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
            "rationale": f"Performance dip using merchant metrics, category offer, and {voice} tone."
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
    
        # ---------- PERFORMANCE SPIKE ----------
    if kind == "perf_spike":
        metric = payload.get("metric", "performance")
        delta = payload.get("delta_pct")
        driver = payload.get("likely_driver")

        body = f"{name}, good momentum — {metric} is improving"

        if delta is not None:
            body += f" by {abs(int(delta * 100))}%"

        body += "."

        if driver:
            body += f"\nLikely driver: {driver}."

        if offer:
            body += f"\n\nBest next step: promote '{offer}' while demand is warm."

        body += "\nReply YES — I’ll draft it."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Performance spike converted into a timely campaign opportunity."
        }


    # ---------- REVIEW THEME ----------
    if kind == "review_theme_emerged":
        theme = payload.get("theme", "customer feedback")
        count = payload.get("occurrences_30d")
        quote = payload.get("common_quote")

        body = f"{name}, customers are repeatedly mentioning '{theme}'"

        if count:
            body += f" — {count} times in the last 30 days"

        body += "."

        if quote:
            body += f"\nExample: \"{quote}\""

        body += "\nReply YES — I’ll draft a polite review reply + fix note."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Review trend detected and converted into reputation-management action."
        }


    # ---------- RENEWAL DUE ----------
    if kind == "renewal_due":
        days = payload.get("days_remaining")
        plan = payload.get("plan", "plan")
        amount = payload.get("renewal_amount")

        body = f"{name}, your {plan} plan"

        if days is not None:
            body += f" expires in {days} days"
        else:
            body += " is due soon"

        body += "."

        if perf.get("views") or perf.get("calls"):
            body += f"\nCurrent value: {perf.get('views', 0)} views, {perf.get('calls', 0)} calls."

        if amount:
            body += f"\nRenewal amount: ₹{amount}."

        body += "\nReply YES — I’ll help you renew before growth actions pause."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Renewal reminder tied to current merchant performance and continuity of growth actions."
        }


    # ---------- GBP UNVERIFIED ----------
    if kind == "gbp_unverified":
        uplift = payload.get("estimated_uplift_pct")

        body = f"{name}, your Google profile is still unverified."

        if uplift:
            body += f"\nEstimated upside after verification: {int(uplift * 100)}% more trust/actions."

        body += "\nReply YES — I’ll guide you through phone/postcard verification."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "GBP verification trigger handled with a direct next step."
        }


    # ---------- REGULATION CHANGE ----------
    if kind == "regulation_change":
        deadline = payload.get("deadline_iso")
        category_name = payload.get("category") or merchant.get("category_slug", "your category")

        body = f"{name}, there is a compliance update for {category_name}."

        if deadline:
            body += f"\nDeadline: {deadline}."

        body += "\nReply YES — I’ll create a short action checklist."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Regulation trigger handled with clear deadline and checklist action."
        }


    # ---------- SUPPLY ALERT ----------
    if kind == "supply_alert":
        molecule = payload.get("molecule")
        batches = payload.get("affected_batches", [])
        manufacturer = payload.get("manufacturer")

        body = f"{name}, urgent supply alert."

        if molecule:
            body += f"\nMolecule: {molecule}."

        if manufacturer:
            body += f"\nManufacturer: {manufacturer}."

        if batches:
            body += f"\nAffected batches: {', '.join(batches)}."

        body += "\nReply YES — I’ll draft a customer filter + recall note."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Supply alert handled with product-specific details and recall workflow."
        }


    # ---------- FESTIVAL UPCOMING ----------
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

        if offer:
            body += f"\nBest move: promote '{offer}' with a timely post."

        body += "\nReply YES — I’ll draft the campaign."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Festival trigger converted into timely campaign opportunity."
        }


    # ---------- IPL MATCH TODAY ----------
    if kind == "ipl_match_today":
        match = payload.get("match", "today’s match")
        venue = payload.get("venue")
        match_time = payload.get("match_time_iso")

        body = f"{name}, {match} is today."

        if venue:
            body += f"\nVenue: {venue}."

        if match_time:
            body += f"\nMatch time: {match_time}."

        body += "\nFor restaurants, match-night combos usually work better than flat discounts."
        body += "\nReply YES — I’ll draft tonight’s WhatsApp + listing post."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "IPL/local event trigger turned into category-relevant campaign action."
        }


    # ---------- CATEGORY SEASONAL ----------
    if kind == "category_seasonal":
        trends = payload.get("trends", [])
        season = payload.get("season")

        body = f"{name}, seasonal demand is shifting"

        if season:
            body += f" for {season}"

        body += "."

        if trends:
            body += f"\nSignals: {', '.join(trends[:3])}."

        body += "\nReply YES — I’ll turn this into a shelf/campaign action plan."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Seasonal category trigger converted into business action."
        }


    # ---------- MILESTONE REACHED ----------
    if kind == "milestone_reached":
        metric = payload.get("metric", "milestone")
        value = payload.get("value_now")
        milestone = payload.get("milestone_value")

        body = f"{name}, quick milestone: {metric}"

        if value:
            body += f" is now {value}"

        if milestone:
            body += f" — close to {milestone}"

        body += ".\nReply YES — I’ll draft a post to highlight this."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Milestone trigger converted into social-proof content."
        }


    # ---------- ACTIVE PLANNING INTENT ----------
    if kind == "active_planning_intent":
        topic = payload.get("intent_topic", "growth idea")
        last_msg = payload.get("merchant_last_message")

        body = f"{name}, "

        if last_msg:
            body += f"continuing from your message: \"{last_msg}\"\n\n"

        body += (
            f"For {topic}, I suggest:\n"
            "1) clear package name\n"
            "2) starter price\n"
            "3) one GBP post\n"
            "4) one WhatsApp message\n\n"
            "Reply YES — I’ll draft both now."
        )

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Merchant intent handled directly instead of asking more qualifying questions."
        }


    # ---------- CURIOUS ASK / SCHEDULED RECURRING ----------
    if kind in ["curious_ask_due", "scheduled_recurring"]:
        ask_template = payload.get("ask_template", "what service is in demand this week")

        body = (
            f"{name}, quick question: {ask_template.replace('_', ' ')}?\n\n"
            "Tell me in one line — I’ll turn it into a post or offer."
        )

        return {
            "body": body,
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Curiosity-driven engagement nudge to increase merchant response frequency."
        }


    # ---------- DORMANT WITH VERA ----------
    if kind == "dormant_with_vera":
        days = payload.get("days_since_last_merchant_message")
        last_topic = payload.get("last_topic", "growth")

        body = f"{name}, it’s been a while since we worked on {last_topic}"

        if days:
            body += f" — {days} days"

        body += ".\nReply YES — I’ll suggest one quick growth action."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Dormancy trigger reopens conversation with low-friction action."
        }


    # ---------- WINBACK ELIGIBLE ----------
    if kind == "winback_eligible":
        days = payload.get("days_since_expiry")
        dip = payload.get("perf_dip_pct")
        lapsed = payload.get("lapsed_customers_added_since_expiry")

        body = f"{name}, you have a winback opportunity."

        if days:
            body += f"\nYour plan expired {days} days ago."

        if dip:
            body += f"\nPerformance is down {abs(int(dip * 100))}%."

        if lapsed:
            body += f"\n{lapsed} customers lapsed since expiry."

        body += "\nReply YES — I’ll draft a restart plan."

        return {
            "body": body,
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Winback trigger uses expiry/performance/customer lapse context."
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
            "rationale": "Customer winback uses lapse state, consent, prior focus, and merchant offer."
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
            body += f"\nStock may run out around: {stock_runs_out}."

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


    # ---------- APPOINTMENT TOMORROW ----------
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

    # ---------- SAFE DEFAULT ----------
    if trigger.get("urgency", 0) >= 4:
        return {
            "body": f"{name}, high-priority update: {kind.replace('_', ' ')}.\nReply YES — I’ll suggest the safest next action.",
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": suppression_key,
            "rationale": "Safe high-urgency fallback without inventing details."
    }

    return None