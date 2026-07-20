"""Module 5: Live Scam Interceptor — turn-by-turn scoring logic (Spec §7).

This is the one genuinely new piece of logic in the module. Everything else
reuses existing code:
  * per-turn scoring reuses Agent 2's rule-based red-flag extractor
    (`threat_evaluator_agent.rule_based_analyze`);
  * the optional LLM reasoning pass reuses Agent 2's `_llm_analyze`.

The cumulative/trajectory formula is intentionally simple and explainable
(no trained sequence model), exactly as documented in the spec:

    cumulative_score = 0.4 * previous_cumulative_score + 0.6 * turn_score

with a flat +15 escalation bonus (capped at 100) applied when THREE consecutive
turns each individually exceed the "moderate" threshold — rewarding sustained,
turn-over-turn escalation, which is itself a strong signal.
"""
import logging
from app.agents.threat_evaluator import threat_evaluator_agent

logger = logging.getLogger("truvia.services.live_scorer")

# Severity-band thresholds — identical to Agent 2 / threat_scores conventions.
MODERATE_THRESHOLD = 40
HIGH_THRESHOLD = 70
CRITICAL_THRESHOLD = 90

# Cumulative/trajectory formula weights (Spec §7.2). Recent turn weighted heavier.
PREV_WEIGHT = 0.4
TURN_WEIGHT = 0.6

# Consecutive-escalation bonus (Spec §7.2).
ESCALATION_BONUS = 15
CONSECUTIVE_TURNS_FOR_BONUS = 3


def severity_band(score: int) -> str:
    """Map a 0-100 score to a severity band (same bands as Agent 2)."""
    if score >= CRITICAL_THRESHOLD:
        return "critical"
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= MODERATE_THRESHOLD:
        return "moderate"
    return "low"


# Category-appropriate mid-conversation guidance (Spec §4.5). Keyed by a
# lowercase substring of the scam category; falls back to the extractor's own
# victim_instructions (the same "Recommended Actions" content Fraud Shield
# already surfaces) when no specific match is found.
INTERVENTION_GUIDANCE = {
    "digital arrest": (
        "They are impersonating law enforcement. Real police, CBI, or courts NEVER "
        "place you under 'digital arrest', interrogate you over a video call, or demand "
        "money to settle a case. Do not pay anything. Ask for a written order, then hang "
        "up and call 1930 or report at cybercrime.gov.in."
    ),
    "arrest": (
        "Genuine law enforcement never demands money over a call to avoid arrest. Do not "
        "transfer any funds. Disconnect and verify by calling 1930."
    ),
    "upi": (
        "No genuine refund or prize needs your UPI PIN or a 'collect request' approval — "
        "entering your PIN sends money OUT, not in. Do not approve any request and do not "
        "share your PIN or OTP. Stop the transaction now."
    ),
    "refund": (
        "Real refunds are automatic and never require you to approve a payment or share an "
        "OTP/PIN. This is a reversal trick. Do not approve anything."
    ),
    "kyc": (
        "Banks never ask you to complete KYC, share an OTP, or click a link over a call or "
        "SMS. Do not share any code or open any link. Verify only through your bank's "
        "official app or branch."
    ),
    "job": (
        "Legitimate jobs never require an upfront deposit, registration fee, or payment to "
        "'unlock' earnings. Any request to pay first is a scam. Do not transfer money."
    ),
    "lottery": (
        "You cannot win a lottery you never entered, and no genuine prize requires a fee or "
        "tax paid in advance. Do not pay or share bank details."
    ),
    "sextortion": (
        "Do not pay and do not share anything further. Blackmail demands escalate if paid. "
        "Stop responding, preserve the messages as evidence, and report at cybercrime.gov.in "
        "or call 1930."
    ),
    "loan": (
        "Legitimate lenders never demand advance 'processing fees' via UPI or threaten you. "
        "Do not pay. Uninstall any loan app that accessed your contacts and report it."
    ),
}


