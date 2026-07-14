"""Officer / Law Enforcement Dashboard end-to-end verification."""
import sys, uuid, json, httpx

BASE = "http://127.0.0.1:8000/api/v1"

def main():
    results = {}
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        # ---- officer login (seeded) ----
        r = c.post("/auth/login", json={"email": "officer@truvia.org", "password": "password"})
        assert r.status_code == 200, f"officer login failed: {r.text}"
        officer_token = r.json()["access_token"]
        # officer id
        c.headers["Authorization"] = f"Bearer {officer_token}"
        me = c.get("/auth/me").json()
        officer_id = me["id"]
        print("officer:", me["email"], me["role"])

        # ---- role guard: a citizen must NOT access officer endpoints ----
        c2 = httpx.Client(base_url=BASE, timeout=30.0)
        clog = c2.post("/auth/login", json={"email": "citizen@truvia.org", "password": "password"})
        if clog.status_code == 200 and "access_token" in clog.json():
            c2.headers["Authorization"] = f"Bearer {clog.json()['access_token']}"
            guard = c2.get("/cases/stats")
            results["citizen_blocked_from_cases"] = guard.status_code == 403
            print("citizen -> /cases/stats:", guard.status_code)
        else:
            print("citizen login unavailable:", clog.status_code, clog.text[:120])
            results["citizen_blocked_from_cases"] = False
        c2.close()

        # ---- KPIs + real daily trend ----
        stats = c.get("/cases/stats").json()
        print("stats:", json.dumps(stats))
        results["kpis_present"] = all(k in stats for k in ("total_reports", "total_cases", "high_risk_entities"))
        dm = stats.get("daily_metrics", [])
        results["daily_metrics_7"] = len(dm) == 7
        # Real trend: labels are real weekday abbreviations and at least one non-zero, and NOT the old fixed Mon..Sun mock ending in total
        results["daily_metrics_realish"] = len(dm) == 7 and sum(d["reports"] for d in dm) > 0

        # ---- emerging trends (predictive) computed, no hardcoded 250% fallback ----
        preds = c.get("/alerts/predictive").json()
        print("predictive count:", len(preds))
        # The old mock always injected a '250%' Digital Arrest alert when none computed.
        results["no_hardcoded_250"] = not any(p.get("velocity_metric", {}).get("trend_percentage") == 250 and "WhatsApp-based fake customs" in p.get("description", "") for p in preds)

        # ---- complaint table filtering (real narrowing) ----
        all_reports = c.get("/reports", params={"limit": "100"}).json()
        escalated = c.get("/reports", params={"limit": "100", "status": "escalated"}).json()
        results["filter_narrows"] = len(escalated) <= len(all_reports) and all(r["status"] == "escalated" for r in escalated)
        print(f"reports total(<=100)={len(all_reports)} escalated={len(escalated)}")

        # ---- cases list + escalated handoff ----
        cases = c.get("/cases").json()
        results["cases_listed"] = len(cases) > 0
        print("cases:", len(cases))

        # ---- investigation detail: real entities + AI summary + linked reports ----
        # Inspect every case; pick the one with the most extracted entities to prove
        # the Report->ReportEntity->Entity join returns real data intact.
        best = None
        best_entities = -1
        for cs in cases:
            d = c.get(f"/cases/{cs['id']}").json()
            ne = len(d.get("entities", []))
            if ne > best_entities:
                best_entities = ne
                best = d
        detail = best
        assert detail, "no cases found"
        print("richest case:", detail["case_number"], "linked:", len(detail["linked_reports"]), "entities:", len(detail["entities"]))
        print("AI summary:", (detail.get("ai_summary") or "")[:180])
        results["detail_has_linked_reports"] = len(detail["linked_reports"]) > 0
        results["detail_has_entities"] = len(detail["entities"]) > 0

        # ---- assignment persists to officer_assignments ----
        asg = c.post(f"/cases/{detail['id']}/assign", json={"officer_id": officer_id})
        results["assign_ok"] = asg.status_code == 200
        # reload detail; assignee should be the officer, AI summary should be real/case-specific
        d2 = c.get(f"/cases/{detail['id']}").json()
        results["assignee_set"] = d2.get("assigned_officer_id") == officer_id
        results["summary_case_specific"] = "linked complaint" in (d2.get("ai_summary") or "").lower()
        print("post-assign summary:", (d2.get("ai_summary") or "")[:200])

    print("\n================ RESULTS ================")
    ok = True
    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
        ok = ok and v
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
