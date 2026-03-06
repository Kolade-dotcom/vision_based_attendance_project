# UX Fixes & Improvements Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix favicon, re-capture bug, login placeholder; add pose guidance animations and course code autocomplete/validation across student and lecturer UIs.

**Architecture:** Mostly frontend changes (HTML/CSS/JS) with one new DB helper function and two new API endpoints for course search. The enroll page JS gains recapture-mode branching and pose animation overlay logic. Course inputs across 3 pages get shared validation + autocomplete dropdown patterns.

**Tech Stack:** Flask (Python), vanilla JS, CSS animations, SVG icons, SQLite/PostgreSQL.

---

## Task 1: Favicon Fix

**Files:**
- Modify: `static/images/favicon.svg`
- Modify: `templates/portal/login.html:8`
- Modify: `templates/portal/enroll.html:8`
- Modify: `templates/portal/base.html:8`
- Modify: `templates/dashboard/base.html:8`

**Step 1: Update the favicon SVG**

Remove the center filled dot (line 4) and change stroke/fill color from `#6366f1` to `#0d9488`:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
  <circle cx="32" cy="32" r="28" fill="none" stroke="#0d9488" stroke-width="4"/>
  <circle cx="32" cy="32" r="18" fill="none" stroke="#0d9488" stroke-width="4"/>
</svg>
```

**Step 2: Update theme-color meta tags**

In all 4 templates, change:
```html
<meta name="theme-color" content="#6366f1" />
```
to:
```html
<meta name="theme-color" content="#0d9488" />
```

Files: `templates/portal/login.html:8`, `templates/portal/enroll.html:8`, `templates/portal/base.html:8`, `templates/dashboard/base.html:8`.

**Step 3: Commit**

```bash
git add static/images/favicon.svg templates/portal/login.html templates/portal/enroll.html templates/portal/base.html templates/dashboard/base.html
git commit -m "fix: update favicon to brand teal and remove center dot"
```

---

## Task 2: Login Placeholder Fix

**Files:**
- Modify: `templates/portal/login.html:277,319`

**Step 1: Update placeholders**

Change both matric number input placeholders from `e.g. 20/52HA001` to `e.g. 125/22/1/0178`:

Line 277 (sign-in form):
```html
placeholder="e.g. 125/22/1/0178"
```

Line 319 (sign-up form):
```html
placeholder="e.g. 125/22/1/0178"
```

**Step 2: Commit**

```bash
git add templates/portal/login.html
git commit -m "fix: update matric number placeholder to realistic format"
```

---

## Task 3: Re-capture Bug Fix

**Files:**
- Modify: `templates/portal/profile.html:278`
- Modify: `templates/portal/enroll.html:569-573`
- Modify: `static/js/portal/enroll.js`
- Modify: `api/routes/portal_routes.py:10-13`

**Step 1: Update profile page link to include recapture flag**

In `templates/portal/profile.html:278`, change:
```html
<a href="/portal/enroll" class="btn btn-secondary btn-sm">Re-capture Face</a>
```
to:
```html
<a href="/portal/enroll?recapture=1" class="btn btn-secondary btn-sm">Re-capture Face</a>
```

**Step 2: Pass recapture flag and enrollment status in the enroll template**

In `api/routes/portal_routes.py`, update the enroll route to pass the query param:
```python
@portal_bp.route('/enroll')
@student_login_required
def enroll():
    recapture = request.args.get('recapture', '0') == '1'
    student = db_helper.get_student_by_matric(session['student_id'])
    is_enrolled = bool(student and student.get('is_enrolled'))
    return render_template('portal/enroll.html', recapture=recapture, is_enrolled=is_enrolled)
```

Add `request` and `db_helper` to imports at top of `api/routes/portal_routes.py`:
```python
from flask import Blueprint, render_template, session, redirect, request
import db_helper
```

In `templates/portal/enroll.html`, update the `window.__STUDENT__` block (~line 569-573):
```html
<script>
  window.__STUDENT__ = {
    name: {{ session.get('student_name', '') | tojson }},
    matric: {{ session.get('student_id', '') | tojson }},
    isEnrolled: {{ is_enrolled | tojson }},
    recapture: {{ recapture | tojson }}
  };
