import sqlite3
c = sqlite3.connect("truvia.db")
print("knowledge_base:", c.execute("select count(*) from knowledge_base").fetchone()[0])
print("kb_chunks:", c.execute("select count(*) from knowledge_base_chunks").fetchone()[0])
print("--- recent audio reports ---")
for r in c.execute("select substr(id,1,8), status, input_confidence, low_confidence_flag, substr(cleaned_text,1,50) from reports where source_type='audio' order by created_at desc limit 6").fetchall():
    print(r)
print("--- threat_scores for audio reports ---")
for r in c.execute("select substr(ts.report_id,1,8), ts.threat_score, ts.severity_band, ts.scam_category from threat_scores ts join reports r on r.id=ts.report_id where r.source_type='audio' order by ts.created_at desc limit 6").fetchall():
    print(r)
c.close()
