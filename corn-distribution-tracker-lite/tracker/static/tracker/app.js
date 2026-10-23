/* Progressive enhancement only. Every workflow works without this file. */
(() => {
  "use strict";

  const sidebar = document.getElementById("sidebar");
  const openButton = document.querySelector("[data-sidebar-open]");
  const closeButtons = document.querySelectorAll("[data-sidebar-close]");
  const backdrop = document.querySelector(".sidebar-backdrop");
  const menuQuery = window.matchMedia("(max-width: 900px)");

  function isMenuMode() {
    return menuQuery.matches;
  }

  function setSidebar(open, { restoreFocus = false } = {}) {
    if (!sidebar || !openButton || !backdrop) return;
    sidebar.classList.toggle("is-open", open);
    backdrop.classList.toggle("is-open", open);
    openButton.setAttribute("aria-expanded", String(open));
    document.body.style.overflow = open ? "hidden" : "";
    if (open) {
      sidebar.querySelector("a, button, input, select, textarea")?.focus();
    } else if (restoreFocus) {
      openButton.focus();
    }
  }

  openButton?.addEventListener("click", () => setSidebar(true));
  closeButtons.forEach((button) => {
    button.addEventListener("click", () => setSidebar(false, { restoreFocus: true }));
  });
  menuQuery.addEventListener?.("change", () => {
    if (!isMenuMode()) setSidebar(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && sidebar?.classList.contains("is-open")) {
      setSidebar(false, { restoreFocus: true });
    }
  });

  // Clicking a navigation target should close the mobile drawer.
  sidebar?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      if (isMenuMode()) setSidebar(false);
    });
  });

  // Dismissible notices.
  document.querySelectorAll("[data-dismiss]").forEach((button) => {
    button.addEventListener("click", () => {
      const notice = button.closest(".notice");
      notice?.remove();
      const stack = document.querySelector(".notice-stack");
      if (stack && !stack.children.length) stack.remove();
    });
  });

  // Destructive or state-changing buttons ask for confirmation.
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const message = form.getAttribute("data-confirm");
      if (message && !window.confirm(message)) {
        event.preventDefault();
      }
    });
  });

  // Give inline validation errors an accessible relationship and invalid state.
  document.querySelectorAll(".form-field").forEach((field) => {
    const control = field.querySelector("input, select, textarea");
    if (!control) return;
    const errors = Array.from(field.querySelectorAll(".error"));
    if (!errors.length) return;
    control.setAttribute("aria-invalid", "true");
    const describedBy = new Set(
      (control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean),
    );
    errors.forEach((error, index) => {
      if (!error.id) error.id = `${control.id || "field"}-error-${index + 1}`;
      describedBy.add(error.id);
    });
    const help = field.querySelector(".helper");
    if (help?.id) describedBy.add(help.id);
    if (describedBy.size) {
      control.setAttribute("aria-describedby", Array.from(describedBy).join(" "));
    }
  });

  // Make horizontally scrollable tables reachable by keyboard.
  function enhanceTables() {
    document.querySelectorAll(".table-wrap").forEach((wrap) => {
      const scrollable = wrap.scrollWidth > wrap.clientWidth + 1;
      if (scrollable) {
        wrap.setAttribute("tabindex", "0");
        if (!wrap.getAttribute("role")) wrap.setAttribute("role", "region");
        if (!wrap.getAttribute("aria-label")) {
          const heading = wrap.closest(".section")?.querySelector("h2");
          wrap.setAttribute(
            "aria-label",
            heading ? `${heading.textContent.trim()} table, scrollable` : "Scrollable data table",
          );
        }
      } else {
        wrap.removeAttribute("tabindex");
      }
    });
  }

  enhanceTables();
  window.addEventListener("resize", enhanceTables);
})();