</script>
```

**Step 3: Update enroll.js to handle recapture mode**

In `static/js/portal/enroll.js`, after the successful face processing (inside `processCapturedFrames` around line 291-300), add recapture branching:

Replace the `.then(function (result) { ... })` block in `processCapturedFrames()` with:

```javascript
.then(function (result) {
  state.processing = false;
  if (!result.ok) {
    showProcessingFailed(result.data.error || 'Face processing failed. Please try again.');
    return;
  }

  state.faceEncoding = result.data.face_encoding;

  // Recapture mode: skip details, just update face and show confirmation
  if (window.__STUDENT__.recapture && window.__STUDENT__.isEnrolled) {
    submitRecapture();
  } else {
    goToStep('details');
  }
})
```

Add a new `submitRecapture()` function (after `processCapturedFrames`):

```javascript
function submitRecapture() {
  fetch('/api/portal/face', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ face_encoding: state.faceEncoding })
  })
    .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
    .then(function (result) {
      if (!result.ok) {
        showProcessingFailed(result.data.error || 'Failed to update face data.');
        return;
      }
      // Fetch existing profile for summary
      return fetch('/api/portal/profile')
        .then(function (res) { return res.json(); })
        .then(function (profile) {
          $('summary-name').textContent = profile.name || '';
          $('summary-matric').textContent = profile.matric || '';
          $('summary-level').textContent = (profile.level || '') + ' Level';
          $('summary-courses').textContent = (profile.courses && profile.courses.length)
            ? profile.courses.join(', ')
            : 'None yet';
          goToStep('confirm');
        });
    })
    .catch(function () {
      showProcessingFailed('Network error. Please try again.');
    });
}
```

**Step 4: Commit**

```bash
git add templates/portal/profile.html templates/portal/enroll.html static/js/portal/enroll.js api/routes/portal_routes.py
git commit -m "fix: skip details form when re-capturing face for enrolled students"
```

---

## Task 4: Pose Guidance Animations

**Files:**
- Modify: `templates/portal/enroll.html` (add CSS + HTML overlay container)
- Modify: `static/js/portal/enroll.js` (trigger animations in `startPose()`)

**Step 1: Add pose hint overlay HTML**

In `templates/portal/enroll.html`, inside the `.camera-viewport` div (after the oval-guide div, ~line 469), add:

```html
<!-- Pose hint overlay -->
<div id="pose-hint" class="pose-hint" aria-live="polite" style="display:none;">
  <div class="pose-hint__icon" id="pose-hint-icon"></div>
  <div class="pose-hint__text" id="pose-hint-text"></div>
</div>
```

**Step 2: Add pose hint CSS**

In the `<style>` block of `templates/portal/enroll.html`, add:

```css
/* --- Pose hint overlay --- */

.pose-hint {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-3);
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.65));
  z-index: 3;
  pointer-events: none;
  animation: pose-hint-in 0.35s ease-out;
}

.pose-hint.fading {
  animation: pose-hint-out 0.4s ease-in forwards;
}

.pose-hint__icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pose-hint__icon svg {
  width: 100%;
  height: 100%;
  color: #fff;
  filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
}

.pose-hint__text {
  font-size: var(--text-base);
  font-weight: 600;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.4);
}

@keyframes pose-hint-in {
  0% { opacity: 0; transform: translateY(12px); }
  100% { opacity: 1; transform: translateY(0); }
}

@keyframes pose-hint-out {
  0% { opacity: 1; transform: translateY(0); }
  100% { opacity: 0; transform: translateY(-8px); }
}
```

**Step 3: Add pose hint logic in enroll.js**

Add an SVG icon map and a `showPoseHint()` function near the top of the IIFE (after the POSES config):

```javascript
var POSE_ICONS = {
  center: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9" stroke-dasharray="4 2"/></svg>',
  left: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 5l-7 7 7 7"/></svg>',
  right: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>',
  up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>',
  down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>',
  smile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="10" r="0.5" fill="currentColor"/><circle cx="15" cy="10" r="0.5" fill="currentColor"/></svg>',
  neutral: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 15h8"/><circle cx="9" cy="10" r="0.5" fill="currentColor"/><circle cx="15" cy="10" r="0.5" fill="currentColor"/></svg>'
};

var poseHintTimer = null;

