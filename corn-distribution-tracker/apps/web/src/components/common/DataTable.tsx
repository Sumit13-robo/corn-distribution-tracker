import { useMemo, useState } from "react";
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

  if (rows.length === 0 && emptyState) {
    return <div>{emptyState}</div>;
  }

  return (
    <div className="data-table-wrap">
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
                  aria-sort={isSorted ? (sortDir === "asc" ? "ascending" : "descending") : sortable ? "none" : undefined}
                  {...(sortable
                    ? {
                        onClick: () => {
                          if (sortKey === column.key) {
                            setSortDir(sortDir === "asc" ? "desc" : "asc");
                          } else {
                            setSortKey(column.key);
                            setSortDir(column.initialSort ?? "asc");
                          }
                        },
                      }
                    : {})}
                >
                  {sortable ? (
                    <button type="button" className="btn ghost" style={{ padding: 0, color: "inherit" }}>
                      {column.header} {isSorted ? (sortDir === "asc" ? "↑" : "↓") : ""}
                      <span className="sr-only">{isSorted ? " (sorted)" : " (activates sorting)"}</span>
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row) => (
            <tr key={rowKey(row)}>
              {columns.map((column) => (
                <td key={column.key} className={cx(column.numeric && "num")}>
                  {column.render ? column.render(row) : String(getPath(row, column.key) ?? "—")}
                </td>
              ))}
              {rowExpandDetail ? <td>{rowExpandDetail(row)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Renders `row.columnKey` when no custom `render` function is provided. */
function getPath(row: unknown, key: string): unknown {
  if (typeof row !== "object" || row === null) return undefined;
  return (row as Record<string, unknown>)[key];
}
