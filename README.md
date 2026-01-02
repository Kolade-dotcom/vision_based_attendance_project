# 🎯 Smart Vision-Based Attendance System

A Flask-based attendance system using **computer vision** and **face recognition** for automated student attendance tracking.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [Project Structure](#-project-structure)
- [API Endpoints](#-api-endpoints)
- [Testing](#-testing)

---

## ✨ Features

- � **Secure Authentication**:
  - Admin Login & Signup system.
  - Protected Dashboard and Enrollment routes.
  - Session-based access control.
- �📸 **Real-time Face Detection**: Automated attendance marking via webcam.
- 👤 **Student Management**:
  - **Enrollment**: Capture face data and details.
  - **Edit Profiles**: Update Name, Level, and **Matric Number** (with cascade updates).
  - **Delete**: Remove students and their history.
- 📊 **Dashboard & Analytics**:
  - Real-time attendance table.
  - Filter statistics by **Level** and **Course**.
- 🔌 **Hardware Integration**: Arduino bridge for LEDs, buzzers, and door control.
- 💾 **SQLite Database**: Persistent storage for students (`students` table), attendance logs (`attendance` table), and admin accounts (`users` table).

---

## 📦 Prerequisites

- **Python 3.13+**
- **Git**
- Windows 10/11

---

## 🔧 Installation

### Step 1: Clone the Repository

```powershell
git clone <repository-url>
cd vision_attendance_project
```

### Step 2: Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 3: Install dlib (CRITICAL for Windows)

> ⚠️ **IMPORTANT**: The `face_recognition` library depends on `dlib`. Since compiling `dlib` on Windows requires heavy build tools, we use a pre-compiled wheel for Python 3.13.

1. **Install the pre-compiled dlib wheel**:

   ```powershell
   pip install https://github.com/omwaman1/dlib/releases/download/dlib/dlib-19.24.99-cp313-cp313-win_amd64.whl
   ```

2. **Install remaining dependencies**:

```powershell
pip install -r requirements.txt
```

### Step 4: Initialize the Database

The application auto-initializes the database on first run. To force initialization (or reset):

```powershell
python -c "from db_helper import init_database; init_database()"
```

---

## 🚀 Running the Application

```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run the Flask server
python app.py
```

Open your browser and navigate to: **http://localhost:5000**

---

## 📁 Project Structure

```
/vision_attendance_project
├── /api
│   ├── /controllers     # Business logic (Auth, Student, Attendance)
│   └── /routes          # API endpoints (Blueprints)
├── /static
│   ├── /css             # StylesheetsAPI
│   └── /js
│       ├── /api         # API Client
│       ├── /modules     # Reusable UI modules
│       ├── /pages       # Page-specific logic
│       └── main.js      # Entry point
├── /templates           # HTML Templates (Base, Index, Enroll, Login)
├── /database            # Schema and SQLite DB
├── /tests               # Pytest suite
├── app.py               # Application entry point
├── camera.py            # Vision processing
├── db_helper.py         # Database utilities
└── requirements.txt     # Dependencies
```

---

## 🔌 API Endpoints

### Authentication

| Endpoint           | Method | Description                       |
| :----------------- | :----- | :-------------------------------- |
| `/api/auth/login`  | POST   | Authenticate user & start session |
| `/api/auth/signup` | POST   | Create new Admin account          |
| `/api/auth/logout` | GET    | End session                       |

### Students

| Endpoint             | Method | Description                      |
| :------------------- | :----- | :------------------------------- |
| `/api/students`      | GET    | List all students                |
| `/api/enroll`        | POST   | Enroll a new student             |
| `/api/students/<id>` | PUT    | Update student (Name, Level, ID) |
| `/api/students/<id>` | DELETE | Delete student                   |

### Attendance

| Endpoint                | Method | Description                               |
| :---------------------- | :----- | :---------------------------------------- |
| `/api/attendance/today` | GET    | Get today's attendance (supports filters) |
| `/api/statistics`       | GET    | Get system stats (supports filters)       |

---

## 🧪 Testing

This project uses **pytest** for Test-Driven Development (TDD).

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_db.py
pytest tests/test_api.py
```

---

## 👥 Team

- Mechatronics Project Team

## 📄 License

This project is for educational purposes.
