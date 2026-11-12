/**
 * app/static/js/main.js — Global UI behaviors
 *
 * Handles:
 * - Sidebar toggle (mobile)
 * - Alert dismiss
 * - Dark mode toggle
 * - Confirm dialog (delete protection)
 * - Toast notifications
 * - Dropdown menus
 * - Form loading states
 */

(function () {
    "use strict";

    // ---- Dark Mode ----
    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("theme", theme);
    }

    // Default to dark theme matching the logo
    const savedTheme = localStorage.getItem("theme") || "dark";
    applyTheme(savedTheme);

    // ---- Sidebar toggle (mobile) ----
    function initSidebar() {
        const toggle = document.getElementById("sidebarToggle");
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("sidebarOverlay");

        if (!toggle || !sidebar) return;

        function openSidebar() {
            sidebar.classList.add("open");
            overlay && overlay.classList.add("open");
        }

        function closeSidebar() {
            sidebar.classList.remove("open");
            overlay && overlay.classList.remove("open");
        }

        toggle.addEventListener("click", () => {
            sidebar.classList.contains("open") ? closeSidebar() : openSidebar();
        });

        overlay && overlay.addEventListener("click", closeSidebar);
    }

    // ---- Alert dismiss ----
    function initAlerts() {
        document.querySelectorAll(".alert-close").forEach((btn) => {
            btn.addEventListener("click", () => {
                const alert = btn.closest(".alert");
                if (alert) {
                    alert.style.opacity = "0";
                    alert.style.transition = "opacity 0.3s";
                    setTimeout(() => alert.remove(), 300);
                }
            });
        });

        // Auto-dismiss success/info alerts after 5 seconds
        document.querySelectorAll(".alert-success, .alert-info").forEach((alert) => {
            setTimeout(() => {
                if (alert && alert.parentNode) {
                    alert.style.opacity = "0";
                    alert.style.transition = "opacity 0.5s";
                    setTimeout(() => alert.remove(), 500);
                }
            }, 5000);
        });
    }

    // ---- Confirm Delete dialog ----
    // Usage: <button data-confirm="Are you sure?" form="delete-form-123">Delete</button>
    // Or: <form data-confirm="Are you sure?">
    function initConfirmDialogs() {
        const overlay = document.getElementById("confirmOverlay");
        const messageEl = document.getElementById("confirmMessage");
        const confirmBtn = document.getElementById("confirmSubmit");
        const cancelBtn = document.getElementById("confirmCancel");

        if (!overlay) return;

        let pendingForm = null;

        function showConfirm(message, form) {
            if (messageEl) messageEl.textContent = message;
            pendingForm = form;
            overlay.classList.add("open");
        }

        function hideConfirm() {
            overlay.classList.remove("open");
            pendingForm = null;
        }

        cancelBtn && cancelBtn.addEventListener("click", hideConfirm);
        overlay.addEventListener("click", (e) => {
            if (e.target === overlay) hideConfirm();
        });

        confirmBtn &&
            confirmBtn.addEventListener("click", () => {
                if (pendingForm) {
                    pendingForm.submit();
                }
                hideConfirm();
            });

        // Intercept form submits with data-confirm
        document.querySelectorAll("form[data-confirm]").forEach((form) => {
            form.addEventListener("submit", (e) => {
                const msg = form.dataset.confirm;
                e.preventDefault();
                showConfirm(msg, form);
            });
        });

        // Intercept button clicks that should confirm
        document.querySelectorAll("[data-confirm-form]").forEach((btn) => {
            btn.addEventListener("click", (e) => {
                const formId = btn.dataset.confirmForm;
                const form = document.getElementById(formId);
                if (form) {
                    e.preventDefault();
                    showConfirm(btn.dataset.confirm || "Are you sure?", form);
                }
            });
        });
    }

    // ---- Dropdown menus ----
    function initDropdowns() {
        document.querySelectorAll(".dropdown-trigger").forEach((trigger) => {
            trigger.addEventListener("click", (e) => {
                e.stopPropagation();
                const dropdown = trigger.closest(".dropdown");
                const isOpen = dropdown.classList.contains("open");

                // Close all dropdowns
                document.querySelectorAll(".dropdown.open").forEach((d) =>
                    d.classList.remove("open")
                );

                if (!isOpen) dropdown.classList.add("open");
            });
        });

        // Close on outside click
        document.addEventListener("click", () => {
            document.querySelectorAll(".dropdown.open").forEach((d) =>
                d.classList.remove("open")
            );
        });
    }

    // ---- Form loading states ----
    // Disables submit buttons during form submission to prevent double-submit
    function initFormProtection() {
        document.querySelectorAll("form:not([data-no-loading])").forEach((form) => {
            form.addEventListener("submit", () => {
                form.querySelectorAll('[type="submit"]').forEach((btn) => {
                    btn.disabled = true;
                    const originalText = btn.innerHTML;
                    btn.innerHTML = '<span class="spinner"></span> Saving…';
                    // Re-enable after 10s in case of server error
                    setTimeout(() => {
                        btn.disabled = false;
                        btn.innerHTML = originalText;
                    }, 10000);
                });
            });
        });
    }

    // ---- Theme toggle ----
    function initThemeToggle() {
        const toggleBtn = document.getElementById("themeToggle");
        if (!toggleBtn) return;

        toggleBtn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            const next = current === "dark" ? "light" : "dark";
            applyTheme(next);
            // Update icon
            updateThemeIcon(next);
        });
    }

    function updateThemeIcon(theme) {
        const icon = document.querySelector("#themeToggle .theme-icon");
        if (icon) icon.textContent = theme === "dark" ? "☀️" : "🌙";
    }

    // ---- File input preview ----
    function initFileInputs() {
        document.querySelectorAll(".file-input-label input[type=file]").forEach((input) => {
            input.addEventListener("change", () => {
                const label = input.closest(".file-input-label");
                const nameEl = label.querySelector(".file-name");
                if (nameEl) {
                    nameEl.textContent = input.files.length
                        ? input.files[0].name
                        : "Choose file…";
                }
            });
        });
    }

    // ---- Amount formatter — show formatted value on blur ----
    function initAmountFormatting() {
        document.querySelectorAll("input[data-type=amount]").forEach((input) => {
            input.addEventListener("blur", () => {
                const val = parseFloat(input.value);
                if (!isNaN(val)) {
                    input.value = val.toFixed(2);
                }
            });
        });
    }

    // ---- Toast API (callable from other scripts) ----
    window.showToast = function (message, type = "success") {
        const container = document.getElementById("toastContainer");
        if (!container) return;

        const icons = { success: "✓", danger: "✗", warning: "⚠", info: "ℹ" };
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${message}`;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    };

    // ---- Init all ----
    document.addEventListener("DOMContentLoaded", () => {
        initSidebar();
        initAlerts();
        initConfirmDialogs();
        initDropdowns();
        initFormProtection();
        initThemeToggle();
        initFileInputs();
        initAmountFormatting();

        // Apply theme from body attribute (set by Jinja from user preference)
        const bodyTheme = document.body.dataset.theme;
        if (bodyTheme) applyTheme(bodyTheme);
        updateThemeIcon(document.documentElement.getAttribute("data-theme") || "dark");

        // Register Service Worker for PWA installability
        if ("serviceWorker" in navigator && window.location.protocol === "https:") {
            window.addEventListener("load", () => {
                navigator.serviceWorker.register("/static/sw.js").catch(() => {});
            });
        }
    });
})();
