import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";

/**
 * Initialize Enrollment Page
 */
export function initEnrollment() {
  const startEnrollCameraBtn = document.getElementById("start-enroll-camera");
  const captureFaceBtn = document.getElementById("capture-face");
  const enrollForm = document.getElementById("enroll-form");
  const addCourseBtn = document.getElementById("add-course-btn");

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
}

/**
 * Capture face for enrollment (Simulated)
 */
function captureFace() {
  const statusEl = document.getElementById("capture-status");
  const enrollBtn = document.getElementById("enroll-btn");

  if (statusEl) {
    statusEl.textContent = "✅ Face captured successfully!";
    statusEl.style.color = "var(--success-color)";
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
        <span class="course-tag">
            ${c}
            <button type="button" onclick="this.parentElement.remove()" data-course="${c}">&times;</button>
        </span>
    `
    )
    .join("");

  // Add event listeners to remove buttons individually to avoid inline onclick issues with modules
  list.querySelectorAll("button").forEach((btn) => {
    btn.onclick = () => removeCourse(btn.dataset.course);
  });

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
      alert(`Student ${data.name} enrolled successfully!`);
      form.reset();
      courses = [];
      renderCourses();

      const enrollBtn = document.getElementById("enroll-btn");
      if (enrollBtn) enrollBtn.disabled = true;

      const statusEl = document.getElementById("capture-status");
      if (statusEl) statusEl.textContent = "";

      // Refresh the list
      fetchEnrolledStudents();
    } else {
      alert(`Enrollment failed: ${result.error || "Unknown error"}`);
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
  } catch (error) {
    console.error("Error fetching students:", error);
  }
}
