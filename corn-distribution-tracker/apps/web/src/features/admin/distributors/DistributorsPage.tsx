import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { DataTable } from "../../../components/common/DataTable";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { ConfirmDialog } from "../../../components/common/ConfirmDialog";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { useToast } from "../../../app/providers";
import { formatDateTime, formatKg } from "../../../lib/format";
import type { DistributorDetailOut, InvitationCreatedOut } from "../../../types/domain";

/**
 * Distributor management (SCREEN_SPECS): list with status and stock, invite
 * creation, rename, deactivation. The raw invitation token is returned once by
 * the API and shown once here for secure delivery; it is never logged.
 */
export function DistributorsPage() {
  const [search, setSearch] = useState("");
  const [searchField, setSearchField] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [createdInvite, setCreatedInvite] = useState<InvitationCreatedOut | null>(null);
  const [inviteCopied, setInviteCopied] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [deactivating, setDeactivating] = useState<DistributorDetailOut | null>(null);
  const queryClient = useQueryClient();
  const toast = useToast();

  const distributors = useQuery({
    queryKey: queryKeys.distributors(search),
    queryFn: () => api.listDistributors(search || undefined),
    placeholderData: (previous) => previous,
  });

  const refresh = () => void queryClient.invalidateQueries({ queryKey: ["distributors"] });

  const invite = useMutation({
    mutationFn: () =>
      api.createInvitation({ email: inviteEmail.trim(), display_name: inviteName.trim(), role: "DISTRIBUTOR" }),
    onSuccess: (result) => {
      setCreatedInvite(result);
      setInviteCopied(false);
      setCopyError(null);
      toast.notify("success", "Invitation created. Deliver the one-time link securely.");
      setInviteOpen(false);
      setInviteEmail("");
      setInviteName("");
      setInviteError(null);
      refresh();
    },
  });

  const inviteUrl = createdInvite
    ? `${window.location.origin}/reset-password?mode=invite&token=${encodeURIComponent(createdInvite.invite_token)}`
    : "";

  async function copyInviteLink(): Promise<void> {
    try {
      await navigator.clipboard.writeText(inviteUrl);
      setInviteCopied(true);
      setCopyError(null);
    } catch {
      setCopyError("Copy was blocked by the browser. Select the link and copy it manually.");
    }
  }

  const rename = useMutation({
    mutationFn: (input: { id: string; displayName: string }) =>
      api.updateDistributor(input.id, input.displayName),
    onSuccess: () => {
      toast.notify("success", "Distributor updated.");
      setEditingId(null);
      refresh();
    },
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => api.deactivateDistributor(id),
    onSuccess: () => {
      toast.notify("success", "Distributor deactivated; sessions revoked.");
      setDeactivating(null);
      refresh();
    },
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Distributors</h1>
          <p className="subtitle">Accounts, stock holdings and invite state. Passwords are never shown or reset here.</p>
        </div>
        <button type="button" className="btn" onClick={() => setInviteOpen(true)}>
          Invite distributor
        </button>
      </div>

      <div className="section">
        <form
          className="row"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            setSearch(searchField.trim());
          }}
        >
          <FormField id="distributor-search" label="Search" className="grow" helper="Name or email, server-side filter.">
            {(ids) => (
              <input
                id="distributor-search"
                type="search"
                value={searchField}
                aria-describedby={ids.describedBy}
                onChange={(event) => setSearchField(event.target.value)}
              />
            )}
          </FormField>
          <button type="submit" className="btn secondary">
            Search
          </button>
          {search ? (
            <button
              type="button"
              className="btn ghost"
              onClick={() => {
                setSearch("");
                setSearchField("");
              }}
            >
              Clear
            </button>
          ) : null}
        </form>
      </div>

      {distributors.isError ? (
        <ErrorState error={distributors.error} onRetry={() => void distributors.refetch()} />
      ) : distributors.isLoading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : (distributors.data?.items.length ?? 0) === 0 ? (
        <EmptyState
          title="No distributors found."
          description={search ? "Try a different search term." : "Invite the first distributor to get started."}
          action={
            <button type="button" className="btn" onClick={() => setInviteOpen(true)}>
              Invite distributor
            </button>
          }
        />
      ) : (
        <div className="section">
          <DataTable
            caption="Distributor accounts"
            rowKey={(row) => row.id}
            emptyState={<EmptyState title="No distributors found." />}
            rows={distributors.data?.items ?? []}
            columns={[
              {
                key: "display_name",
                header: "Name",
                sortValue: (row) => row.display_name,
                render: (row) =>
                  editingId === row.id ? (
                    <form
                      className="row"
                      onSubmit={(event) => {
                        event.preventDefault();
                        if (!editName.trim()) return;
                        rename.mutate({ id: row.id, displayName: editName.trim() });
                      }}
                    >
                      <input value={editName} onChange={(event) => setEditName(event.target.value)} aria-label="New display name" />
                      <button type="submit" className="btn small" disabled={rename.isPending}>
                        Save
                      </button>
                      <button type="button" className="btn ghost small" onClick={() => setEditingId(null)}>
                        Cancel
                      </button>
                    </form>
                  ) : (
                    <button
                      type="button"
                      className="btn ghost"
                      style={{ padding: 0, textAlign: "left" }}
                      onClick={() => {
                        setEditingId(row.id);
                        setEditName(row.display_name);
                      }}
                      aria-label={`Rename ${row.display_name}`}
                    >
                      {row.display_name}
                    </button>
                  ),
              },
              { key: "email", header: "Email", sortValue: (row) => row.email },
              {
                key: "status",
                header: "Status",
                sortValue: (row) => (row.is_active ? "ACTIVE" : "INACTIVE"),
                render: (row) => (row.is_active ? <StatusBadge status="ACTIVE" /> : <StatusBadge status="CANCELLED" label="Deactivated" />),
              },
              {
                key: "stock_balance_kg",
                header: "Held (kg)",
                numeric: true,
                sortValue: (row) => Number(row.stock_balance_kg),
                render: (row) => formatKg(row.stock_balance_kg),
              },
              {
                key: "available_kg",
                header: "Available (kg)",
                numeric: true,
                sortValue: (row) => Number(row.available_kg),
                render: (row) => formatKg(row.available_kg),
              },
              {
                key: "open_assignment_count",
                header: "Open assignments",
                numeric: true,
                render: (row) => row.open_assignment_count ?? "—",
              },
              {
                key: "invite",
                header: "Invite state",
                render: (row) => (row.has_open_invitation ? <StatusBadge status="SUBMITTED" label="Invitation pending" /> : <span className="muted small">—</span>),
              },
              { key: "last_login", header: "Last login", sortValue: (row) => row.last_login_at ?? "", render: (row) => formatDateTime(row.last_login_at) },
              {
                key: "actions",
                header: "Actions",
                render: (row) =>
                  row.is_active ? (
                    <button type="button" className="btn ghost small" onClick={() => setDeactivating(row)}>
                      Deactivate…
                    </button>
                  ) : null,
              },
            ]}
          />
        </div>
      )}

      <ConfirmDialog
        open={inviteOpen}
        title="Invite a distributor"
        message={
          <div className="stack">
            <p className="small muted">
              A one-time invitation link will be created and shown here once. Deliver it to the distributor through
              your organization&rsquo;s approved secure channel.
            </p>
            <FormField id="invite-email" label="Email" required>
              {(ids) => (
                <input
                  id="invite-email"
                  type="email"
                  value={inviteEmail}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setInviteEmail(event.target.value)}
                />
              )}
            </FormField>
            <FormField id="invite-name" label="Display name" required>
              {(ids) => (
                <input
                  id="invite-name"
                  type="text"
                  value={inviteName}
                  aria-describedby={ids.describedBy}
                  onChange={(event) => setInviteName(event.target.value)}
                />
              )}
            </FormField>
            {inviteError ? <p className="notice warning" role="alert">{inviteError}</p> : null}
            {invite.error ? <ErrorState error={invite.error} /> : null}
          </div>
        }
        confirmLabel="Create invitation"
        busy={invite.isPending}
        onConfirm={() => {
          if (!/.+@.+\..+/.test(inviteEmail.trim()) || !inviteName.trim()) {
            setInviteError("Enter a valid email and a display name.");
            return;
          }
          setInviteError(null);
          invite.mutate();
        }}
        onCancel={() => {
          setInviteError(null);
          setInviteOpen(false);
        }}
      />

      <ConfirmDialog
        open={createdInvite !== null}
        title="Invitation link ready"
        message={
          <div className="stack">
            <p>
              Send this one-time link to <strong>{createdInvite?.email}</strong> through your organization&rsquo;s
              approved secure channel. It disappears when you close this dialog and cannot be shown again.
            </p>
            <label className="form-field" htmlFor="created-invite-link">
              <span className="label">Invitation link</span>
              <input
                id="created-invite-link"
                type="text"
                readOnly
                value={inviteUrl}
                onFocus={(event) => event.currentTarget.select()}
              />
            </label>
            {inviteCopied ? (
              <p className="notice success" role="status">
                Link copied to the clipboard.
              </p>
            ) : null}
            {copyError ? (
              <p className="notice warning" role="alert">
                {copyError}
              </p>
            ) : null}
            <p className="small muted">
              The recipient will set their display name and password after opening the link.
            </p>
          </div>
        }
        confirmLabel={inviteCopied ? "Copied" : "Copy link"}
        cancelLabel="Close"
        onConfirm={() => void copyInviteLink()}
        onCancel={() => {
          setCreatedInvite(null);
          setInviteCopied(false);
          setCopyError(null);
        }}
      />

      <ConfirmDialog
        open={deactivating !== null}
        title={`Deactivate ${deactivating?.display_name ?? ""}?`}
        message="The distributor can no longer sign in and active sessions are revoked server-side. Drafts on their device remain local to them."
        confirmLabel="Deactivate"
        destructive
        busy={deactivate.isPending}
        onConfirm={() => deactivating && deactivate.mutate(deactivating.id)}
        onCancel={() => setDeactivating(null)}
      />

    </div>
  );
}