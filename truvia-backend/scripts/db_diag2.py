import sqlite3
c = sqlite3.connect("truvia.db")
def q(sql):
    try:
        return c.execute(sql).fetchall()
    except Exception as e:
        return [("ERR", str(e))]
print("officers:", q("select email, role, name from users where role in ('officer','admin')"))
print("total reports:", q("select count(*) from reports")[0][0])
print("total cases:", q("select count(*) from cases")[0][0])
print("case_reports links:", q("select count(*) from case_reports")[0][0])
print("escalated reports:", q("select count(*) from reports where status='escalated'")[0][0])
print("officer_assignments:", q("select count(*) from officer_assignments")[0][0])
print("reports by day (last):", q("select date(created_at) d, count(*) from reports group by d order by d desc limit 8"))
c.close()
