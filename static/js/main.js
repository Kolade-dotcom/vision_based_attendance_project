/**
 * Smart Vision-Based Attendance System
 * Main Entry Point (ES Module)
 */

import { initDashboard } from "./pages/dashboard.js";
import { initEnrollment } from "./pages/enrollment.js";

document.addEventListener("DOMContentLoaded", function () {
  console.log("Smart Attendance System initialized (Modular)");

  // Initialize based on current page elements
  if (document.getElementById("start-camera")) {
    initDashboard();
    setupCameraListeners("camera-feed", "start-camera");
  }

  if (document.getElementById("enroll-form")) {
    initEnrollment();
    setupCameraListeners("enroll-camera", "start-enroll-camera");
  }
});

/**
 * Shared camera setup logic
 */
function setupCameraListeners(containerId, buttonId) {
  const btn = document.getElementById(buttonId);
  if (btn) {
    btn.addEventListener("click", function () {
      startCameraFeed(containerId);
      // If we are on enrollment, we might need to enable capture button
      const captureBtn = document.getElementById("capture-face");
      if (captureBtn) captureBtn.disabled = false;
    });
  }
}

/**
 * Start camera feed (placeholder implementation)
 * In a real app, this would use the /video_feed endpoint with an <img> tag
 */
function startCameraFeed(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return;

  // Clear container and ensure full height/width without padding
  container.innerHTML = `
        <video id="video-${containerId}" autoplay playsinline class="w-full h-full object-cover rounded-lg"></video>
    `;

  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices
      .getUserMedia({ video: true })
      .then(function (stream) {
        const video = document.getElementById(`video-${containerId}`);
        if (video) {
          video.srcObject = stream;
        }
      })
      .catch(function (err) {
        console.error("Error accessing camera:", err);
        container.innerHTML = `
                    <div class="flex flex-col items-center justify-center h-full text-center p-4">
                        <p class="text-red-500 font-medium mb-1">⚠️ Camera Error</p>
                        <p class="text-xs text-slate-500">Access denied or unavailable</p>
                    </div>
                `;
      });
  }
}
