import oracledb
def get_connection():
    return oracledb.connect(user="system", password="password", dsn="localhost:1521/xe")