import { apiClient } from "../api/client.js";
import { escapeHtml, uiHelpers } from "../modules/ui.js";
import { Combobox } from "../combobox.js";

// Module-level state for face capture
let captureStatusInterval = null;
let faceEncodingData = null;

/**
 * Modal Helper Functions
 */
function openModal(modalEl) {
  if (!modalEl) return;
  document.body.classList.add("modal-open");
  modalEl.classList.remove("hidden");

  // Trigger animations
  const backdrop = modalEl.querySelector("[data-modal-backdrop]");
  const content = modalEl.querySelector("[data-modal-content]");

  if (backdrop) {
    backdrop.classList.remove("closing");
    backdrop.classList.add("modal-backdrop");
  }
  if (content) {
    content.classList.remove("closing");
    content.classList.add("modal-content");
  }

  modalEl.dataset.state = "open";
}

function closeModal(modalEl) {
  if (!modalEl) return;

  // Trigger closing animations
  const backdrop = modalEl.querySelector("[data-modal-backdrop]");
  const content = modalEl.querySelector("[data-modal-content]");

  if (backdrop) backdrop.classList.add("closing");
  if (content) content.classList.add("closing");

  modalEl.dataset.state = "closed";

  setTimeout(() => {
    modalEl.classList.add("hidden");
    document.body.classList.remove("modal-open");
  }, 150);
}

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
  fetchPendingCount();
  fetchEnrollmentLinks();

  // Setup Edit/Delete Event Delegation
  const tableBody = document.getElementById("students-tbody");
  if (tableBody) {
    tableBody.addEventListener("click", handleTableActions);
  }

  // Setup Modal Listeners
  setupModalListeners();

  // Setup Enrollment Links Modal
  setupEnrollmentLinksListeners();

  // Setup Status Filter
  const statusFilter = document.getElementById("status-filter");
  if (statusFilter) {
    statusFilter.addEventListener("change", () => {
      fetchEnrolledStudents(statusFilter.value);
    });
  }
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

  // Show loading state
  const originalContent = startBtn.innerHTML;
  startBtn.disabled = true;
  startBtn.innerHTML = `<svg class="animate-spin h-4 w-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Starting...`;

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

    // Reset button state (hidden but ready for next time)
    startBtn.disabled = false;
    startBtn.innerHTML = originalContent;

    // Start polling for status
    captureStatusInterval = setInterval(pollCaptureStatus, 500);
  } catch (error) {
    console.error("Error starting capture:", error);
    if (statusEl) statusEl.textContent = "Error: " + error.message;

    // Restore button on error
    startBtn.disabled = false;
    startBtn.innerHTML = originalContent;
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

      // Show toast instead of status text
      if (window.showToast) {
        showToast(
          "Success",
          "Face capture complete! You can now enroll the student.",
          "success"
        );
      }

      // Hide the status element
      if (statusEl) {
        statusEl.textContent = "";
        statusEl.classList.add("hidden");
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
    statusEl.classList.remove("text-emerald-600", "hidden");
    statusEl.classList.add("text-slate-500");
  }
  if (enrollBtn) enrollBtn.disabled = true;
  if (progressBar) progressBar.style.width = "0%";

  faceEncodingData = null;
  const hiddenInput = document.getElementById("face-encoding-data");
  if (hiddenInput) hiddenInput.value = "";
}

/**
 * Handle Edit/Delete/Approve/Reject Button Clicks
 */
function handleTableActions(e) {
  const editBtn = e.target.closest(".edit-btn");
  const deleteBtn = e.target.closest(".delete-btn");
  const approveBtn = e.target.closest(".approve-btn");
  const rejectBtn = e.target.closest(".reject-btn");

  if (editBtn) {
    const student = {
      id: editBtn.dataset.id,
      name: editBtn.dataset.name,
      level: editBtn.dataset.level,
    };
    openEditModal(student);
  } else if (deleteBtn) {
    openDeleteModal(deleteBtn.dataset.id);
  } else if (approveBtn) {
    approveStudent(approveBtn.dataset.id);
  } else if (rejectBtn) {
    rejectStudent(rejectBtn.dataset.id);
  }
}

