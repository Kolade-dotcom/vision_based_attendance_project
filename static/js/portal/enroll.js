(function () {
  'use strict';

  /* ======================================================================
     Configuration
     ====================================================================== */

  var POSES = [
    { id: 'center',  label: 'Look straight at the camera' },
    { id: 'left',    label: 'Turn your head slightly left' },
    { id: 'right',   label: 'Turn your head slightly right' },
    { id: 'up',      label: 'Tilt your chin up slightly' },
    { id: 'down',    label: 'Look slightly downward' },
    { id: 'smile',   label: 'Give a natural smile' },
    { id: 'neutral', label: 'Relax your face' }
  ];

  var POSE_ICONS = {
    center: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="9" stroke-dasharray="4 2"/></svg>',
    left: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 5l-7 7 7 7"/></svg>',
    right: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>',
    up: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>',
    down: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14"/><path d="M5 12l7 7 7-7"/></svg>',
    smile: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><circle cx="9" cy="10" r="0.5" fill="currentColor"/><circle cx="15" cy="10" r="0.5" fill="currentColor"/></svg>',
    neutral: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="10"/><path d="M8 15h8"/><circle cx="9" cy="10" r="0.5" fill="currentColor"/><circle cx="15" cy="10" r="0.5" fill="currentColor"/></svg>'
  };

  var poseHintTimer = null;

  function showPoseHint(poseId, label) {
    var hint = $('pose-hint');
    var iconEl = $('pose-hint-icon');
    var textEl = $('pose-hint-text');
    if (!hint) return;

    clearTimeout(poseHintTimer);
    hint.classList.remove('fading');
    hint.style.display = '';

    iconEl.innerHTML = POSE_ICONS[poseId] || '';
    textEl.textContent = label;

    // Force reflow to restart animation
    void hint.offsetWidth;
    hint.style.animation = 'none';
    void hint.offsetWidth;
    hint.style.animation = '';

    poseHintTimer = setTimeout(function () {
      hint.classList.add('fading');
      setTimeout(function () {
        hint.style.display = 'none';
        hint.classList.remove('fading');
      }, 400);
    }, 2500);
  }

  var FRAMES_PER_POSE = 3;
  var CAPTURE_INTERVAL_MS = 1500;
  var COURSE_CODE_RE = /^[A-Z]{3}\d{3}$/;

  /* ======================================================================
     State
     ====================================================================== */

  var state = {
    currentStep: 'welcome',
    cameraStream: null,
    poseIndex: 0,
    frameIndex: 0,
    capturedFrames: [],
    captureTimer: null,
    faceEncoding: null,
    courses: [],
    processing: false,
    faceDetector: null,
    faceDetectionSupported: false,
    lastFaceDetected: false
  };

  /* ======================================================================
     DOM references
     ====================================================================== */

  var $ = function (id) { return document.getElementById(id); };

  var steps = {
    welcome: $('step-welcome'),
    capture: $('step-capture'),
    details: $('step-details'),
    confirm: $('step-confirm')
  };

  var video = $('camera-video');
  var canvas = $('capture-canvas');
  var dotStepper = $('dot-stepper');
  var captureInstruction = $('capture-instruction');
  var captureProgress = $('capture-progress');
  var cameraViewport = $('camera-viewport');

  /* ======================================================================
     Face detection (browser API)
     ====================================================================== */

  function initFaceDetection() {
    if (typeof window.FaceDetector !== 'undefined') {
      try {
        state.faceDetector = new FaceDetector({ fastMode: true, maxDetectedFaces: 1 });
        state.faceDetectionSupported = true;
      } catch (e) {
        state.faceDetectionSupported = false;
      }
    }
  }

  function detectFaceInFrame() {
    if (!state.faceDetectionSupported || !state.faceDetector) {
      return Promise.resolve(true); // assume face present if API unavailable
    }
    return state.faceDetector.detect(video)
      .then(function (faces) { return faces.length > 0; })
      .catch(function () { return true; }); // assume present on error
  }

  initFaceDetection();

  /* ======================================================================
     Step navigation
     ====================================================================== */

  function goToStep(name) {
    Object.keys(steps).forEach(function (key) {
      steps[key].classList.toggle('active', key === name);
    });
    state.currentStep = name;
  }

  /* ======================================================================
     Error display
     ====================================================================== */

  function showError(elementId, message) {
    var el = $(elementId);
    el.textContent = message;
    el.classList.add('visible');
  }

  function hideError(elementId) {
    var el = $(elementId);
    el.textContent = '';
    el.classList.remove('visible');
  }

  /* ======================================================================
     Button loading state
     ====================================================================== */

  function setButtonLoading(btn, loading) {
    if (loading) {
      btn.classList.add('loading');
      btn.disabled = true;
    } else {
      btn.classList.remove('loading');
      btn.disabled = false;
    }
  }

  /* ======================================================================
     Step 1: Welcome — request camera permission
     ====================================================================== */

  $('btn-start-camera').addEventListener('click', function () {
    var btn = this;
    hideError('welcome-error');
    setButtonLoading(btn, true);

    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } })
      .then(function (stream) {
        state.cameraStream = stream;
        video.srcObject = stream;
        showCameraView();
        initDotStepper();
        startPose(0);
        goToStep('capture');
        setButtonLoading(btn, false);
      })
      .catch(function (err) {
        setButtonLoading(btn, false);
        var message = 'Could not access camera. ';
        if (err.name === 'NotAllowedError') {
          message += 'Please allow camera access in your browser settings and try again.';
        } else if (err.name === 'NotFoundError') {
          message += 'No camera found on this device.';
        } else {
          message += err.message || 'Unknown error.';
        }
        showError('welcome-error', message);
      });
  });

  /* ======================================================================
     Camera viewport: show/hide video vs processing overlay
     ====================================================================== */

  function showCameraView() {
    video.style.display = '';
    var overlay = $('processing-overlay');
    if (overlay) overlay.style.display = 'none';
  }

  function showProcessingOverlay() {
    video.style.display = 'none';
    var overlay = $('processing-overlay');
    if (overlay) overlay.style.display = 'flex';
  }

  /* ======================================================================
     Dot stepper
     ====================================================================== */

  function initDotStepper() {
    dotStepper.innerHTML = '';
    POSES.forEach(function (pose, i) {
      var dot = document.createElement('div');
      dot.className = 'dot';
      dot.setAttribute('aria-label', pose.label);
      dot.dataset.index = i;
      dotStepper.appendChild(dot);
    });
  }

  function updateDotStepper() {
    var dots = dotStepper.querySelectorAll('.dot');
    dots.forEach(function (dot, i) {
      dot.className = 'dot';
      dot.innerHTML = '';
      if (i < state.poseIndex) {
        dot.classList.add('completed');
        dot.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="3" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>';
      } else if (i === state.poseIndex) {
        dot.classList.add('current');
      }
    });
  }

  /* ======================================================================
     Step 2: Guided face capture
     ====================================================================== */

  function startPose(index) {
    state.poseIndex = index;
    state.frameIndex = 0;
    updateDotStepper();
    captureInstruction.textContent = POSES[index].label;
    captureProgress.textContent = 'Capturing 0/' + FRAMES_PER_POSE + '...';
    hideError('capture-error');

    showPoseHint(POSES[index].id, POSES[index].label);

    clearInterval(state.captureTimer);
    state.captureTimer = setInterval(captureFrame, CAPTURE_INTERVAL_MS);
  }

  function captureFrame() {
    if (state.frameIndex >= FRAMES_PER_POSE) return;

    // Use face detection to validate before capturing
    detectFaceInFrame().then(function (faceDetected) {
      if (!faceDetected) {
        // Show feedback but don't count this frame
        captureProgress.textContent = 'No face detected — please position your face in the oval';
        captureProgress.style.color = 'var(--danger)';
        return;
      }

      captureProgress.style.color = '';

      var ctx = canvas.getContext('2d');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

      var dataUrl = canvas.toDataURL('image/jpeg', 0.85);
      state.capturedFrames.push(dataUrl);

      state.frameIndex++;
      captureProgress.textContent = 'Capturing ' + state.frameIndex + '/' + FRAMES_PER_POSE + '...';

      if (state.frameIndex >= FRAMES_PER_POSE) {
        clearInterval(state.captureTimer);
        advancePose();
      }
    });
  }

  function advancePose() {
    var nextIndex = state.poseIndex + 1;
    if (nextIndex < POSES.length) {
      startPose(nextIndex);
    } else {
      // All poses captured — stop camera and show processing state
      stopCamera();
      showProcessingOverlay();
      captureInstruction.textContent = 'Processing your photos';
      captureProgress.textContent = 'This may take up to a minute...';
      captureProgress.style.color = '';
      updateDotStepper();
      processCapturedFrames();
    }
  }

  function stopCamera() {
    clearInterval(state.captureTimer);
    if (state.cameraStream) {
      state.cameraStream.getTracks().forEach(function (track) { track.stop(); });
      state.cameraStream = null;
    }
  }

  function processCapturedFrames() {
    if (state.processing) return;
    state.processing = true;

    var frames = state.capturedFrames.map(function (dataUrl) {
      return dataUrl.split(',')[1];
    });

    fetch('/api/portal/process-capture', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ frames: frames })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        state.processing = false;
        if (!result.ok) {
          showProcessingFailed(result.data.error || 'Face processing failed. Please try again.');
          return;
        }

        state.faceEncoding = result.data.face_encoding;

        // Recapture mode: skip details, just update face and show confirmation
        if (window.__STUDENT__.recapture && window.__STUDENT__.isEnrolled) {
          submitRecapture();
        } else {
          goToStep('details');
        }
      })
      .catch(function () {
        state.processing = false;
        showProcessingFailed('Network error. Please check your connection and try again.');
      });
  }

  function submitRecapture() {
    fetch('/api/portal/face', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ face_encoding: state.faceEncoding })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        if (!result.ok) {
          showProcessingFailed(result.data.error || 'Failed to update face data.');
          return;
        }
        // Fetch existing profile for summary
        return fetch('/api/portal/profile')
          .then(function (res) { return res.json(); })
          .then(function (profile) {
            $('summary-name').textContent = profile.name || '';
            $('summary-matric').textContent = profile.matric || '';
            $('summary-level').textContent = (profile.level || '') + ' Level';
            $('summary-courses').textContent = (profile.courses && profile.courses.length)
              ? profile.courses.join(', ')
              : 'None yet';
            goToStep('confirm');
          });
      })
      .catch(function () {
        showProcessingFailed('Network error. Please try again.');
      });
  }

  function showProcessingFailed(message) {
    showCameraView(); // restore camera viewport look
    showError('capture-error', message);
    captureInstruction.textContent = 'Processing failed';
    captureProgress.textContent = 'Tap "Retry" to capture your photos again.';

    // Show retry button
    var retryBtn = $('btn-capture-retry');
    if (retryBtn) retryBtn.style.display = '';
  }

  /* --- Capture back button --- */

  $('btn-capture-back').addEventListener('click', function () {
    stopCamera();
    resetCaptureState();
    goToStep('welcome');
  });

  /* --- Retry button --- */

  var retryBtn = $('btn-capture-retry');
  if (retryBtn) {
    retryBtn.addEventListener('click', function () {
      hideError('capture-error');
      retryBtn.style.display = 'none';
      resetCaptureState();

      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } })
        .then(function (stream) {
          state.cameraStream = stream;
          video.srcObject = stream;
          showCameraView();
          startPose(0);
        })
        .catch(function () {
          goToStep('welcome');
        });
    });
  }

  function resetCaptureState() {
    state.capturedFrames = [];
    state.poseIndex = 0;
    state.frameIndex = 0;
    captureProgress.textContent = '';
    captureProgress.style.color = '';
    captureInstruction.textContent = '';
    showCameraView();
  }

  /* ======================================================================
     Step 3: Academic details
     ====================================================================== */

  var courseInput = $('course-input');
  var chipList = $('chip-list');

  function renderChips() {
    chipList.innerHTML = '';
    state.courses.forEach(function (code, i) {
      var chip = document.createElement('span');
      chip.className = 'chip';
      chip.textContent = code;

      var removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'chip-remove';
      removeBtn.setAttribute('aria-label', 'Remove ' + code);
      removeBtn.innerHTML = '&times;';
      removeBtn.addEventListener('click', function () {
        state.courses.splice(i, 1);
        renderChips();
      });

      chip.appendChild(removeBtn);
      chipList.appendChild(chip);
    });
  }

  function addCourse() {
    var val = courseInput.value.trim().toUpperCase();
    if (!val) return;
    if (!COURSE_CODE_RE.test(val)) {
      showError('details-error', 'Course code must be 3 letters + 3 digits (e.g. MTE413)');
      return;
    }
    hideError('details-error');
    if (state.courses.indexOf(val) !== -1) {
      courseInput.value = '';
      return;
    }
    state.courses.push(val);
    courseInput.value = '';
    renderChips();
    courseInput.focus();
  }

  $('btn-add-course').addEventListener('click', addCourse);

  /* --- Course autocomplete --- */

  var suggestionsEl = $('course-suggestions');
  var acActiveIndex = -1;
  var acDebounceTimer = null;

  function fetchCourseSuggestions(query) {
    if (!query || query.length < 1) {
      closeSuggestions();
      return;
    }
    clearTimeout(acDebounceTimer);
    acDebounceTimer = setTimeout(function () {
      fetch('/api/portal/courses/search?q=' + encodeURIComponent(query))
        .then(function (res) { return res.json(); })
        .then(function (results) {
          renderSuggestions(results);
        })
        .catch(function () { closeSuggestions(); });
    }, 150);
  }

  function renderSuggestions(results) {
    if (!results || results.length === 0) {
      closeSuggestions();
      return;
    }
    acActiveIndex = -1;
    suggestionsEl.innerHTML = '';
    results.forEach(function (code, i) {
      var item = document.createElement('div');
      item.className = 'course-autocomplete__item';
      item.textContent = code;
      item.dataset.index = i;
      item.addEventListener('mousedown', function (e) {
        e.preventDefault();
        selectSuggestion(code);
      });
      suggestionsEl.appendChild(item);
    });
    suggestionsEl.classList.add('open');
  }

  function closeSuggestions() {
    suggestionsEl.classList.remove('open');
    suggestionsEl.innerHTML = '';
    acActiveIndex = -1;
  }

  function selectSuggestion(code) {
    courseInput.value = code;
    closeSuggestions();
    courseInput.focus();
  }

  function navigateSuggestions(direction) {
    var items = suggestionsEl.querySelectorAll('.course-autocomplete__item');
    if (items.length === 0) return;
    acActiveIndex = Math.max(-1, Math.min(items.length - 1, acActiveIndex + direction));
    items.forEach(function (item, i) {
      item.classList.toggle('active', i === acActiveIndex);
    });
  }

  courseInput.addEventListener('input', function () {
    var val = this.value.trim().toUpperCase();
    this.value = val;
    fetchCourseSuggestions(val);
  });

  courseInput.addEventListener('blur', function () {
    setTimeout(closeSuggestions, 150);
  });

  courseInput.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      navigateSuggestions(1);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      navigateSuggestions(-1);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      var items = suggestionsEl.querySelectorAll('.course-autocomplete__item');
      if (acActiveIndex >= 0 && items[acActiveIndex]) {
        selectSuggestion(items[acActiveIndex].textContent);
      } else {
        addCourse();
      }
    } else if (e.key === 'Escape') {
      closeSuggestions();
    }
  });

  /* --- Details back button --- */

  $('btn-details-back').addEventListener('click', function () {
    goToStep('capture');
    resetCaptureState();
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } } })
      .then(function (stream) {
        state.cameraStream = stream;
        video.srcObject = stream;
        showCameraView();
        startPose(0);
      })
      .catch(function () {
        goToStep('welcome');
      });
  });

  /* --- Submit enrollment --- */

  $('btn-details-submit').addEventListener('click', function () {
    var btn = this;
    hideError('details-error');

    var level = $('level-select').value;
    if (!level) {
      showError('details-error', 'Please select your level.');
      return;
    }

    if (!state.faceEncoding) {
      showError('details-error', 'Face capture is missing. Please go back and recapture.');
      return;
    }

    setButtonLoading(btn, true);

    fetch('/api/portal/enroll', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        face_encoding: state.faceEncoding,
        level: level,
        courses: state.courses
      })
    })
      .then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); })
      .then(function (result) {
        setButtonLoading(btn, false);
        if (!result.ok) {
          showError('details-error', result.data.error || 'Enrollment failed. Please try again.');
          return;
        }

        populateSummary(level);
        goToStep('confirm');
      })
      .catch(function () {
        setButtonLoading(btn, false);
        showError('details-error', 'Network error. Please check your connection and try again.');
      });
  });

  function populateSummary(level) {
    var student = window.__STUDENT__ || {};
    $('summary-name').textContent = student.name || '';
    $('summary-matric').textContent = student.matric || '';
    $('summary-level').textContent = level + ' Level';
    $('summary-courses').textContent = state.courses.length
      ? state.courses.join(', ')
      : 'None yet';
  }

  /* ======================================================================
     Step 4: Go home
     ====================================================================== */

  $('btn-go-home').addEventListener('click', function () {
    window.location.href = '/portal/';
  });

  /* ======================================================================
     Cleanup on page unload
     ====================================================================== */

  window.addEventListener('beforeunload', stopCamera);
})();
