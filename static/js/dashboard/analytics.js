(function () {
  "use strict";

  var state = {
    selectedCourse: "all",
    courses: [],
  };

  var dom = {
    courseSelector: document.getElementById("course-selector-container"),
    trendSkeleton: document.getElementById("trend-skeleton"),
    trendChart: document.getElementById("trend-chart"),
    trendEmpty: document.getElementById("trend-empty"),
    leaderboardTbody: document.getElementById("leaderboard-tbody"),
    leaderboardEmpty: document.getElementById("leaderboard-empty"),
    leaderboardCount: document.getElementById("leaderboard-count"),
  };

  function escapeHtml(str) {
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(str || ""));
    return div.innerHTML;
  }

  function formatDate(isoString) {
    if (!isoString) return "-";
    var d = new Date(isoString);
    if (isNaN(d.getTime())) {
      d = new Date(isoString.replace("T", " "));
    }
    if (isNaN(d.getTime())) return isoString;
    var day = d.getDate();
    var months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    return day + " " + months[d.getMonth()];
  }

  function courseParam() {
    if (state.selectedCourse && state.selectedCourse !== "all") {
      return "?course=" + encodeURIComponent(state.selectedCourse);
    }
    return "";
  }

  // --- Course Selector ---

  function renderCourseSelector(courses) {
    state.courses = courses;
    var container = dom.courseSelector;
    if (!container) return;
    container.innerHTML = "";

    var allCourses = ["All Courses"].concat(courses);

    if (courses.length <= 3) {
      var pills = document.createElement("div");
      pills.className = "course-pills";
      for (var i = 0; i < allCourses.length; i++) {
        var pill = document.createElement("button");
        pill.type = "button";
        pill.className = "course-pill";
        var val = i === 0 ? "all" : courses[i - 1];
        pill.setAttribute("data-course", val);
        pill.textContent = allCourses[i];
        if (val === state.selectedCourse) pill.classList.add("active");
        pill.addEventListener("click", onCoursePillClick);
        pills.appendChild(pill);
      }
      container.appendChild(pills);
    } else {
      var selectOpts = allCourses.map(function (c, idx) {
        return { value: idx === 0 ? "all" : courses[idx - 1], label: c };
      });
      new CustomSelect(container, {
        options: selectOpts,
        value: state.selectedCourse,
        ariaLabel: "Filter by course",
        onChange: function (val) {
          state.selectedCourse = val;
          loadAnalytics();
        }
      });
    }
  }

  function onCoursePillClick(e) {
    state.selectedCourse = e.target.getAttribute("data-course");
    var pills = dom.courseSelector.querySelectorAll(".course-pill");
    for (var i = 0; i < pills.length; i++) {
      pills[i].classList.remove("active");
    }
    e.target.classList.add("active");
    loadAnalytics();
  }

  // --- Trend Chart ---

  function renderTrendChart(data) {
    dom.trendSkeleton.style.display = "none";

    if (!data || data.length === 0) {
      dom.trendChart.style.display = "none";
      dom.trendEmpty.style.display = "";
      return;
    }

    dom.trendEmpty.style.display = "none";
    dom.trendChart.style.display = "";
    dom.trendChart.innerHTML = "";

    var axisLine = document.createElement("div");
    axisLine.className = "trend-axis-line";
    dom.trendChart.appendChild(axisLine);

    for (var i = 0; i < data.length; i++) {
      var item = data[i];
      var group = document.createElement("div");
      group.className = "trend-bar-group";

      var bar = document.createElement("div");
      bar.className = "trend-bar";
      var heightPct = Math.max(item.rate, 2);
      bar.style.height = heightPct + "%";
      bar.title =
        escapeHtml(item.course_code) +
        " - " +
        item.rate +
        "% (" +
        item.attended +
        "/" +
        item.total +
        ")";

      var label = document.createElement("span");
      label.className = "trend-bar-label";
      label.textContent = item.rate + "%";
      bar.appendChild(label);

      var dateLabel = document.createElement("span");
      dateLabel.className = "trend-bar-date";
      dateLabel.textContent = formatDate(item.date);

      group.appendChild(bar);
      group.appendChild(dateLabel);
      dom.trendChart.appendChild(group);
    }
  }

  // --- Leaderboard ---

  function renderLeaderboard(data) {
    var tbody = dom.leaderboardTbody;

    var skeletons = tbody.querySelectorAll("[data-skeleton]");
    for (var s = 0; s < skeletons.length; s++) {
      skeletons[s].parentNode.removeChild(skeletons[s]);
    }

    if (!data || data.length === 0) {
      tbody.innerHTML = "";
      dom.leaderboardEmpty.style.display = "";
      dom.leaderboardCount.textContent = "";
      return;
    }

    dom.leaderboardEmpty.style.display = "none";
    dom.leaderboardCount.textContent = data.length + " students";
    tbody.innerHTML = "";

    for (var i = 0; i < data.length; i++) {
      var st = data[i];
      var tr = document.createElement("tr");

      var tdRank = document.createElement("td");
      tdRank.textContent = i + 1;
      tr.appendChild(tdRank);

      var tdId = document.createElement("td");
      tdId.className = "font-mono";
      tdId.textContent = escapeHtml(st.student_id);
      tr.appendChild(tdId);

      var tdName = document.createElement("td");
      tdName.textContent = escapeHtml(st.name);
      tr.appendChild(tdName);

      var tdSessions = document.createElement("td");
      tdSessions.textContent = st.attended + "/" + st.total_sessions;
      tr.appendChild(tdSessions);

      var tdRate = document.createElement("td");
      var ratePill = document.createElement("span");
      ratePill.className = "pill";
      ratePill.textContent = st.rate + "%";
      if (st.rate < 75) {
        ratePill.classList.add("pill-warning");
      } else {
        ratePill.classList.add("pill-present");
      }
      tdRate.appendChild(ratePill);
      tr.appendChild(tdRate);

      tbody.appendChild(tr);
    }
  }

  // --- Data Loading ---

  function loadAnalytics() {
    loadTrend();
    loadLeaderboard();
  }

  function loadTrend() {
    dom.trendSkeleton.style.display = "";
    dom.trendChart.style.display = "none";
    dom.trendEmpty.style.display = "none";

    fetch("/api/dashboard/analytics/trend" + courseParam())
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        renderTrendChart(data);
      })
      .catch(function () {
        dom.trendSkeleton.style.display = "none";
        dom.trendEmpty.style.display = "";
      });
  }

  function loadLeaderboard() {
    fetch("/api/dashboard/analytics/leaderboard" + courseParam())
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        renderLeaderboard(data);
      })
      .catch(function () {
        renderLeaderboard([]);
      });
  }

  function loadCourses() {
    fetch("/api/dashboard/courses")
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        renderCourseSelector(data);
      })
      .catch(function () {
        renderCourseSelector([]);
      });
  }

  // --- Init ---

  function init() {
    loadCourses();
    loadAnalytics();
  }

  init();
})();