/**
 * Approve a pending student
 */
async function approveStudent(studentId) {
  try {
    const response = await fetch(
      `/api/students/${encodeURIComponent(studentId)}/approve`,
      {
        method: "POST",
      }
    );
    const result = await response.json();

    if (result.status === "success") {
      showToast("Success", "Student approved successfully", "success");
      fetchEnrolledStudents(
        document.getElementById("status-filter")?.value || ""
      );
      fetchPendingCount();
    } else {
      showToast("Error", result.error || "Failed to approve student", "error");
    }
  } catch (error) {
    console.error("Approve error:", error);
    showToast("Error", "Failed to approve student", "error");
  }
}

/**
 * Reject a pending student
 */
async function rejectStudent(studentId) {
  const reason = prompt("Enter rejection reason (optional):");

  try {
    const response = await fetch(
      `/api/students/${encodeURIComponent(studentId)}/reject`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason }),
      }
    );
    const result = await response.json();

    if (result.status === "success") {
      showToast("Success", "Student enrollment rejected", "success");
      fetchEnrolledStudents(
        document.getElementById("status-filter")?.value || ""
      );
      fetchPendingCount();
    } else {
      showToast("Error", result.error || "Failed to reject student", "error");
    }
  } catch (error) {
    console.error("Reject error:", error);
    showToast("Error", "Failed to reject student", "error");
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
      closeModal(editModal);
    });

    saveEditBtn.addEventListener("click", saveEditStudent);
  }

  // Delete Modal
  const deleteModal = document.getElementById("delete-modal");
  const closeDeleteBtn = document.getElementById("cancel-delete");
  const confirmDeleteBtn = document.getElementById("confirm-delete");

  if (deleteModal) {
    closeDeleteBtn.addEventListener("click", () => {
      closeModal(deleteModal);
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

  openModal(modal);
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
      closeModal(document.getElementById("edit-modal"));
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
  openModal(modal);
}

async function confirmDeleteStudent() {
  if (!studentToDeleteId) return;

  try {
    const result = await apiClient.deleteStudent(studentToDeleteId);
    if (result.status === "success") {
      showToast("Success", "Student deleted successfully", "success");
      closeModal(document.getElementById("delete-modal"));
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
            ${escapeHtml(c)}
            <button type="button" class="ml-1 rounded-full hover:bg-slate-200 p-0.5 text-slate-500 hover:text-slate-900" onclick="this.parentElement.remove()" data-course="${escapeHtml(c)}">
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
async function fetchEnrolledStudents(statusFilter = "") {
  try {
    const url = statusFilter
      ? `/api/students?status=${statusFilter}`
      : "/api/students";
    const response = await fetch(url);
    const students = await response.json();
    uiHelpers.updateStudentsTable(students);
    // Re-init icons for new rows
    if (window.lucide) {
      lucide.createIcons();
    }
  } catch (error) {
    console.error("Error fetching students:", error);
  }
}

/**
 * Fetch pending count for badge
 */
async function fetchPendingCount() {
  try {
    const response = await fetch("/api/students/pending/count");
    const data = await response.json();
    const badge = document.getElementById("pending-badge");
    const countEl = document.getElementById("pending-count");

    if (data.count > 0) {
      badge?.classList.remove("hidden");
      if (countEl) countEl.textContent = data.count;
    } else {
      badge?.classList.add("hidden");
    }
  } catch (error) {
    console.error("Error fetching pending count:", error);
  }
}

// ============================================================================
// Enrollment Links Management
// ============================================================================

let expiresCombobox;

function setupEnrollmentLinksListeners() {
  // Initialize Expires Combobox
  expiresCombobox = new Combobox({
    containerId: "link-expires-combobox",
    placeholder: "Select duration",
    searchable: false,
    name: "link-expires",
    options: [
      { value: "24", label: "24 hours" },
      { value: "48", label: "48 hours" },
      { value: "72", label: "72 hours (3 days)" },
      { value: "168", label: "1 week" },
    ],
  });
  // Set default to 48 hours
  expiresCombobox.select({ value: "48", label: "48 hours" });
  const createLinkBtn = document.getElementById("create-link-btn");
  const createLinkModal = document.getElementById("create-link-modal");
  const cancelCreateLink = document.getElementById("cancel-create-link");
  const confirmCreateLink = document.getElementById("confirm-create-link");
  const qrModal = document.getElementById("qr-modal");
  const closeQrModal = document.getElementById("close-qr-modal");

  if (createLinkBtn) {
    createLinkBtn.addEventListener("click", () => {
      openModal(createLinkModal);
    });
  }

  if (cancelCreateLink) {
    cancelCreateLink.addEventListener("click", () => {
      closeModal(createLinkModal);
    });
  }

  if (confirmCreateLink) {
    confirmCreateLink.addEventListener("click", createEnrollmentLink);
  }

  if (closeQrModal) {
    closeQrModal.addEventListener("click", () => {
      closeModal(qrModal);
    });
  }

  // Event delegation for links container
  const linksContainer = document.getElementById("enrollment-links-container");
  if (linksContainer) {
    linksContainer.addEventListener("click", handleLinkActions);
  }
}

async function createEnrollmentLink() {
  const description = document.getElementById("link-description")?.value || "";
  const courseCode = document.getElementById("link-course")?.value || null;
  const expiresInput = document.querySelector(
    "#link-expires-combobox input[type=hidden]"
  );
  const expiresHours = parseInt(expiresInput?.value || "48");
  const maxUses = document.getElementById("link-max-uses")?.value || null;

  try {
    const response = await fetch("/api/enrollment-links", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        description,
        course_code: courseCode,
        expires_hours: expiresHours,
        max_uses: maxUses ? parseInt(maxUses) : null,
      }),
    });

    const result = await response.json();

    if (result.status === "success") {
      showToast("Success", "Enrollment link created!", "success");
      closeModal(document.getElementById("create-link-modal"));

      // Clear form
      document.getElementById("link-description").value = "";
      document.getElementById("link-course").value = "";
      document.getElementById("link-max-uses").value = "";

      // Refresh links
      fetchEnrollmentLinks();
    } else {
      showToast("Error", result.error || "Failed to create link", "error");
    }
  } catch (error) {
    console.error("Error creating link:", error);
    showToast("Error", "Failed to create link", "error");
  }
}

async function fetchEnrollmentLinks() {
  try {
    const response = await fetch("/api/enrollment-links");
    const links = await response.json();
    renderEnrollmentLinks(links);
  } catch (error) {
    console.error("Error fetching links:", error);
  }
}

function renderEnrollmentLinks(links) {
  const container = document.getElementById("enrollment-links-container");
  if (!container) return;

  if (!links || links.length === 0) {
    container.innerHTML =
      '<p class="text-sm text-slate-500 text-center py-4">No enrollment links created yet</p>';
    return;
  }

  container.innerHTML = links
    .map((link) => {
      const isActive = link.is_active && new Date(link.expires_at) > new Date();
      const usageText = link.max_uses
        ? `${link.current_uses}/${link.max_uses}`
        : `${link.current_uses} uses`;
      const expiresDate = new Date(link.expires_at).toLocaleDateString();

      return `
      <div class="border border-slate-200 rounded-lg p-4 ${
        isActive ? "" : "opacity-50"
      }">
        <div class="flex items-start justify-between gap-4">
          <div class="flex-1 min-w-0">
            <p class="font-medium text-slate-900 truncate">${
              escapeHtml(link.description) || "Enrollment Link"
            }</p>
            <p class="text-xs text-slate-500 mt-1">
              ${
                link.course_code ? `Course: ${escapeHtml(link.course_code)} • ` : ""
              }${usageText} • Expires: ${expiresDate}
            </p>
          </div>
          <div class="flex items-center gap-2 flex-shrink-0">
            ${
              isActive
                ? `
              <button class="copy-link-btn inline-flex items-center justify-center rounded-md text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 h-8 w-8" data-url="${escapeHtml(link.url)}" title="Copy Link">
                <i data-lucide="copy" class="h-4 w-4"></i>
              </button>
              <button class="qr-link-btn inline-flex items-center justify-center rounded-md text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 h-8 w-8" data-token="${escapeHtml(link.token)}" data-url="${escapeHtml(link.url)}" title="Show QR Code">
                <i data-lucide="qr-code" class="h-4 w-4"></i>
              </button>
              <button class="revoke-link-btn inline-flex items-center justify-center rounded-md text-sm font-medium border border-red-200 bg-white hover:bg-red-50 text-red-600 h-8 w-8" data-id="${escapeHtml(link.id)}" title="Revoke">
                <i data-lucide="x" class="h-4 w-4"></i>
              </button>
            `
                : `
              <span class="text-xs text-slate-400">Inactive</span>
            `
            }
          </div>
        </div>
      </div>
    `;
    })
    .join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function handleLinkActions(e) {
  const copyBtn = e.target.closest(".copy-link-btn");
  const qrBtn = e.target.closest(".qr-link-btn");
  const revokeBtn = e.target.closest(".revoke-link-btn");

  if (copyBtn) {
    copyToClipboard(copyBtn.dataset.url);
  } else if (qrBtn) {
    showQrCode(qrBtn.dataset.token, qrBtn.dataset.url);
  } else if (revokeBtn) {
    revokeLink(revokeBtn.dataset.id);
  }
}

function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      showToast("Copied", "Link copied to clipboard", "success");
    })
    .catch(() => {
      showToast("Error", "Failed to copy link", "error");
    });
}

