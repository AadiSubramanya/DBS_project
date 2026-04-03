# Setup Guide: Online MCQ Test Management System

This document provides a detailed, beginner-friendly walkthrough on how to set up the Python Flask frontend and Oracle Database backend locally on your Windows machine.

---

## Part 1: Install Python Requirements

Since we are not using a Virtual Environment (`venv`), we will install the required Python packages globally.

1. **Open Anaconda Prompt** from your Windows Start Menu.
2. Use the `cd` command to navigate to this project folder, for example:
   ```bash
   cd c:\Users\aadis\OneDrive\Desktop\dbs_project
   ```
3. Run the following command to install the required web framework bindings:
   ```bash
   pip install -r requirements.txt
   ```
   *(This will automatically install `Flask` for the web server and `oracledb` for the database connection).*

---

## Part 2: Oracle Database Installation

If you do not have Oracle Database installed yet, you will need **Oracle Database Express Edition (XE)**.

1. **Download Oracle XE**: Search Google for "Oracle Database 21c Express Edition for Windows x64" and download the zip file.
2. **Install**: Extract the folder and run `setup.exe`. 
   > [!IMPORTANT] 
   > During setup, you will be prompted to create a password for the administrative user accounts (`SYS`, `SYSTEM`, etc.). **Write this password down** because you will need it to connect the application!
3. **Finish Setup**: Allow the installer to finish. It automatically creates the background Oracle services.

---

## Part 3: Running the Schema Script

Now we need to create the Tables inside the Oracle database.

1. Open your Windows Start Menu and search for **SQL\*Plus**. Run it.
2. It will ask for your Username and Password:
   - **Enter user-name**: `system`
   - **Enter password**: *(Type the password you created in Part 2. Note: The cursor will not move while typing, this is normal).*
3. Now that you are logged into the database, tell SQL\*Plus to execute our SQL files. Type the following and press Enter:
   ```sql
   @c:\Users\aadis\OneDrive\Desktop\dbs_project\database\schema.sql
   ```
   *This command will create the `USERS`, `QUESTIONS`, and all corresponding tables.*
4. Add the initial mock data (so you can log into the website as an admin):
   ```sql
   @c:\Users\aadis\OneDrive\Desktop\dbs_project\database\mock_data.sql
   ```

---

## Part 4: Connect the Python App to Oracle

1. In VS Code, open the file named **`db_config.py`**.
2. Locate the line that says:
   ```python
   DB_PASSWORD = "your_password"
   ```
3. Change `"your_password"` to the actual password you created during the Oracle XE installation. Save the file.

---

## Part 5: Start the Server

1. **Open Anaconda Prompt**.
2. Make sure you are inside the project directory:
   ```bash
   cd c:\Users\aadis\OneDrive\Desktop\dbs_project
   ```
3. Run the Python application:
   ```bash
   python app.py
   ```
3. You should see a message stating that the development server is running.
4. Open your Web Browser (Edge, Chrome) and go to:
   ```
   http://localhost:5000
   ```

**You're done!** You can click "Login" and test it out. If everything was entered correctly, the Python script will securely route your HTML forms through the `db_config.py` straight into the Oracle Database.
