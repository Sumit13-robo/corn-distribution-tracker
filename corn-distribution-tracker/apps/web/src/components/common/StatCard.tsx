import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  hint?: ReactNode;
  definition?: string;
  testId?: string;
}

/** KPI card. `definition` explains the metric (denominators/units) per spec. */
export function StatCard({ label, value, unit, hint, definition, testId }: StatCardProps) {
  return (
    <div className="stat-card" data-testid={testId ?? undefined}>
      <div className="label">{label}</div>
      <div className="value">
        {value}
        {unit ? <span className="unit">{unit}</span> : null}
      </div>
      {hint ? <div className="hint">{hint}</div> : null}
      {definition ? (
        <p className="hint" style={{ marginTop: "var(--space-1)" }}>
          {definition}
        </p>
      ) : null}
    </div>
  );
}
