/**
 * Simple Toast Notification System
 * Mimics Shadcn UI toast style
 */

function showToast(title, description, type = "default") {
  const container = document.getElementById("toast-container");

  // Create toast element
  const toast = document.createElement("div");

  // Base classes
  let classes =
    "pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all data-[swipe=cancel]:translate-x-0 data-[swipe=end]:translate-x-[var(--radix-toast-swipe-end-x)] data-[swipe=move]:translate-x-[var(--radix-toast-swipe-move-x)] data-[swipe=move]:transition-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[swipe=end]:animate-out data-[state=closed]:fade-out-80 data-[state=closed]:slide-out-to-right-full data-[state=open]:slide-in-from-top-full data-[state=open]:sm:slide-in-from-bottom-full min-w-[300px] bg-white";

  // Type specific styling
  if (type === "error") {
    // destructive
    classes += " border-red-200 bg-red-50 text-red-900";
  } else if (type === "success") {
    classes += " border-slate-200 bg-white text-slate-950";
  } else {
    classes += " border-slate-200 bg-white text-slate-950";
  }

  toast.className = classes;

  // Toast Content
  const content = `
        <div class="grid gap-1">
            ${title ? `<div class="text-sm font-semibold">${title}</div>` : ""}
            ${
              description
                ? `<div class="text-sm opacity-90">${description}</div>`
                : ""
            }
        </div>
        <button class="absolute right-2 top-2 rounded-md p-1 text-slate-950/50 opacity-0 transition-opacity hover:text-slate-950 focus:opacity-100 focus:outline-none focus:ring-2 group-hover:opacity-100" onclick="this.parentElement.remove()">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" class="h-4 w-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
        </button>
    `;

  toast.innerHTML = content;

  // Add to container
  container.appendChild(toast);

  // Auto remove after 3 seconds
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Export for module usage if needed (though currently loaded via script tag)
window.showToast = showToast;
