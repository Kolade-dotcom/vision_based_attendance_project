/**
 * Escape HTML special characters to prevent XSS.
 */
export function escapeHtml(str) {
    if (str == null) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(String(str)));
    return div.innerHTML;
}

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
              <td class="p-4 align-middle">${escapeHtml(record.student_id)}</td>
              <td class="p-4 align-middle font-medium text-slate-900">${
                escapeHtml(record.student_name)
              }</td>
              <td class="p-4 align-middle">${new Date(
                record.timestamp
              ).toLocaleTimeString()}</td>
              <td class="p-4 align-middle">
                ${
                  record.status === "present"
                    ? `<span class="inline-flex items-center rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700 ring-1 ring-inset ring-green-600/20">Present</span>`
                    : `<span class="inline-flex items-center rounded-md bg-red-50 px-2 py-1 text-xs font-medium text-red-700 ring-1 ring-inset ring-red-600/20">${escapeHtml(record.status)}</span>`
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
                  <td colspan="5" class="h-24 text-center align-middle text-slate-500">No students enrolled yet</td>
              </tr>
          `;
      return;
    }

    const getStatusBadge = (status) => {
      switch (status) {
        case "pending":
          return `<span class="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-800">Pending</span>`;
        case "approved":
          return `<span class="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800">Approved</span>`;
        case "rejected":
          return `<span class="inline-flex items-center rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">Rejected</span>`;
        default:
          return `<span class="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium text-slate-800">${
            escapeHtml(status) || "Unknown"
          }</span>`;
      }
    };

    const getActionButtons = (student) => {
      if (student.status === "pending") {
        return `
          <div class="flex items-center gap-2">
            <button class="approve-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 bg-emerald-600 text-white hover:bg-emerald-500 h-8 px-3" data-id="${escapeHtml(student.student_id)}">
              <i data-lucide="check" class="h-4 w-4 mr-1"></i> Approve
            </button>
            <button class="reject-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 border border-red-200 bg-white hover:bg-red-50 text-red-600 h-8 px-3" data-id="${escapeHtml(student.student_id)}">
              <i data-lucide="x" class="h-4 w-4 mr-1"></i> Reject
            </button>
          </div>
        `;
      }

      return `
        <div class="flex items-center gap-2">
          <button class="edit-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-950 focus-visible:ring-offset-2 border border-slate-200 bg-white hover:bg-slate-100 h-8 px-3" data-id="${
            escapeHtml(student.student_id)
          }" data-name="${escapeHtml(student.name)}" data-level="${escapeHtml(student.level || "")}">
            <i data-lucide="pencil" class="h-4 w-4 mr-1"></i> Edit
          </button>
          <button class="delete-btn inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2 border border-red-200 bg-white hover:bg-red-50 text-red-600 h-8 px-3" data-id="${
            escapeHtml(student.student_id)
          }">
            <i data-lucide="trash-2" class="h-4 w-4 mr-1"></i> Delete
          </button>
        </div>
      `;
    };

    tbody.innerHTML = students
      .map(
        (student) => `
          <tr class="border-b transition-colors hover:bg-slate-100/50 data-[state=selected]:bg-slate-100">
              <td class="p-4 align-middle">${escapeHtml(student.student_id)}</td>
              <td class="p-4 align-middle font-medium text-slate-900">${
                escapeHtml(student.name)
              }</td>
              <td class="p-4 align-middle">${getStatusBadge(
                student.status
              )}</td>
              <td class="p-4 align-middle">${new Date(
                student.created_at
              ).toLocaleDateString()}</td>
              <td class="p-4 align-middle">${getActionButtons(student)}</td>
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
