# Project Workflow & Architecture

This document briefly describes the architecture of the Online MCQ Test Management System and explains the role of every file in the consolidated codebase.

---

## 🏗️ Architecture Overview

The system follows a standard **Model-View-Controller (MVC)** pattern:
1. **Model (Database Layer)**: Handled by Oracle Database to store Users, Subjects, Questions, Tests, and Attempts securely. The connection logic is bridged by `db_config.py`.
2. **Controller (Backend Logic)**: Handled by `app.py`. This is where Flask defines routing, permissions, authentication, and execution of SQL queries against the database models.
3. **View (Frontend Layer)**: Rendered dynamically via HTML templates infused with Jinja logic and styled beautifully by a centralized CSS system (`style.css`).

---

## 📁 File Structure & Responsibilities

### ⚙️ Core Application

- **`app.py`**
  The brain of the application. It hosts the Flask web server, manages all the URL routes (like `/login`, `/dashboard`, `/test`), handles `session` tracking for User Authorization, and directly executes Python-to-Oracle SQL queries utilizing `oracledb`. 

- **`db_config.py`**
  A lightweight helper module containing the `get_connection()` function. It isolates your database credentials (username and password) and connection string to keep the main application clean.

- **`requirements.txt`**
  A simple text file listing the Python package dependencies (`Flask` and `oracledb`). Running `pip install -r requirements.txt` uses this file to configure the backend environment.

### 🎨 Frontend Templates (`/templates`)

We use **Jinja2** to dynamically render data passed from `app.py` into our HTML pages.

- **`base.html`**
  The "skeleton" of our application frontend. It acts as the master template containing the layout, CSS links, and the top navigation bar. Every other template "extends" this file to inherit the style and navigation.

- **`auth.html`**
  A consolidated, dynamic authentication template. It serves as both the **Login** page and the **Registration** page depending on the arguments specified in `app.py`. It adjusts input fields logically based on context.

- **`dashboard.html`**
  The central hub of operations. It renders dynamically based on the active user’s Role (`Admin`, `Instructor`, or `Student`). It is responsible for routing Admins to data grids/audit logs, Instructors to test-creation tools, and Students to their available active tests.

- **`manage.html`**
  The private instructor interface for a specific test. Instructors arrive here to curate questions belonging to an active test from the Question Bank and to view the scoring results of the students who took it.

- **`test.html`**
  The live examination interface for Students. It receives the chosen Test ID via URL, requests the corresponding Test details/Questions from Oracle, and presents the user with a multiple-choice submittable form.

### 💎 Styling (`/static/css`)

- **`style.css`**
  The single source of truth for design aesthetics. It contains the application's unique variables (like base colors), gradient logic, and modern UX classes like `.glass-panel` and `.btn`. Ensuring consistent visual branding across all views without inline styling.

### 🗄️ Database Definitions (`/database`)

- **`schema.sql`**
  The initial DDL (Data Definition Language) script intended to set up the Oracle schema structure. It creates Tables ranging from Users, Subjects, Questions to Tests, alongside automated sequences for unique ID generation.
  
- **`mock_data.sql`**
  An initial injection DML script to populate your tables with example generic data, granting you immediate capabilities to test interactions without having to bootstrap everything yourself.

### 🛠️ Developer Scripts

- **`view_database.py`**
  A secondary CLI tool designed separately from the web application. It securely connects to the data store to print out raw console-ready snapshots of the DB table rows for immediate debugging checks.

- **`README.md`**
  The startup tutorial designed for any incoming developer detailing specifically how to set up their Windows terminal, pip installations, and SQL*Plus sequences.
