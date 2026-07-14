"""Ad-hoc end-to-end verification of the Citizen Fraud Shield flow.
Run against a live server on 127.0.0.1:8000. Prints PASS/FAIL per acceptance criterion.
"""
import sys
import time
import uuid
import httpx

BASE = "http://127.0.0.1:8000/api/v1"

SCAM_A = (
    "URGENT: This is Inspector Sharma from CBI. A parcel in your name contains illegal "
    "drugs. You are under digital arrest. Do NOT disconnect. To avoid immediate arrest, "
    "transfer Rs 250000 now to UPI id cbi.verify@okhdfc or share the OTP sent to your phone."
)
SCAM_B = (
    "Dear customer, your electricity bill is overdue. Power will be disconnected tonight. "
    "Pay immediately at http://quick-bill-pay.example and call 9876543210."
)
BENIGN = "Hey, are we still on for lunch tomorrow at 1pm? Let me know, thanks!"


def jprint(label, obj):
    print(f"--- {label} ---")
    print(obj)


def main():
    results = {}
    email = f"citizen_{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        # Register + login
        r = c.post("/auth/register", json={"email": email, "password": "Password123!", "name": "Test Citizen", "phone": "9000000001"})
        assert r.status_code in (201, 409), r.text
        r = c.post("/auth/login", json={"email": email, "password": "Password123!"})
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"

        def submit_text(text):
            resp = c.post("/reports/submit", data={"source_type": "text", "text_content": text})
            assert resp.status_code == 201, resp.text
            rid = resp.json()["id"]
            # poll
            for _ in range(30):
                d = c.get(f"/reports/{rid}").json()
                if d["status"] in ("scored", "escalated", "failed") or d["threat_scores"]:
                    return d
                time.sleep(1)
            return c.get(f"/reports/{rid}").json()

        rep_a = submit_text(SCAM_A)
        rep_b = submit_text(SCAM_B)
        rep_benign = submit_text(BENIGN)

        sa = rep_a["threat_scores"][0] if rep_a["threat_scores"] else None
        sb = rep_b["threat_scores"][0] if rep_b["threat_scores"] else None
        sn = rep_benign["threat_scores"][0] if rep_benign["threat_scores"] else None

        jprint("SCAM_A score", {k: sa[k] for k in ("threat_score", "severity_band", "scam_category", "confidence_score", "degraded_mode")} if sa else None)
        jprint("SCAM_A reasoning", sa["reasoning_json"] if sa else None)
        jprint("SCAM_B score", {k: sb[k] for k in ("threat_score", "severity_band", "scam_category")} if sb else None)
        jprint("BENIGN score", {k: sn[k] for k in ("threat_score", "severity_band", "scam_category")} if sn else None)

        # Criterion: real, differing scores (not canned)
        results["scores_present"] = bool(sa and sb and sn)
        results["scores_differ"] = bool(sa and sn and sa["threat_score"] != sn["threat_score"])
        results["scam_high_benign_low"] = bool(sa and sn and sa["threat_score"] > sn["threat_score"])
        # Criterion: explanation references actual content signals
        ind = " ".join(sa["reasoning_json"].get("key_indicators", [])).lower() if sa else ""
        results["explanation_specific"] = any(w in ind for w in ("arrest", "law enforcement", "otp", "financial", "transaction", "upi"))

        # Criterion: entities captured (UPI/phone/domain) — check via officer? citizen can't list entities.
        # Verify indirectly: escalate rep_a and confirm case persisted; entities used for linking.
        esc = c.post(f"/reports/{rep_a['id']}/escalate")
        results["escalate_ok"] = esc.status_code == 200 and "case_id" in esc.json()
        case_id = esc.json().get("case_id")
        jprint("escalate", esc.json())

        # Re-fetch report: status should be escalated now (only after explicit action)
        rep_a2 = c.get(f"/reports/{rep_a['id']}").json()
        results["status_escalated_only_after_action"] = rep_a2["status"] == "escalated" and rep_b["status"] == "scored"

        # Criterion: chat returns grounded answer with citations
        chat = c.post("/chat", json={"query": "Is it safe to scan a QR code to receive a refund?"})
        results["chat_ok"] = chat.status_code == 200
        cj = chat.json()
        results["chat_has_citations"] = bool(cj.get("citations"))
        jprint("chat answer", cj.get("answer"))
        jprint("chat citations", cj.get("citations"))

        # Criterion: PDF download reflects this report
        pdf = c.get(f"/reports/{rep_a['id']}/pdf")
        results["pdf_ok"] = pdf.status_code == 200 and pdf.content[:4] == b"%PDF" and len(pdf.content) > 1000
        jprint("pdf bytes", len(pdf.content))

        # Criterion: history lists the submissions
        hist = c.get("/reports", params={"limit": "20"}).json()
        ids = {h["id"] for h in hist}
        results["history_lists_reports"] = {rep_a["id"], rep_b["id"], rep_benign["id"]}.issubset(ids)

    print("\n================ RESULTS ================")
    ok = True
    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
        ok = ok and v
    print("=========================================")
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
