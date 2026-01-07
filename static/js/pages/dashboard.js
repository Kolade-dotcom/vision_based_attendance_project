import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";
import { Combobox } from "../combobox.js";

/**
 * Initialize Dashboard Page
 */
export async function initDashboard() {
  console.log("Initializing Dashboard...");
  try {
    const startCameraBtn = document.getElementById("start-camera");
    const startSessionBtn = document.getElementById("start-session-btn");
    const endSessionBtn = document.getElementById("end-session-btn");
    let courseCombobox;
    let sessionTimerInterval;

    if (startSessionBtn) {
      startSessionBtn.addEventListener("click", () =>
        startSession(courseCombobox)
      );
    }

    // Global references for camera management
    window.dashboardState = {
      isCameraRunning: false,
    };

    if (endSessionBtn) {
      endSessionBtn.addEventListener("click", () => endSession());
    }

    // Initialize Course Combobox
    console.log("Initializing Combobox...");
    courseCombobox = new Combobox({
      containerId: "course-combobox",
      placeholder: "Select Course...",
      searchable: true,
      options: [], // Will be populated
      onSelect: (value) => {
        refreshDashboard(value);
        validateStartSession();
      },
    });

    // Initial validation check
    validateStartSession();

    // Initial Data Fetch
    await populateCourseDropdown(courseCombobox);
    await checkActiveSession();
    loadSessionHistory();
    refreshDashboard();
    console.log("Dashboard Initialized successfully");
  } catch (error) {
    console.error("Dashboard Initialization Failed:", error);
    if (window.showToast)
      window.showToast(
        "System Error",
        "Failed to load dashboard components.",
        "error"
      );
  }
}

/**
 * Refresh dashboard data based on filters
 */
function refreshDashboard(courseValue) {
  // Use passed value or try to find it (if triggered elsewhere)
  let course = courseValue || "";

  // If function called without args (initial load), try to get value from combobox hidden input if it exists
  if (courseValue === undefined) {
    const hiddenInput = document.querySelector(
      "#course-combobox input[type=hidden]"
    );
    if (hiddenInput) course = hiddenInput.value;
  }

  fetchStatistics(course);
  fetchTodayAttendance(course);
}

/**
 * Fetch and populate course dropdown
 * Uses students data to find unique courses
 */
async function populateCourseDropdown(comboboxInstance) {
  try {
    const students = await apiClient.getStudents();
    const courses = new Set();

    students.forEach((s) => {
      if (s.courses && Array.isArray(s.courses)) {
        s.courses.forEach((c) => courses.add(c));
      }
    });

    const options = Array.from(courses)
      .sort()
      .map((code) => ({ value: code, label: code })); // Map to {value, label}

    comboboxInstance.setOptions(options);
  } catch (error) {
    console.error("Error populating courses:", error);
  }
}

/**
 * Fetch today's attendance records
 */
async function fetchTodayAttendance(course) {
  try {
    const params = new URLSearchParams();
    if (course) params.append("course", course);

    const queryString = params.toString();
    const url = queryString
      ? `/api/attendance/today?${queryString}`
      : "/api/attendance/today";

    const response = await fetch(url);
    const attendance = await response.json();
    uiHelpers.updateAttendanceTable(attendance);
  } catch (error) {
    console.error("Error fetching attendance:", error);
  }
}

/**
 * Fetch system statistics
 */
async function fetchStatistics(course) {
  try {
    const params = new URLSearchParams();
    if (course) params.append("course", course);

    const queryString = params.toString();
    const url = queryString
      ? `/api/statistics?${queryString}`
      : "/api/statistics";

    const response = await fetch(url);
    const stats = await response.json();

    uiHelpers.updateStatistic("total-present", stats.present_today);
    uiHelpers.updateStatistic("total-late", stats.late_today);
    uiHelpers.updateStatistic("total-students", stats.total_students);
  } catch (error) {
    console.error("Error fetching statistics:", error);
  }
}

// --- Session Management ---

function validateStartSession() {
  const startBtn = document.getElementById("start-session-btn");
  const hiddenInput = document.querySelector(
    "#course-combobox input[type=hidden]"
  );

  const courseSelected = hiddenInput && hiddenInput.value;

  if (startBtn) {
    if (courseSelected) {
      startBtn.disabled = false;
      startBtn.classList.remove("opacity-50", "pointer-events-none");
    } else {
      startBtn.disabled = true;
      startBtn.classList.add("opacity-50", "pointer-events-none");
    }
  }
}

