-- Smart Vision-Based Attendance System
-- Database Schema

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL, -- Generic ID, can be Matric Number e.g. 125/22/1/0178
    name TEXT NOT NULL,
    email TEXT,
    level TEXT,         -- e.g. "400"
    courses TEXT,       -- JSON array of course codes e.g. '["MTE411", "MTE412"]'
    face_encoding BLOB,  -- Serialized face encoding data
    created_at TEXT NOT NULL,
    updated_at TEXT
);

-- Create index on student_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);

-- Attendance records table
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent')),
    course_code TEXT,   -- e.g. "MTE411"
    level TEXT,         -- e.g. "400" (Level at time of attendance)
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE
);

-- Create indexes for attendance queries
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);

-- System settings table (for future use)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT
);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES 
    ('late_threshold_minutes', '15', datetime('now')),
    ('session_start_time', '09:00', datetime('now')),
    ('session_end_time', '17:00', datetime('now'));
