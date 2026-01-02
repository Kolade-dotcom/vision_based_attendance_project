import { apiClient } from "../api/client.js";
import { uiHelpers } from "../modules/ui.js";
import { Combobox } from "../combobox.js";

/**
 * Initialize Dashboard Page
 */
export async function initDashboard() {
  const startCameraBtn = document.getElementById("start-camera");
  let courseCombobox;

  if (startCameraBtn) {
    startCameraBtn.addEventListener("click", function () {
      console.log("Starting dashboard camera...");
    });
  }

  // Initialize Course Combobox
  courseCombobox = new Combobox({
    containerId: "course-combobox",
    placeholder: "Select Course...",
    searchable: true,
    options: [], // Will be populated
    onSelect: (value) => refreshDashboard(value),
  });

  // Initial Data Fetch
  await populateCourseDropdown(courseCombobox);
  refreshDashboard();
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
