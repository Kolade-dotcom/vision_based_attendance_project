import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";
import { Combobox } from "../combobox.js";

// Module-level state for face capture
let captureStatusInterval = null;
let faceEncodingData = null;

/**
 * Initialize Enrollment Page
 */
export function initEnrollment() {
  const startEnrollCameraBtn = document.getElementById("start-enroll-camera");
  const resetCaptureBtn = document.getElementById("reset-capture");
  const enrollForm = document.getElementById("enroll-form");
  const addCourseBtn = document.getElementById("add-course-btn");

  // Initialize Level Combobox (Non-searchable)
  new Combobox({
    containerId: "level-combobox",
    placeholder: "Select Level",
    searchable: false,
    name: "level", // Important for FormData
    options: [
      { value: "100", label: "100 Level" },
      { value: "200", label: "200 Level" },
      { value: "300", label: "300 Level" },
      { value: "400", label: "400 Level" },
      { value: "500", label: "500 Level" },
    ],
  });

  if (startEnrollCameraBtn) {
    startEnrollCameraBtn.addEventListener("click", startGuidedCapture);
  }

  if (resetCaptureBtn) {
    resetCaptureBtn.addEventListener("click", resetCapture);
  }

  if (enrollForm) {
    enrollForm.addEventListener("submit", function (e) {
      e.preventDefault();
      submitEnrollment();
    });
  }

  if (addCourseBtn) {
    addCourseBtn.addEventListener("click", addCourse);
  }

  // Fetch initial data
  fetchEnrolledStudents();

  // Setup Edit/Delete Event Delegation
  const tableBody = document.getElementById("students-tbody");
  if (tableBody) {
    tableBody.addEventListener("click", handleTableActions);
  }

  // Setup Modal Listeners
  setupModalListeners();
}

/**
 * Start the guided face capture process
 */
async function startGuidedCapture() {
  const cameraPlaceholder = document.getElementById("enroll-camera");
  const videoElement = document.getElementById("enrollment-video");
  const progressContainer = document.getElementById(
    "capture-progress-container"
  );
  const startBtn = document.getElementById("start-enroll-camera");
  const resetBtn = document.getElementById("reset-capture");
  const statusEl = document.getElementById("capture-status");

  try {
    // Call API to start capture session
    const response = await fetch("/api/start_capture", { method: "POST" });
    const result = await response.json();

    if (result.status !== "success") {
      throw new Error(result.error || "Failed to start capture");
    }

    // Update UI
    if (cameraPlaceholder) cameraPlaceholder.classList.add("hidden");
    if (videoElement) {
      videoElement.src = "/enrollment_video_feed?" + Date.now();
      videoElement.classList.remove("hidden");
    }
    if (progressContainer) progressContainer.classList.remove("hidden");
    if (startBtn) startBtn.classList.add("hidden");
    if (resetBtn) resetBtn.classList.remove("hidden");
    if (statusEl) statusEl.textContent = "Follow the on-screen instructions...";

    // Start polling for status
    captureStatusInterval = setInterval(pollCaptureStatus, 500);
  } catch (error) {
    console.error("Error starting capture:", error);
    if (statusEl) statusEl.textContent = "Error: " + error.message;
  }
}

/**
 * Poll capture status and update UI
 */
async function pollCaptureStatus() {
  const instructionEl = document.getElementById("capture-instruction");
  const countEl = document.getElementById("capture-count");
  const progressBar = document.getElementById("capture-progress-bar");
  const feedbackEl = document.getElementById("capture-feedback");
  const statusEl = document.getElementById("capture-status");
  const enrollBtn = document.getElementById("enroll-btn");

  try {
    const response = await fetch("/api/capture_status");
    const status = await response.json();

    // Update UI elements
    if (instructionEl) instructionEl.textContent = status.instruction;
    if (countEl) {
      const totalFrames = status.total_stages * status.frames_needed;
      const captured =
        status.stage_index * status.frames_needed + status.frames_captured;
      countEl.textContent = `${captured}/${totalFrames}`;
    }
    if (progressBar) progressBar.style.width = `${status.progress_percent}%`;

    // Check if complete
    if (status.is_complete) {
      clearInterval(captureStatusInterval);
      captureStatusInterval = null;

      // Fetch face encoding
      await fetchFaceEncoding();

      if (statusEl) {
        statusEl.textContent = "✅ Face capture complete!";
        statusEl.classList.remove("text-slate-500");
        statusEl.classList.add("text-emerald-600");
      }
      if (feedbackEl) feedbackEl.textContent = "";
      if (enrollBtn) enrollBtn.disabled = false;
    }
  } catch (error) {
    console.error("Error polling status:", error);
  }
}

