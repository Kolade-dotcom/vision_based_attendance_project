# Design: Lecturer Dashboard + Student Portal Split

**Date**: 2026-03-05
**Status**: Approved

---

## 1. Overview

Split the monolithic Lumina attendance app into two distinct interfaces within a single Flask server:

- **Lecturer Dashboard** (`/dashboard/*`) — session management, attendance monitoring, analytics
- **Student Portal** (`/portal/*`) — self-enrollment, attendance history, profile management

Designed for future separation into independent Flask apps sharing the same database.

## 2. Architecture

### 2.1 Separation Strategy

Same Flask server, separate blueprint groups:

```
/dashboard/*       → dashboard_bp (lecturer pages)
/portal/*          → portal_bp (student pages)
/api/dashboard/*   → dashboard_api_bp (lecturer API)
/api/portal/*      → portal_api_bp (student API)
/                  → redirect to /dashboard/
```

### 2.2 Shared Core (used by both apps)

- `db_helper.py` — database operations
- `config.py` — configuration
- `camera.py` / `face_processor.py` — face recognition engine
- `esp32_bridge.py` — hardware communication
- `database/schema.sql` — single SQLite database

### 2.3 Separated Concerns

- Templates: `templates/dashboard/` vs `templates/portal/`
- Static JS: `static/js/dashboard/` vs `static/js/portal/`
- Routes: separate blueprint files per app
- Controllers: separate controller files per app
- Auth: two separate session systems (lecturer vs student)

## 3. Lecturer Dashboard

### 3.1 Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/dashboard/login` | Login/Signup | Lecturer authentication |
| `/dashboard/` | Live Session | Camera feed, real-time attendance, session controls, history |
| `/dashboard/analytics` | Analytics | Attendance trends, student leaderboard, course stats |
| `/dashboard/settings` | Settings | Late threshold, camera source, course management, account |

### 3.2 Layout

- **Desktop**: 240px fixed sidebar (left). Logo top, nav links middle, user card + theme toggle bottom. Full text labels with 3px left border accent on active item.
- **Mobile**: Top app bar with hamburger → slide-in drawer from left.
- **Content area**: Max-width 1280px, centered, `px-6` desktop / `px-4` mobile.
- **Sidebar nav items**: Live Session | Analytics | Settings

### 3.3 Live Session Page (`/dashboard/`)

Top-to-bottom flow:

1. **Header bar**: "Good morning, {name}" greeting + course selector (right-aligned).
2. **Session control strip**: Single horizontal bar showing session state.
   - No active session: Course selector + "Start Session" button.
   - Active session: Teal left-border accent, course code, elapsed time (live counter), "End Session" button.
3. **Two-column layout** (stacks on mobile):
   - Left (60%): Live camera feed with face detection overlay. Below: real-time attendance table. Rows slide in on recognition. Status pills: teal=present, amber=late.
   - Right (40%): Session stats as large numbers with labels (not cards). e.g., big "12" + "Present", big "3" + "Late".
4. **Session history**: Data table with sharp corners, subtle row hover, alternating warm-gray backgrounds. Columns: date, course, duration, student count, actions (export CSV, delete).

### 3.4 Analytics Page (`/dashboard/analytics`)

- Course selector at top (adaptive: pills for 1-3 courses, dropdown for 4+)
- **Attendance rate trend**: Line chart, last 10 sessions
- **Student leaderboard**: Table sorted by attendance %. Red flags for students below 75%
- **Session summaries**: Recent sessions with quick stats, exportable

### 3.5 Settings Page (`/dashboard/settings`)

- Late threshold (minutes) — default 15
- Camera source (ESP32 URL / webcam / auto)
- Manage courses — add/remove course codes (inline chips + input)
- Account info (name, email, password change)

### 3.6 Course Selector Component

Adaptive based on course count:
- 1-3 courses: Horizontal pill toggle
- 4+ courses: Compact dropdown with current course shown as pill

Used across all pages consistently.

## 4. Student Portal

### 4.1 Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/portal/login` | Login/Signup | Student authentication (matric + password) |
| `/portal/enroll` | Onboarding | First-time guided face capture + academic details |
| `/portal/` | Home | Status card, today's attendance, quick stats, recent activity |
| `/portal/attendance` | Attendance | Full history, filterable by course, grouped by month |
| `/portal/profile` | Profile | Edit info, courses, re-capture face, change password |

