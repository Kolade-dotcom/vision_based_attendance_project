(function () {
  'use strict';

  var profileData = null;
  var editingCourses = [];
  var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    var toast = document.createElement('div');
    toast.className = 'toast toast-' + (type || 'success');
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function () {
      toast.classList.add('removing');
      setTimeout(function () { toast.remove(); }, 200);
    }, 3000);
  }

  function setLoading(btn, loading) {
    if (loading) {
      btn.dataset.originalText = btn.textContent;
      btn.textContent = 'Saving\u2026';
      btn.disabled = true;
    } else {
      btn.textContent = btn.dataset.originalText || btn.textContent;
      btn.disabled = false;
    }
  }

  function renderProfile(data) {
    document.getElementById('profile-name').textContent = data.name || '';
    document.getElementById('profile-matric').textContent = data.matric || '';
    document.getElementById('profile-level').textContent = 'Level ' + (data.level || '—');

    var faceStatus = document.getElementById('face-status');
    if (data.is_enrolled) {
      faceStatus.className = 'pill pill-present';
      faceStatus.textContent = 'Enrolled \u2713';
    } else {
      faceStatus.className = 'pill pill-absent';
      faceStatus.textContent = 'Not enrolled';
    }

    renderCourseChips(data.courses || [], false);
  }

  function renderCourseChips(courses, editable) {
    var container = document.getElementById('course-chips');
    if (!courses || courses.length === 0) {
      container.innerHTML = '<span style="font-size: var(--text-sm); color: var(--text-muted);">No courses added</span>';
      return;
    }

    var html = '';
    courses.forEach(function (course) {
      html += '<span class="course-chip">'
        + escapeHtml(course);
      if (editable) {
        html += '<button type="button" class="course-chip__remove" data-course="'
          + escapeHtml(course)
          + '" aria-label="Remove ' + escapeHtml(course) + '">&times;</button>';
      }
      html += '</span>';
    });
    container.innerHTML = html;

    if (editable) {
      container.querySelectorAll('.course-chip__remove').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var courseToRemove = this.getAttribute('data-course');
          editingCourses = editingCourses.filter(function (c) { return c !== courseToRemove; });
          renderCourseChips(editingCourses, true);
        });
      });
    }
  }

  function showContent() {
    document.getElementById('profile-skeleton').style.display = 'none';
    document.getElementById('profile-content').style.display = 'block';
  }

  function showErrorState() {
    var skeleton = document.getElementById('profile-skeleton');
    skeleton.innerHTML = '<div class="empty-state">'
      + '<p>Could not load profile. Please try refreshing.</p>'
      + '</div>';
    skeleton.removeAttribute('aria-busy');
  }

  // --- Profile editing (name, email) ---

  var btnEditProfile = document.getElementById('btn-edit-profile');
  var profileEditForm = document.getElementById('profile-edit-form');
  var btnSaveProfile = document.getElementById('btn-save-profile');
  var btnCancelProfile = document.getElementById('btn-cancel-profile');

  btnEditProfile.addEventListener('click', function () {
    document.getElementById('edit-name').value = profileData.name || '';
    document.getElementById('edit-email').value = profileData.email || '';
    profileEditForm.style.display = 'block';
    btnEditProfile.style.display = 'none';
  });

  btnCancelProfile.addEventListener('click', function () {
    profileEditForm.style.display = 'none';
    btnEditProfile.style.display = '';
  });

  btnSaveProfile.addEventListener('click', function () {
    var name = document.getElementById('edit-name').value.trim();
    var email = document.getElementById('edit-email').value.trim();
    if (!name) {
      showToast('Name is required', 'error');
      return;
    }

    setLoading(btnSaveProfile, true);
    fetch('/api/portal/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name, email: email, level: profileData.level, courses: profileData.courses })
    })
      .then(function (res) {
        return res.json().then(function (d) { return { ok: res.ok, data: d }; });
      })
      .then(function (result) {
        setLoading(btnSaveProfile, false);
        if (!result.ok) {
          showToast(result.data.error || 'Failed to save', 'error');
          return;
        }
        profileData.name = name;
        profileData.email = email;
        renderProfile(profileData);
        profileEditForm.style.display = 'none';
        btnEditProfile.style.display = '';
        showToast('Profile updated');
      })
      .catch(function () {
        setLoading(btnSaveProfile, false);
        showToast('Network error', 'error');
      });
  });

  // --- Academic editing (level, courses) ---

  var btnEditAcademic = document.getElementById('btn-edit-academic');
  var academicEditForm = document.getElementById('academic-edit-form');
  var courseAddForm = document.getElementById('course-add-form');
  var btnSaveAcademic = document.getElementById('btn-save-academic');
  var btnCancelAcademic = document.getElementById('btn-cancel-academic');
  var btnAddCourse = document.getElementById('btn-add-course');
  var addCourseInput = document.getElementById('add-course-input');

  btnEditAcademic.addEventListener('click', function () {
    document.getElementById('edit-level').value = String(profileData.level || '100');
    editingCourses = (profileData.courses || []).slice();
    renderCourseChips(editingCourses, true);
    academicEditForm.style.display = 'block';
    courseAddForm.style.display = 'block';
    btnEditAcademic.style.display = 'none';
  });

  btnCancelAcademic.addEventListener('click', function () {
    academicEditForm.style.display = 'none';
    courseAddForm.style.display = 'none';
    btnEditAcademic.style.display = '';
    renderCourseChips(profileData.courses || [], false);
  });

  btnAddCourse.addEventListener('click', function () {
    var code = addCourseInput.value.trim().toUpperCase();
    if (!code) return;
    if (!COURSE_CODE_RE.test(code)) {
      showToast('Course code must be 3 letters + 3 digits (e.g. MTE413)', 'error');
      return;
    }
    if (editingCourses.indexOf(code) !== -1) {
      showToast('Course already added', 'warning');
      return;
    }
    editingCourses.push(code);
    renderCourseChips(editingCourses, true);
    addCourseInput.value = '';
    addCourseInput.focus();
  });

  addCourseInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      btnAddCourse.click();
    }
  });

  btnSaveAcademic.addEventListener('click', function () {
    var level = parseInt(document.getElementById('edit-level').value, 10);

    setLoading(btnSaveAcademic, true);
    fetch('/api/portal/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: profileData.name, email: profileData.email, level: level, courses: editingCourses })
    })
      .then(function (res) {
        return res.json().then(function (d) { return { ok: res.ok, data: d }; });
      })
      .then(function (result) {
        setLoading(btnSaveAcademic, false);
        if (!result.ok) {
          showToast(result.data.error || 'Failed to save', 'error');
          return;
        }
        profileData.level = level;
        profileData.courses = editingCourses.slice();
        renderProfile(profileData);
        academicEditForm.style.display = 'none';
        courseAddForm.style.display = 'none';
        btnEditAcademic.style.display = '';
        showToast('Academic info updated');
      })
      .catch(function () {
        setLoading(btnSaveAcademic, false);
        showToast('Network error', 'error');
      });
  });

  // --- Change password ---

  var btnChangePassword = document.getElementById('btn-change-password');

  btnChangePassword.addEventListener('click', function () {
    var currentPw = document.getElementById('current-password').value;
    var newPw = document.getElementById('new-password').value;

    if (!currentPw || !newPw) {
      showToast('Both fields are required', 'error');
      return;
    }
    if (newPw.length < 6) {
      showToast('New password must be at least 6 characters', 'error');
      return;
    }

    setLoading(btnChangePassword, true);
    fetch('/api/portal/password', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: currentPw, new_password: newPw })
    })
      .then(function (res) {
        return res.json().then(function (d) { return { ok: res.ok, data: d }; });
      })
      .then(function (result) {
        setLoading(btnChangePassword, false);
        if (!result.ok) {
          showToast(result.data.error || 'Password change failed', 'error');
          return;
        }
        document.getElementById('current-password').value = '';
        document.getElementById('new-password').value = '';
        showToast('Password updated');
      })
      .catch(function () {
        setLoading(btnChangePassword, false);
        showToast('Network error', 'error');
      });
  });

  // --- Load profile data ---

  fetch('/api/portal/profile')
    .then(function (res) {
      if (res.status === 401 || res.status === 403) {
        window.location.href = '/portal/login';
        return null;
      }
      return res.json().then(function (data) { return { ok: res.ok, data: data }; });
    })
    .then(function (result) {
      if (!result) return;
      if (!result.ok) {
        showErrorState();
        return;
      }
      profileData = result.data;
      renderProfile(profileData);
      showContent();
    })
    .catch(function () {
      showErrorState();
    });
})();
