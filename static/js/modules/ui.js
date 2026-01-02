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
                    <td colspan="4" class="h-24 text-center align-middle text-slate-500">No attendance records yet today</td>
                </tr>
            `;
      return;
    }

    tbody.innerHTML = records
      .map(
        (record) => `
          <tr class="border-b transition-colors hover:bg-slate-100/50 data-[state=selected]:bg-slate-100">
              <td class="p-4 align-middle">${record.student_id}</td>
              <td class="p-4 align-middle font-medium text-slate-900">${
                record.student_name
              }</td>
              <td class="p-4 align-middle">${new Date(
                record.timestamp
              ).toLocaleTimeString()}</td>
              <td class="p-4 align-middle">
                ${
                  record.status === "present"
                    ? `<span class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">Present</span>`
                    : `<span class="inline-flex items-center rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20">${record.status}</span>`
                }
              </td>
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
                  <td colspan="4" class="h-24 text-center align-middle text-slate-500">No students enrolled yet</td>
              </tr>
          `;
      return;
    }

    tbody.innerHTML = students
      .map(
        (student) => `
          <tr class="border-b transition-colors hover:bg-slate-100/50 data-[state=selected]:bg-slate-100">
              <td class="p-4 align-middle">${student.student_id}</td>
              <td class="p-4 align-middle font-medium text-slate-900">${
                student.name
              }</td>
              <td class="p-4 align-middle">${student.level || "-"}</td>
              <td class="p-4 align-middle">${new Date(
                student.created_at
              ).toLocaleDateString()}</td>
              <td class="p-4 align-middle">
                <div class="flex items-center gap-2">
                    <button class="edit-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-slate-100 hover:text-slate-900 h-8 w-8" data-id="${
                      student.student_id
                    }" data-name="${student.name}" data-level="${
          student.level || ""
        }">
                        <i data-lucide="pencil" class="h-4 w-4"></i>
                        <span class="sr-only">Edit</span>
                    </button>
                    <button class="delete-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-red-100 hover:text-red-900 h-8 w-8 text-red-600" data-id="${
                      student.student_id
                    }">
                        <i data-lucide="trash-2" class="h-4 w-4"></i>
                        <span class="sr-only">Delete</span>
                    </button>
                </div>
              </td>
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
