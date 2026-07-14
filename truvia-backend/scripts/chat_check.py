"""Verify chat answers are grounded, per-query, and non-canned. Writes to chat_out.txt."""
import uuid, httpx, json

BASE = "http://127.0.0.1:8000/api/v1"
QUESTIONS = [
    "Is it safe to scan a QR code to receive a refund?",
    "What should I do if I get a digital arrest call from CBI?",
    "What is my liability if there is an unauthorized transaction on my bank account?",
]

def main():
    out = []
    email = f"chat_{uuid.uuid4().hex[:8]}@example.com"
    with httpx.Client(base_url=BASE, timeout=60.0) as c:
        c.post("/auth/register", json={"email": email, "password": "Password123!", "name": "Chat", "phone": "9000000002"})
        c.headers["Authorization"] = f"Bearer {c.post('/auth/login', json={'email': email, 'password': 'Password123!'}).json()['access_token']}"
        answers = []
        for q in QUESTIONS:
            r = c.post("/chat", json={"query": q})
            j = r.json()
            answers.append(j.get("answer", ""))
            out.append(f"Q: {q}\nHTTP: {r.status_code}\nANSWER:\n{j.get('answer')}\nCITATIONS: {json.dumps([(ci.get('source'), ci.get('title')) for ci in j.get('citations', [])])}\n{'-'*70}")
        # Canned-answer check: the old bug appended an identical 'Safety Action Plan' to every answer.
        out.append("CANNED_PLAN_PRESENT: " + str(any("Safety Action Plan" in a for a in answers)))
        out.append("ANSWERS_ALL_DISTINCT: " + str(len(set(answers)) == len(answers)))
    with open("chat_out.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("done")

if __name__ == "__main__":
    main()
