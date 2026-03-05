(function () {
  'use strict';

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  var WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var FULL_MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  var MAX_PILLS = 3;
  var state = {
    courses: [],
    records: [],
    stats: {},
    activeCourse: null
  };

  function formatTime(timestamp) {
    if (!timestamp) return '';
    var d = new Date(timestamp);
    var hours = d.getHours();
    var minutes = d.getMinutes();
    var ampm = hours >= 12 ? 'PM' : 'AM';
    hours = hours % 12 || 12;
    var mins = minutes < 10 ? '0' + minutes : minutes;
    return hours + ':' + mins + ' ' + ampm;
  }

  function statusPillClass(status) {
    if (status === 'present') return 'pill pill-present';
    if (status === 'late') return 'pill pill-late';
    return 'pill pill-absent';
  }

  function statusLabel(status) {
    if (status === 'present') return 'Present';
    if (status === 'late') return 'Late';
    return 'Absent';
  }

  function groupByMonth(records) {
    var groups = {};
    var order = [];
    records.forEach(function (rec) {
      var d = new Date(rec.timestamp);
      var key = d.getFullYear() + '-' + d.getMonth();
      if (!groups[key]) {
        groups[key] = {
          label: FULL_MONTHS[d.getMonth()] + ' ' + d.getFullYear(),
          items: []
        };
        order.push(key);
      }
      groups[key].items.push(rec);
    });
    return order.map(function (key) { return groups[key]; });
  }

  function renderFilter() {
    var container = document.getElementById('att-filter');
    var allCourses = ['All'].concat(state.courses);

    if (allCourses.length <= MAX_PILLS + 1) {
      var html = '<div class="att-filter-pills course-pills">';
      allCourses.forEach(function (course) {
        var isActive = (course === 'All' && !state.activeCourse)
          || course === state.activeCourse;
        var cls = 'course-pill' + (isActive ? ' active' : '');
        html += '<button type="button" class="' + cls + '" '
          + 'data-course="' + escapeHtml(course) + '"'
          + '>' + escapeHtml(course) + '</button>';
      });
      html += '</div>';
      container.innerHTML = html;

      container.querySelectorAll('.course-pill').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var course = this.getAttribute('data-course');
          state.activeCourse = course === 'All' ? null : course;
          loadAttendance();
        });
      });
    } else {
      container.innerHTML = '<div class="att-filter-dropdown" id="att-filter-dropdown-container"></div>';
      var dropdownContainer = document.getElementById('att-filter-dropdown-container');
      var selectOpts = allCourses.map(function (course) {
        return { value: course, label: course };
      });
      new CustomSelect(dropdownContainer, {
        options: selectOpts,
        value: state.activeCourse || 'All',
        ariaLabel: 'Filter by course',
        onChange: function (val) {
          state.activeCourse = val === 'All' ? null : val;
          loadAttendance();
        }
      });
    }
  }

  function renderSummary() {
    var courseEl = document.getElementById('summary-course');
    var detailEl = document.getElementById('summary-detail');

    courseEl.textContent = state.activeCourse || 'All Courses';

    var stats = state.stats;
    if (stats && stats.total_sessions !== undefined) {
      var attended = (stats.present || 0) + (stats.late || 0);
      var total = stats.total_sessions || 0;
      var rate = stats.attendance_rate !== undefined ? stats.attendance_rate : 0;
      detailEl.textContent = rate + '% (' + attended + '/' + total + ' sessions)';
    } else {
      detailEl.textContent = '';
    }
  }

  function renderList() {
    var container = document.getElementById('att-list-container');

    if (!state.records || state.records.length === 0) {
      container.innerHTML = '<div class="empty-state">'
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
        + '<p>No attendance records yet.</p>'
        + '<p style="font-size:var(--text-sm)">Your attendance will appear here once your lecturer starts a session.</p>'
        + '</div>';
      return;
    }

    var groups = groupByMonth(state.records);
    var html = '';

    groups.forEach(function (group) {
      html += '<div class="month-header">' + escapeHtml(group.label) + '</div>';
      html += '<ul class="att-list">';

      group.items.forEach(function (rec) {
        var d = new Date(rec.timestamp);
        var day = d.getDate();
        var weekday = WEEKDAYS[d.getDay()];
        var courseCode = rec.course_code || rec.session_course || '';
        var status = rec.status || 'absent';
        var time = formatTime(rec.timestamp);

        html += '<li class="att-entry">'
          + '<div class="att-entry__date">'
          + '<div class="att-entry__day">' + day + '</div>'
          + '<div class="att-entry__weekday">' + weekday + '</div>'
          + '</div>'
          + '<span class="att-entry__course">' + escapeHtml(courseCode) + '</span>'
          + '<div class="att-entry__right">'
          + '<span class="' + statusPillClass(status) + '">'
          + escapeHtml(statusLabel(status))
          + '</span>'
          + '<span class="att-entry__time">' + escapeHtml(time) + '</span>'
          + '</div>'
          + '</li>';
      });

      html += '</ul>';
    });

    container.innerHTML = html;
  }

  function showContent() {
    document.getElementById('att-skeleton').style.display = 'none';
    document.getElementById('att-content').style.display = 'block';
  }

  function showErrorState() {
    var skeleton = document.getElementById('att-skeleton');
    skeleton.innerHTML = '<div class="empty-state">'
      + '<p>Could not load attendance data. Please try refreshing.</p>'
      + '</div>';
    skeleton.removeAttribute('aria-busy');
  }

  function loadAttendance() {
    var url = '/api/portal/attendance';
    if (state.activeCourse) {
      url += '?course=' + encodeURIComponent(state.activeCourse);
    }

    fetch(url)
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

        var data = result.data;
        state.records = data.records || [];
        state.stats = data.stats || {};

        if (data.courses && state.courses.length === 0) {
          state.courses = data.courses;
        }

        renderFilter();
        renderSummary();
        renderList();
        showContent();
      })
      .catch(function () {
        showErrorState();
      });
  }

  loadAttendance();
})();
