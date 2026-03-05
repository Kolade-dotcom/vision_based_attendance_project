(function () {
  'use strict';

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  var WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  var MONTHS = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'
  ];

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

  function formatDate(timestamp) {
    if (!timestamp) return '';
    var d = new Date(timestamp);
    return d.getDate() + ' ' + MONTHS[d.getMonth()];
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

  function renderStatusCard(student) {
    document.getElementById('student-name').textContent = student.name;
    document.getElementById('student-matric').textContent = student.matric;
    var badge = document.getElementById('enrollment-badge');
    if (student.is_enrolled) {
      badge.textContent = 'Enrolled \u2713';
    } else {
      badge.textContent = 'Not Enrolled';
      badge.style.backgroundColor = 'var(--warning-light)';
      badge.style.color = 'var(--warning)';
    }
  }

  function renderTodaySection(todayItems) {
    var section = document.getElementById('today-section');
    if (!todayItems || todayItems.length === 0) {
      section.style.display = 'none';
      return;
    }

    var html = '';
    todayItems.forEach(function (item) {
      var detail;
      if (item.marked) {
        detail = 'You were marked '
          + escapeHtml(item.status)
          + ' at '
          + escapeHtml(formatTime(item.time));
      } else {
        detail = 'Session active \u2014 awaiting your attendance';
      }

      html += '<div class="today-card">'
        + '<div class="today-card__course">'
        + escapeHtml(item.course_code)
        + '</div>'
        + '<div class="today-card__detail">'
        + detail
        + '</div>'
        + '</div>';
    });

    section.innerHTML = html;
    section.style.display = 'block';
  }

  function renderQuickStats(stats, coursesCount) {
    var rate = stats.attendance_rate !== undefined ? stats.attendance_rate + '%' : '—';
    document.getElementById('stat-rate').textContent = rate;
    document.getElementById('stat-courses').textContent = String(coursesCount);
  }

  function renderRecent(records) {
    var container = document.getElementById('recent-container');

    if (!records || records.length === 0) {
      container.innerHTML = '<div class="empty-state">'
        + '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>'
        + '<p>No attendance records yet</p>'
        + '</div>';
      return;
    }

    var html = '<ul class="recent-list">';
    records.forEach(function (rec) {
      var date = formatDate(rec.timestamp);
      var courseCode = rec.course_code || rec.session_course || '';
      var status = rec.status || 'absent';

      html += '<li class="recent-item">'
        + '<span class="recent-item__date">' + escapeHtml(date) + '</span>'
        + '<span class="recent-item__course">' + escapeHtml(courseCode) + '</span>'
        + '<span class="recent-item__status ' + statusPillClass(status) + '">'
        + escapeHtml(statusLabel(status))
        + '</span>'
        + '</li>';
    });
    html += '</ul>';
    container.innerHTML = html;
  }

  function showContent() {
    document.getElementById('home-skeleton').style.display = 'none';
    document.getElementById('home-content').style.display = 'block';
  }

  function showErrorState() {
    var skeleton = document.getElementById('home-skeleton');
    skeleton.innerHTML = '<div class="empty-state">'
      + '<p>Could not load home page data. Please try refreshing.</p>'
      + '</div>';
    skeleton.removeAttribute('aria-busy');
  }

  fetch('/api/portal/home')
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
      renderStatusCard(data.student);
      renderTodaySection(data.today);

      var coursesCount = Array.isArray(data.courses) ? data.courses.length : 0;
      renderQuickStats(data.stats || {}, coursesCount);

      renderRecent(data.recent);
      showContent();
    })
    .catch(function () {
      showErrorState();
    });
})();
