-- Smart Vision-Based Attendance System
-- PostgreSQL Database Schema

-- Users table (Admin authentication)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    courses TEXT,
    created_at TEXT DEFAULT (NOW()::text)
);

-- Enrollment Links table (must be created BEFORE students, which references it)
CREATE TABLE IF NOT EXISTS enrollment_links (
    id SERIAL PRIMARY KEY,
    token TEXT UNIQUE NOT NULL,
    created_by INTEGER NOT NULL,
    course_code TEXT,
    level TEXT,
    description TEXT,
    max_uses INTEGER DEFAULT NULL,
    current_uses INTEGER DEFAULT 0,
    expires_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (NOW()::text),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_enrollment_links_token ON enrollment_links(token);
CREATE INDEX IF NOT EXISTS idx_enrollment_links_created_by ON enrollment_links(created_by);

-- Students table
CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    email TEXT,
    level TEXT,
    courses TEXT,
    face_encoding BYTEA,
    password_hash TEXT,
    is_enrolled INTEGER DEFAULT 0,
    status TEXT DEFAULT 'approved' CHECK(status IN ('pending', 'approved', 'rejected')),
    enrolled_via_link_id INTEGER,
    created_by INTEGER,
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    FOREIGN KEY (enrolled_via_link_id) REFERENCES enrollment_links(id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_students_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_students_status ON students(status);

-- Class Sessions table
CREATE TABLE IF NOT EXISTS class_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    course_code TEXT NOT NULL,
    scheduled_start TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (NOW()::text),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_active ON class_sessions(is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_course ON class_sessions(course_code);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON class_sessions(user_id);

-- Attendance records table
CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id TEXT NOT NULL,
    session_id INTEGER,
    timestamp TEXT NOT NULL,
    status TEXT DEFAULT 'present' CHECK(status IN ('present', 'late', 'absent')),
    course_code TEXT,
    level TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    FOREIGN KEY (session_id) REFERENCES class_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance(timestamp);
CREATE INDEX IF NOT EXISTS idx_attendance_session ON attendance(session_id);

-- System settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT
);

-- Insert default settings
INSERT INTO settings (key, value, updated_at) VALUES
    ('late_threshold_minutes', '15', NOW()::text),
    ('session_start_time', '09:00', NOW()::text),
    ('session_end_time', '17:00', NOW()::text)
ON CONFLICT (key) DO NOTHING;
