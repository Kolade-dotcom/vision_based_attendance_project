/**
 * Reusable Shadcn-style Combobox/Select Component
 * Supports searchable and non-searchable modes.
 */
export class Combobox {
  constructor({
    containerId,
    options = [],
    searchable = false,
    placeholder = "Select option...",
    onSelect,
    name = "",
  }) {
    console.log("Combobox: Constructor called for", containerId);
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error("Combobox: Container not found for ID:", containerId);
      return;
    }

    this.options = options; // Array of { value, label }
    this.searchable = searchable;
    this.placeholder = placeholder;
    this.onSelect = onSelect;
    this.name = name;
    this.value = "";
    this.isOpen = false;

    this.init();
    console.log("Combobox: Initialized");
  }

  init() {
    this.container.classList.add("relative", "w-full");

    // Hidden input for form submission
    this.hiddenInput = document.createElement("input");
    this.hiddenInput.type = "hidden";
    this.hiddenInput.name = this.name;
    this.container.appendChild(this.hiddenInput);

    // Trigger Button
    this.trigger = document.createElement("button");
    this.trigger.type = "button";
    this.trigger.className =
      "flex h-10 w-full items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2 text-sm ring-offset-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50";
    this.trigger.innerHTML = `
            <span class="truncate text-slate-500">${this.placeholder}</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 opacity-50"><path d="m6 9 6 6 6-6"/></svg>
        `;
    this.trigger.addEventListener("click", () => this.toggle());
    this.container.appendChild(this.trigger);

    // Dropdown List Container
    this.listContainer = document.createElement("div");
    this.listContainer.className =
      "absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border border-slate-200 bg-white p-1 text-slate-950 shadow-md data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[side=bottom]:slide-in-from-top-2 hidden";

    // Search Input (only if searchable)
    if (this.searchable) {
      const searchContainer = document.createElement("div");
      searchContainer.className =
        "flex items-center border-b px-3 pb-2 mb-1 sticky top-0 bg-white";
      searchContainer.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2 h-4 w-4 opacity-50"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                <input class="flex h-11 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-slate-500 disabled:cursor-not-allowed disabled:opacity-50" placeholder="Search..." />
            `;
      this.searchInput = searchContainer.querySelector("input");
      this.searchInput.addEventListener("input", (e) =>
        this.filterOptions(e.target.value)
      );
      this.listContainer.appendChild(searchContainer);
    }

    // Options List
    this.optionsList = document.createElement("div");
    this.listContainer.appendChild(this.optionsList);

    this.container.appendChild(this.listContainer);

    // Render initial options
    this.renderOptions(this.options);

    // Close on click outside
    document.addEventListener("click", (e) => {
      if (!this.container.contains(e.target)) {
        this.close();
      }
    });
  }

  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.open();
    }
  }

  open() {
    this.isOpen = true;
    this.listContainer.classList.remove("hidden");
    if (this.searchable) {
      this.searchInput.value = "";
      this.searchInput.focus();
      this.filterOptions("");
    }
  }

  close() {
    this.isOpen = false;
    this.listContainer.classList.add("hidden");
  }

  filterOptions(query) {
    const lowerQuery = query.toLowerCase();
    const filtered = this.options.filter((opt) =>
      opt.label.toLowerCase().includes(lowerQuery)
    );
    this.renderOptions(filtered);
  }

  renderOptions(options) {
    this.optionsList.innerHTML = "";
    if (options.length === 0) {
      this.optionsList.innerHTML = `<div class="py-6 text-center text-sm text-slate-500">No option found.</div>`;
      return;
    }

    options.forEach((opt) => {
      const item = document.createElement("div");
      const isSelected = this.value === opt.value;
      item.className = `relative flex cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none data-[disabled]:pointer-events-none data-[disabled]:opacity-50 hover:bg-slate-100 cursor-pointer ${
        isSelected ? "bg-slate-100" : ""
      }`;
      item.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2 h-4 w-4 ${
                  isSelected ? "opacity-100" : "opacity-0"
                }"><polyline points="20 6 9 17 4 12"/></svg>
                <span>${opt.label}</span>
            `;
      item.addEventListener("click", () => this.select(opt));
      this.optionsList.appendChild(item);
    });
  }

  select(option) {
    this.value = option.value;
    this.hiddenInput.value = option.value;

    // Update Trigger Text
    const textSpan = this.trigger.querySelector("span");
    textSpan.textContent = option.label;
    textSpan.classList.remove("text-slate-500");
    textSpan.classList.add("text-slate-900");

    this.close();

    if (this.onSelect) {
      this.onSelect(option.value);
    }
  }

  setOptions(newOptions) {
    this.options = newOptions;
    this.renderOptions(newOptions);
  }

  reset() {
    this.value = "";
    this.hiddenInput.value = "";
    const textSpan = this.trigger.querySelector("span");
    textSpan.textContent = this.placeholder;
    textSpan.classList.add("text-slate-500");
    textSpan.classList.remove("text-slate-900");
  }
}
