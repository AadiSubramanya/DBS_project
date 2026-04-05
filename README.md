# Online MCQ Test Management System

A high-performance, secure, and modern web application for managing multiple-choice assessments. Built with **Flask** and backed by **Oracle Database**, this system features a stunning "Negated Newsprint" design and robust role-based access control (RBAC).

---

## 🚀 Key Features

- **Dual-Role Dashboards**: Tailored experiences for Students, Instructors, and Admins.
- **Advanced Result Analytics**: In-depth performance metrics for instructors, including per-question accuracy and score distributions.
- **Smart Test Timers**: Server-synchronized countdowns with automated submission and low-time warnings.
- **Modern UI/UX**: High-contrast, sharp-edged aesthetic with support for both Dark and Light modes.
- **Secure Persistence**: Full Oracle SQL integration with audit logging and cascading data integrity.
- **Dynamic Question Banking**: Reusable questions across multiple tests for efficient exam management.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.x, Flask
- **Database**: Oracle Database (XE/Standard/Enterprise)
- **Database Driver**: `oracledb` (Thin Mode)
- **Frontend**: HTML5, CSS3 (Vanilla), Jinja2 Templates
- **Typography**: Playfair Display, Inter, Lora, JetBrains Mono

---

## 📦 Prerequisites

1. **Python 3.8+** installed (Anaconda recommended).
2. **Oracle Database Express Edition (XE)** or higher.
3. **requirements.txt** dependencies installed.

---

## ⚙️ Local Setup Guide

### 1. Install Dependencies
Open your terminal (e.g., Anaconda Prompt) and run:
```bash
pip install -r requirements.txt
```

### 2. Database Initialization
1. Log into your Oracle instance via **SQL*Plus** or SQL Developer as `SYSTEM`.
2. Execute the consolidated schema script:
```sql
@database/schema.sql
```
*Note: This script creates all tables, sequences, and initial seed data (Admin: admin/123, Teacher: teacher/123, Student: student/123).*

### 3. Connection Configuration
Open `db_config.py` and update your Oracle credentials:
```python
DB_USER = "system"
DB_PASSWORD = "your_oracle_password"
DB_DSN = "localhost:1521/xe"
```

### 4. Run the Application
Start the Flask development server:
```bash
python app.py
```
Visit `http://localhost:5000` in your browser.

---

## 📂 Project Structure

- `app.py`: Main application logic and routing.
- `db_config.py`: Database connection factory and credentials.
- `database/`: SQL scripts for schema definition and initial data.
- `static/css/style.css`: Centralized design system and theme variables.
- `templates/`: Dynamic Jinja2 HTML templates for all views.
- `PROJECT_STRUCTURE.md`: Detailed file-by-file explorer guide.

---

## 📜 License
This project is developed for educational purposes as part of a Database Management Systems (DBMS) coursework.