/**
 * Fetch face encoding after capture is complete
 */
async function fetchFaceEncoding() {
  try {
    const response = await fetch("/api/get_face_encoding");
    const result = await response.json();

    if (result.status === "success") {
      faceEncodingData = result.face_encoding;
      // Store in hidden input
      const hiddenInput = document.getElementById("face-encoding-data");
      if (hiddenInput) hiddenInput.value = faceEncodingData;
      console.log(
        `Face encoding captured with ${result.encoding_count} samples`
      );
    }
  } catch (error) {
    console.error("Error fetching face encoding:", error);
  }
}

/**
 * Reset the face capture process
 */
async function resetCapture() {
  // Stop polling
  if (captureStatusInterval) {
    clearInterval(captureStatusInterval);
    captureStatusInterval = null;
  }

  // Reset backend
  await fetch("/api/reset_capture", { method: "POST" });

  // Reset UI
  const cameraPlaceholder = document.getElementById("enroll-camera");
  const videoElement = document.getElementById("enrollment-video");
  const progressContainer = document.getElementById(
    "capture-progress-container"
  );
  const startBtn = document.getElementById("start-enroll-camera");
  const resetBtn = document.getElementById("reset-capture");
  const statusEl = document.getElementById("capture-status");
  const enrollBtn = document.getElementById("enroll-btn");
  const progressBar = document.getElementById("capture-progress-bar");

  if (cameraPlaceholder) cameraPlaceholder.classList.remove("hidden");
  if (videoElement) {
    videoElement.src = "";
    videoElement.classList.add("hidden");
  }
  if (progressContainer) progressContainer.classList.add("hidden");
  if (startBtn) startBtn.classList.remove("hidden");
  if (resetBtn) resetBtn.classList.add("hidden");
  if (statusEl) {
    statusEl.textContent = "";
    statusEl.classList.remove("text-emerald-600");
    statusEl.classList.add("text-slate-500");
  }
  if (enrollBtn) enrollBtn.disabled = true;
  if (progressBar) progressBar.style.width = "0%";

  faceEncodingData = null;
  const hiddenInput = document.getElementById("face-encoding-data");
  if (hiddenInput) hiddenInput.value = "";
}

/**
 * Handle Edit/Delete Button Clicks
 */
function handleTableActions(e) {
  const editBtn = e.target.closest(".edit-btn");
  const deleteBtn = e.target.closest(".delete-btn");

  if (editBtn) {
    const student = {
      id: editBtn.dataset.id,
      name: editBtn.dataset.name,
      level: editBtn.dataset.level,
    };
    openEditModal(student);
  } else if (deleteBtn) {
    openDeleteModal(deleteBtn.dataset.id);
  }
}

/**
 * Modal Logic
 */
let editLevelCombobox;
let studentToDeleteId = null;

function setupModalListeners() {
  // Edit Modal
  const editModal = document.getElementById("edit-modal");
  const closeEditBtn = document.getElementById("cancel-edit");
  const saveEditBtn = document.getElementById("save-edit");

  if (editModal) {
    // Init Combobox inside modal once
    editLevelCombobox = new Combobox({
      containerId: "edit-level-combobox",
      placeholder: "Select Level",
      searchable: false,
      name: "edit-level",
      options: [
        { value: "100", label: "100 Level" },
        { value: "200", label: "200 Level" },
        { value: "300", label: "300 Level" },
        { value: "400", label: "400 Level" },
        { value: "500", label: "500 Level" },
      ],
    });

    closeEditBtn.addEventListener("click", () => {
      editModal.classList.add("hidden");
      editModal.dataset.state = "closed";
    });

    saveEditBtn.addEventListener("click", saveEditStudent);
  }

  // Delete Modal
  const deleteModal = document.getElementById("delete-modal");
  const closeDeleteBtn = document.getElementById("cancel-delete");
  const confirmDeleteBtn = document.getElementById("confirm-delete");

  if (deleteModal) {
    closeDeleteBtn.addEventListener("click", () => {
      deleteModal.classList.add("hidden");
      deleteModal.dataset.state = "closed";
    });

    confirmDeleteBtn.addEventListener("click", confirmDeleteStudent);
  }
}

function openEditModal(student) {
  const modal = document.getElementById("edit-modal");
  document.getElementById("original-student-id").value = student.id;
  document.getElementById("edit-student-id").value = student.id;
  document.getElementById("edit-name").value = student.name;

  // Set combobox value
  if (editLevelCombobox && student.level) {
    // Find option that matches level
    const option = editLevelCombobox.options.find(
      (opt) => opt.value === student.level
    );
    if (option) {
      editLevelCombobox.select(option);
    } else {
      editLevelCombobox.reset();
    }
  }

  modal.classList.remove("hidden");
  modal.dataset.state = "open";
}

