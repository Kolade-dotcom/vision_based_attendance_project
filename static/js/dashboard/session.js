(function () {
  "use strict";

  // --- State ---
  var state = {
    activeSession: null,
    sessionStartTime: null,
    courses: [],
    selectedCourse: "all",
    attendanceRecords: [],
    knownAttendanceIds: new Set(),
    pollingTimer: null,
    elapsedTimer: null,
    deleteTargetId: null,
  };

  // --- DOM refs ---
  var dom = {
    greeting: document.getElementById("greeting"),
    courseSelector: document.getElementById("course-selector-container"),
    strip: document.getElementById("session-strip"),
    stripInactive: document.getElementById("strip-inactive"),
    stripActive: document.getElementById("strip-active"),
    sessionCourseSelect: document.getElementById("session-course-select"),
    btnStart: document.getElementById("btn-start-session"),
    btnEnd: document.getElementById("btn-end-session"),
    activeCourseCode: document.getElementById("active-course-code"),
    sessionElapsed: document.getElementById("session-elapsed"),
    sessionStudentCount: document.getElementById("session-student-count"),
    cameraFeed: document.getElementById("camera-feed"),
    cameraEmpty: document.getElementById("camera-empty"),
    attendanceTbody: document.getElementById("attendance-tbody"),
    attendanceEmpty: document.getElementById("attendance-empty"),
    statsSkeleton: document.getElementById("stats-skeleton"),
    statsContent: document.getElementById("stats-content"),
    statsEmpty: document.getElementById("stats-empty"),
    statPresent: document.getElementById("stat-present"),
    statLate: document.getElementById("stat-late"),
    statTotal: document.getElementById("stat-total"),
    historyTbody: document.getElementById("history-tbody"),
    historyEmpty: document.getElementById("history-empty"),
    modalEnd: document.getElementById("modal-end-session"),
    btnConfirmEnd: document.getElementById("btn-confirm-end"),
    modalDelete: document.getElementById("modal-delete-session"),
    btnConfirmDelete: document.getElementById("btn-confirm-delete"),
  };

  // --- Helpers ---

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function showToast(message, type) {
    var container = document.getElementById("toast-container");
    if (!container) return;
    var toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "success");
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.classList.add("removing");
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 200);
    }, 3000);
  }

  function formatTime(isoString) {
    if (!isoString) return "-";
    var d = new Date(isoString);
    if (isNaN(d.getTime())) {
      // Try parsing ISO without timezone
      d = new Date(isoString.replace("T", " "));
    }
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function formatDate(isoString) {
    if (!isoString) return "-";
    var d = new Date(isoString);
    if (isNaN(d.getTime())) {
      d = new Date(isoString.replace("T", " "));
    }
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleDateString([], {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  }

  function formatDuration(startIso, endIso) {
    if (!startIso) return "-";
    var start = new Date(startIso);
    var end = endIso ? new Date(endIso) : new Date();
    if (isNaN(start.getTime())) return "-";
    var diffMs = end - start;
    if (diffMs < 0) return "-";
    var totalSec = Math.floor(diffMs / 1000);
    var h = Math.floor(totalSec / 3600);
    var m = Math.floor((totalSec % 3600) / 60);
    if (h > 0) return h + "h " + m + "m";
    return m + "m";
  }

  function formatElapsed(startIso) {
    if (!startIso) return "00:00:00";
    var start = new Date(startIso);
    if (isNaN(start.getTime())) {
      start = new Date(startIso.replace("T", " "));
    }
    if (isNaN(start.getTime())) return "00:00:00";
    var diffMs = Date.now() - start.getTime();
    if (diffMs < 0) diffMs = 0;
    var totalSec = Math.floor(diffMs / 1000);
    var h = Math.floor(totalSec / 3600);
    var m = Math.floor((totalSec % 3600) / 60);
    var s = totalSec % 60;
    return (
      String(h).padStart(2, "0") +
      ":" +
      String(m).padStart(2, "0") +
      ":" +
      String(s).padStart(2, "0")
    );
  }

  function setGreeting() {
    var hour = new Date().getHours();
    var period = "morning";
    if (hour >= 12 && hour < 17) period = "afternoon";
    else if (hour >= 17) period = "evening";
    var el = dom.greeting;
    if (!el) return;
    var name = el.textContent.split(",")[1];
    el.textContent = "Good " + period + "," + (name || " Lecturer");
  }

  function clearSkeletons(container) {
    if (!container) return;
    var skeletons = container.querySelectorAll("[data-skeleton]");
    for (var i = 0; i < skeletons.length; i++) {
      skeletons[i].parentNode.removeChild(skeletons[i]);
    }
  }

  function openModal(id) {
    var modal = document.getElementById(id);
    if (modal) modal.classList.add("is-open");
  }

  function closeModal(id) {
    var modal = document.getElementById(id);
    if (modal) modal.classList.remove("is-open");
  }

  // --- API ---

  function apiFetch(url, options) {
    return fetch(url, options).then(function (res) {
      if (!res.ok) {
        return res.json().then(function (body) {
          throw new Error(body.error || "Request failed");
        });
      }
      var ct = res.headers.get("content-type") || "";
      if (ct.indexOf("application/json") !== -1) {
        return res.json();
      }
      return res;
    });
  }

  // --- Course Selector ---

  function extractCoursesFromHistory(history) {
    var seen = {};
    var courses = [];
    for (var i = 0; i < history.length; i++) {
      var code = history[i].course_code;
      if (code && !seen[code]) {
        seen[code] = true;
        courses.push(code);
      }
    }
    return courses;
  }

  function renderCourseSelector(courses) {
    state.courses = courses;
    var container = dom.courseSelector;
    if (!container) return;
    container.innerHTML = "";

    var allCourses = ["All Courses"].concat(courses);

    if (courses.length <= 3) {
      var pills = document.createElement("div");
      pills.className = "course-pills";
      for (var i = 0; i < allCourses.length; i++) {
        var pill = document.createElement("button");
        pill.type = "button";
        pill.className = "course-pill";
        var val = i === 0 ? "all" : courses[i - 1];
        pill.setAttribute("data-course", val);
        pill.textContent = allCourses[i];
        if (val === state.selectedCourse) pill.classList.add("active");
        pill.addEventListener("click", onCoursePillClick);
        pills.appendChild(pill);
      }
      container.appendChild(pills);
    } else {
      var select = document.createElement("select");
      select.className = "input";
      select.setAttribute("aria-label", "Filter by course");
      for (var j = 0; j < allCourses.length; j++) {
        var opt = document.createElement("option");
        opt.value = j === 0 ? "all" : courses[j - 1];
        opt.textContent = allCourses[j];
        if (opt.value === state.selectedCourse) opt.selected = true;
        select.appendChild(opt);
      }
      select.addEventListener("change", function () {
        state.selectedCourse = this.value;
        loadHistory();
      });
      container.appendChild(select);
    }

    populateSessionCourseSelect(courses);
  }

  function onCoursePillClick(e) {
    var val = e.currentTarget.getAttribute("data-course");
    state.selectedCourse = val;
    var pills = dom.courseSelector.querySelectorAll(".course-pill");
    for (var i = 0; i < pills.length; i++) {
      pills[i].classList.toggle("active", pills[i].getAttribute("data-course") === val);
    }
    loadHistory();
  }

  function populateSessionCourseSelect(courses) {
    var select = dom.sessionCourseSelect;
    if (!select) return;
    select.innerHTML = '<option value="">Select course</option>';
    for (var i = 0; i < courses.length; i++) {
      var opt = document.createElement("option");
      opt.value = courses[i];
      opt.textContent = courses[i];
      select.appendChild(opt);
    }
  }

  // --- Session UI State ---

  function setSessionActive(session) {
    state.activeSession = session;
    state.sessionStartTime = session.start_time;
    state.knownAttendanceIds = new Set();

    dom.strip.classList.add("is-active");
    dom.stripInactive.style.display = "none";
    dom.stripActive.style.display = "flex";
    dom.activeCourseCode.textContent = escapeHtml(session.course_code || "");

    // Camera
    dom.cameraFeed.style.display = "block";
    dom.cameraEmpty.style.display = "none";
    // Force reload of feed
    dom.cameraFeed.src = "/video_feed?" + Date.now();

    // Stats
    dom.statsSkeleton.style.display = "none";
    dom.statsContent.style.display = "block";
    dom.statsEmpty.style.display = "none";

    startElapsedTimer();
    startAttendancePolling();
    loadStats();
  }

  function setSessionInactive() {
    state.activeSession = null;
    state.sessionStartTime = null;

    dom.strip.classList.remove("is-active");
    dom.stripInactive.style.display = "flex";
    dom.stripActive.style.display = "none";

    // Camera
    dom.cameraFeed.style.display = "none";
    dom.cameraEmpty.style.display = "flex";

    // Stats
    dom.statsSkeleton.style.display = "none";
    dom.statsContent.style.display = "none";
    dom.statsEmpty.style.display = "flex";

    // Clear attendance
    clearSkeletons(dom.attendanceTbody);
    dom.attendanceTbody.innerHTML = "";
    dom.attendanceEmpty.style.display = "flex";
    state.attendanceRecords = [];
    state.knownAttendanceIds = new Set();

    stopElapsedTimer();
    stopAttendancePolling();
  }

  // --- Elapsed Timer ---

  function startElapsedTimer() {
    stopElapsedTimer();
    updateElapsed();
    state.elapsedTimer = setInterval(updateElapsed, 1000);
  }

  function stopElapsedTimer() {
    if (state.elapsedTimer) {
      clearInterval(state.elapsedTimer);
      state.elapsedTimer = null;
    }
  }

  function updateElapsed() {
    if (!state.sessionStartTime) return;
    dom.sessionElapsed.textContent = formatElapsed(state.sessionStartTime);
  }

  // --- Attendance Polling ---

  function startAttendancePolling() {
    stopAttendancePolling();
    loadAttendance();
    state.pollingTimer = setInterval(loadAttendance, 3000);
  }

  function stopAttendancePolling() {
    if (state.pollingTimer) {
      clearInterval(state.pollingTimer);
      state.pollingTimer = null;
    }
  }

  function loadAttendance() {
    apiFetch("/api/attendance/today")
      .then(function (records) {
        if (!Array.isArray(records)) return;
        renderAttendance(records);
        updateStudentCount(records.length);
      })
      .catch(function () {
        // Silently fail on polling errors
      });
  }

  function renderAttendance(records) {
    clearSkeletons(dom.attendanceTbody);

    if (records.length === 0) {
      dom.attendanceTbody.innerHTML = "";
      dom.attendanceEmpty.style.display = "flex";
      return;
    }

    dom.attendanceEmpty.style.display = "none";

    // Build a unique key for each record
    var newIds = new Set();
    for (var i = 0; i < records.length; i++) {
      var r = records[i];
      var key = r.student_id + "|" + r.timestamp;
      newIds.add(key);
    }

    // Only re-render if changed
    if (
      newIds.size === state.knownAttendanceIds.size &&
      [...newIds].every(function (id) {
        return state.knownAttendanceIds.has(id);
      })
    ) {
      return;
    }

    var fragment = document.createDocumentFragment();
    for (var j = 0; j < records.length; j++) {
      var rec = records[j];
      var recKey = rec.student_id + "|" + rec.timestamp;
      var isNew = !state.knownAttendanceIds.has(recKey);
      var tr = document.createElement("tr");
      if (isNew) tr.className = "attendance-row-new";

      var pillClass = rec.status === "late" ? "pill-late" : "pill-present";

      tr.innerHTML =
        "<td>" +
        escapeHtml(formatTime(rec.timestamp)) +
        "</td>" +
        '<td class="font-mono">' +
        escapeHtml(rec.student_id || "") +
        "</td>" +
        "<td>" +
        escapeHtml(rec.student_name || "") +
        "</td>" +
        '<td><span class="pill ' +
        pillClass +
        '">' +
        escapeHtml(rec.status || "") +
        "</span></td>";
      fragment.appendChild(tr);
    }

    dom.attendanceTbody.innerHTML = "";
    dom.attendanceTbody.appendChild(fragment);
    state.knownAttendanceIds = newIds;
    state.attendanceRecords = records;
  }

  function updateStudentCount(count) {
    dom.sessionStudentCount.textContent =
      count + " student" + (count !== 1 ? "s" : "");
  }

  // --- Stats ---

  function loadStats() {
    var courseParam =
      state.activeSession && state.activeSession.course_code
        ? "?course=" + encodeURIComponent(state.activeSession.course_code)
        : "";

    apiFetch("/api/statistics" + courseParam)
      .then(function (data) {
        dom.statPresent.textContent = data.present_today || 0;
        dom.statLate.textContent = data.late_today || 0;
        dom.statTotal.textContent = data.total_students || 0;
      })
      .catch(function () {
        dom.statPresent.textContent = "-";
        dom.statLate.textContent = "-";
        dom.statTotal.textContent = "-";
      });
  }

  // --- History ---

  function loadHistory() {
    apiFetch("/api/sessions/history")
      .then(function (history) {
        if (!Array.isArray(history)) return;

        // Extract courses from history for selector
        var courses = extractCoursesFromHistory(history);
        if (
          state.courses.length === 0 ||
          courses.length !== state.courses.length
        ) {
          renderCourseSelector(courses);
        }

        // Filter by selected course
        var filtered = history;
        if (state.selectedCourse && state.selectedCourse !== "all") {
          filtered = history.filter(function (s) {
            return s.course_code === state.selectedCourse;
          });
        }

        renderHistory(filtered);
      })
      .catch(function () {
        clearSkeletons(dom.historyTbody);
        dom.historyTbody.innerHTML = "";
        dom.historyEmpty.style.display = "flex";
      });
  }

  function renderHistory(sessions) {
    clearSkeletons(dom.historyTbody);
    dom.historyTbody.innerHTML = "";

    if (sessions.length === 0) {
      dom.historyEmpty.style.display = "flex";
      return;
    }

    dom.historyEmpty.style.display = "none";

    var fragment = document.createDocumentFragment();
    for (var i = 0; i < sessions.length; i++) {
      var s = sessions[i];
      var tr = document.createElement("tr");
      tr.innerHTML =
        "<td>" +
        escapeHtml(formatDate(s.start_time)) +
        "</td>" +
        '<td><span class="font-mono">' +
        escapeHtml(s.course_code || "") +
        "</span></td>" +
        "<td>" +
        escapeHtml(formatDuration(s.start_time, s.end_time)) +
        "</td>" +
        "<td>-</td>" +
        '<td><button type="button" class="btn btn-ghost btn-sm" data-export="' +
        escapeHtml(String(s.id)) +
        '">Export CSV</button> ' +
        '<button type="button" class="btn btn-ghost btn-sm btn-danger-ghost" data-delete="' +
        escapeHtml(String(s.id)) +
        '">Delete</button></td>';
      fragment.appendChild(tr);
    }

    dom.historyTbody.appendChild(fragment);
  }

  // --- Session Actions ---

  function startSession() {
    var courseCode = dom.sessionCourseSelect.value;
    if (!courseCode) {
      showToast("Select a course first", "warning");
      return;
    }

    dom.btnStart.disabled = true;
    dom.btnStart.textContent = "Starting...";

    apiFetch("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ course_code: courseCode }),
    })
      .then(function (data) {
        showToast("Session started", "success");
        checkActiveSession();
        loadHistory();
      })
      .catch(function (err) {
        showToast(err.message || "Failed to start session", "error");
      })
      .finally(function () {
        dom.btnStart.disabled = false;
        dom.btnStart.textContent = "Start Session";
      });
  }

  function endSession() {
    if (!state.activeSession) return;

    dom.btnConfirmEnd.disabled = true;
    dom.btnConfirmEnd.textContent = "Ending...";

    apiFetch("/api/sessions/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.activeSession.id }),
    })
      .then(function () {
        closeModal("modal-end-session");
        showToast("Session ended", "success");
        setSessionInactive();
        loadHistory();
      })
      .catch(function (err) {
        showToast(err.message || "Failed to end session", "error");
      })
      .finally(function () {
        dom.btnConfirmEnd.disabled = false;
        dom.btnConfirmEnd.textContent = "End Session";
      });
  }

  function deleteSession(sessionId) {
    dom.btnConfirmDelete.disabled = true;
    dom.btnConfirmDelete.textContent = "Deleting...";

    apiFetch("/api/sessions/" + sessionId, { method: "DELETE" })
      .then(function () {
        closeModal("modal-delete-session");
        showToast("Session deleted", "success");
        state.deleteTargetId = null;
        loadHistory();
      })
      .catch(function (err) {
        showToast(err.message || "Failed to delete session", "error");
      })
      .finally(function () {
        dom.btnConfirmDelete.disabled = false;
        dom.btnConfirmDelete.textContent = "Delete";
      });
  }

  function exportSession(sessionId) {
    window.open("/api/sessions/" + sessionId + "/export", "_blank");
  }

  // --- Check Active Session ---

  function checkActiveSession() {
    apiFetch("/api/sessions/active")
      .then(function (data) {
        if (data && data.id) {
          setSessionActive(data);
        } else {
          setSessionInactive();
        }
      })
      .catch(function () {
        setSessionInactive();
      });
  }

  // --- Event Bindings ---

  dom.btnStart.addEventListener("click", startSession);

  dom.btnEnd.addEventListener("click", function () {
    openModal("modal-end-session");
  });

  dom.btnConfirmEnd.addEventListener("click", endSession);

  dom.btnConfirmDelete.addEventListener("click", function () {
    if (state.deleteTargetId) {
      deleteSession(state.deleteTargetId);
    }
  });

  // Dismiss modals via cancel buttons
  document.querySelectorAll("[data-dismiss]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      closeModal(this.getAttribute("data-dismiss"));
    });
  });

  // Dismiss modals via backdrop click
  document.querySelectorAll(".modal-backdrop").forEach(function (backdrop) {
    backdrop.addEventListener("click", function (e) {
      if (e.target === this) {
        this.classList.remove("is-open");
      }
    });
  });

  // Dismiss modals via Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-backdrop.is-open").forEach(function (m) {
        m.classList.remove("is-open");
      });
    }
  });

  // Delegated clicks on history table (export / delete)
  dom.historyTbody.addEventListener("click", function (e) {
    var target = e.target;

    var exportBtn = target.closest("[data-export]");
    if (exportBtn) {
      exportSession(exportBtn.getAttribute("data-export"));
      return;
    }

    var deleteBtn = target.closest("[data-delete]");
    if (deleteBtn) {
      state.deleteTargetId = deleteBtn.getAttribute("data-delete");
      openModal("modal-delete-session");
    }
  });

  // --- Init ---
  setGreeting();
  checkActiveSession();
  loadHistory();
})();
