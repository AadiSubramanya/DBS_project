from db_config import get_connection
import oracledb

def view_all_users():
    try:
        # Establish connection using your config
        conn = get_connection()
        cursor = conn.cursor()
        
        # Execute the SQL Query to fetch all users
        cursor.execute("SELECT user_id, username, password_hash, full_name, role FROM USERS")
        
        # Fetch all rows returned by the query
        users = cursor.fetchall()
        
        if not users:
            print("No users found in the database.")
            return

        print("-" * 80)
        print(f"{'ID':<5} | {'USERNAME':<15} | {'PASSWORD':<15} | {'ROLE':<15} | {'FULL NAME'}")
        print("-" * 80)
        
        for user in users:
            print(f"{user[0]:<5} | {user[1]:<15} | {user[2]:<15} | {user[4]:<15} | {user[3]}")
            
        print("-" * 80)
        
        # Close connection
        conn.close()
        
    except oracledb.Error as e:
        print(f"Failed to connect or query database. Error: {e}")

if __name__ == '__main__':
    print("Fetching users from Oracle Database...\n")
    view_all_users()
