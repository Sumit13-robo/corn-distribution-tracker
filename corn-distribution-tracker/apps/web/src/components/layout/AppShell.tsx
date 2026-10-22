import { useCallback, useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/**
 * Role-aware layout shell. On narrow screens the sidebar is an off-canvas
 * drawer; route changes focus the main region so keyboard and screen-reader
 * users are not left on a stale navigation link.
 */
export function AppShell() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const asideWasOpen = useRef(false);
  const mainRef = useRef<HTMLElement>(null);

  const closeNavigation = useCallback(() => setNavOpen(false), []);

  useEffect(() => {
    if (navOpen) {
      asideWasOpen.current = true;
      return;
    }
    if (!asideWasOpen.current) return;
    asideWasOpen.current = false;
    const frame = window.requestAnimationFrame(() => {
      document.getElementById("nav-menu-button")?.focus();
    });
    return () => window.cancelAnimationFrame(frame);
  }, [navOpen]);

  useEffect(() => {
    const frame = window.requestAnimationFrame(() => {
      window.scrollTo({ top: 0, left: 0, behavior: "auto" });
      mainRef.current?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [location.pathname]);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!navOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [navOpen]);

  useEffect(() => {
    const desktop = window.matchMedia("(min-width: 901px)");
    function closeOnDesktop(event: MediaQueryListEvent) {
      if (event.matches) setNavOpen(false);
    }
    desktop.addEventListener("change", closeOnDesktop);
    return () => desktop.removeEventListener("change", closeOnDesktop);
  }, []);

  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <Sidebar open={navOpen} onClose={closeNavigation} />
      <div className="main-area">
        <TopBar onOpenNavigation={() => setNavOpen(true)} navigationOpen={navOpen} />
        <main id="main-content" ref={mainRef} className="page" tabIndex={-1}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
