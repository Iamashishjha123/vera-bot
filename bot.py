def compose(category, merchant, trigger, customer=None):
    name = merchant["identity"]["name"]
    merchant_id = merchant["merchant_id"]

    kind = trigger["kind"]
    payload = trigger.get("payload", {})
    signals = merchant.get("signals", [])
    subscription = merchant.get("subscription", {})

    # ---------------- PERF DIP ----------------
    if kind == "perf_dip":
        delta = payload.get("delta_pct", 0)

        if delta > -0.2:
            return None  # ignore small dips

        problem = []
        if "no_active_offers" in signals:
            problem.append("no active offers")
        if "unverified_gbp" in signals:
            problem.append("profile not verified")

        problem_text = ", ".join(problem) if problem else "low engagement"

        return {
            "body": (
                f"{name}, your performance dropped {abs(delta)*100:.0f}% in last 7 days.\n\n"
                f"Main issue: {problem_text}.\n\n"
                "Reply YES and I’ll fix this in 10 seconds."
            ),
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": trigger["suppression_key"],
            "rationale": "Significant performance drop with identifiable issues"
        }

    # ---------------- RENEWAL ----------------
    if kind == "renewal_due":
        days = payload.get("days_remaining", 0)

        return {
            "body": (
                f"{name}, your Pro plan expires in {days} days.\n\n"
                "After expiry, visibility drops sharply.\n\n"
                "Reply YES to renew instantly."
            ),
            "cta": "YES/NO",
            "send_as": "vera",
            "suppression_key": trigger["suppression_key"],
            "rationale": "Subscription expiring soon"
        }

    # ---------------- REVIEW ISSUE ----------------
    if kind == "review_theme_emerged":
        theme = payload.get("theme")
        quote = payload.get("common_quote", "")

        return {
            "body": (
                f"{name}, customers are mentioning '{theme}' more often.\n\n"
                f"Example: \"{quote}\"\n\n"
                "Fixing this can improve ratings quickly. Want help?"
            ),
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": trigger["suppression_key"],
            "rationale": "Negative review trend detected"
        }

    # ---------------- CUSTOMER RECALL ----------------
    if kind == "recall_due" and customer:
        cname = customer["identity"]["name"]
        service = payload.get("service_due")

        if not customer["preferences"].get("reminder_opt_in"):
            return None  # respect consent

        return {
            "body": (
                f"Hi {cname}, it's time for your {service} 👋\n\n"
                "We have slots this week.\n"
                "Reply YES to book instantly."
            ),
            "cta": "YES/STOP",
            "send_as": "merchant_on_behalf",
            "suppression_key": trigger["suppression_key"],
            "rationale": "Service recall due"
        }

    # ---------------- COMPETITOR ----------------
    if kind == "competitor_opened":
        comp = payload.get("competitor_name")
        offer = payload.get("their_offer")

        return {
            "body": (
                f"{name}, a new competitor ({comp}) opened nearby.\n"
                f"They are offering: {offer}\n\n"
                "Want me to create a stronger counter-offer?"
            ),
            "cta": "open_ended",
            "send_as": "vera",
            "suppression_key": trigger["suppression_key"],
            "rationale": "Competitive threat detected"
        }

    # ---------------- FALLBACK ----------------
    return None