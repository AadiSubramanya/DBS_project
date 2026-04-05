import oracledb
try:
    conn = oracledb.connect(user='admin', password='123', dsn='localhost:1521/XE')
except Exception as e:
    try:
        conn = oracledb.connect(user='system', password='123', dsn='localhost:1521/XE')
    except Exception as e:
        print(f"Error connecting: {e}")
        exit(1)

c = conn.cursor()
c.execute("SELECT table_name FROM user_tables")
tables = c.fetchall()
print("Tables in DB:", [t[0] for t in tables])
conn.close()
