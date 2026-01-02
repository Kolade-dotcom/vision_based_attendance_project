/**
 * API Client Module
 * Handles all communication with the backend.
 */

export const apiClient = {
  /**
   * Enroll a new student.
   */
  async enrollStudent(studentData) {
    const response = await fetch("/api/enroll", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(studentData),
    });
    return await response.json();
  },

  /**
   * Fetch all enrolled students.
   */
  async getStudents() {
    const response = await fetch("/api/students");
    return await response.json();
  },

  /**
   * Fetch today's attendance records.
   */
  async getAttendanceToday() {
    const response = await fetch("/api/attendance/today");
    return await response.json();
  },

  /**
   * Fetch system statistics.
   */
  async getStatistics() {
    const response = await fetch("/api/statistics");
    return await response.json();
  },
  /**
   * Update student details.
   */
  async updateStudent(studentId, data) {
    const response = await fetch(`/api/students/${studentId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(data),
    });
    return await response.json();
  },

  /**
   * Delete a student.
   */
  async deleteStudent(studentId) {
    const response = await fetch(`/api/students/${studentId}`, {
      method: "DELETE",
    });
    return await response.json();
  },
};
