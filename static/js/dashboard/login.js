(function () {
  'use strict';

  var tabSignin = document.getElementById('tab-signin');
  var tabSignup = document.getElementById('tab-signup');
  var panelSignin = document.getElementById('panel-signin');
  var panelSignup = document.getElementById('panel-signup');
  var signinError = document.getElementById('signin-error');
  var signupError = document.getElementById('signup-error');

  function switchTab(activeTab) {
    var isSignin = activeTab === tabSignin;

    tabSignin.setAttribute('aria-selected', String(isSignin));
    tabSignup.setAttribute('aria-selected', String(!isSignin));

    if (isSignin) {
      panelSignin.hidden = false;
      panelSignup.hidden = true;
    } else {
      panelSignin.hidden = true;
      panelSignup.hidden = false;
    }

    signinError.textContent = '';
    signupError.textContent = '';
  }

  tabSignin.addEventListener('click', function () {
    switchTab(tabSignin);
  });

  tabSignup.addEventListener('click', function () {
    switchTab(tabSignup);
  });

  /* Keyboard navigation between tabs */
  [tabSignin, tabSignup].forEach(function (tab) {
    tab.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        var target = tab === tabSignin ? tabSignup : tabSignin;
        target.focus();
        switchTab(target);
      }
    });
  });

  function showError(el, message) {
    el.textContent = message;
  }

  function clearError(el) {
    el.textContent = '';
  }

  function setSubmitLoading(btn, loading) {
    if (loading) {
      btn.disabled = true;
      btn.dataset.originalText = btn.textContent;
      btn.textContent = 'Please wait\u2026';
    } else {
      btn.disabled = false;
      btn.textContent = btn.dataset.originalText || btn.textContent;
    }
  }

  function postJSON(url, body) {
    return fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (res) {
      return res.json().then(function (data) {
        return { ok: res.ok, status: res.status, data: data };
      });
    });
  }

  /* --- Sign in ----------------------------------------------------------- */
  panelSignin.addEventListener('submit', function (e) {
    e.preventDefault();
    clearError(signinError);

    var email = panelSignin.querySelector('[name="email"]').value.trim();
    var password = panelSignin.querySelector('[name="password"]').value;

    if (!email || !password) {
      showError(signinError, 'Please enter both email and password.');
      return;
    }

    var submitBtn = panelSignin.querySelector('button[type="submit"]');
    setSubmitLoading(submitBtn, true);

    postJSON('/api/auth/login', { email: email, password: password })
      .then(function (res) {
        if (res.ok) {
          window.location.href = '/dashboard/';
        } else {
          showError(signinError, res.data.error || 'Invalid email or password.');
        }
      })
      .catch(function () {
        showError(signinError, 'Network error. Please try again.');
      })
      .finally(function () {
        setSubmitLoading(submitBtn, false);
      });
  });

  /* --- Create account ---------------------------------------------------- */
  panelSignup.addEventListener('submit', function (e) {
    e.preventDefault();
    clearError(signupError);

    var name = panelSignup.querySelector('[name="name"]').value.trim();
    var email = panelSignup.querySelector('[name="email"]').value.trim();
    var password = panelSignup.querySelector('[name="password"]').value;

    if (!name || !email || !password) {
      showError(signupError, 'Please fill in all fields.');
      return;
    }

    var submitBtn = panelSignup.querySelector('button[type="submit"]');
    setSubmitLoading(submitBtn, true);

    postJSON('/api/auth/signup', { name: name, email: email, password: password })
      .then(function (res) {
        if (res.ok) {
          window.location.href = '/dashboard/';
        } else {
          showError(signupError, res.data.error || 'Could not create account.');
        }
      })
      .catch(function () {
        showError(signupError, 'Network error. Please try again.');
      })
      .finally(function () {
        setSubmitLoading(submitBtn, false);
      });
  });
})();