async function checkActiveSession() {
  try {
    // Check if there is any active session globally (or we could filter by selected course if we enforced course selection first)
    // For now, let's just check global active or try to get it.
    // If the API supports filtering by course, we might need to know the course first.
    // Assuming single global active session for the lecturer context or per-course.
    // Let's call basic active endpoint.
    const response = await fetch("/api/sessions/active");
    const data = await response.json();

    if (response.ok && data.id) {
      updateSessionUI(data);
      startCamera(); // Auto-start camera if session is active
    } else {
      resetSessionUI();
    }
  } catch (e) {
    console.error("Error checking active session", e);
  }
}

async function startSession(courseCombobox) {
  const startBtn = document.getElementById("start-session-btn");
  const hiddenInput = document.querySelector(
    "#course-combobox input[type=hidden]"
  );
  const courseCode = hiddenInput ? hiddenInput.value : null;

  if (!courseCode) {
    showToast("Input Required", "Please select a course first.", "error");
    return;
  }

  // Show loading state
  const originalContent = startBtn.innerHTML;
  startBtn.disabled = true;
  startBtn.innerHTML = `<svg class="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Starting...`;

  try {
    const response = await fetch("/api/sessions/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        course_code: courseCode,
      }),
    });

    const result = await response.json();
    if (response.ok) {
      // Reset button before UI update (in case updateSessionUI hides the button)
      startBtn.disabled = false;
      startBtn.innerHTML = originalContent;

      updateSessionUI(result); // result might need to look like full session object or we re-fetch
      checkActiveSession(); // Re-fetch to be sure
      loadSessionHistory();
      startCamera();
      showToast(
        "Session Started",
        `Monitoring attendance for ${result.course_code}`,
        "success"
      );
    } else {
      showToast("Error", "Error starting session: " + result.error, "error");
      // Restore button on error
      startBtn.disabled = false;
      startBtn.innerHTML = originalContent;
    }
  } catch (e) {
    console.error(e);
    showToast("Error", "Failed to start session", "error");
    // Restore button on error
    startBtn.disabled = false;
    startBtn.innerHTML = originalContent;
  }
}

async function endSession() {
  const endBtn = document.getElementById("end-session-btn");
  const sessionId = endBtn.dataset.sessionId;

  if (!sessionId) return;

  // Show Modal
  const modal = document.getElementById("end-session-modal");
  const backdrop = document.getElementById("modal-backdrop");
  const panel = document.getElementById("modal-panel");
  const confirmBtn = document.getElementById("confirm-end-session");
  const cancelBtn = document.getElementById("cancel-end-session");

  if (!modal) return;

  // Open Modal logic
  modal.classList.remove("hidden");
  // Animation delay
  requestAnimationFrame(() => {
    backdrop.dataset.state = "open";
    panel.dataset.state = "open";
  });

  // Handle Confirm
  const handleConfirm = async () => {
    try {
      const response = await fetch("/api/sessions/end", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });

      if (response.ok) {
        resetSessionUI();
        loadSessionHistory();
        stopCamera();
        showToast("Session Ended", "Attendance session closed.", "default");
        closeModal();
      } else {
        const data = await response.json();
        showToast(
          "Error",
          "Error ending session: " + (data.error || "Unknown error"),
          "error"
        );
        closeModal(); // Optional: keep open on error? No, better to close.
      }
    } catch (e) {
      console.error(e);
      showToast("Error", "Failed to process request", "error");
      closeModal();
    }
  };

  // Handle Close
  const closeModal = () => {
    backdrop.dataset.state = "closed";
    panel.dataset.state = "closed";
    setTimeout(() => {
      modal.classList.add("hidden");
      // cleanup listeners to avoid duplicates if opened again without reload (though wrapper approach avoids this usually, let's safe guard)
      confirmBtn.removeEventListener("click", onConfirmClick);
      cancelBtn.removeEventListener("click", onCancelClick);
    }, 200);
  };

  // Event Listeners (One-time wrapper)
  const onConfirmClick = () => handleConfirm();
  const onCancelClick = () => closeModal();

  confirmBtn.onclick = onConfirmClick; // Simple assignment to overwrite previous if any
  cancelBtn.onclick = onCancelClick;
}

let timerInterval;

function startCamera() {
  if (window.dashboardState.isCameraRunning) return;

  const feedContainer = document.getElementById("camera-feed");
  const placeholder = document.getElementById("camera-placeholder");

  if (placeholder) placeholder.classList.add("hidden");

  // Check if image already exists
  let img = feedContainer.querySelector("img");
  if (!img) {
    img = document.createElement("img");
    img.src = "/video_feed"; // Assuming this route exists or will be created
    img.className = "w-full h-full object-cover rounded-lg";
    img.alt = "Live Camera Feed";
    feedContainer.appendChild(img);
  } else {
    img.classList.remove("hidden");
    img.src = "/video_feed?t=" + new Date().getTime(); // Refresh src to restart stream
  }

  window.dashboardState.isCameraRunning = true;
}

