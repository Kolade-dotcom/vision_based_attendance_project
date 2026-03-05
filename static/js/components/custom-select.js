/**
 * CustomSelect — A styled dropdown replacement for native <select>.
 *
 * Usage:
 *   var sel = new CustomSelect(containerEl, {
 *     options: [{ value: 'all', label: 'All Courses' }, ...],
 *     value: 'all',
 *     placeholder: 'Select...',
 *     compact: false,
 *     onChange: function(value, label) { ... }
 *   });
 *
 *   sel.setValue('MTE411');
 *   sel.setOptions([...]);
 *   sel.destroy();
 */
(function () {
  'use strict';

  function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
  }

  var CHEVRON_SVG = '<svg class="custom-select__chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>';

  var CHECK_SVG = '<svg class="custom-select__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';

  function CustomSelect(container, opts) {
    this.container = container;
    this.opts = opts || {};
    this.options = this.opts.options || [];
    this.value = this.opts.value !== undefined ? this.opts.value : '';
    this.placeholder = this.opts.placeholder || 'Select...';
    this.compact = !!this.opts.compact;
    this.onChange = this.opts.onChange || null;
    this.isOpen = false;

    this._onTriggerClick = this._handleTriggerClick.bind(this);
    this._onDocClick = this._handleDocClick.bind(this);
    this._onKeyDown = this._handleKeyDown.bind(this);

    this._build();
  }

  CustomSelect.prototype._build = function () {
    this.container.innerHTML = '';

    var root = document.createElement('div');
    root.className = 'custom-select' + (this.compact ? ' custom-select--compact' : '');
    this.root = root;

    // Trigger button
    var trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'custom-select__trigger';
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    if (this.opts.ariaLabel) {
      trigger.setAttribute('aria-label', this.opts.ariaLabel);
    }
    this.trigger = trigger;

    var valueSpan = document.createElement('span');
    valueSpan.className = 'custom-select__value';
    this.valueSpan = valueSpan;
    trigger.appendChild(valueSpan);

    var chevronSpan = document.createElement('span');
    chevronSpan.innerHTML = CHEVRON_SVG;
    trigger.appendChild(chevronSpan.firstChild);

    root.appendChild(trigger);

    // Menu
    var menu = document.createElement('div');
    menu.className = 'custom-select__menu';
    menu.setAttribute('role', 'listbox');
    this.menu = menu;
    root.appendChild(menu);

    this.container.appendChild(root);

    this._renderOptions();
    this._updateDisplay();

    trigger.addEventListener('click', this._onTriggerClick);
    document.addEventListener('click', this._onDocClick, true);
    trigger.addEventListener('keydown', this._onKeyDown);
  };

  CustomSelect.prototype._renderOptions = function () {
    var self = this;
    this.menu.innerHTML = '';

    this.options.forEach(function (opt) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'custom-select__option';
      btn.setAttribute('role', 'option');
      btn.setAttribute('data-value', opt.value);

      if (opt.value === self.value) {
        btn.classList.add('custom-select__option--active');
        btn.setAttribute('aria-selected', 'true');
      }

      var checkSpan = document.createElement('span');
      checkSpan.innerHTML = CHECK_SVG;
      btn.appendChild(checkSpan.firstChild);

      var label = document.createElement('span');
      label.textContent = opt.label;
      btn.appendChild(label);

      btn.addEventListener('click', function (e) {
        e.stopPropagation();
        self._select(opt.value, opt.label);
      });

      self.menu.appendChild(btn);
    });
  };

  CustomSelect.prototype._updateDisplay = function () {
    var selected = null;
    for (var i = 0; i < this.options.length; i++) {
      if (this.options[i].value === this.value) {
        selected = this.options[i];
        break;
      }
    }

    if (selected) {
      this.valueSpan.textContent = selected.label;
      this.valueSpan.classList.remove('custom-select__value--placeholder');
    } else {
      this.valueSpan.textContent = this.placeholder;
      this.valueSpan.classList.add('custom-select__value--placeholder');
    }
  };

  CustomSelect.prototype._select = function (value, label) {
    this.value = value;
    this._close();
    this._renderOptions();
    this._updateDisplay();
    if (this.onChange) {
      this.onChange(value, label);
    }
  };

  CustomSelect.prototype._handleTriggerClick = function (e) {
    e.stopPropagation();
    if (this.isOpen) {
      this._close();
    } else {
      this._open();
    }
  };

  CustomSelect.prototype._handleDocClick = function (e) {
    if (this.isOpen && this.root && !this.root.contains(e.target)) {
      this._close();
    }
  };

  CustomSelect.prototype._handleKeyDown = function (e) {
    if (e.key === 'Escape' && this.isOpen) {
      this._close();
      e.preventDefault();
    }
    if (e.key === 'Enter' || e.key === ' ') {
      if (!this.isOpen) {
        this._open();
        e.preventDefault();
      }
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault();
      var idx = -1;
      for (var i = 0; i < this.options.length; i++) {
        if (this.options[i].value === this.value) { idx = i; break; }
      }
      if (e.key === 'ArrowDown') {
        idx = Math.min(idx + 1, this.options.length - 1);
      } else {
        idx = Math.max(idx - 1, 0);
      }
      this._select(this.options[idx].value, this.options[idx].label);
    }
  };

  CustomSelect.prototype._open = function () {
    this.isOpen = true;
    this.root.classList.add('custom-select--open');
    this.trigger.setAttribute('aria-expanded', 'true');
  };

  CustomSelect.prototype._close = function () {
    this.isOpen = false;
    this.root.classList.remove('custom-select--open');
    this.trigger.setAttribute('aria-expanded', 'false');
  };

  CustomSelect.prototype.setValue = function (value) {
    this.value = value;
    this._renderOptions();
    this._updateDisplay();
  };

  CustomSelect.prototype.setOptions = function (options, value) {
    this.options = options;
    if (value !== undefined) {
      this.value = value;
    }
    this._renderOptions();
    this._updateDisplay();
  };

  CustomSelect.prototype.getValue = function () {
    return this.value;
  };

  CustomSelect.prototype.destroy = function () {
    if (this.trigger) {
      this.trigger.removeEventListener('click', this._onTriggerClick);
      this.trigger.removeEventListener('keydown', this._onKeyDown);
    }
    document.removeEventListener('click', this._onDocClick, true);
    this.container.innerHTML = '';
  };

  // Export globally
  window.CustomSelect = CustomSelect;
})();