function showPoseHint(poseId, label) {
  var hint = $('pose-hint');
  var iconEl = $('pose-hint-icon');
  var textEl = $('pose-hint-text');
  if (!hint) return;

  clearTimeout(poseHintTimer);
  hint.classList.remove('fading');
  hint.style.display = '';

  iconEl.innerHTML = POSE_ICONS[poseId] || '';
  textEl.textContent = label;

  // Force reflow to restart animation
  void hint.offsetWidth;
  hint.style.animation = 'none';
  void hint.offsetWidth;
  hint.style.animation = '';

  poseHintTimer = setTimeout(function () {
    hint.classList.add('fading');
    setTimeout(function () {
      hint.style.display = 'none';
      hint.classList.remove('fading');
    }, 400);
  }, 2500);
}
```

**Step 4: Call showPoseHint from startPose()**

In the `startPose(index)` function (~line 209), add a call after setting the instruction text:

```javascript
function startPose(index) {
  state.poseIndex = index;
  state.frameIndex = 0;
  updateDotStepper();
  captureInstruction.textContent = POSES[index].label;
  captureProgress.textContent = 'Capturing 0/' + FRAMES_PER_POSE + '...';
  hideError('capture-error');

  showPoseHint(POSES[index].id, POSES[index].label);

  clearInterval(state.captureTimer);
  state.captureTimer = setInterval(captureFrame, CAPTURE_INTERVAL_MS);
}
```

**Step 5: Commit**

```bash
git add templates/portal/enroll.html static/js/portal/enroll.js
git commit -m "feat: add animated pose guidance overlay during face capture"
```

---

## Task 5: Course Code Validation

**Files:**
- Modify: `static/js/portal/enroll.js` (addCourse function ~line 387)
- Modify: `static/js/portal/profile.js` (btnAddCourse click ~line 179)
- Modify: `static/js/dashboard/settings.js` (onAddCourse ~line 102)

**Step 1: Add validation to all 3 course add functions**

The regex to enforce: `/^[A-Z]{3}\d{3}$/`

**enroll.js** — replace `addCourse()` (~line 387-398):

```javascript
var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

function addCourse() {
  var val = courseInput.value.trim().toUpperCase();
  if (!val) return;
  if (!COURSE_CODE_RE.test(val)) {
    showError('details-error', 'Course code must be 3 letters + 3 digits (e.g. MTE413)');
    return;
  }
  hideError('details-error');
  if (state.courses.indexOf(val) !== -1) {
    courseInput.value = '';
    return;
  }
  state.courses.push(val);
  courseInput.value = '';
  renderChips();
  courseInput.focus();
}
```

**profile.js** — update btnAddCourse click handler (~line 179-190):

```javascript
var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

btnAddCourse.addEventListener('click', function () {
  var code = addCourseInput.value.trim().toUpperCase();
  if (!code) return;
  if (!COURSE_CODE_RE.test(code)) {
    showToast('Course code must be 3 letters + 3 digits (e.g. MTE413)', 'error');
    return;
  }
  if (editingCourses.indexOf(code) !== -1) {
    showToast('Course already added', 'warning');
    return;
  }
  editingCourses.push(code);
  renderCourseChips(editingCourses, true);
  addCourseInput.value = '';
  addCourseInput.focus();
});
```

**settings.js** — update `onAddCourse()` (~line 102-113):

```javascript
var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

function onAddCourse() {
  var val = dom.newCourseInput.value.trim().toUpperCase();
  if (!val) return;
  if (!COURSE_CODE_RE.test(val)) {
    showToast("Course code must be 3 letters + 3 digits (e.g. MTE413)", "error");
    return;
  }
  if (state.courses.indexOf(val) !== -1) {
    showToast("Course already added", "warning");
    return;
  }
  state.courses.push(val);
  dom.newCourseInput.value = "";
  renderCourseChips();
  saveCourses();
}
```

**Step 2: Also add maxlength="6" to course inputs that don't have it**

- `templates/portal/enroll.html:514` — add `maxlength="6"` to `#course-input`
- `templates/dashboard/settings.html:218` — add `maxlength="6"` to `#new-course-input`
- `templates/portal/profile.html:265` — already has `maxlength="10"`, change to `maxlength="6"`

**Step 3: Commit**

```bash
git add static/js/portal/enroll.js static/js/portal/profile.js static/js/dashboard/settings.js templates/portal/enroll.html templates/portal/profile.html templates/dashboard/settings.html
git commit -m "feat: enforce course code format validation (3 letters + 3 digits)"
```

