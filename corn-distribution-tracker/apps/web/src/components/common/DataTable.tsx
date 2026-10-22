import { useId, useMemo, useState } from "react";
import { cx } from "../../lib/format";
import type { ReactNode } from "react";

export interface DataTableColumn<T> {
  key: string;
  header: string;
  render?: (row: T) => ReactNode;
  /** Right-aligned numeric column (tabular figures). */
  numeric?: boolean;
  /** Value used for client-side sorting within the loaded page. */
  sortValue?: (row: T) => string | number;
  initialSort?: "asc" | "desc";
}

interface DataTableProps<T> {
  columns: Array<DataTableColumn<T>>;
  rows: T[];
  caption: string;
  rowKey: (row: T) => string;
  emptyState?: ReactNode;
  rowExpandDetail?: (row: T) => ReactNode;
}

/**
 * Reusable, accessible table: sortable headers expose aria-sort, the caption
 * identifies the data, and sorting happens inside the already loaded page
 * (server-side filtering/pagination stays authoritative).
 */
export function DataTable<T>({ columns, rows, caption, rowKey, emptyState, rowExpandDetail }: DataTableProps<T>) {
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const sortControlId = useId();

  const sortedRows = useMemo(() => {
    if (sortKey === null) return rows;
    const column = columns.find((c) => c.key === sortKey);
    const sortValue = column?.sortValue;
    if (!sortValue) return rows;
    const sorted = [...rows].sort((a, b) => {
      const av = sortValue(a);
      const bv = sortValue(b);
      if (typeof av === "number" && typeof bv === "number") return av - bv;
      return String(av).localeCompare(String(bv));
    });
    return sortDir === "asc" ? sorted : sorted.reverse();
  }, [rows, columns, sortKey, sortDir]);

  const sortableColumns = columns.filter((column) => column.sortValue);

  function activateSort(columnKey: string): void {
    if (sortKey === columnKey) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortKey(columnKey);
      const column = columns.find((candidate) => candidate.key === columnKey);
      setSortDir(column?.initialSort ?? "asc");
    }
  }

  function cell(column: DataTableColumn<T>, row: T): ReactNode {
    return column.render ? column.render(row) : String(getPath(row, column.key) ?? "—");
  }

  if (rows.length === 0 && emptyState) {
    return <div>{emptyState}</div>;
  }

  return (
    <div>
      <div className="data-card-tools">
        {sortableColumns.length > 0 ? (
          <>
            <label className="data-card-sort" htmlFor={sortControlId}>
              Sort by
              <select
                id={sortControlId}
                value={sortKey ?? ""}
                onChange={(event) => {
                  if (!event.target.value) {
                    setSortKey(null);
                    return;
                  }
                  activateSort(event.target.value);
                }}
              >
                <option value="">Default order</option>
                {sortableColumns.map((column) => (
                  <option key={column.key} value={column.key}>
                    {column.header}
                  </option>
                ))}
              </select>
            </label>
            <button
              type="button"
              className="btn secondary small"
              onClick={() => sortKey && activateSort(sortKey)}
              disabled={!sortKey}
            >
              {sortDir === "asc" ? "Ascending" : "Descending"}
            </button>
          </>
        ) : null}
      </div>

      <div
        className="data-table-wrap data-table-responsive"
        role="region"
        aria-label={`${caption}. Scroll horizontally if needed.`}
        tabIndex={0}
      >
        <table className="data-table">
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {columns.map((column) => {
                const sortable = Boolean(column.sortValue);
                const isSorted = sortKey === column.key;
                return (
                  <th
                    key={column.key}
                    scope="col"
                    className={cx(column.numeric && "num")}
                    aria-sort={
                      isSorted ? (sortDir === "asc" ? "ascending" : "descending") : sortable ? "none" : undefined
                    }
                    {...(sortable ? { onClick: () => activateSort(column.key) } : {})}
                  >
                    {sortable ? (
                      <button type="button" className="table-sort">
                        {column.header} {isSorted ? (sortDir === "asc" ? "↑" : "↓") : ""}
                        <span className="sr-only">{isSorted ? " (sorted)" : " (activates sorting)"}</span>
                      </button>
                    ) : (
                      column.header
                    )}
                  </th>
                );
              })}
              {rowExpandDetail ? (
                <th scope="col">
                  <span className="sr-only">Actions</span>
                </th>
              ) : null}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td key={column.key} className={cx(column.numeric && "num")}>
                    {cell(column, row)}
                  </td>
                ))}
                {rowExpandDetail ? <td className="row-actions">{rowExpandDetail(row)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="data-cards" aria-label={caption}>
        {sortedRows.map((row) => (
          <li key={rowKey(row)} className="data-card">
            <dl className="data-card-fields">
              {columns.map((column) => (
                <div className="data-card-field" key={column.key}>
                  <dt>{column.header}</dt>
                  <dd className={cx(column.numeric && "num")}>{cell(column, row)}</dd>
                </div>
              ))}
              {rowExpandDetail ? (
                <div className="data-card-field">
                  <dt>Actions</dt>
                  <dd className="row-actions">{rowExpandDetail(row)}</dd>
                </div>
              ) : null}
            </dl>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Renders `row.columnKey` when no custom `render` function is provided. */
function getPath(row: unknown, key: string): unknown {
  if (typeof row !== "object" || row === null) return undefined;
  return (row as Record<string, unknown>)[key];
}
