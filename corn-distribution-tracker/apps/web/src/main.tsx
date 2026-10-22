import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { restoreSession } from "./lib/session";
import "./styles/global.css";

// Session restore kick-off: the access token stays in memory; on a reload the
// HttpOnly refresh cookie re-issues it while the router shows a loading state.
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