---

## Task 6: Course Search API

**Files:**
- Modify: `db_helper.py` (add `search_all_course_codes` function)
- Modify: `api/routes/portal_api_routes.py` (add search endpoint)
- Modify: `api/routes/dashboard_api_routes.py` (add search endpoint)

**Step 1: Add DB helper function**

Add to `db_helper.py` (after `get_recent_session_courses`):

```python
def search_all_course_codes(query, student_level=None, limit=8):
    """Search all unique course codes in the system by prefix.

    Returns matching codes sorted with level-matching codes first.
    """
    query = (query or '').strip().upper()
    if not query:
        return []

    seen = set()
    all_codes = []

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. From students
        cursor.execute(
            "SELECT DISTINCT courses FROM students "
            "WHERE courses IS NOT NULL AND courses != ''"
        )
        for row in cursor.fetchall():
            try:
                for c in json.loads(row['courses']):
                    if c and c not in seen:
                        all_codes.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

        # 2. From class sessions
        cursor.execute("SELECT DISTINCT course_code FROM class_sessions")
        for row in cursor.fetchall():
            c = row['course_code']
            if c and c not in seen:
                all_codes.append(c)
                seen.add(c)

        # 3. From lecturers
        cursor.execute(
            "SELECT courses FROM users WHERE courses IS NOT NULL AND courses != ''"
        )
        for row in cursor.fetchall():
            try:
                for c in json.loads(row['courses']):
                    if c and c not in seen:
                        all_codes.append(c)
                        seen.add(c)
            except (json.JSONDecodeError, TypeError):
                pass

    # Filter by prefix
    matches = [c for c in all_codes if c.upper().startswith(query)]

    # Sort: level-matching first (if student_level provided), then alphabetical
    if student_level:
        level_digit = str(student_level)[0] if student_level else None
        def sort_key(code):
            # code[3] is the first digit of the number part
            level_match = 0 if (len(code) >= 4 and code[3] == level_digit) else 1
            return (level_match, code)
        matches.sort(key=sort_key)
    else:
        matches.sort()

    return matches[:limit]
```

**Step 2: Add portal search endpoint**

In `api/routes/portal_api_routes.py`, add:

```python
@portal_api_bp.route('/courses/search', methods=['GET'])
@student_login_required
def search_courses():
    q = request.args.get('q', '')
    student = db_helper.get_student_by_matric(session['student_id'])
    level = student.get('level') if student else None
    results = db_helper.search_all_course_codes(q, student_level=level)
    return jsonify(results)
```

**Step 3: Add dashboard search endpoint**

In `api/routes/dashboard_api_routes.py`, add:

```python
@dashboard_api_bp.route("/courses/search")
@dashboard_login_required
def search_courses():
    q = request.args.get("q", "")
    results = db_helper.search_all_course_codes(q)
    return jsonify(results)
```

**Step 4: Commit**

```bash
git add db_helper.py api/routes/portal_api_routes.py api/routes/dashboard_api_routes.py
git commit -m "feat: add course code search API endpoint"
```

---

## Task 7: Course Autocomplete Frontend

**Files:**
- Modify: `templates/portal/enroll.html` (add autocomplete CSS + dropdown markup)
- Modify: `templates/portal/profile.html` (add autocomplete CSS + dropdown markup)
- Modify: `templates/dashboard/settings.html` (add autocomplete CSS + dropdown markup)
- Modify: `static/js/portal/enroll.js` (autocomplete logic)
- Modify: `static/js/portal/profile.js` (autocomplete logic)
- Modify: `static/js/dashboard/settings.js` (autocomplete logic)

**Step 1: Add shared autocomplete CSS**

Add to `static/css/design-system.css` (at the end, before any closing brace):

```css
/* === Course autocomplete === */

.course-autocomplete-wrap {
  position: relative;
}

.course-autocomplete {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 20;
  max-height: 200px;
  overflow-y: auto;
  background-color: var(--surface-raised);
  border: 1px solid var(--border);
  border-top: none;
  border-radius: 0 0 var(--radius-md) var(--radius-md);
  box-shadow: var(--shadow-md);
}

.course-autocomplete.open {
  display: block;
}

.course-autocomplete__item {
  padding: var(--space-2) var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  color: var(--text-primary);
  cursor: pointer;
  transition: var(--transition-colors);
}

.course-autocomplete__item:hover,
.course-autocomplete__item.active {
  background-color: var(--brand-light);
  color: var(--brand);
}

.course-autocomplete__empty {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--text-muted);
  font-style: italic;
}
```

