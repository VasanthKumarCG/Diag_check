from src.db.migrate import kw
import psycopg,json
def main():
 with psycopg.connect(**kw()) as c:
  with c.cursor() as q:
   q.execute("SELECT (SELECT COUNT(*) FROM raw.diagnostic_report),(SELECT COUNT(*) FROM raw.ecu_version),(SELECT COUNT(*) FROM raw.dtc_event),(SELECT COUNT(*) FROM raw.environment_signal),(SELECT COUNT(*) FROM raw.vehicle_test_summary)")
   print(json.dumps(dict(zip(['reports','ecus','dtcs','signals','test_summaries'],q.fetchone())),indent=2))
if __name__=='__main__':main()
