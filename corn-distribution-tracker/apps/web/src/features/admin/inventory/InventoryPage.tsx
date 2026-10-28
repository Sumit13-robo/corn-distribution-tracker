import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, newId } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { ConfirmDialog } from "../../../components/common/ConfirmDialog";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { StatCard } from "../../../components/common/StatCard";
import { useToast } from "../../../app/providers";
import { formatDateTime, formatKg } from "../../../lib/format";
import type { DistributorDetailOut, StockMovementOut } from "../../../types/domain";

/**
 * Inventory and ledger (SCREEN_SPECS): balances per account, receipts,
 * allocations, adjustments with reason + double confirmation, movement history
 * with reversal, and reconciliation status. There is deliberately no
 * manually-editable balance field anywhere — balances are derived from the
 * immutable ledger on the server.
 */
export function InventoryPage() {
  const queryClient = useQueryClient();
  const toast = useToast();

  const summary = useQuery({ queryKey: queryKeys.inventorySummary(), queryFn: () => api.inventorySummary() });

  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null);
  const ledger = useQuery({
    queryKey: queryKeys.accountLedger(selectedAccountId ?? "none"),
    queryFn: () => api.accountLedger(selectedAccountId as string),
    enabled: selectedAccountId !== null,
  });

  /* Receipt form */
  const [receiptQuantity, setReceiptQuantity] = useState("");
  const [receiptReference, setReceiptReference] = useState("");
  const [receiptNotes, setReceiptNotes] = useState("");

  /* Allocation form */
  const [allocationDistributor, setAllocationDistributor] = useState("");
  const [allocationQuantity, setAllocationQuantity] = useState("");

  /* Adjustment form (requires review/confirm + mandatory reason) */
  const [adjustmentAccount, setAdjustmentAccount] = useState("");
  const [adjustmentDestination, setAdjustmentDestination] = useState("");
  const [adjustmentQuantity, setAdjustmentQuantity] = useState("");
  const [adjustmentType, setAdjustmentType] = useState<"LOSS" | "RETURN">("LOSS");
  const [adjustmentReason, setAdjustmentReason] = useState("");
  const [adjustConfirmOpen, setAdjustConfirmOpen] = useState(false);

  /* Reversal prompt */
  const [reversalTarget, setReversalTarget] = useState<StockMovementOut | null>(null);
  const [reversalReason, setReversalReason] = useState("");

  const distributors = useQuery({ queryKey: queryKeys.distributors(""), queryFn: () => api.listDistributors() });

  const invalidateAll = () => {
    void queryClient.invalidateQueries({ queryKey: ["inventory-summary"] });
    void queryClient.invalidateQueries({ queryKey: ["account-ledger"] });
    void queryClient.invalidateQueries({ queryKey: ["distributors"] });
    void queryClient.invalidateQueries({ queryKey: ["analytics-overview"] });
  };

  const receipt = useMutation({
    mutationFn: () =>
      api.postReceipt(
        {
          quantity: receiptQuantity,
          unit: "KG",
          source_reference: receiptReference.trim(),
          notes: receiptNotes || null,
        },
        newId(),
      ),
    onSuccess: (movement) => {
      toast.notify("success", `Receipt posted (${movement.id}).`);
      setReceiptQuantity("");
      setReceiptReference("");
      setReceiptNotes("");
      invalidateAll();
    },
  });
  const allocation = useMutation({
    mutationFn: () =>
      api.postAllocation({ distributor_user_id: allocationDistributor, quantity: allocationQuantity, unit: "KG" }, newId()),
    onSuccess: (movement) => {
      toast.notify("success", `Allocation posted (${movement.id}).`);
      setAllocationQuantity("");
      invalidateAll();
    },
  });
  const adjustment = useMutation({
    mutationFn: () =>
      api.postAdjustment(
        {
          account_id: adjustmentAccount,
          quantity: adjustmentQuantity,
          unit: "KG",
          movement_type: adjustmentType,
          reason: adjustmentReason.trim(),
          destination_account_id: adjustmentType === "RETURN" ? adjustmentDestination : null,
        },
        newId(),
      ),
    onSuccess: (movement) => {
      toast.notify("success", `Adjustment posted (${movement.id}).`);
      setAdjustmentQuantity("");
      setAdjustmentDestination("");
      setAdjustmentReason("");
      invalidateAll();
    },
  });
  const reversal = useMutation({
    mutationFn: (target: StockMovementOut) =>
      api.reverseMovement(target.id, { reason: reversalReason.trim() }, newId()),
    onSuccess: (movement) => {
      toast.notify("success", `Reversal posted (${movement.id}).`);
      setReversalTarget(null);
      setReversalReason("");
      invalidateAll();
    },
  });

  function postReceipt(event: React.FormEvent) {
    event.preventDefault();
    if (!receiptReference.trim()) {
      toast.notify("warning", "A source reference is required for receipts.");
      return;
    }
    receipt.mutate();
  }

  function postAdjustment() {
    setAdjustConfirmOpen(false);
    adjustment.mutate();
  }

  const centralAvailable = (summary.data?.accounts ?? [])
    .filter((account) => account.account_type === "CENTRAL")
    .reduce((acc, account) => acc + Number(account.available_kg), 0);

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Inventory and ledger</h1>
          <p className="subtitle">Balances come from the append-only ledger; movements are never edited or deleted.</p>
        </div>
      </div>

      {summary.isError ? (
        <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
      ) : summary.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : !summary.data ? (
        <EmptyState title="No inventory data." />
      ) : (
        <div className="section">
          <div className="metric-row">
            <StatCard label="Central available" value={formatKg(String(centralAvailable))} unit="kg" definition="Central accounts' available stock (posted − reserved)." />
            {summary.data.reconciliation ? (
              <StatCard
                label="Reconciliation"
                value={summary.data.reconciliation.balanced ? "Balanced" : "Check"}
                definition={`net external ${formatKg(summary.data.reconciliation.net_external_kg)} kg · ledger total ${formatKg(summary.data.reconciliation.sum_account_balances_kg)} kg`}
              />
            ) : null}
          </div>
          {summary.data.reconciliation ? (
            <p className="muted small" data-testid="reconciliation-detail">
              Received {formatKg(summary.data.reconciliation.received_kg)} kg · reversed receipts{" "}
              {formatKg(summary.data.reconciliation.reversed_receipt_kg)} kg · losses{" "}
              {formatKg(summary.data.reconciliation.loss_kg)} kg · reversed losses{" "}
              {formatKg(summary.data.reconciliation.reversed_loss_kg)} kg. Internal transfers net to zero.
            </p>
          ) : null}
          <h2 style={{ marginTop: "var(--space-3)" }}>Account balances</h2>
          <DataTable
            caption="Stock account balances"
            rowKey={(account) => account.id}
            rows={summary.data.accounts}
            columns={[
              { key: "account", header: "Account", render: (account) => account.name },
              {
                key: "type",
                header: "Type",
                render: (account) => <StatusBadge status="ACTIVE" label={account.account_type} tone="info" />,
              },
              {
                key: "posted",
                header: "Posted balance (kg)",
                numeric: true,
                render: (account) => formatKg(account.posted_balance_kg),
              },
              {
                key: "reserved",
                header: "Reserved (kg)",
                numeric: true,
                render: (account) => formatKg(account.reserved_kg),
              },
              {
                key: "available",
                header: "Available (kg)",
                numeric: true,
                render: (account) => formatKg(account.available_kg),
              },
              {
                key: "ledger",
                header: "Ledger",
                render: (account) => (
                  <button type="button" className="btn ghost small" onClick={() => setSelectedAccountId(account.id)}>
                    View ledger
                  </button>
                ),
              },
            ]}
          />
        </div>
      )}

      <div className="section">
        <h2>Receive stock (admin)</h2>
        <p className="muted small">Receipts add to central stock with a unique idempotency key per submission.</p>
        {receipt.error ? <ErrorState error={receipt.error} /> : null}
        <form className="form-grid" onSubmit={postReceipt} style={{ maxWidth: 520 }}>
          <div className="row">
            <FormField id="receipt-qty" label="Quantity (kg)" required className="grow">
              {(ids) => (
                <input
                  id="receipt-qty"
                  type="text"
                  inputMode="decimal"
                  className="num"
                  value={receiptQuantity}
                  aria-describedby={ids.describedBy}
                  onChange={(e) => setReceiptQuantity(e.target.value)}
                />
              )}
            </FormField>
            <FormField id="receipt-ref" label="Source reference" required className="grow" helper="e.g. supplier note id.">
              {(ids) => (
                <input
                  id="receipt-ref"
                  type="text"
                  value={receiptReference}
                  aria-describedby={ids.describedBy}
                  onChange={(e) => setReceiptReference(e.target.value)}
                />
              )}
            </FormField>
          </div>
          <FormField id="receipt-notes" label="Notes">
            {(ids) => <textarea id="receipt-notes" rows={2} value={receiptNotes} aria-describedby={ids.describedBy} onChange={(e) => setReceiptNotes(e.target.value)} />}
          </FormField>
          <div className="form-actions">
            <button type="submit" className="btn" disabled={receipt.isPending || !receiptQuantity || !receiptReference}>
              {receipt.isPending ? "Posting…" : "Post receipt"}
            </button>
          </div>
        </form>
      </div>

      <div className="section">
        <h2>Allocate to distributor (admin)</h2>
        <p className="muted small">Transfers canonical stock from central to a distributor account.</p>
        {allocation.error ? <ErrorState error={allocation.error} /> : null}
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            allocation.mutate();
          }}
          style={{ maxWidth: 520 }}
        >
          <div className="row">
            <FormField id="allocation-distributor" label="Distributor" required className="grow">
              {(ids) => (
                <select
                  id="allocation-distributor"
                  aria-describedby={ids.describedBy}
                  value={allocationDistributor}
                  onChange={(e) => setAllocationDistributor(e.target.value)}
                >
                  <option value="">Choose distributor…</option>
                  {(distributors.data?.items ?? []).map((item: DistributorDetailOut) => (
                    <option key={item.id} value={item.id}>
                      {item.display_name} ({formatKg(item.stock_balance_kg)} kg held)
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <FormField id="allocation-qty" label="Quantity (kg)" required className="grow">
              {(ids) => (
                <input
                  id="allocation-qty"
                  type="text"
                  inputMode="decimal"
                  className="num"
                  value={allocationQuantity}
                  aria-describedby={ids.describedBy}
                  onChange={(e) => setAllocationQuantity(e.target.value)}
                />
              )}
            </FormField>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn" disabled={allocation.isPending || !allocationDistributor || !allocationQuantity}>
              {allocation.isPending ? "Posting…" : "Post allocation"}
            </button>
          </div>
        </form>
      </div>

      <div className="section">
        <h2>Adjustment (admin, requires reason and confirmation)</h2>
        <p className="muted small">Loss/return adjustments are irreversible ledger movements; confirming posts the movement.</p>
        {adjustment.error ? <ErrorState error={adjustment.error} /> : null}
        <form
          className="form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            if (!adjustmentAccount || !adjustmentQuantity || adjustmentReason.trim().length < 3) {
              toast.notify("warning", "Account, quantity and a reason (min 3 characters) are required.");
              return;
            }
            if (adjustmentType === "RETURN" && !adjustmentDestination) {
              toast.notify("warning", "A destination account is required for a return.");
              return;
            }
            if (adjustmentType === "RETURN" && adjustmentDestination === adjustmentAccount) {
              toast.notify("warning", "Source and destination accounts must differ.");
              return;
            }
            setAdjustConfirmOpen(true);
          }}
          style={{ maxWidth: 520 }}
        >
          <div className="row">
            <FormField id="adjust-account" label="Account" required className="grow">
              {(ids) => (
                <select
                  id="adjust-account"
                  aria-describedby={ids.describedBy}
                  value={adjustmentAccount}
                  onChange={(e) => setAdjustmentAccount(e.target.value)}
                >
                  <option value="">Choose account…</option>
                  {(summary.data?.accounts ?? []).map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name} ({account.account_type})
                    </option>
                  ))}
                </select>
              )}
            </FormField>
            <FormField id="adjust-type" label="Type" required className="grow">
              {(ids) => (
                <select
                  id="adjust-type"
                  aria-describedby={ids.describedBy}
                  value={adjustmentType}
                  onChange={(e) => setAdjustmentType(e.target.value === "RETURN" ? "RETURN" : "LOSS")}
                >
                  <option value="LOSS">Loss</option>
                  <option value="RETURN">Return</option>
                </select>
              )}
            </FormField>
            <FormField id="adjust-qty" label="Quantity (kg)" required className="grow">
              {(ids) => (
                <input
                  id="adjust-qty"
                  type="text"
                  inputMode="decimal"
                  className="num"
                  value={adjustmentQuantity}
                  aria-describedby={ids.describedBy}
                  onChange={(e) => setAdjustmentQuantity(e.target.value)}
                />
              )}
            </FormField>
          </div>
          {adjustmentType === "RETURN" ? (
            <FormField id="adjust-destination" label="Destination account" required helper="The account that receives the returned stock.">
              {(ids) => (
                <select
                  id="adjust-destination"
                  aria-describedby={ids.describedBy}
                  value={adjustmentDestination}
                  onChange={(e) => setAdjustmentDestination(e.target.value)}
                >
                  <option value="">Choose destination…</option>
                  {(summary.data?.accounts ?? [])
                    .filter((account) => account.id !== adjustmentAccount)
                    .map((account) => (
                      <option key={account.id} value={account.id}>
                        {account.name} ({account.account_type})
                      </option>
                    ))}
                </select>
              )}
            </FormField>
          ) : null}
          <FormField id="adjust-reason" label="Reason" required helper="Three characters minimum; stored with the movement.">
            {(ids) => (
              <input
                id="adjust-reason"
                type="text"
                value={adjustmentReason}
                aria-describedby={ids.describedBy}
                onChange={(e) => setAdjustmentReason(e.target.value)}
              />
            )}
          </FormField>
          <div className="form-actions">
            <button type="submit" className="btn destructive" disabled={adjustment.isPending}>
              {adjustment.isPending ? "Posting…" : "Post adjustment…"}
            </button>
          </div>
        </form>
      </div>

      {selectedAccountId ? (
        <div className="section">
          <div className="row">
            <h2 className="grow">Account ledger</h2>
            <button type="button" className="btn ghost" onClick={() => setSelectedAccountId(null)}>
              Close
            </button>
          </div>
          {ledger.isError ? (
            <ErrorState error={ledger.error} onRetry={() => void ledger.refetch()} />
          ) : ledger.isLoading ? (
            <div className="skeleton" style={{ height: 120 }} />
          ) : (ledger.data?.items.length ?? 0) === 0 ? (
            <EmptyState title="No movements for this account yet." />
          ) : (
            <DataTable
              caption="Account movement history"
              rowKey={(row) => row.id}
              emptyState={<EmptyState title="No movements for this account yet." />}
              rows={ledger.data?.items ?? []}
              columns={[
                {
                  key: "posted_at",
                  header: "Posted",
                  sortValue: (row) => row.posted_at,
                  render: (row) => formatDateTime(row.posted_at),
                },
                { key: "movement_type", header: "Type", sortValue: (row) => row.movement_type, render: (row) => <StatusBadge status={row.movement_type} /> },
                { key: "quantity", header: "Quantity (kg)", numeric: true, sortValue: (row) => Number(row.quantity_kg), render: (row) => formatKg(row.quantity_kg) },
                { key: "reference", header: "Reference", render: (row) => (row.reference_id ? `${row.reference_type} ${row.reference_id.slice(0, 8)}…` : row.reference_type) },
                { key: "reason", header: "Reason", render: (row) => row.reason ?? "—" },
                {
                  key: "reversal",
                  header: "Reversal",
                  render: (row) =>
                    row.movement_type === "REVERSAL" ? (
                      <span className="small muted">reversal of {row.reversal_of_id?.slice(0, 8) ?? "—"}</span>
                    ) : row.reversed_by_id ? (
                      <span className="small muted">reversed · correction {row.reversed_by_id.slice(0, 8)}</span>
                    ) : (
                      <button type="button" className="btn ghost small" onClick={() => setReversalTarget(row)}>
                        Reverse…
                      </button>
                    ),
                },
              ]}
            />
          )}
        </div>
      ) : null}

      <ConfirmDialog
        open={adjustConfirmOpen}
        title="Post this adjustment?"
        message={
          <p>
            This posts an irreversible {adjustmentType === "LOSS" ? "loss" : "return"} movement of{" "}
            <strong className="num">{formatKg(adjustmentQuantity)} kg</strong> to the selected account. The ledger cannot
            be edited afterwards — a reversal is the only correction path.
          </p>
        }
        confirmLabel="Post adjustment"
        destructive
        busy={adjustment.isPending}
        onConfirm={() => postAdjustment()}
        onCancel={() => setAdjustConfirmOpen(false)}
      />

      <ConfirmDialog
        open={reversalTarget !== null}
        title="Reverse this movement?"
        message={
          <div className="stack">
            <p>
              The reversal debits the account that received the original movement and credits the original source. It is
              refused if that would overdraw the receiving account, and a linked delivery becomes <strong>REVERSED</strong>.
              Post only under the correct reason; the reversal is itself immutable and cannot be reversed.
            </p>
            <FormField id="reversal-reason" label="Reason" required helper="Three characters minimum.">
              {(ids) => (
                <input
                  id="reversal-reason"
                  type="text"
                  value={reversalReason}
                  aria-describedby={ids.describedBy}
                  onChange={(e) => setReversalReason(e.target.value)}
                />
              )}
            </FormField>
          </div>
        }
        confirmLabel="Post reversal"
        destructive={false}
        busy={reversal.isPending}
        onConfirm={() => {
          if (reversalReason.trim().length < 3) {
            toast.notify("warning", "A reason of at least 3 characters is required.");
            return;
          }
          if (reversalTarget) reversal.mutate(reversalTarget);
        }}
        onCancel={() => setReversalTarget(null)}
      />

      {reversal.error ? <ErrorState error={reversal.error} /> : null}
    </div>
  );
}