**Step 2: Update HTML for enroll page course input**

In `templates/portal/enroll.html`, wrap the course input row (~line 510-518) with an autocomplete container:

Replace:
```html
<div class="course-input-row">
  <input
    type="text"
    id="course-input"
    class="input"
    placeholder="e.g. MTE411"
    autocomplete="off"
  />
  <button type="button" id="btn-add-course" class="btn btn-secondary">Add</button>
</div>
```

With:
```html
<div class="course-input-row">
  <div class="course-autocomplete-wrap" style="flex:1;">
    <input
      type="text"
      id="course-input"
      class="input"
      placeholder="e.g. MTE411"
      maxlength="6"
      autocomplete="off"
    />
    <div id="course-suggestions" class="course-autocomplete"></div>
  </div>
  <button type="button" id="btn-add-course" class="btn btn-secondary">Add</button>
</div>
```

**Step 3: Update HTML for profile page course input**

In `templates/portal/profile.html`, wrap the add-course input (~line 259-268):

Replace:
```html
<div class="course-add">
  <input
    type="text"
    id="add-course-input"
    class="input"
    placeholder="e.g. MTE411"
    maxlength="6"
  />
  <button type="button" class="btn btn-secondary btn-sm" id="btn-add-course">Add</button>
</div>
```

With:
```html
<div class="course-add">
  <div class="course-autocomplete-wrap" style="flex:1;">
    <input
      type="text"
      id="add-course-input"
      class="input"
      placeholder="e.g. MTE411"
      maxlength="6"
      autocomplete="off"
    />
    <div id="course-suggestions" class="course-autocomplete"></div>
  </div>
  <button type="button" class="btn btn-secondary btn-sm" id="btn-add-course">Add</button>
</div>
```

**Step 4: Update HTML for dashboard settings course input**

In `templates/dashboard/settings.html`, wrap the course input (~line 213-221):

Replace:
```html
<div class="settings-field-row">
  <input
    type="text"
    id="new-course-input"
    class="input"
    placeholder="e.g. MTE411"
  />
  <button type="button" class="btn btn-primary btn-sm" id="add-course-btn">Add</button>
</div>
```

With:
```html
<div class="settings-field-row">
  <div class="course-autocomplete-wrap" style="flex:1;">
    <input
      type="text"
      id="new-course-input"
      class="input"
      placeholder="e.g. MTE411"
      maxlength="6"
      autocomplete="off"
    />
    <div id="course-suggestions" class="course-autocomplete"></div>
  </div>
  <button type="button" class="btn btn-primary btn-sm" id="add-course-btn">Add</button>
</div>
```

**Step 5: Add autocomplete JS to enroll.js**

Add this block after the `addCourse()` function in `static/js/portal/enroll.js`:

```javascript
/* --- Course autocomplete --- */

var suggestionsEl = $('course-suggestions');
var acActiveIndex = -1;
var acDebounceTimer = null;

function fetchCourseSuggestions(query) {
  if (!query || query.length < 1) {
    closeSuggestions();
    return;
  }
  clearTimeout(acDebounceTimer);
  acDebounceTimer = setTimeout(function () {
    fetch('/api/portal/courses/search?q=' + encodeURIComponent(query))
      .then(function (res) { return res.json(); })
      .then(function (results) {
        renderSuggestions(results, query);
      })
      .catch(function () { closeSuggestions(); });
  }, 150);
}

function renderSuggestions(results, query) {
  if (!results || results.length === 0) {
    closeSuggestions();
    return;
  }
  acActiveIndex = -1;
  suggestionsEl.innerHTML = '';
  results.forEach(function (code, i) {
    var item = document.createElement('div');
    item.className = 'course-autocomplete__item';
    item.textContent = code;
    item.dataset.index = i;
    item.addEventListener('mousedown', function (e) {
      e.preventDefault();
      selectSuggestion(code);
    });
    suggestionsEl.appendChild(item);
  });
  suggestionsEl.classList.add('open');
}

function closeSuggestions() {
  suggestionsEl.classList.remove('open');
  suggestionsEl.innerHTML = '';
  acActiveIndex = -1;
}

function selectSuggestion(code) {
  courseInput.value = code;
  closeSuggestions();
  courseInput.focus();
}

function navigateSuggestions(direction) {
  var items = suggestionsEl.querySelectorAll('.course-autocomplete__item');
  if (items.length === 0) return;
  acActiveIndex = Math.max(-1, Math.min(items.length - 1, acActiveIndex + direction));
  items.forEach(function (item, i) {
    item.classList.toggle('active', i === acActiveIndex);
  });
}

courseInput.addEventListener('input', function () {
  var val = this.value.trim().toUpperCase();
  this.value = val;
  fetchCourseSuggestions(val);
});

courseInput.addEventListener('blur', function () {
  setTimeout(closeSuggestions, 150);
});

courseInput.addEventListener('keydown', function (e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    navigateSuggestions(1);
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    navigateSuggestions(-1);
  } else if (e.key === 'Enter') {
    e.preventDefault();
    var items = suggestionsEl.querySelectorAll('.course-autocomplete__item');
    if (acActiveIndex >= 0 && items[acActiveIndex]) {
      selectSuggestion(items[acActiveIndex].textContent);
    } else {
      addCourse();
    }
  } else if (e.key === 'Escape') {
    closeSuggestions();
  }
});
```

