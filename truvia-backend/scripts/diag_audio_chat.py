"""Diagnostic for audio latency + chat behaviour against the live backend."""
import time, uuid, httpx

BASE = "http://127.0.0.1:8000/api/v1"

def main():
    email = f"diag_{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=BASE, timeout=180.0) as c:
        c.post("/auth/register", json={"email": email, "password": "Password123!", "name": "Diag", "phone": "9000000001"})
        c.headers["Authorization"] = f"Bearer {c.post('/auth/login', json={'email': email, 'password': 'Password123!'}).json()['access_token']}"

        # ---- AUDIO latency ----
        with open("storage/test_scam_call.wav", "rb") as f:
            wav = f.read()
        t0 = time.time()
        r = c.post("/reports/submit", data={"source_type": "audio"}, files={"files": ("scam.wav", wav, "audio/wav")})
        rid = r.json()["id"]
        print(f"[audio] submitted id={rid[:8]} in {time.time()-t0:.1f}s")
        last = None
        scored_at = None
        while time.time() - t0 < 150:
            d = c.get(f"/reports/{rid}").json()
            st = d["status"]
            has = len(d["threat_scores"]) > 0
            if st != last:
                print(f"[audio] t={time.time()-t0:5.1f}s status={st} has_score={has}")
                last = st
            if st in ("scored", "escalated", "failed") or has:
                scored_at = time.time() - t0
                sc = d["threat_scores"][0] if has else None
                print(f"[audio] SCORED at t={scored_at:.1f}s  transcript={ (d.get('cleaned_text') or '')[:80]!r}")
                if sc:
                    print(f"[audio] score={sc['threat_score']} band={sc['severity_band']} cat={sc['scam_category']}")
                break
            time.sleep(1)
        else:
            print("[audio] NEVER SCORED within 150s")
        print(f"[audio] >>> frontend polls ~30s; scored_at={scored_at}")

        # ---- CHAT ----
        for q in ["Is it safe to scan a QR code to receive a refund?",
                  "What should I do if I get a digital arrest call?"]:
            cr = c.post("/chat", json={"query": q})
            print(f"\n[chat] Q={q!r} -> HTTP {cr.status_code}")
            if cr.status_code == 200:
                j = cr.json()
                print("[chat] answer:", (j.get("answer") or "")[:200])
                print("[chat] citations:", [(ci.get("source"), ci.get("title")) for ci in j.get("citations", [])])
            else:
                print("[chat] body:", cr.text[:300])

if __name__ == "__main__":
    main()
