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

### 🔐 Authentication & Security

- Admin Login & Signup system
- Protected Dashboard and Enrollment routes
- Session-based access control

### 📸 Real-time Face Detection

- Automated attendance marking via **ESP32-CAM wireless streaming**
- **Optimized detection** with frame resizing (0.25x) and frame skipping
- Cached Haar Cascade classifier for better performance
- HOG-based face detector with tracking for stability
- Green bounding boxes around detected faces

### 📅 Session Management

- **Start/End Class Sessions** with course selection and scheduled time
- **Session Timer** displaying elapsed time
- **Session History** with view, export, and delete actions
- **Session-scoped attendance** - records are linked to specific sessions
- **Smart Late Detection** - 15-minute grace period from session start; students arriving after are marked "late"

### 👤 Student Management

- **Enrollment**: Guided multi-pose face capture with real-time feedback
- **Edit Profiles**: Update Name, Level, and Matric Number (with cascade updates)
- **Delete**: Remove students and their attendance history
- **Recently Enrolled** table with Edit/Delete actions
- **Loading States**: Visual feedback during face capture initialization

### 📊 Dashboard & Analytics

- Real-time session attendance table (auto-updates during active sessions)
- Filter statistics by Level and Course
- Statistics cards (Present, Late, Total Students)
- Toast notifications for user feedback

### 🔌 Hardware Integration (ESP32-Based)

- **ESP32-CAM**: Wireless video streaming over WiFi
- **ESP32 DevKit**: Controls LCD display and buzzer
- **16x2 LCD with I2C**: Displays attendance status and student names
- **Active Buzzer**: Audio feedback for successful/failed recognition
- **Wireless Architecture**: No cables between camera and PC

### 💾 Database

- SQLite with tables: `students`, `attendance`, `class_sessions`, `users`
- Test isolation with temporary databases

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

2. **Install setuptools** (required for face_recognition_models):

   ```powershell
   pip install --upgrade setuptools
   ```

3. **Install face_recognition_models**:

   ```powershell
   pip install git+https://github.com/ageitgey/face_recognition_models
   ```

4. **Install remaining dependencies**:

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
│   ├── /controllers     # Business logic (Auth, Student, Session, Attendance)
│   └── /routes          # API endpoints (Blueprints)
├── /static
│   ├── /css             # Stylesheets
│   └── /js
│       ├── /api         # API Client
│       ├── /modules     # Reusable UI modules
│       ├── /pages       # Page-specific logic (dashboard, enrollment)
│       └── main.js      # Entry point
├── /templates           # HTML Templates (Base, Index, Enroll, Login)
├── /database            # Schema and SQLite DB
├── /tests               # Pytest suite (with test isolation)
├── app.py               # Application entry point
├── camera.py            # Vision processing (supports ESP32-CAM stream)
├── esp32_bridge.py      # WiFi communication with ESP32 hardware
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

### Sessions

| Endpoint                        | Method | Description                      |
| :------------------------------ | :----- | :------------------------------- |
| `/api/sessions/start`           | POST   | Start a new class session        |
| `/api/sessions/end`             | POST   | End the active session           |
| `/api/sessions/active`          | GET    | Get current active session       |
| `/api/sessions/history`         | GET    | Get past session history         |
| `/api/sessions/<id>/attendance` | GET    | Get attendance for a session     |
| `/api/sessions/<id>/export`     | GET    | Export session attendance as CSV |
| `/api/sessions/<id>`            | DELETE | Delete a session and its records |

### Attendance

| Endpoint                | Method | Description                               |
| :---------------------- | :----- | :---------------------------------------- |
| `/api/attendance/today` | GET    | Get session attendance (supports filters) |
| `/api/statistics`       | GET    | Get system stats (supports filters)       |

---

## 🧪 Testing

This project uses **pytest** with **test database isolation** - tests run against temporary databases and don't affect production data.

```powershell
# Run all tests
pytest

# Run specific test file
pytest tests/test_db.py
pytest tests/test_sessions.py -v

# Run with verbose output
pytest -v --tb=short
```

### Test Coverage

- `test_db.py` - Database helper functions
- `test_api.py` - API endpoint tests
- `test_sessions.py` - Session management and history

---

## 👥 Team

**MTE 411 - Mechatronics System Design Project**

- **Team Lead**: Salako Akolade
- **Team Members**: Balogun Azeez, Raji Muhibudeen, Giwa Fuad, Olumuyiwa Timilehin
- **Supervisor**: Engr. S. Ogundipe
- **Institution**: Abiola Ajimobi Technical University

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
