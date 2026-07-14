"""Phase 1 verification: dismiss persistence + real public alerts."""
import sys, uuid, time, httpx

BASE = "http://127.0.0.1:8000/api/v1"
SCAM = "Congratulations! You won Rs 50000 lottery. Pay Rs 999 fee to UPI win@okicici and share OTP."

def main():
    res = {}
    email = f"p1_{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=BASE, timeout=90.0) as c:
        c.post("/auth/register", json={"email": email, "password": "Password123!", "name": "P1", "phone": "9000000021"})
        c.headers["Authorization"] = f"Bearer {c.post('/auth/login', json={'email': email, 'password': 'Password123!'}).json()['access_token']}"

        # submit + wait scored
        rid = c.post("/reports/submit", data={"source_type": "text", "text_content": SCAM}).json()["id"]
        for _ in range(30):
            d = c.get(f"/reports/{rid}").json()
            if d["status"] == "scored" or d["threat_scores"]:
                break
            time.sleep(1)

        # dismiss
        dm = c.post(f"/reports/{rid}/dismiss")
        res["dismiss_ok"] = dm.status_code == 200 and dm.json().get("status") == "dismissed"
        # persists after "refresh" (re-fetch)
        again = c.get(f"/reports/{rid}").json()
        res["dismiss_persists"] = again["status"] == "dismissed"
        print("after dismiss, status =", again["status"])

        # dismiss should be blocked once escalated: submit another, escalate, then dismiss -> 409
        rid2 = c.post("/reports/submit", data={"source_type": "text", "text_content": SCAM}).json()["id"]
        for _ in range(30):
            if c.get(f"/reports/{rid2}").json()["status"] == "scored":
                break
            time.sleep(1)
        c.post(f"/reports/{rid2}/escalate")
        blocked = c.post(f"/reports/{rid2}/dismiss")
        res["escalated_not_dismissable"] = blocked.status_code == 409
        print("dismiss after escalate ->", blocked.status_code)

        # public alerts: real, data-driven
        pub = c.get("/alerts/public").json()
        print("public alerts count:", len(pub))
        for a in pub[:4]:
            print("  ", a["severity"], "|", a["title"], "|", a["description"][:80])
        # must reflect real categories (title starts with 'Trending:'), not the old hardcoded advisories
        res["public_real_or_empty"] = all(a["title"].startswith("Trending:") for a in pub)
        res["no_hardcoded_public"] = not any("Fake Police Customs Callers" in a.get("title", "") for a in pub)
        # category filter narrows
        if pub:
            some_cat = pub[0]["title"].replace("Trending: ", "")
            filtered = c.get("/alerts/public", params={"category": some_cat}).json()
            res["public_category_filter"] = all(some_cat.lower() in a["title"].lower() for a in filtered)
        else:
            res["public_category_filter"] = True

    print("\n===== PHASE 1 RESULTS =====")
    ok = True
    for k, v in res.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
        ok = ok and v
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
