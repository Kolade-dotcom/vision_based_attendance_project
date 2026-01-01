/**
 * UI Helper Module
 * Handles shared UI updates across pages.
 */

export const uiHelpers = {
  /**
   * Update attendance table with data.
   */
  updateAttendanceTable(records) {
    const tbody = document.getElementById("attendance-tbody");
    if (!tbody) return;

    if (!records || records.length === 0) {
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
              <td>${record.student_name}</td>
              <td>${new Date(record.timestamp).toLocaleTimeString()}</td>
              <td><span class="status-${record.status}">${
          record.status
        }</span></td>
          </tr>
      `
      )
      .join("");
  },

  /**
   * Update students table with data.
   */
  updateStudentsTable(students) {
    const tbody = document.getElementById("students-tbody");
    if (!tbody) return;

    if (!students || students.length === 0) {
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
              <td>${new Date(student.created_at).toLocaleDateString()}</td>
          </tr>
      `
      )
      .join("");
  },

  /**
   * Update a statistic display.
   */
  updateStatistic(elementId, value) {
    const el = document.getElementById(elementId);
    if (el) {
      el.textContent = value;
    }
  },
};
