import { AppProviders } from "./app/providers";
import { AppRoutes } from "./app/router";

/** Application shell: providers plus the role-aware router. */
export function App() {
  return (
    <AppProviders>
      <AppRoutes />
    </AppProviders>
  );
}
