# Project Structure & Directory Guide

This document provides a detailed walkthrough of the Online MCQ Test Management System's file hierarchy. Each file's role and its relationship with the rest of the application is explained below.

---

## 📁 Root Directory

### ⚙️ Backend & Configuration
- **`app.py`**
  The core of the application. It contains all Flask routing logic, authentication management, role-based access control (RBAC), and SQL execution logic. It serves as the primary controller in the MVC architecture.
- **`db_config.py`**
  A dedicated module for database connection management. It encapsulates the `oracledb` connection settings and credentials, providing a clean interface for the main app to interact with the Oracle instance.
- **`requirements.txt`**
  Lists all Python dependencies required for the project (`Flask` and `oracledb`). Used for setting up the development environment.

### 📄 Documentation
- **`README.md`**
  The entry-level setup guide containing installation instructions, technology stack details, and a high-level feature overview.
- **`PROJECT_STRUCTURE.md`**
  (This file) A comprehensive guide to the internal file architecture and responsibilities of each component.

---

## 🗄️ Database (`/database`)

- **`schema.sql`**
  The single source of truth for the database structure. It contains both the **DDL** (Data Definition Language) for creating tables/sequences and the **Seed Data** (DML) for initial user accounts and subjects. It includes:
  - `USERS`: RBAC-enabled user accounts.
  - `SUBJECTS`: Academic categories for tests.
  - `QUESTIONS`: Centralized question bank.
  - `TESTS`: Time-bound assessments.
  - `STUDENT_ANSWERS`: Log of all exam attempts and accuracy data.

---

## 🎨 Frontend Static Assets (`/static`)

- **`css/style.css`**
  The centralized stylesheet for the entire application. It implements the **Negated Newsprint** design system, featuring CSS variables for easy theme toggling, sharp-edged UI components, and premium typography. It also houses specialized styles for the student test timer and question cards.

---

## 🎨 Frontend Templates (`/templates`)

The application uses **Jinja2** templating to render dynamic content passed from the backend.

- **`base.html`**
  The master layout file. It contains the HTML boilerplate, navigation bar, and flash message logic that every other page inherits.
- **`auth.html`**
  A dynamic authentication page that serves both Login and Registration views.
- **`dashboard.html`**
  The role-specific landing page for Students, Instructors, and Admins.
- **`manage.html`**
  The instructor's interface for curating test questions and viewing student result summaries.
- **`test.html`**
  The high-stakes examination interface for students, featuring the prominent sticky timer and interactive question cards.
- **`test_analytics.html`**
  A dedicated dashboard for in-depth result reporting, including score distributions and per-question accuracy metrics.

---

## 🏗️ Architecture Summary

The project follows a **Modified MVC (Model-View-Controller)** pattern:
- **Model**: Oracle SQL Tables (`database/schema.sql`).
- **View**: Jinja2 Templates (`/templates`) & Vanilla CSS (`/static/css`).
- **Controller**: Flask Routes and SQL Glue (`app.py`).
- **Config**: Credential isolation (`db_config.py`).