function showQrCode(token, url) {
  const modal = document.getElementById("qr-modal");
  const img = document.getElementById("qr-code-image");
  const urlEl = document.getElementById("qr-link-url");

  if (img) {
    img.src = `/api/enrollment-links/${token}/qr`;
  }
  if (urlEl) {
    urlEl.textContent = url;
  }

  openModal(modal);
}

async function revokeLink(linkId) {
  // Show revoke confirmation modal
  const revokeModal = document.getElementById("revoke-modal");
  const cancelRevokeBtn = document.getElementById("cancel-revoke");
  const confirmRevokeBtn = document.getElementById("confirm-revoke");

  if (!revokeModal) {
    // Fallback to confirm if modal not found
    if (!confirm("Are you sure you want to revoke this link?")) return;
    await performRevoke(linkId);
    return;
  }

  openModal(revokeModal);

  // Handle cancel
  const handleCancel = () => {
    closeModal(revokeModal);
    cancelRevokeBtn.removeEventListener("click", handleCancel);
    confirmRevokeBtn.removeEventListener("click", handleConfirm);
  };

  // Handle confirm
  const handleConfirm = async () => {
    closeModal(revokeModal);
    cancelRevokeBtn.removeEventListener("click", handleCancel);
    confirmRevokeBtn.removeEventListener("click", handleConfirm);
    await performRevoke(linkId);
  };

  cancelRevokeBtn.addEventListener("click", handleCancel);
  confirmRevokeBtn.addEventListener("click", handleConfirm);

  // Close on backdrop click
  revokeModal.addEventListener(
    "click",
    (e) => {
      if (e.target === revokeModal) {
        handleCancel();
      }
    },
    { once: true }
  );
}

async function performRevoke(linkId) {
  try {
    const response = await fetch(`/api/enrollment-links/${linkId}/revoke`, {
      method: "POST",
    });
    const result = await response.json();

    if (result.status === "success") {
      showToast("Success", "Link revoked", "success");
      fetchEnrollmentLinks();
    } else {
      showToast("Error", result.error || "Failed to revoke link", "error");
    }
  } catch (error) {
    console.error("Error revoking link:", error);
    showToast("Error", "Failed to revoke link", "error");
  }
}
