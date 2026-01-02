import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";
import { Combobox } from "../combobox.js";

/**
 * Initialize Enrollment Page
 */
export function initEnrollment() {
  const startEnrollCameraBtn = document.getElementById("start-enroll-camera");
  const captureFaceBtn = document.getElementById("capture-face");
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
    startEnrollCameraBtn.addEventListener("click", function () {
      console.log("Starting enrollment camera...");
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
 * Capture face for enrollment (Simulated)
 */
function captureFace() {
  const statusEl = document.getElementById("capture-status");
  const enrollBtn = document.getElementById("enroll-btn");

  if (statusEl) {
    statusEl.textContent = "✅ Face captured successfully!";
    // statusEl.style.color = "var(--success-color)"; // Handled by Tailwind classes if needed or valid default
  }

  if (enrollBtn) {
    enrollBtn.disabled = false;
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
      // Reset level combobox
      // Note: To fully reset combobox we might need to expose a reset method or re-init,
      // but for now form reset clears native inputs, combobox hidden input needs manual clear if not re-inited.
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
