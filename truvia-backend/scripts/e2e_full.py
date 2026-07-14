"""Full end-to-end verification: text + image + audio uploads produce real,
content-tied verdicts. Run against a live backend on 127.0.0.1:8000."""
import io
import sys
import time
import uuid
import httpx
from PIL import Image, ImageDraw, ImageFont

BASE = "http://127.0.0.1:8000/api/v1"

TEXT_SCAM = (
    "Congratulations! You have won Rs 25,00,000 in the KBC lucky draw. "
    "To claim, pay a refundable processing fee of Rs 4999 to UPI kbc.claim@okicici "
    "and share the OTP sent to your phone."
)
BENIGN = "Hey, are we still meeting for lunch tomorrow at 1pm? Let me know."

IMAGE_LINES = [
    "URGENT: This is CBI Officer Sharma.",
    "A parcel in your name has illegal drugs.",
    "You are under DIGITAL ARREST.",
    "Transfer Rs 250000 to UPI cbi.verify@okhdfc",
    "or share the OTP now to avoid arrest.",
]


def make_scam_png() -> bytes:
    img = Image.new("RGB", (920, 360), "white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)
    except Exception:
        font = ImageFont.load_default()
    y = 28
    for line in IMAGE_LINES:
        d.text((28, y), line, fill="black", font=font)
        y += 60
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main():
    results = {}
    email = f"citizen_{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=BASE, timeout=120.0) as c:
        c.post("/auth/register", json={"email": email, "password": "Password123!", "name": "E2E Citizen", "phone": "9000000009"})
        r = c.post("/auth/login", json={"email": email, "password": "Password123!"})
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

        def poll(rid, tries=60):
            for _ in range(tries):
                d = c.get(f"/reports/{rid}").json()
                if d["status"] in ("scored", "escalated", "failed") or d["threat_scores"]:
                    return d
                time.sleep(1)
            return c.get(f"/reports/{rid}").json()

        def submit_text(text):
            resp = c.post("/reports/submit", data={"source_type": "text", "text_content": text})
            assert resp.status_code == 201, resp.text
            return poll(resp.json()["id"])

        def submit_file(source_type, filename, content, mime):
            resp = c.post(
                "/reports/submit",
                data={"source_type": source_type},
                files={"files": (filename, content, mime)},
            )
            assert resp.status_code == 201, resp.text
            return poll(resp.json()["id"])

        # --- TEXT ---
        rep_text = submit_text(TEXT_SCAM)
        rep_benign = submit_text(BENIGN)
        # --- IMAGE ---
        rep_img = submit_file("screenshot", "scam.png", make_scam_png(), "image/png")
        # --- AUDIO ---
        with open("storage/test_scam_call.wav", "rb") as f:
            wav = f.read()
        rep_aud = submit_file("audio", "scam_call.wav", wav, "audio/wav")

        def score(rep):
            return rep["threat_scores"][0] if rep.get("threat_scores") else None

        for label, rep in [("TEXT", rep_text), ("BENIGN", rep_benign), ("IMAGE", rep_img), ("AUDIO", rep_aud)]:
            s = score(rep)
            print(f"\n===== {label} =====")
            print("status:", rep["status"], "| low_conf:", rep["low_confidence_flag"], "| input_conf:", rep.get("input_confidence"))
            print("cleaned_text:", (rep.get("cleaned_text") or "")[:200])
            if s:
                print(f"score={s['threat_score']} band={s['severity_band']} cat={s['scam_category']} conf={s['confidence_score']} degraded={s['degraded_mode']}")
                print("indicators:", s["reasoning_json"].get("key_indicators"))
            else:
                print("NO THREAT SCORE")

        st, sb, si, sa = score(rep_text), score(rep_benign), score(rep_img), score(rep_aud)

        # --- Acceptance assertions ---
        results["text_scored"] = bool(st and st["threat_score"] is not None)
        results["image_scored_real"] = bool(si and si["scam_category"] != "Insufficient Content" and si["threat_score"] > 0)
        results["audio_scored_real"] = bool(sa and sa["scam_category"] != "Insufficient Content" and sa["threat_score"] > 0)
        # content-tied: extracted text must contain real signals from that specific input
        img_text = (rep_img.get("cleaned_text") or "").lower()
        aud_text = (rep_aud.get("cleaned_text") or "").lower()
        results["image_content_tied"] = any(w in img_text for w in ("arrest", "cbi", "otp", "digital"))
        results["audio_content_tied"] = any(w in aud_text for w in ("arrest", "investigation", "officer", "otp", "digital"))
        results["no_verdict_absent"] = all(score(r) is not None for r in [rep_text, rep_img, rep_aud])
        results["scores_vary"] = len({st["threat_score"], sb["threat_score"], si["threat_score"]}) >= 2
        results["benign_lower_than_scam"] = sb["threat_score"] < si["threat_score"]

        # Chat / PDF / escalate / history
        chat = c.post("/chat", json={"query": "Is it safe to scan a QR code to receive a refund?"})
        results["chat_cited"] = chat.status_code == 200 and bool(chat.json().get("citations"))
        pdf = c.get(f"/reports/{rep_img['id']}/pdf")
        results["pdf_real"] = pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
        esc = c.post(f"/reports/{rep_aud['id']}/escalate")
        results["escalate_persisted"] = esc.status_code == 200 and bool(esc.json().get("case_id"))
        hist = c.get("/reports", params={"limit": "20"}).json()
        ids = {h["id"] for h in hist}
        results["history_real"] = {rep_text["id"], rep_img["id"], rep_aud["id"]}.issubset(ids)

    print("\n================ RESULTS ================")
    ok = True
    for k, v in results.items():
        print(f"{'PASS' if v else 'FAIL'}  {k}")
        ok = ok and v
    print("OVERALL:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
