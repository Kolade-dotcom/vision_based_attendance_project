-- Smart Vision-Based Attendance System
-- Database Schema

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- Users table (Admin authentication)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL, -- Generic ID, can be Matric Number e.g. 125/22/1/0178
    name TEXT NOT NULL,
    email TEXT,
    level TEXT,         -- e.g. "400"
    courses TEXT,       -- JSON array of course codes e.g. '["MTE411", "MTE412"]'
    face_encoding BLOB,  -- Serialized face encoding data
    password_hash TEXT,            -- bcrypt hash for portal login
    is_enrolled INTEGER DEFAULT 0, -- 1 = face capture completed
    status TEXT DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'rejected')),
    enrolled_via_link_id INTEGER,  -- FK to enrollment_links (NULL if enrolled by lecturer directly)
    created_by INTEGER,            -- FK to users (lecturer who enrolled or approved)
    rejection_reason TEXT,         -- Reason if status is 'rejected'
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (enrolled_via_link_id) REFERENCES enrollment_links(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Create index on student_id for faster lookups
CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);

-- Enrollment Links table (for self-enrollment)
CREATE TABLE IF NOT EXISTS enrollment_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,           -- Secure random token (URL-safe)
    created_by INTEGER NOT NULL,          -- Lecturer user ID
    course_code TEXT,                     -- Optional: pre-fill course
    level TEXT,                           -- Optional: pre-fill level
    description TEXT,                     -- Optional: link description/name
    max_uses INTEGER DEFAULT NULL,        -- NULL = unlimited
    current_uses INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,             -- ISO timestamp
    is_active INTEGER DEFAULT 1,          -- 0 = revoked
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_enrollment_links_token ON enrollment_links(token);
CREATE INDEX IF NOT EXISTS idx_enrollment_links_created_by ON enrollment_links(created_by);

-- Class Sessions table
CREATE TABLE IF NOT EXISTS class_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,           -- Links session to lecturer who created it
    course_code TEXT NOT NULL,
    scheduled_start TEXT,           -- e.g. "2024-01-15T09:00:00"
    start_time TEXT NOT NULL,       -- Actual start time
    end_time TEXT,                  -- NULL while session is active
    is_active INTEGER DEFAULT 1,    -- 1 = active, 0 = ended
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index on class_sessions for active session lookups
CREATE INDEX IF NOT EXISTS idx_sessions_active ON class_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_course ON class_sessions(course_code);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON class_sessions(user_id);

-- Attendance records table
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL,
    session_id INTEGER,             -- Links to class_sessions
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent')),
    course_code TEXT,   -- e.g. "MTE411"
    level TEXT,         -- e.g. "400" (Level at time of attendance)
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE
);

-- Create indexes for attendance queries
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);

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