function stopCamera() {
  const feedContainer = document.getElementById("camera-feed");
  const placeholder = document.getElementById("camera-placeholder");

  const img = feedContainer.querySelector("img");
  if (img) {
    // Stop stream by removing src or removing element. Removing element is cleaner for MJPEG.
    img.remove();
    // Or img.src = ""; img.classList.add("hidden");
  }

  if (placeholder) placeholder.classList.remove("hidden");
  window.dashboardState.isCameraRunning = false;
}

function updateSessionUI(session) {
  // Show Session Overlay
  const overlay = document.getElementById("session-overlay");
  const activeSessionInfo = document.getElementById("active-session-info");
  const activeCard = document.getElementById("active-session-card"); // Check if this still exists (we removed it from HTML but check for safety)

  if (overlay) {
    overlay.classList.remove("hidden");
    // Small delay to allow display block to apply before opacity transition
    requestAnimationFrame(() => {
      overlay.dataset.state = "visible";
    });

    activeSessionInfo.textContent = `${session.course_code}`; // Simplified text

    const sessionCard = document.getElementById("active-session-card");
    if (sessionCard)
      sessionCard.dataset.sessionId = session.id || session.session_id;

    // Store session ID on overlay end button or global
    const endBtn = document.getElementById("end-session-btn");
    if (endBtn) endBtn.dataset.sessionId = session.id || session.session_id;
  }

  // Previous UI code (can be removed or adapted if we fully switched)
  if (activeCard) activeCard.classList.add("hidden"); // Ensure old card is hidden if it exists

  // Force dashboard to show this session's context and start polling
  startAttendancePolling(session.course_code);

  // Start Timer - use current time as start for accurate display
  // (The DB start_time may be slightly earlier due to camera initialization delay)
  if (timerInterval) clearInterval(timerInterval);
  const startTime = Date.now(); // Use current time when UI updates, not DB time

  timerInterval = setInterval(() => {
    const now = Date.now();
    const diff = now - startTime;

    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((diff % (1000 * 60)) / 1000);

    const timerDisplay = document.getElementById("session-timer");
    if (timerDisplay) {
      timerDisplay.textContent = `${String(hours).padStart(2, "0")}:${String(
        minutes
      ).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    }
  }, 1000);
}

let attendancePollingInterval;

function startAttendancePolling(courseCode) {
  if (attendancePollingInterval) clearInterval(attendancePollingInterval);
  // Initial fetch
  refreshDashboard(courseCode);
  // Poll every 5 seconds
  attendancePollingInterval = setInterval(() => {
    fetchTodayAttendance(courseCode);
    fetchStatistics(courseCode);
  }, 5000);
}

function stopAttendancePolling() {
  if (attendancePollingInterval) {
    clearInterval(attendancePollingInterval);
    attendancePollingInterval = null;
  }
}

function resetSessionUI() {
  const overlay = document.getElementById("session-overlay");
  if (overlay) {
    overlay.dataset.state = "closed";
    setTimeout(() => {
      overlay.classList.add("hidden");
    }, 300); // Wait for transition
  }

  if (timerInterval) clearInterval(timerInterval);

  stopAttendancePolling(); // Stop polling when UI resets

  const timerDisplay = document.getElementById("session-timer");
  if (timerDisplay) timerDisplay.textContent = "00:00:00";
}

async function loadSessionHistory() {
  try {
    const response = await fetch("/api/sessions/history");
    const history = await response.json();

    const tbody = document.getElementById("session-history-tbody");
    tbody.innerHTML = "";

    if (history.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="h-24 text-center align-middle text-slate-500">No past sessions found</td></tr>';
      return;
    }

    history.forEach((session) => {
      const tr = document.createElement("tr");
      tr.className = "border-b transition-colors hover:bg-slate-100/50";

      const start = new Date(session.start_time).toLocaleString();
      const end = session.end_time
        ? new Date(session.end_time).toLocaleString()
        : "Active";

      tr.innerHTML = `
                <td class="p-4 align-middle">${session.course_code}</td>
                <td class="p-4 align-middle">${start}</td>
                <td class="p-4 align-middle">${end}</td>
                <td class="p-4 align-middle">
                    <div class="flex gap-2">
                        <button onclick="viewSessionAttendance(${session.id}, '${session.course_code}')" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 border border-slate-200 bg-white hover:bg-slate-100 h-9 px-3">
                            <i data-lucide="eye" class="h-4 w-4 mr-1"></i> View
                        </button>
                        <a href="/api/sessions/${session.id}/export" target="_blank" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 border border-slate-200 bg-white hover:bg-slate-100 h-9 px-3">
                            <i data-lucide="download" class="h-4 w-4 mr-1"></i> Export
                        </a>
                        <button onclick="confirmDeleteSession(${session.id}, '${session.course_code}')" class="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 border border-red-200 bg-white hover:bg-red-50 text-red-600 h-9 px-3">
                            <i data-lucide="trash-2" class="h-4 w-4 mr-1"></i> Delete
                        </button>
                    </div>
                </td>
            `;
      tbody.appendChild(tr);
    });

    // Re-initialize Lucide icons for dynamically added content
    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error("Error loading history", e);
  }
}

// --- View Past Session Attendance (Global Function for onclick) ---
window.viewSessionAttendance = async function (sessionId, courseCode) {
  try {
    const response = await fetch(`/api/sessions/${sessionId}/attendance`);
    const records = await response.json();

    const modal = document.getElementById("view-attendance-modal");
    const backdrop = document.getElementById("view-modal-backdrop");
    const panel = document.getElementById("view-modal-panel");
    const titleEl = document.getElementById("view-modal-title");
    const tbody = document.getElementById("view-attendance-tbody");

    if (!modal) {
      console.error("View Attendance Modal not found in DOM");
      return;
    }

    titleEl.textContent = `Attendance for ${courseCode}`;
    tbody.innerHTML = "";

    if (records.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="h-24 text-center align-middle text-slate-500">No attendance records for this session</td></tr>';
    } else {
      records.forEach((r) => {
        const tr = document.createElement("tr");
        tr.className = "border-b transition-colors hover:bg-slate-100/50";
        tr.innerHTML = `
          <td class="p-4 align-middle">${r.student_id}</td>
          <td class="p-4 align-middle">${r.student_name}</td>
          <td class="p-4 align-middle">${new Date(
            r.timestamp
          ).toLocaleString()}</td>
          <td class="p-4 align-middle"><span class="inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${
            r.status === "present"
              ? "bg-green-50 text-green-700"
              : "bg-yellow-50 text-yellow-700"
          }">${r.status}</span></td>
        `;
        tbody.appendChild(tr);
      });
    }

    // Open Modal
    modal.classList.remove("hidden");
    requestAnimationFrame(() => {
      backdrop.dataset.state = "open";
      panel.dataset.state = "open";
    });

    // Re-initialize Lucide icons for dynamically added content
    if (window.lucide) lucide.createIcons();
  } catch (e) {
    console.error("Error fetching session attendance", e);
    if (window.showToast)
      showToast("Error", "Failed to load attendance records", "error");
  }
};

window.closeViewAttendanceModal = function () {
  const modal = document.getElementById("view-attendance-modal");
  const backdrop = document.getElementById("view-modal-backdrop");
  const panel = document.getElementById("view-modal-panel");

  backdrop.dataset.state = "closed";
  panel.dataset.state = "closed";
  setTimeout(() => modal.classList.add("hidden"), 200);
};

// --- Delete Session ---
let pendingDeleteSessionId = null;

window.confirmDeleteSession = function (sessionId, courseCode) {
  pendingDeleteSessionId = sessionId;

  const modal = document.getElementById("delete-session-modal");
  const backdrop = document.getElementById("delete-modal-backdrop");
  const panel = document.getElementById("delete-modal-panel");
  const courseEl = document.getElementById("delete-session-course");

  if (!modal) {
    console.error("Delete Session Modal not found");
    return;
  }

  courseEl.textContent = courseCode;

  modal.classList.remove("hidden");
  requestAnimationFrame(() => {
    backdrop.dataset.state = "open";
    panel.dataset.state = "open";
  });
};

window.closeDeleteModal = function () {
  const modal = document.getElementById("delete-session-modal");
  const backdrop = document.getElementById("delete-modal-backdrop");
  const panel = document.getElementById("delete-modal-panel");

  backdrop.dataset.state = "closed";
  panel.dataset.state = "closed";
  setTimeout(() => {
    modal.classList.add("hidden");
    pendingDeleteSessionId = null;
  }, 200);
};

window.executeDeleteSession = async function () {
  if (!pendingDeleteSessionId) return;

  try {
    const response = await fetch(`/api/sessions/${pendingDeleteSessionId}`, {
      method: "DELETE",
    });

    if (response.ok) {
      closeDeleteModal();
      loadSessionHistory();
      if (window.showToast)
        showToast("Deleted", "Session has been removed", "default");
    } else {
      const data = await response.json();
      if (window.showToast)
        showToast("Error", data.error || "Failed to delete session", "error");
    }
  } catch (e) {
    console.error("Error deleting session", e);
    if (window.showToast)
      showToast("Error", "Failed to delete session", "error");
  }
};
