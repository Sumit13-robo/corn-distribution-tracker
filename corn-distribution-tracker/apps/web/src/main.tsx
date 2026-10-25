import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { restoreSession } from "./lib/session";
import "maplibre-gl/dist/maplibre-gl.css";
import "./styles/global.css";

// Session restore kick-off: ask /auth/me whether the HttpOnly session cookie is
// still valid while the router shows a loading state.
void restoreSession();

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root missing from index.html");
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
