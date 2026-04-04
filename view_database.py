from db_config import get_connection
import oracledb

def view_database():
    tables_to_query = [
        'USERS', 'SUBJECTS', 'AUDIT_LOGS', 'QUESTIONS',
        'TESTS', 'TEST_QUESTIONS', 'TEST_ATTEMPTS', 'STUDENT_ANSWERS'
    ]
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Verify which tables actually exist by checking user_tables
        cursor.execute("SELECT table_name FROM user_tables")
        existing_tables = [row[0].upper() for row in cursor.fetchall()]

        for table in tables_to_query:
            if table not in existing_tables:
                print(f"Table {table} does not exist in the database.")
                continue
                
            print("\n" + "=" * 80)
            print(f"TABLE: {table}")
            print("=" * 80)
            
            # Get columns
            cursor.execute(f"SELECT column_name FROM user_tab_columns WHERE table_name = '{table}' ORDER BY column_id")
            columns = [row[0] for row in cursor.fetchall()]
            
            if not columns:
                continue
                
            # Print Header
            header = " | ".join([f"{col[:15]:<15}" for col in columns])
            print(header)
            print("-" * len(header))
            
            # Get Rows
            cursor.execute(f"SELECT * FROM {table}")
            rows = cursor.fetchall()
            
            if not rows:
                print("No records found.")
            else:
                for row in rows:
                    # Format each column to truncate at 15 chars for display purposes
                    formatted_row = " | ".join([f"{str(val)[:15]:<15}" if val is not None else f"{'NULL':<15}" for val in row])
                    print(formatted_row)
                    
        print("\n" + "=" * 80)
        conn.close()
        
    except oracledb.Error as e:
        print(f"Database Error: {e}")

if __name__ == '__main__':
    print("Fetching active tables from Oracle Database...\n")
    view_database()