### 4.2 Layout

- **Mobile**: No sidebar. Bottom navigation bar — 3 tabs: Home | Attendance | Profile. Fixed bottom, 56px height, 48px touch targets. Active tab = teal, others muted.
- **Desktop**: Bottom nav moves to top horizontal nav under slim header. Content max-width 640px, centered. App-like feel on wide screens.
- **Top bar**: Slim — logo left ("Lumina"), theme toggle right. No hamburger.

### 4.3 Signup → Enrollment Flow

1. **`/portal/login`**: Login / Sign Up tabs. Signup fields: matric number, full name, email, password. On submit → auto-redirect to enrollment.

2. **`/portal/enroll`** (shown if `is_enrolled = false`): Full-screen onboarding, no bottom nav visible.
   - **Step 1**: "Let's set up face recognition" — brief explanation, camera permission. Big "Start Camera" button.
   - **Step 2**: Guided face capture. Camera viewport fills most of screen. Current instruction in large text above camera. Horizontal dot stepper — 7 dots for 7 poses, current filled teal.
   - **Step 3**: Academic details — Level dropdown, courses multi-input.
   - **Step 4**: Confirmation — "You're all set" summary card. "Go to Home" button.

   If closed mid-capture, next login resumes here.

### 4.4 Home Page (`/portal/`)

Quick-glance screen (like a banking app home):

- **Status card**: Large, teal-tinted background. Student name, matric number, enrollment status.
- **Today's attendance**: If active session exists for their course, prominent card: "MTE411 — You were marked present at 10:23 AM" or "Session active — you haven't been marked yet."
- **Quick stats**: Two large numbers — "87% attendance rate" and "2 courses enrolled".
- **Recent activity**: Last 5 attendance records as a simple list. Date, course, status pill. Tappable.

### 4.5 Attendance Page (`/portal/attendance`)

- **Course filter**: Adaptive pill toggle / dropdown at top.
- **Summary bar** (sticky on scroll): "MTE411: 87% (26/30 sessions)" — always visible.
- **Attendance list**: Chronological, grouped by month. Each entry: date, course code, time marked, status pill. List format (not table) — mobile-friendly.
- **Empty state**: "No attendance records yet. Your attendance will appear here once your lecturer starts a session."

### 4.6 Profile Page (`/portal/profile`)

- **Profile header**: Name, matric, email. Inline edit (tap pencil → fields editable → save).
- **Courses**: Enrolled courses as removable chips + add input.
- **Level**: Editable dropdown.
- **Face enrollment**: "Face enrolled ✓" with "Re-capture" button → launches guided capture flow.
- **Account**: Change password. Logout button.
- No avatar/photo upload (privacy concern with face data).

## 5. Visual Design System

### 5.1 Typography

| Role | Font | Notes |
|------|------|-------|
| Display/Headings | Bricolage Grotesque | Characterful geometric sans, letterspacing -0.03em on large sizes |
| Body | Plus Jakarta Sans | Warm humanist sans, excellent small-size readability |
| Monospace/Data | JetBrains Mono | Matric numbers, timestamps, session IDs |

### 5.2 Color Palette

**Light mode (default):**

| Token | Value | Usage |
|-------|-------|-------|
| `--brand` | `#0d9488` (Teal 600) | Primary actions, active states |
| `--brand-light` | `#ccfbf1` (Teal 50) | Tinted backgrounds, selections |
| `--accent` | `#f97316` (Orange 500) | Notifications, badges, late status |
| `--surface` | `#FAFAF8` | Warm off-white page background |
| `--surface-raised` | `#FFFFFF` | Cards, elevated surfaces |
| `--surface-sunken` | `#f0f0ec` | Inset areas, table alternating rows |
| `--text-primary` | `#1a1a1a` | Headings |
| `--text-secondary` | `#5c5c5c` | Body text |
| `--text-muted` | `#9ca3af` | Helper text, timestamps |
| `--success` | `#059669` | Present, connected |
| `--warning` | `#d97706` | Late arrivals |
| `--danger` | `#dc2626` | Absent, errors |
| `--border` | `#e8e8e4` | Warm gray borders |

**Dark mode:**

