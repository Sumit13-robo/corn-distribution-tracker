import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="state-block" data-testid="empty-state">
      <span className="title">{title}</span>
      {description ? <div>{description}</div> : null}
      {action ? <div className="actions">{action}</div> : null}
    </div>
  );
}
