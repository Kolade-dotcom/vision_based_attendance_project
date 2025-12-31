/**
 * Smart Vision-Based Attendance System
 * Main JavaScript Module
 */

document.addEventListener("DOMContentLoaded", function () {
  console.log("Smart Attendance System initialized");

  // Initialize based on current page
  if (document.getElementById("start-camera")) {
    initDashboard();
  }

  if (document.getElementById("enroll-form")) {
    initEnrollment();
  }
});

/**
 * Initialize Dashboard Page
 */
function initDashboard() {
  const startCameraBtn = document.getElementById("start-camera");

  if (startCameraBtn) {
    startCameraBtn.addEventListener("click", function () {
      startCameraFeed("camera-feed");
    });
  }

  // Fetch initial statistics
  fetchStatistics();

  // Fetch today's attendance
  fetchTodayAttendance();
}

/**
 * Initialize Enrollment Page
 */
function initEnrollment() {
  const startEnrollCameraBtn = document.getElementById("start-enroll-camera");
  const captureFaceBtn = document.getElementById("capture-face");
  const enrollForm = document.getElementById("enroll-form");

  if (startEnrollCameraBtn) {
    startEnrollCameraBtn.addEventListener("click", function () {
      startCameraFeed("enroll-camera");
      if (captureFaceBtn) {
        captureFaceBtn.disabled = false;
      }
    });
  }

  if (captureFaceBtn) {
    captureFaceBtn.addEventListener("click", function () {
      captureFace();
    });
  }

  if (enrollForm) {
    enrollForm.addEventListener("submit", function (e) {
      e.preventDefault();
      submitEnrollment();
    });
  }

  // Fetch enrolled students
  fetchEnrolledStudents();
}

/**
 * Start camera feed (placeholder implementation)
 */
function startCameraFeed(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // In a real implementation, this would connect to the Flask video stream
  container.innerHTML = `
        <video id="video-${containerId}" autoplay playsinline></video>
        <p style="color: rgba(255,255,255,0.6); margin-top: 10px;">
            Camera active - Connect to /video_feed for live stream
        </p>
    `;

  // Try to access webcam using getUserMedia
  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then(function (stream) {
        const video = document.getElementById(`video-${containerId}`);
        if (video) {
          video.srcObject = stream;
          video.style.width = "100%";
          video.style.height = "auto";
          video.style.borderRadius = "10px";
        }
      })
      .catch(function (err) {
        console.error("Error accessing camera:", err);
        container.innerHTML = `
                    <p style="color: #ff6b6b;">
                        ⚠️ Camera access denied or unavailable
                    </p>
                    <p style="color: rgba(255,255,255,0.6);">
                        Please allow camera access to use this feature
                    </p>
                `;
      });
  }
}

/**
 * Capture face for enrollment
 */
function captureFace() {
  const statusEl = document.getElementById("capture-status");
  const enrollBtn = document.getElementById("enroll-btn");

  // Simulate face capture
  if (statusEl) {
    statusEl.textContent = "✅ Face captured successfully!";
    statusEl.style.color = "var(--success-color)";
  }

  if (enrollBtn) {
    enrollBtn.disabled = false;
  }

  console.log(
    "Face captured - In production, this would send to /api/capture_face"
  );
}

/**
 * Submit enrollment form
 */
function submitEnrollment() {
  const form = document.getElementById("enroll-form");
  const formData = new FormData(form);

  const data = {
    student_id: formData.get("student_id"),
    name: formData.get("name"),
    email: formData.get("email"),
  };

  console.log("Enrolling student:", data);

  // In production, POST to /api/enroll
  // For now, show success message
  alert(`Student ${data.name} enrolled successfully!`);
  form.reset();

  const enrollBtn = document.getElementById("enroll-btn");
  if (enrollBtn) enrollBtn.disabled = true;

  const statusEl = document.getElementById("capture-status");
  if (statusEl) statusEl.textContent = "";
}

/**
 * Fetch today's attendance records
 */
function fetchTodayAttendance() {
  // In production, fetch from /api/attendance/today
  console.log("Fetching today's attendance...");

  // Placeholder data
  const attendance = [];
  updateAttendanceTable(attendance);
}

/**
 * Update attendance table with data
 */
function updateAttendanceTable(records) {
  const tbody = document.getElementById("attendance-tbody");
  if (!tbody) return;

  if (records.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-message">No attendance records yet today</td>
            </tr>
        `;
    return;
  }

  tbody.innerHTML = records
    .map(
      (record) => `
        <tr>
            <td>${record.student_id}</td>
            <td>${record.name}</td>
            <td>${record.time}</td>
            <td><span class="status-${record.status}">${record.status}</span></td>
        </tr>
    `
    )
    .join("");
}

/**
 * Fetch statistics
 */
function fetchStatistics() {
  // In production, fetch from /api/statistics
  console.log("Fetching statistics...");

  // Update UI with placeholder values
  updateStatistic("total-present", 0);
  updateStatistic("total-late", 0);
  updateStatistic("total-students", 0);
}

/**
 * Update a statistic display
 */
function updateStatistic(elementId, value) {
  const el = document.getElementById(elementId);
  if (el) {
    el.textContent = value;
  }
}

/**
 * Fetch enrolled students
 */
function fetchEnrolledStudents() {
  // In production, fetch from /api/students
  console.log("Fetching enrolled students...");

  const students = [];
  updateStudentsTable(students);
}

/**
 * Update students table with data
 */
function updateStudentsTable(students) {
  const tbody = document.getElementById("students-tbody");
  if (!tbody) return;

  if (students.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-message">No students enrolled yet</td>
            </tr>
        `;
    return;
  }

  tbody.innerHTML = students
    .map(
      (student) => `
        <tr>
            <td>${student.student_id}</td>
            <td>${student.name}</td>
            <td>${student.email || "-"}</td>
            <td>${student.enrolled_date}</td>
        </tr>
    `
    )
    .join("");
}
