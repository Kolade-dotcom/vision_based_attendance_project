# UX Fixes & Improvements Design — 2026-03-06

## 1. Favicon Fix

**Current**: SVG with 2 concentric circle strokes + filled center dot, all `#6366f1` (indigo).
**Change**: Remove the center dot element. Change stroke color to `#0d9488` (brand teal). Update `theme-color` meta tags from `#6366f1` to `#0d9488` in all templates (login, enroll, portal base, dashboard base).

Files: `static/images/favicon.svg`, all `templates/**/base.html`, `templates/portal/login.html`, `templates/portal/enroll.html`.

## 2. Re-capture Bug Fix

**Problem**: "Re-capture Face" on profile links to `/portal/enroll`, which always shows the full 4-step flow including the academic details form. Already-enrolled students shouldn't need to re-fill details.

**Solution**: Change the profile link to `/portal/enroll?recapture=1`. On the enroll page:
- Pass `is_enrolled` and `recapture` flag via `window.__STUDENT__`.
- In recapture mode, after face processing succeeds, call `PUT /api/portal/face` (existing `update_face_logic`) instead of `POST /api/portal/enroll`.
- Skip the details step entirely — go straight to confirmation showing existing profile data.
- Fetch existing profile data via `/api/portal/profile` to populate the summary card.

Files: `templates/portal/profile.html`, `templates/portal/enroll.html`, `static/js/portal/enroll.js`, `api/routes/portal_routes.py`.

## 3. Pose Guidance Animations

**Problem**: Users miss the text-only pose instructions during face capture.

**Solution**: Add a brief visual overlay on the camera viewport when each new pose starts. The overlay:
- Appears with a slide-in + fade-in animation.
- Shows an SVG icon/arrow indicating the pose direction (arrow pointing left/right/up/down, smiley face, neutral face, centered crosshair).
- Stays visible for ~2.5 seconds, then fades out.
- Uses brand colors, semi-transparent background strip for contrast.
- Does not block the face detection area (positioned at top or bottom edge of viewport).

Pose icons:
- **center**: Crosshair/target icon
- **left**: Left-pointing arrow with "Look left" text
- **right**: Right-pointing arrow with "Look right" text
- **up**: Up-pointing arrow with "Look up" text
- **down**: Down-pointing arrow with "Look down" text
- **smile**: Smiley face icon
- **neutral**: Calm/relaxed face icon

CSS animations: `@keyframes pose-hint-in` (slide + fade in), `@keyframes pose-hint-out` (fade out). Total visible duration ~2.5s.

Files: `templates/portal/enroll.html` (styles + HTML container), `static/js/portal/enroll.js` (trigger logic in `startPose()`).

## 4. Course Code Autocomplete & Validation

### 4a. Validation (all 3 course inputs)

Enforce format: exactly 3 uppercase letters + 3 digits (regex: `/^[A-Z]{3}\d{3}$/`).
- Show inline error below input if format is invalid on add attempt.
- Auto-uppercase on input.
- Apply to: enroll page, profile page, dashboard settings page.

### 4b. Autocomplete suggestions

**New API endpoint**: `GET /api/portal/courses/search?q=<query>` (student) and `GET /api/dashboard/courses/search?q=<query>` (lecturer).
- Returns array of matching course codes from the database.
- Matches by prefix (case-insensitive).
- Sorts results: level-matching courses first (for student endpoint, using student's level), then alphabetical.
- Max 8 results.

**New DB function**: `search_all_course_codes(query)` — collects all distinct course codes from:
1. `students.courses` JSON arrays
2. `class_sessions.course_code`
3. `users.courses` JSON arrays

**Frontend autocomplete component** (shared pattern across all 3 inputs):
- Dropdown appears below the input as user types (after 1+ character).
- Keyboard navigation (up/down arrows, Enter to select, Escape to close).
- Click to select.
- Styled to match existing input/chip design.
- On selection, auto-fills input; user still clicks "Add" to confirm.

Files: `db_helper.py`, `api/routes/portal_api_routes.py`, `api/routes/dashboard_api_routes.py`, `static/js/portal/enroll.js`, `static/js/portal/profile.js`, `static/js/dashboard/settings.js`, `templates/portal/enroll.html`, `templates/portal/profile.html`, `templates/dashboard/settings.html`.

## 5. Login Placeholder Fix

Change matric number placeholder from `e.g. 20/52HA001` to `e.g. 125/22/1/0178` on both sign-in and sign-up forms.

Files: `templates/portal/login.html` (lines 277, 319).
