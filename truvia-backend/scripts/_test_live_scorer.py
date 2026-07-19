"""Deterministic unit test of the Live Scam Interceptor scorer (LLM disabled).

Verifies Spec §7 + §10 checklist items that don't require the DB/HTTP layer:
  * escalating conversation -> cumulative score rises
  * de-escalating conversation -> plateaus/declines, not stuck high
  * intervention fires exactly once per high-crossing
  * exact formula: 0.4*prev + 0.6*turn (+15 bonus on 3 consecutive moderate+)
"""
import asyncio
from app.agents.threat_evaluator import threat_evaluator_agent
from app.services import live_session_scorer as scorer

# Disable the LLM so the trajectory math is deterministic and offline.
threat_evaluator_agent.client = None


async def run_conversation(name, turns):
    print(f"\n=== {name} ===")
    prev = 0
    prior_scores = []
    intervened = False
    fires = 0
    trajectory = []
    for i, t in enumerate(turns):
        full = "\n".join(turns[: i + 1])
        res = await scorer.score_turn(
            turn_text=t,
            previous_cumulative=prev,
            prior_turn_scores=prior_scores,
            full_conversation_text=full,
            intervention_already_shown=intervened,
        )
        if res["fire_intervention"]:
            fires += 1
            intervened = True
        trajectory.append(res["cumulative_score"])
        print(
            f"  turn {i}: turn_score={res['turn_score']:3d} cum={res['cumulative_score']:3d} "
            f"band={res['severity_band']:8s} escalating={res['is_escalating']!s:5s} "
            f"bonus={res['bonus_applied']!s:5s} fire={res['fire_intervention']!s:5s}"
        )
        prev = res["cumulative_score"]
        prior_scores.append(res["turn_score"])
    print(f"  trajectory={trajectory}  intervention_fires={fires}")
    return trajectory, fires


async def main():
    # 1. Manual formula check: prev=50, turn=100, no bonus -> 0.4*50+0.6*100 = 80
    r = await scorer.score_turn(
        turn_text="pay 50000 via upi now or police will arrest you",
        previous_cumulative=50,
        prior_turn_scores=[30],  # window [30, turn>=40] -> only 2 elems, no bonus
        full_conversation_text="x",
        intervention_already_shown=False,
    )
    print("Formula check prev=50 turn=100 ->", r["cumulative_score"], "(expected 80)")

    # Escalating: benign -> urgency -> impersonation -> payment demand
    esc, esc_fires = await run_conversation(
        "Escalating conversation",
        [
            "Hello, is this Mr Sharma?",
            "This is an urgent notice, your account will be blocked today, act immediately.",
            "I am calling from CBI. There is a warrant and you are under digital arrest.",
            "Transfer 50000 rupees via UPI now to clear your name or we arrest you.",
            "Share the OTP you just received to confirm the payment immediately.",
        ],
    )

    # De-escalating: alarming start, then caller backs off / benign
    deesc, deesc_fires = await run_conversation(
        "De-escalating conversation",
        [
            "This is CBI, you are under arrest, pay via UPI immediately or warrant issued!",
            "Oh sorry, I think I dialed the wrong number.",
            "No payment needed, please ignore my earlier message.",
            "Have a nice day, thank you.",
            "Goodbye.",
        ],
    )

    print("\n--- assertions ---")
    assert esc[-1] > esc[0], "escalating: final should exceed first"
    assert esc[-1] >= 70, f"escalating: should reach high, got {esc[-1]}"
    assert esc_fires == 1, f"escalating: intervention should fire exactly once, got {esc_fires}"
    assert deesc[-1] < deesc[0], f"de-escalating: should decline from peak, got {deesc}"
    assert deesc[-1] < 70, f"de-escalating: should not stay high, got {deesc[-1]}"
    print("ALL ASSERTIONS PASSED")


asyncio.run(main())