async function saveEditStudent() {
  const originalId = document.getElementById("original-student-id").value;
  const newId = document.getElementById("edit-student-id").value;
  const name = document.getElementById("edit-name").value;
  const levelInput = document.querySelector(
    "#edit-level-combobox input[type=hidden]"
  );
  const level = levelInput ? levelInput.value : "";

  try {
    const result = await apiClient.updateStudent(originalId, {
      student_id: newId,
      name,
      level,
    });
    if (result.status === "success") {
      showToast("Success", "Student updated successfully", "success");
      document.getElementById("edit-modal").classList.add("hidden");
      fetchEnrolledStudents(); // Refresh table
    } else {
      showToast("Error", result.error || "Update failed", "error");
    }
  } catch (error) {
    console.error("Update error:", error);
    showToast("Error", "Failed to update student", "error");
  }
}

function openDeleteModal(studentId) {
  studentToDeleteId = studentId;
  const modal = document.getElementById("delete-modal");
  modal.classList.remove("hidden");
  modal.dataset.state = "open";
}

async function confirmDeleteStudent() {
  if (!studentToDeleteId) return;

  try {
    const result = await apiClient.deleteStudent(studentToDeleteId);
    if (result.status === "success") {
      showToast("Success", "Student deleted successfully", "success");
      document.getElementById("delete-modal").classList.add("hidden");
      fetchEnrolledStudents(); // Refresh table
    } else {
      showToast("Error", result.error || "Delete failed", "error");
    }
  } catch (error) {
    console.error("Delete error:", error);
    showToast("Error", "Failed to delete student", "error");
  }
}

/**
 * Manage Courses List
 */
let courses = [];

function addCourse() {
  const input = document.getElementById("course-input");
  const courseCode = input.value.trim().toUpperCase();

  if (courseCode && !courses.includes(courseCode)) {
    courses.push(courseCode);
    renderCourses();
    input.value = "";
  }
}

function removeCourse(courseCode) {
  courses = courses.filter((c) => c !== courseCode);
  renderCourses();
}

function renderCourses() {
  const list = document.getElementById("course-list");
  const hiddenInput = document.getElementById("courses-data");

  list.innerHTML = courses
    .map(
      (c) => `
        <span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-900 animate-in fade-in zoom-in duration-200">
            ${c}
            <button type="button" class="ml-1 rounded-full hover:bg-slate-200 p-0.5 text-slate-500 hover:text-slate-900" onclick="this.parentElement.remove()" data-course="${c}">
                <i data-lucide="x" class="h-3 w-3"></i>
            </button>
        </span>
    `
    )
    .join("");

  // Add event listeners to remove buttons individually to avoid inline onclick issues with modules
  list.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => removeCourse(btn.dataset.course);
  });

  lucide.createIcons();
  hiddenInput.value = JSON.stringify(courses);
}

/**
 * Submit enrollment form
 */
async function submitEnrollment() {
  const form = document.getElementById("enroll-form");
  const formData = new FormData(form);

  const data = {
    student_id: formData.get("student_id"),
    name: formData.get("name"),
    email: formData.get("email"),
    level: formData.get("level"),
    courses: JSON.parse(formData.get("courses") || "[]"),
    face_encoding: faceEncodingData || null,
  };

  try {
    const result = await apiClient.enrollStudent(data);

    if (result.status === "success") {
      showToast(
        "Success",
        `Student ${data.name} enrolled successfully!`,
        "success"
      );
      form.reset();
      courses = [];
      renderCourses();

      const enrollBtn = document.getElementById("enroll-btn");
      if (enrollBtn) enrollBtn.disabled = true;

      const statusEl = document.getElementById("capture-status");
      if (statusEl) statusEl.textContent = "";

      // Refresh the list
      fetchEnrolledStudents();

      // Reset face capture state
      resetCapture();

      // Reset level combobox
      const levelHidden = document.querySelector(
        "#level-combobox input[type=hidden]"
      );
      if (levelHidden) levelHidden.value = "";
    } else {
      showToast(
        "Error",
        `Enrollment failed: ${result.error || "Unknown error"}`,
        "error"
      );
    }
  } catch (error) {
    console.error("Error submitting enrollment:", error);
  }
}

/**
 * Fetch all enrolled students
 */
async function fetchEnrolledStudents() {
  try {
    const students = await apiClient.getStudents();
    uiHelpers.updateStudentsTable(students);
    // Re-init icons for new rows
    if (window.lucide) {
      lucide.createIcons();
    }
  } catch (error) {
    console.error("Error fetching students:", error);
  }
}
