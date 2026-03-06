(function () {
  "use strict";

  var state = {
    courses: [],
    cameraSource: "auto",
  };

  var dom = {
    lateThreshold: document.getElementById("late-threshold"),
    saveAttendanceBtn: document.getElementById("save-attendance-btn"),
    cameraRadios: document.querySelectorAll('input[name="camera-source"]'),
    esp32IpField: document.getElementById("esp32-ip-field"),
    esp32Ip: document.getElementById("esp32-ip"),
    saveCameraBtn: document.getElementById("save-camera-btn"),
    courseChips: document.getElementById("course-chips"),
    newCourseInput: document.getElementById("new-course-input"),
    addCourseBtn: document.getElementById("add-course-btn"),
    accountName: document.getElementById("account-name"),
    accountEmail: document.getElementById("account-email"),
    saveAccountBtn: document.getElementById("save-account-btn"),
    currentPassword: document.getElementById("current-password"),
    newPassword: document.getElementById("new-password"),
    changePasswordBtn: document.getElementById("change-password-btn"),
    passwordFeedback: document.getElementById("password-feedback"),
  };

  var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str || ""));
    return div.innerHTML;
  }

  function showToast(message, type) {
    var container = document.getElementById("toast-container");
    if (!container) return;

    var toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "success");
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(function () {
      toast.classList.add("removing");
      setTimeout(function () {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
      }, 200);
    }, 3000);
  }

  function updateEsp32IpVisibility() {
    var show = state.cameraSource === "esp32" || state.cameraSource === "auto";
    dom.esp32IpField.style.display = show ? "" : "none";
  }

  function renderCourseChips() {
    dom.courseChips.innerHTML = "";
    for (var i = 0; i < state.courses.length; i++) {
      var chip = document.createElement("span");
      chip.className = "chip";

      var text = document.createTextNode(escapeHtml(state.courses[i]) + " ");
      chip.appendChild(text);

      var removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "chip-remove";
      removeBtn.setAttribute("aria-label", "Remove " + state.courses[i]);
      removeBtn.textContent = "\u00D7";
      removeBtn.setAttribute("data-course", state.courses[i]);
      removeBtn.addEventListener("click", onRemoveCourse);
      chip.appendChild(removeBtn);

      dom.courseChips.appendChild(chip);
    }
  }

  function saveCourses() {
    fetch("/api/dashboard/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ courses: state.courses }),
    })
      .then(function (res) {
        if (!res.ok) throw new Error("Failed to save");
        showToast("Courses updated", "success");
      })
      .catch(function () {
        showToast("Failed to save courses", "error");
      });
  }

  function onRemoveCourse(e) {
    var course = e.currentTarget.getAttribute("data-course");
    state.courses = state.courses.filter(function (c) {
      return c !== course;
    });
    renderCourseChips();
    saveCourses();
  }

  function onAddCourse() {
    var val = dom.newCourseInput.value.trim().toUpperCase();
    if (!val) return;
    if (!COURSE_CODE_RE.test(val)) {
      showToast("Course code must be 3 letters + 3 digits (e.g. MTE413)", "error");
      return;
    }
    if (state.courses.indexOf(val) !== -1) {
      showToast("Course already added", "warning");
      return;
    }
    state.courses.push(val);
    dom.newCourseInput.value = "";
    renderCourseChips();
    saveCourses();
  }

  function loadSettings() {
    fetch("/api/dashboard/settings")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        dom.lateThreshold.value = data.late_threshold_minutes || 15;

        state.cameraSource = data.camera_source || "auto";
        for (var i = 0; i < dom.cameraRadios.length; i++) {
          dom.cameraRadios[i].checked =
            dom.cameraRadios[i].value === state.cameraSource;
        }
        updateEsp32IpVisibility();

        dom.esp32Ip.value = data.esp32_ip || "192.168.1.100";

        state.courses = (data.user && data.user.courses) || [];
        renderCourseChips();

        if (data.user && data.user.name) {
          dom.accountName.value = data.user.name;
        }
        if (data.user && data.user.email) {
          dom.accountEmail.value = data.user.email;
        }
      })
      .catch(function () {
        showToast("Failed to load settings", "error");
      });
  }

  function bindEvents() {
    dom.saveAttendanceBtn.addEventListener("click", function () {
      var val = parseInt(dom.lateThreshold.value, 10);
      if (isNaN(val) || val < 1) {
        showToast("Enter a valid threshold", "error");
        return;
      }
      fetch("/api/dashboard/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ late_threshold_minutes: val }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Failed");
          showToast("Attendance settings saved", "success");
        })
        .catch(function () {
          showToast("Failed to save", "error");
        });
    });

    for (var i = 0; i < dom.cameraRadios.length; i++) {
      dom.cameraRadios[i].addEventListener("change", function () {
        state.cameraSource = this.value;
        updateEsp32IpVisibility();
      });
    }

    dom.saveCameraBtn.addEventListener("click", function () {
      var payload = { camera_source: state.cameraSource };
      if (state.cameraSource !== "webcam") {
        payload.esp32_ip = dom.esp32Ip.value.trim();
      }
      fetch("/api/dashboard/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Failed");
          showToast("Camera settings saved", "success");
        })
        .catch(function () {
          showToast("Failed to save", "error");
        });
    });

    dom.addCourseBtn.addEventListener("click", onAddCourse);
    dom.newCourseInput.addEventListener("keydown", function (e) {
      if (e.key === "Enter") {
        e.preventDefault();
        onAddCourse();
      }
    });

    dom.saveAccountBtn.addEventListener("click", function () {
      var name = dom.accountName.value.trim();
      var email = dom.accountEmail.value.trim();
      if (!name || !email) {
        showToast("Name and email are required", "error");
        return;
      }
      fetch("/api/dashboard/account", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, email: email }),
      })
        .then(function (res) {
          if (!res.ok) throw new Error("Failed");
          showToast("Account updated", "success");
          var sidebarName = document.querySelector(".dash-user-name");
          var sidebarEmail = document.querySelector(".dash-user-email");
          if (sidebarName) sidebarName.textContent = name;
          if (sidebarEmail) sidebarEmail.textContent = email;
        })
        .catch(function () {
          showToast("Failed to update account", "error");
        });
    });

    dom.changePasswordBtn.addEventListener("click", function () {
      var current = dom.currentPassword.value;
      var next = dom.newPassword.value;
      dom.passwordFeedback.style.display = "none";

      if (!current || !next) {
        showFeedback("Both fields are required", true);
        return;
      }
      if (next.length < 6) {
        showFeedback("New password must be at least 6 characters", true);
        return;
      }

      fetch("/api/dashboard/password", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_password: current,
          new_password: next,
        }),
      })
        .then(function (res) {
          return res.json().then(function (data) {
            return { ok: res.ok, data: data };
          });
        })
        .then(function (result) {
          if (!result.ok) {
            showFeedback(result.data.error || "Failed to change password", true);
            return;
          }
          dom.currentPassword.value = "";
          dom.newPassword.value = "";
          showFeedback("Password changed successfully", false);
          showToast("Password changed", "success");
        })
        .catch(function () {
          showFeedback("Failed to change password", true);
        });
    });
  }

  function showFeedback(message, isError) {
    dom.passwordFeedback.textContent = message;
    dom.passwordFeedback.className =
      "password-feedback " + (isError ? "is-error" : "is-success");
    dom.passwordFeedback.style.display = "";
  }

  function init() {
    bindEvents();
    loadSettings();
  }

  init();
})();