Remove the old standalone `courseInput.addEventListener('keydown', ...)` block (~line 402-407) since it's now integrated above.

**Step 6: Add autocomplete JS to profile.js**

Add similar autocomplete logic in `static/js/portal/profile.js`, after the `btnAddCourse` event listeners.

The pattern is the same but uses `addCourseInput` instead of `courseInput`, and the suggestions element is `$('course-suggestions')`:

```javascript
/* --- Course autocomplete --- */

var courseSuggestions = document.getElementById('course-suggestions');
var acActiveIndex = -1;
var acDebounceTimer = null;

function fetchCourseSuggestions(query) {
  if (!query || query.length < 1) {
    closeSuggestions();
    return;
  }
  clearTimeout(acDebounceTimer);
  acDebounceTimer = setTimeout(function () {
    fetch('/api/portal/courses/search?q=' + encodeURIComponent(query))
      .then(function (res) { return res.json(); })
      .then(function (results) { renderSuggestions(results); })
      .catch(function () { closeSuggestions(); });
  }, 150);
}

function renderSuggestions(results) {
  if (!results || results.length === 0) {
    closeSuggestions();
    return;
  }
  acActiveIndex = -1;
  courseSuggestions.innerHTML = '';
  results.forEach(function (code, i) {
    var item = document.createElement('div');
    item.className = 'course-autocomplete__item';
    item.textContent = code;
    item.dataset.index = i;
    item.addEventListener('mousedown', function (e) {
      e.preventDefault();
      addCourseInput.value = code;
      closeSuggestions();
      addCourseInput.focus();
    });
    courseSuggestions.appendChild(item);
  });
  courseSuggestions.classList.add('open');
}

function closeSuggestions() {
  courseSuggestions.classList.remove('open');
  courseSuggestions.innerHTML = '';
  acActiveIndex = -1;
}

addCourseInput.addEventListener('input', function () {
  var val = this.value.trim().toUpperCase();
  this.value = val;
  fetchCourseSuggestions(val);
});

addCourseInput.addEventListener('blur', function () {
  setTimeout(closeSuggestions, 150);
});

addCourseInput.addEventListener('keydown', function (e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    var items = courseSuggestions.querySelectorAll('.course-autocomplete__item');
    acActiveIndex = Math.min(items.length - 1, acActiveIndex + 1);
    items.forEach(function (item, i) { item.classList.toggle('active', i === acActiveIndex); });
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    var items2 = courseSuggestions.querySelectorAll('.course-autocomplete__item');
    acActiveIndex = Math.max(-1, acActiveIndex - 1);
    items2.forEach(function (item, i) { item.classList.toggle('active', i === acActiveIndex); });
  } else if (e.key === 'Enter') {
    e.preventDefault();
    var items3 = courseSuggestions.querySelectorAll('.course-autocomplete__item');
    if (acActiveIndex >= 0 && items3[acActiveIndex]) {
      addCourseInput.value = items3[acActiveIndex].textContent;
      closeSuggestions();
    } else {
      btnAddCourse.click();
    }
  } else if (e.key === 'Escape') {
    closeSuggestions();
  }
});
```

