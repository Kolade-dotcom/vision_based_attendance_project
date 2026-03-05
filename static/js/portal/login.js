(function () {
  'use strict';

  var tabSignin = document.getElementById('tab-signin');
  var tabSignup = document.getElementById('tab-signup');
  var panelSignin = document.getElementById('panel-signin');
  var panelSignup = document.getElementById('panel-signup');

  function switchTab(activeTab) {
    var isSignin = activeTab === tabSignin;

    tabSignin.setAttribute('aria-selected', isSignin ? 'true' : 'false');
    tabSignup.setAttribute('aria-selected', isSignin ? 'false' : 'true');

    panelSignin.classList.toggle('active', isSignin);
    panelSignup.classList.toggle('active', !isSignin);

    hideError('signin-error');
    hideError('signup-error');
  }

  tabSignin.addEventListener('click', function () { switchTab(tabSignin); });
  tabSignup.addEventListener('click', function () { switchTab(tabSignup); });

  function showError(elementId, message) {
    var el = document.getElementById(elementId);
    el.textContent = message;
    el.classList.add('visible');
  }

  function hideError(elementId) {
    var el = document.getElementById(elementId);
    el.textContent = '';
    el.classList.remove('visible');
  }

  function setLoading(form, loading) {
    var btn = form.querySelector('button[type="submit"]');
    if (loading) {
      btn.classList.add('loading');
      btn.disabled = true;
    } else {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  }

  panelSignin.addEventListener('submit', function (e) {
    e.preventDefault();
    hideError('signin-error');

    var matric = document.getElementById('signin-matric').value.trim();
    var password = document.getElementById('signin-password').value;

    if (!matric || !password) {
      showError('signin-error', 'Please fill in all required fields.');
      return;
    }

    setLoading(panelSignin, true);

    fetch('/api/portal/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ matric_number: matric, password: password })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        setLoading(panelSignin, false);
        if (!result.ok) {
          showError('signin-error', result.data.error || 'Invalid credentials.');
          return;
        }
        if (result.data.is_enrolled) {
          window.location.href = '/portal/';
        } else {
          window.location.href = '/portal/enroll';
        }
      })
      .catch(function () {
        setLoading(panelSignin, false);
        showError('signin-error', 'Something went wrong. Please try again.');
      });
  });

  panelSignup.addEventListener('submit', function (e) {
    e.preventDefault();
    hideError('signup-error');

    var matric = document.getElementById('signup-matric').value.trim();
    var name = document.getElementById('signup-name').value.trim();
    var email = document.getElementById('signup-email').value.trim();
    var password = document.getElementById('signup-password').value;

    if (!matric || !name || !password) {
      showError('signup-error', 'Please fill in all required fields.');
      return;
    }

    var payload = { matric_number: matric, name: name, password: password };
    if (email) {
      payload.email = email;
    }

    setLoading(panelSignup, true);

    fetch('/api/portal/auth/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        setLoading(panelSignup, false);
        if (!result.ok) {
          showError('signup-error', result.data.error || 'Could not create account.');
          return;
        }
        window.location.href = '/portal/enroll';
      })
      .catch(function () {
        setLoading(panelSignup, false);
        showError('signup-error', 'Something went wrong. Please try again.');
      });
  });
})();
