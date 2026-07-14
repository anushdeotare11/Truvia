"""Phase 2 verification: complaint filters + CSV, my-cases, correlated complaints, intelligence package persistence."""
import sys, sqlite3, httpx

BASE = "http://127.0.0.1:8000/api/v1"

def main():
    res = {}
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        c.headers["Authorization"] = f"Bearer {c.post('/auth/login', json={'email':'officer@truvia.org','password':'password'}).json()['access_token']}"
        me = c.get("/auth/me").json(); officer_id = me["id"]

        # --- complaint filters (real narrowing) ---
        base = c.get("/reports", params={"limit": "200"}).json()
        # score filter
        hi = c.get("/reports", params={"limit": "200", "score_min": "80"}).json()
        res["score_filter"] = all((r["threat_scores"][0]["threat_score"] >= 80) for r in hi if r["threat_scores"])
        # category filter
        cat = None
        for r in base:
            if r["threat_scores"]:
                cat = r["threat_scores"][0]["scam_category"]; break
        if cat:
            catres = c.get("/reports", params={"limit":"200","category": cat}).json()
            res["category_filter"] = all(r["threat_scores"] and r["threat_scores"][0]["scam_category"] == cat for r in catres) and len(catres) <= len(base)
        else:
            res["category_filter"] = True
        print(f"base={len(base)} score>=80={len(hi)} category('{cat}')")

        # --- CSV export ---
        csv_resp = c.get("/reports/export", params={"score_min": "80"})
        ct = csv_resp.headers.get("content-type", "")
        body = csv_resp.text
        res["csv_export"] = csv_resp.status_code == 200 and "text/csv" in ct and body.splitlines()[0].startswith("Report ID")
        print("csv header:", body.splitlines()[0][:60], "| rows:", len(body.splitlines()) - 1)

        # --- my cases (scoped) ---
        mine = c.get("/cases", params={"mine": "true"}).json()
        # verify each returned case is actually assigned to this officer
        ok_scope = True
        for cs in mine:
            d = c.get(f"/cases/{cs['id']}").json()
            if d.get("assigned_officer_id") != officer_id:
                ok_scope = False; break
        res["my_cases_scoped"] = ok_scope
        print("my cases:", len(mine))

        # --- correlated complaints + package persistence on richest case ---
        cases = c.get("/cases").json()
        best = None; bestn = -1
        for cs in cases:
            d = c.get(f"/cases/{cs['id']}").json()
            if len(d.get("entities", [])) > bestn:
                bestn = len(d.get("entities", [])); best = d
        res["correlated_present"] = "correlated_reports" in best and isinstance(best["correlated_reports"], list)
        print("richest case:", best["case_number"], "entities:", len(best["entities"]), "correlated:", len(best.get("correlated_reports", [])))

        # package generation + persistence
        before = _pkg_count()
        pkg = c.get(f"/cases/{best['id']}/package")
        res["package_pdf"] = pkg.status_code == 200 and pkg.content[:4] == b"%PDF"
        after = _pkg_count()
        res["package_persisted"] = after == before + 1
        print(f"intelligence_packages: {before} -> {after}")

    print("\n===== PHASE 2 RESULTS =====")
    ok = True
    for k, v in res.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}"); ok = ok and v
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

def _pkg_count():
    c = sqlite3.connect("truvia.db")
    n = c.execute("select count(*) from intelligence_packages").fetchone()[0]
    c.close(); return n

if __name__ == "__main__":
    main()