| Token | Light → Dark |
|-------|-------------|
| `--brand` | `#0d9488` → `#2dd4bf` |
| `--accent` | `#f97316` → `#fb923c` |
| `--surface` | `#FAFAF8` → `#141414` |
| `--surface-raised` | `#FFFFFF` → `#1e1e1e` |
| `--surface-sunken` | `#f0f0ec` → `#0a0a0a` |
| `--text-primary` | `#1a1a1a` → `#f0f0ec` |
| `--text-secondary` | `#5c5c5c` → `#a1a1a1` |
| `--text-muted` | `#9ca3af` → `#6b7280` |
| `--border` | `#e8e8e4` → `#2a2a2a` |

Theme persists via localStorage, respects prefers-color-scheme on first visit, FOUC prevention via inline script in `<head>`.

### 5.3 Anti-Vibecode Rules

Per FRONTEND_ASSIST.md:

- No uniform `rounded-lg` — mix sharp corners (tables, inputs) with soft rounds (avatars, badges)
- No colored-circle icons — icons used functionally, varying sizes
- Custom shadow scale, not Tailwind defaults
- Off-white `#FAFAF8` backgrounds, warm gray borders (not cold slate)
- Intentional spacing rhythm (not uniform p-4/p-6)
- Semantic HTML (nav, main, section, header, footer)
- All interactive states: hover, focus, active, disabled
- All data states: loading, empty, error, populated
- Mobile-first responsive design
- WCAG AA contrast ratios
- No "Supercharge/Unlock/Elevate" copy — specific, concrete text
- Font pairing with character (Bricolage Grotesque + Plus Jakarta Sans)
- No transition-all — specify exact properties

### 5.4 Spatial Personality

- **Lecturer dashboard**: Medium-dense. Data-rich with clear hierarchy.
- **Student portal**: Generous. Larger touch targets, more breathing room. Max-width 640px content.

## 6. Database Changes

### 6.1 Students Table Modifications

```sql
ALTER TABLE students ADD COLUMN password_hash TEXT;
ALTER TABLE students ADD COLUMN is_enrolled BOOLEAN DEFAULT 0;
```

- `password_hash`: bcrypt hash for portal login
- `is_enrolled`: whether face capture is complete (gates portal access)
- Keep `status` column but default to 'approved' (no approval workflow)
- Keep `enrolled_via_link_id` column (no migration risk) but unused

### 6.2 Enrollment Links Table

Keep table in schema but remove all routes/controllers/UI for it. No data migration needed.

## 7. What Gets Removed

- Enrollment links system (routes, controllers, templates, JS)
- Approval/rejection workflow (controllers, UI elements)
- Public enrollment routes (`/api/public/*`) — replaced by portal enrollment
- Lecturer-side student enrollment page (`/enroll`)
- Lecturer-side student management UI (edit/delete individual students)
- `templates/public_enroll.html`, `templates/enrollment_success.html`
- `api/controllers/enrollment_link_controller.py`
- `api/controllers/public_enrollment_controller.py`
- `api/routes/enrollment_link_routes.py`
- `api/routes/public_enrollment_routes.py`

## 8. What Gets Added

- Student auth system (signup/login/logout, separate from lecturer)
- Portal blueprint with 5 pages + API endpoints
- Dashboard analytics page
- Dashboard settings page
- Redesigned dashboard templates with new visual system
- New portal templates (mobile-first)
- Shared design token CSS (theme.css overhaul)
- Adaptive course selector component
- Student attendance API (for portal)
- Student profile API (for portal)
- Face re-capture flow (reuses existing guided capture logic)

## 9. Critical Bug Fixes (from code review)

To be addressed during implementation:

1. **SECRET_KEY hardcoded fallback** — fail loudly if not set
2. **pickle deserialization** — switch to numpy.tobytes/frombuffer
3. **Missing auth on endpoints** — add @login_required decorators
4. **get_attendance_for_active_session missing user_id arg** — fix call
5. **record_attendance returns int, used as dict** — return proper dict
6. **Stored XSS in JS template literals** — HTML-escape all dynamic content
7. **Debug print statements** — replace with logging module
8. **Duplicate face_distance computation** — remove redundant call
9. **Developer comments in db_helper** — clean up
10. **No MAX_CONTENT_LENGTH** — add request size limit
