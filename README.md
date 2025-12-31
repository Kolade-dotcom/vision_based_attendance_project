# 🎯 Smart Vision-Based Attendance System

A Flask-based attendance system using **computer vision** and **face recognition** for automated student attendance tracking.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Running the Application](#-running-the-application)
- [Project Structure](#-project-structure)
- [API Endpoints](#-api-endpoints)

---

## ✨ Features

- 📸 Real-time face detection and recognition
- 👤 Student enrollment with face capture
- 📊 Attendance tracking and statistics
- 🔌 Arduino integration for hardware feedback (LEDs, buzzers, door control)
- 💾 SQLite database for persistent storage

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
├── /static
│   ├── /css
│   │   └── style.css        # Main stylesheet
│   ├── /js
│   │   └── main.js          # Frontend JavaScript
│   └── /images              # Static images
├── /templates
│   ├── index.html           # Dashboard page
│   └── enroll.html          # Student enrollment page
├── /database
│   └── schema.sql           # SQLite schema
├── app.py                   # Flask entry point
├── camera.py                # OpenCV camera & face detection
├── db_helper.py             # Database operations
├── arduino_bridge.py        # Hardware communication (simulation)
├── requirements.txt         # Python dependencies
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## 🔌 API Endpoints

| Endpoint      | Method | Description             |
| ------------- | ------ | ----------------------- |
| `/`           | GET    | Dashboard page          |
| `/enroll`     | GET    | Student enrollment page |
| `/api/health` | GET    | Health check endpoint   |

---

## 🛠️ Development

### Testing Individual Modules

```powershell
# Test camera module
python camera.py

# Test database module
python db_helper.py

# Test Arduino bridge (simulation mode)
python arduino_bridge.py
```

### Common Issues

**dlib installation fails:**

- Ensure you are using the correct wheel URL for your Python version
- Make sure your virtual environment is activated
- If the wheel architecture (amd64) matches your system

**Camera not working:**

- Check that no other application is using the webcam
- Try changing `camera_index` in `Camera()` constructor

---

## 👥 Team

- Mechatronics Project Team

## 📄 License

This project is for educational purposes.
