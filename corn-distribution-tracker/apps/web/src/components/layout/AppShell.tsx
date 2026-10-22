import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";

/** Role-aware layout shell (skip link, sidebar, top bar, main region). */
export function AppShell() {
  return (
    <div className="app-shell">
      <a href="#main-content" className="sr-only">
        Skip to main content
      </a>
      <Sidebar />
      <div className="main-area">
        <TopBar />
        <main id="main-content" className="page">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
