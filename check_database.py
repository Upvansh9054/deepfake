"""
Interactive SQLite Database Explorer for Deepfake Shield.
"""
import sys
import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "deepfake_shield.db"

def inspect_summary():
    if not DB_FILE.exists():
        print(f"\n❌ Database file not found: {DB_FILE}\n")
        return

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    print("\n" + "=" * 70)
    print(" 🛡️  DEEPFAKE SHIELD - DATABASE OVERVIEW")
    print("=" * 70)
    print(f" Database Path: {DB_FILE.resolve()}")
    print("-" * 70)

    tables = ["users", "scans", "scan_results", "risk_reports", "alerts", "audit_logs"]
    print(" TABLE RECORD COUNTS:")
    for t in tables:
        try:
            count = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"   • {t:<15}: {count} records stored")
        except Exception:
            pass

    print("\n LATEST 5 SCANS:")
    query = """
        SELECT s.id, s.title, s.media_type, s.status, r.composite_risk_score, r.risk_level, s.created_at
        FROM scans s
        LEFT JOIN risk_reports r ON s.id = r.scan_id
        ORDER BY s.created_at DESC LIMIT 5
    """
    for row in c.execute(query).fetchall():
        risk = f"{row[4]}% ({row[5]})" if row[4] is not None else "N/A"
        print(f"   • [{row[6]}] ID: {row[0][:8]}... | Type: {row[2]:<10} | Risk: {risk:<18} | {row[1]}")

    print("=" * 70 + "\n")
    conn.close()

def list_scans():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = """
        SELECT s.id, s.title, s.media_type, s.status, r.composite_risk_score, r.risk_level, res.verdict, s.created_at
        FROM scans s
        LEFT JOIN risk_reports r ON s.id = r.scan_id
        LEFT JOIN scan_results res ON s.id = res.scan_id
        ORDER BY s.created_at DESC
    """
    rows = c.execute(query).fetchall()
    print("\n" + "=" * 105)
    print(f" {'ID':<10} | {'TYPE':<10} | {'VERDICT':<22} | {'RISK':<8} | {'CREATED AT':<20} | {'TITLE'}")
    print("-" * 105)
    for r in rows:
        verdict = r[6] or "N/A"
        risk = f"{r[4]}%" if r[4] is not None else "N/A"
        created = str(r[7])[:19] if r[7] else "N/A"
        print(f" {r[0][:8]:<10} | {r[2]:<10} | {verdict:<22} | {risk:<8} | {created:<20} | {r[1]}")
    print("=" * 105)
    print(f" Total Scans: {len(rows)}\n")
    conn.close()

def list_users():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    rows = c.execute("SELECT id, full_name, email, role, is_active, created_at FROM users").fetchall()
    print("\n" + "=" * 90)
    print(f" {'ID':<10} | {'ROLE':<10} | {'EMAIL':<30} | {'NAME':<20} | {'ACTIVE'}")
    print("-" * 90)
    for r in rows:
        print(f" {r[0][:8]:<10} | {r[3]:<10} | {r[2]:<30} | {r[1]:<20} | {bool(r[4])}")
    print("=" * 90)
    print(f" Total Users: {len(rows)}\n")
    conn.close()

def custom_query(sql: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        rows = c.execute(sql).fetchall()
        cols = [desc[0] for desc in c.description] if c.description else []
        print("\n" + " | ".join(cols))
        print("-" * 80)
        for r in rows:
            print(" | ".join(str(val) for val in r))
        print(f"\n({len(rows)} rows returned)\n")
    except Exception as e:
        print(f"\n❌ Query error: {e}\n")
    finally:
        conn.close()

def interactive_menu():
    while True:
        print("=" * 55)
        print("  🛡️  DEEPFAKE SHIELD - SQLITE DATABASE VIEWER")
        print("=" * 55)
        print("  [1] View All Forensic Scans (Verdicts & Risk Scores)")
        print("  [2] View All Registered Users")
        print("  [3] View Database Overview & Row Counts")
        print("  [4] Run a Custom SQL Query")
        print("  [5] Exit")
        print("=" * 55)
        choice = input("Select an option (1-5): ").strip()

        if choice == "1":
            list_scans()
        elif choice == "2":
            list_users()
        elif choice == "3":
            inspect_summary()
        elif choice == "4":
            sql = input("\nEnter SQL Query (e.g. SELECT * FROM users): ").strip()
            if sql:
                custom_query(sql)
        elif choice in ["5", "q", "exit"]:
            print("\nExiting database viewer. Goodbye!\n")
            break
        else:
            print("\n⚠️ Invalid selection, please enter 1, 2, 3, 4, or 5.\n")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "scans":
            list_scans()
        elif arg == "users":
            list_users()
        elif arg.startswith("select"):
            custom_query(sys.argv[1])
        else:
            inspect_summary()
    else:
        # If run directly with no args in terminal or double-clicked
        interactive_menu()