Replace the old `addCourseInput.addEventListener('keydown', ...)` block (~line 192-197) since it's now integrated above.

**Step 7: Add autocomplete JS to dashboard settings.js**

Add similar pattern in `static/js/dashboard/settings.js`. Add after `onAddCourse()`:

```javascript
/* --- Course autocomplete --- */

var courseSuggestions = document.getElementById("course-suggestions");
var acActiveIndex = -1;
var acDebounceTimer = null;

function fetchCourseSuggestions(query) {
  if (!query || query.length < 1) {
    closeSuggestions();
    return;
  }
  clearTimeout(acDebounceTimer);
  acDebounceTimer = setTimeout(function () {
    fetch("/api/dashboard/courses/search?q=" + encodeURIComponent(query))
      .then(function (res) { return res.json(); })
      .then(function (results) { renderSuggestions(results); })
      .catch(function () { closeSuggestions(); });
  }, 150);
}

function renderSuggestions(results) {
  if (!results || results.length === 0) {
    closeSuggestions();
    return;
  }
  acActiveIndex = -1;
  courseSuggestions.innerHTML = "";
  results.forEach(function (code, i) {
    var item = document.createElement("div");
    item.className = "course-autocomplete__item";
    item.textContent = code;
    item.dataset.index = i;
    item.addEventListener("mousedown", function (e) {
      e.preventDefault();
      dom.newCourseInput.value = code;
      closeSuggestions();
      dom.newCourseInput.focus();
    });
    courseSuggestions.appendChild(item);
  });
  courseSuggestions.classList.add("open");
}

function closeSuggestions() {
  courseSuggestions.classList.remove("open");
  courseSuggestions.innerHTML = "";
  acActiveIndex = -1;
}

dom.newCourseInput.addEventListener("input", function () {
  var val = this.value.trim().toUpperCase();
  this.value = val;
  fetchCourseSuggestions(val);
});

dom.newCourseInput.addEventListener("blur", function () {
  setTimeout(closeSuggestions, 150);
});
```

Update the existing keydown listener in `bindEvents()` (~line 195-200) to also handle arrow keys and escape:

Replace:
```javascript
dom.newCourseInput.addEventListener("keydown", function (e) {
  if (e.key === "Enter") {
    e.preventDefault();
    onAddCourse();
  }
});
```

With:
```javascript
dom.newCourseInput.addEventListener("keydown", function (e) {
  if (e.key === "ArrowDown") {
    e.preventDefault();
    var items = courseSuggestions.querySelectorAll(".course-autocomplete__item");
    acActiveIndex = Math.min(items.length - 1, acActiveIndex + 1);
    items.forEach(function (item, i) { item.classList.toggle("active", i === acActiveIndex); });
  } else if (e.key === "ArrowUp") {
    e.preventDefault();
    var items2 = courseSuggestions.querySelectorAll(".course-autocomplete__item");
    acActiveIndex = Math.max(-1, acActiveIndex - 1);
    items2.forEach(function (item, i) { item.classList.toggle("active", i === acActiveIndex); });
  } else if (e.key === "Enter") {
    e.preventDefault();
    var items3 = courseSuggestions.querySelectorAll(".course-autocomplete__item");
    if (acActiveIndex >= 0 && items3[acActiveIndex]) {
      dom.newCourseInput.value = items3[acActiveIndex].textContent;
      closeSuggestions();
    } else {
      onAddCourse();
    }
  } else if (e.key === "Escape") {
    closeSuggestions();
  }
});
```

**Step 8: Commit**

```bash
git add static/css/design-system.css templates/portal/enroll.html templates/portal/profile.html templates/dashboard/settings.html static/js/portal/enroll.js static/js/portal/profile.js static/js/dashboard/settings.js
git commit -m "feat: add course code autocomplete with search suggestions"
```

---

## Summary of commits

1. `fix: update favicon to brand teal and remove center dot`
2. `fix: update matric number placeholder to realistic format`
3. `fix: skip details form when re-capturing face for enrolled students`
4. `feat: add animated pose guidance overlay during face capture`
5. `feat: enforce course code format validation (3 letters + 3 digits)`
6. `feat: add course code search API endpoint`
7. `feat: add course code autocomplete with search suggestions`
