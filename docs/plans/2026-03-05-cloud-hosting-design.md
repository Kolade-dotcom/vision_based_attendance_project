# Cloud Hosting Design — Hybrid Architecture

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Host the attendance app on the web while keeping face recognition and ESP32 hardware interaction on the local laptop, connected via WebSocket.

**Architecture:** Cloud Flask app (Render free tier) + Neon PostgreSQL + local worker script. Dashboard controls sessions; worker captures video, runs face recognition, streams frames, and reports attendance via WebSocket + REST API.

**Tech Stack:** Flask-SocketIO, eventlet, psycopg2, python-socketio[client], Neon PostgreSQL, Render, cron-job.org

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────┐
│                RENDER (Free tier)                  │
│                                                    │
│  Flask App                                         │
│  ├── Dashboard UI (lecturer)                       │
│  ├── Portal UI (student)                           │
│  ├── REST API (sessions, attendance, courses)      │
│  └── WebSocket server (Flask-SocketIO)             │
│       ├── Receives video frames from worker        │
│       ├── Sends session start/end commands          │
│       └── Relays live feed to dashboard browsers   │
│                                                    │
└──────────────┬───────────────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
    ▼                     ▼
Neon PostgreSQL      Your Laptop (Worker)
(DATABASE_URL)       ├── Connects via WebSocket
                     ├── Captures ESP32-CAM / webcam
                     ├── Runs face recognition (dlib)
                     ├── Streams JPEG frames to cloud
                     ├── POSTs attendance results
                     └── Controls ESP32 hardware
```

## Data Flows

1. Lecturer clicks "Start Session" → cloud sends `session:start` via WebSocket → worker begins capture + recognition
2. Worker recognizes a face → POSTs attendance to cloud API → dashboard polls and shows it
3. Worker streams JPEG frames via WebSocket → cloud relays to dashboard browsers → live canvas feed
4. Lecturer clicks "End Session" → cloud sends `session:end` → worker stops camera + ESP32

## Database Migration

- Replace sqlite3 in db_helper.py with psycopg2 connection pool
- Schema syntax changes: AUTOINCREMENT → SERIAL, datetime('now') → NOW()
- Connection string from env var DATABASE_URL
- Keep SQLite fallback for local development (no DATABASE_URL = use SQLite)

## Worker Script (worker.py)

Reuses: camera.py, esp32_bridge.py, config.py, face_recognition

- Connects to cloud WebSocket, authenticates with WORKER_API_KEY
- Waits for session:start command
- Capture loop: grab frame → detect/recognize → stream JPEG → POST attendance
- On session:end: stops camera, releases resources
- ESP32 feedback stays as-is

## New API Endpoints

- GET /api/worker/faces — returns enrolled student face encodings
- POST /api/worker/attendance — worker reports recognized student

## Live Camera Feed

- Worker sends JPEG frames via SocketIO (~5 FPS, 640x360, quality 70)
- Cloud relays to dashboard browsers
- Dashboard uses <canvas> instead of <img src="/video_feed">
- Fallback: "Camera offline" message on disconnect

## Deployment

- Render: GitHub auto-deploy, gunicorn --worker-class eventlet -w 1 app:app
- Neon: Free PostgreSQL, connection string in DATABASE_URL
- Keep-alive: cron-job.org pings /api/health every 14 minutes
- Env vars: DATABASE_URL, SECRET_KEY, WORKER_API_KEY

## New Dependencies

- flask-socketio + eventlet (cloud WebSocket server)
- python-socketio[client] (worker client)
- psycopg2-binary (PostgreSQL)
