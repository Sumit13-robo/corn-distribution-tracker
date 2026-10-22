import type { ReactNode } from "react";

interface FormFieldChildProps {
  /** Value for aria-describedby on the input: helper (and error) element ids. */
  describedBy: string;
}

interface FormFieldProps {
  id: string;
  label: string;
  required?: boolean;
  helper?: ReactNode;
  error?: string | null;
  children: ReactNode | ((props: FormFieldChildProps) => ReactNode);
  /** Extra wrapping class so callers can switch to row layouts. */
  className?: string;
}

/**
 * Form field wrapper that wires label + helper text + error message together.
 * Pass `aria-describedby={describedBy}` to the input using the render form so
 * screen readers announce helper and validation errors with the control.
 */
export function FormField({ id, label, required, helper, error, children, className }: FormFieldProps) {
  const describedByIds = [helper ? `${id}-helper` : null, error ? `${id}-error` : null].filter(Boolean).join(" ");
  return (
    <div className={`form-field ${className ?? ""}`.trim()}>
      <label htmlFor={id}>
        {label}
        {required ? <span aria-hidden="true"> *</span> : null}
      </label>
      {typeof children === "function" ? children({ describedBy: describedByIds }) : children}
      {helper ? (
        <span className="helper" id={`${id}-helper`}>
          {helper}
        </span>
      ) : null}
      {error ? (
        <span className="error" id={`${id}-error`} role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
