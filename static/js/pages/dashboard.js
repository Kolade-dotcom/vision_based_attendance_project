import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";

/**
 * Initialize Dashboard Page
 */
export async function initDashboard() {
  const startCameraBtn = document.getElementById("start-camera");
  const levelSelect = document.getElementById("filter-level");
  const courseSelect = document.getElementById("filter-course");

  if (startCameraBtn) {
    startCameraBtn.addEventListener("click", function () {
      console.log("Starting dashboard camera...");
    });
  }

  // Event listeners for filters
  if (levelSelect) levelSelect.addEventListener("change", refreshDashboard);
  if (courseSelect) courseSelect.addEventListener("change", refreshDashboard);

  // Initial Data Fetch
  await populateCourseDropdown();
  refreshDashboard();
}

/**
 * Refresh dashboard data based on filters
 */
function refreshDashboard() {
  const level = document.getElementById("filter-level")?.value || "";
  const course = document.getElementById("filter-course")?.value || "";

  fetchStatistics(level, course);
  fetchTodayAttendance(level, course);
}

/**
 * Fetch and populate course dropdown
 * Uses students data to find unique courses
 */
async function populateCourseDropdown() {
  const select = document.getElementById("filter-course");
  if (!select) return;

  try {
    const students = await apiClient.getStudents();
    const courses = new Set();

    students.forEach((s) => {
      if (s.courses && Array.isArray(s.courses)) {
        s.courses.forEach((c) => courses.add(c));
      }
    });

    // Sort and append options
    Array.from(courses)
      .sort()
      .forEach((code) => {
        const option = document.createElement("option");
        option.value = code;
        option.textContent = code;
        select.appendChild(option);
      });
  } catch (error) {
    console.error("Error populating courses:", error);
  }
}

/**
 * Fetch today's attendance records
 */
async function fetchTodayAttendance(level, course) {
  try {
    // Construct query string manually or via URLSearchParams
    const params = new URLSearchParams();
    if (level) params.append("level", level);
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
async function fetchStatistics(level, course) {
  try {
    const params = new URLSearchParams();
    if (level) params.append("level", level);
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