def build_intervention_message(category: str | None, reasoning: dict | None) -> str:
    """Produce category-specific, mid-conversation guidance for the banner."""
    key = (category or "").lower()
    for fragment, message in INTERVENTION_GUIDANCE.items():
        if fragment in key:
            return message
    # Fallback: reuse the extractor's own victim_instructions (Fraud Shield's
    # "Recommended Actions") where the category isn't specifically mapped.
    instructions = (reasoning or {}).get("victim_instructions") or []
    if instructions:
        return "This looks like an active scam. " + " ".join(instructions[:2])
    return (
        "This conversation shows strong signs of an active scam. Do not share OTPs, "
        "passwords, or PINs, and do not make any payment. End the call and verify "
        "independently before doing anything they ask."
    )


async def score_turn(
    *,
    turn_text: str,
    previous_cumulative: int,
    prior_turn_scores: list[int],
    full_conversation_text: str,
    intervention_already_shown: bool,
) -> dict:
    """Score a single new turn against the whole conversation-so-far.

    Args:
        turn_text: the text the citizen typed for this new turn.
        previous_cumulative: the trajectory score as of the previous turn (0 for the first turn).
        prior_turn_scores: individual turn_scores of all prior turns, in order.
        full_conversation_text: all turns joined (used only for the optional LLM pass).
        intervention_already_shown: whether the "high" banner has already fired this session.

    Returns a dict with the per-turn and cumulative assessment plus intervention state.
    """
    # 1. Per-turn scoring — reuse Agent 2's rule-based extractor (Spec §7.1).
    turn_score, _turn_band, turn_category, _turn_conf, reasoning, degraded = (
        threat_evaluator_agent.rule_based_analyze(turn_text)
    )

    # 2. Cumulative/trajectory scoring (Spec §7.2). Exact documented formula.
    cumulative = PREV_WEIGHT * float(previous_cumulative) + TURN_WEIGHT * float(turn_score)

    # Consecutive-escalation bonus: +15 (capped at 100) when the last three
    # turns (including this one) each individually exceed the moderate threshold.
    all_turn_scores = list(prior_turn_scores) + [turn_score]
    window = all_turn_scores[-CONSECUTIVE_TURNS_FOR_BONUS:]
    bonus_applied = (
        len(window) == CONSECUTIVE_TURNS_FOR_BONUS
        and all(s >= MODERATE_THRESHOLD for s in window)
    )
    if bonus_applied:
        cumulative += ESCALATION_BONUS

    cumulative_score = int(round(cumulative))
    cumulative_score = max(0, min(cumulative_score, 100))  # clamp 0..100
    band = severity_band(cumulative_score)

    scam_category = turn_category

    # 3. Conditional LLM pass (Spec §7.3): only invoke Agent 2's full LLM
    #    reasoning once the rule-based cumulative score reaches moderate or
    #    above — not on every turn (latency + cost). Enriches the category and
    #    reasoning for the overall assessment; the trajectory score itself
    #    stays rule-based/explainable.
    llm_used = False
    if cumulative_score >= MODERATE_THRESHOLD and threat_evaluator_agent.client:
        try:
            _, _, llm_category, _, llm_reasoning, _ = await threat_evaluator_agent._llm_analyze(
                full_conversation_text
            )
            if llm_category:
                scam_category = llm_category
            if llm_reasoning:
                reasoning = llm_reasoning
            llm_used = True
        except Exception as e:  # pragma: no cover - network dependent
            logger.error(f"Live-session LLM enrichment failed: {e}. Using rule-based reasoning.")

    # 4. Intervention threshold (Spec §7.4): fire the first time the cumulative
    #    score crosses into "high", and only once per session per crossing.
    fire_intervention = (not intervention_already_shown) and cumulative_score >= HIGH_THRESHOLD
    intervention = None
    if fire_intervention:
        intervention = {
            "shown": True,
            "message": build_intervention_message(scam_category, reasoning),
            "category": scam_category,
        }

    return {
        "turn_score": turn_score,
        "cumulative_score": cumulative_score,
        "severity_band": band,
        "scam_category": scam_category,
        "reasoning": reasoning,  # stored as flagged_phrases_json (threat_scores.reasoning_json shape)
        "is_escalating": cumulative_score > previous_cumulative,
        "bonus_applied": bonus_applied,
        "llm_used": llm_used,
        "degraded": degraded,
        "fire_intervention": fire_intervention,
        "intervention": intervention,
    }
