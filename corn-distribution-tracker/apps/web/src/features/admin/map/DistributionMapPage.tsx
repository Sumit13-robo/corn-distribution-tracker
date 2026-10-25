import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { MapCanvas } from "../../../components/common/MapCanvas";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { formatDateTime, formatKg, humanizeStatus } from "../../../lib/format";
import { googleMapsViewerUrl, osmViewerUrl } from "../../../lib/map";
import type { CampaignOut, MapDeliveryOut } from "../../../types/domain";

const LEGEND: Array<{ status: string; color: string; label: string }> = [
  { status: "APPROVED", color: "var(--color-success-text)", label: "Approved delivery" },
  { status: "SUBMITTED", color: "var(--color-pending-text)", label: "Delivery awaiting review" },
];

function deliveryColor(status: string): string {
  if (status === "APPROVED") return "var(--color-success-text)";
  if (status === "SUBMITTED") return "var(--color-pending-text)";
  return "var(--color-muted)";
}

/**
 * Admin distribution map. It intentionally plots only distributor-recorded
 * delivery locations. A site's reference coordinates are not a delivery and
 * are never drawn here; rejected/cancelled claims are excluded by the API.
 * The synchronized list is the keyboard-accessible alternative to the map.
 */
export function DistributionMapPage() {
  const [campaignId, setCampaignId] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const campaigns = useQuery({
    queryKey: queryKeys.campaigns(undefined),
    queryFn: () => api.listCampaigns(undefined),
  });

  const mapDeliveries = useQuery({
    queryKey: queryKeys.mapDeliveries(campaignId || null, null),
    queryFn: () => api.mapDeliveries(campaignId ? { campaign_id: campaignId } : {}),
  });

  const deliveries = useMemo(() => mapDeliveries.data ?? [], [mapDeliveries.data]);

  const selected: MapDeliveryOut | null = useMemo(
    () => deliveries.find((delivery) => delivery.id === selectedId) ?? null,
    [deliveries, selectedId],
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Distribution map</h1>
          <p className="subtitle">
            Only locations recorded by distributors when they submitted a delivery. Site reference coordinates and
            sites without deliveries are not plotted.
          </p>
        </div>
      </div>

      <div className="section">
        <div className="row">
          <FormField
            id="map-campaign"
            label="Campaign filter"
            helper="Scope delivery markers to one campaign."
            className="grow"
          >
            {(ids) => (
              <select
                id="map-campaign"
                aria-describedby={ids.describedBy}
                value={campaignId}
                onChange={(event) => {
                  setCampaignId(event.target.value);
                  setSelectedId(null);
                }}
              >
                <option value="">All campaigns</option>
                {(campaigns.data?.items ?? []).map((campaign: CampaignOut) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name}
                  </option>
                ))}
              </select>
            )}
          </FormField>
        </div>
      </div>

      {deliveries.length > 0 ? (
        <div className="section">
          <h2>Delivery locations</h2>
          <div className="stack small">
            {deliveries.map((delivery) => (
              <button
                key={delivery.id}
                type="button"
                className={`map-site-item${selectedId === delivery.id ? " is-selected" : ""}`}
                aria-pressed={selectedId === delivery.id}
                onClick={() => setSelectedId(delivery.id)}
                data-testid={`delivery-list-item-${delivery.id}`}
              >
                <span className="map-site-title">
                  <span aria-hidden="true">{selectedId === delivery.id ? "▸" : "○"}</span>
                  <strong>{delivery.site_code}</strong>
                  <span className="map-site-name">{delivery.site_name}</span>
                </span>
                <span className="map-site-meta">
                  <span>{delivery.distributor_name}</span>
                  <StatusBadge status={delivery.status} />
                  <span className="num">{formatKg(delivery.quantity_kg)} kg</span>
                  <span className="muted small">{formatDateTime(delivery.submitted_at)}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {mapDeliveries.isError ? (
        <ErrorState error={mapDeliveries.error} onRetry={() => void mapDeliveries.refetch()} />
      ) : mapDeliveries.isLoading ? (
        <div className="skeleton" style={{ height: 420 }} />
      ) : deliveries.length === 0 ? (
        <EmptyState
          title="No recorded delivery locations yet."
          description="A marker appears only after a distributor submits a delivery with a captured device location. Site coordinates alone are not plotted."
        />
      ) : (
        <div className="section">
          <MapCanvas
            ariaLabel="Map of distributor delivery locations"
            points={deliveries.map((delivery) => ({
              id: delivery.id,
              latitude: delivery.location_latitude,
              longitude: delivery.location_longitude,
              label: `${delivery.distributor_name} delivered ${formatKg(delivery.quantity_kg)} kg to ${delivery.site_name} (${delivery.site_code}), ${humanizeStatus(delivery.status)}`,
              color: deliveryColor(delivery.status),
              selected: delivery.id === selectedId,
              onSelect: () => setSelectedId(delivery.id),
            }))}
            fallback={
              <div>
                <DeliveryFallbackBoard
                  deliveries={deliveries}
                  selectedId={selectedId}
                  onSelect={(id) => setSelectedId(id)}
                />
                <p className="notice" style={{ marginTop: "var(--space-2)" }} role="status">
                  Interactive map tiles could not start (WebGL unavailable or the tile server is blocked). Positions
                  on this board use the distributor-recorded coordinates; use the list to select a delivery.
                </p>
              </div>
            }
          />
          <p className="small muted" style={{ marginTop: "var(--space-2)" }}>
            Markers are the device locations captured with delivery submissions. They are supporting evidence, not
            proof against spoofing. Only one marker per delivery is shown.
          </p>
          <div className="map-legend" aria-label="Delivery map legend">
            {LEGEND.map((entry) => (
              <span key={entry.status} className="legend-item">
                <span className="swatch" style={{ background: entry.color }} />
                {entry.label}
              </span>
            ))}
          </div>
        </div>
      )}

      {selected ? (
        <div className="section" data-testid="delivery-drawer">
          <div className="row">
            <h2 className="grow">
              {selected.site_code} — {selected.site_name}
            </h2>
            <StatusBadge status={selected.status} />
          </div>
          <p>
            <strong>Distributor:</strong> {selected.distributor_name}
          </p>
          <p>
            <strong>Quantity:</strong> {formatKg(selected.quantity_kg)} kg
          </p>
          <p>
            <strong>Submitted:</strong> {formatDateTime(selected.submitted_at)}
          </p>
          <p className="small muted">
            Delivery location:{" "}
            <span className="num">
              {selected.location_latitude}, {selected.location_longitude}
            </span>
            {selected.location_accuracy_m ? ` · ±${selected.location_accuracy_m} m` : ""}
            {" · "}
            <a
              href={osmViewerUrl(selected.location_latitude, selected.location_longitude)}
              target="_blank"
              rel="noreferrer"
            >
              OpenStreetMap
            </a>
            {" · "}
            <a
              href={googleMapsViewerUrl(selected.location_latitude, selected.location_longitude)}
              target="_blank"
              rel="noreferrer"
            >
              Google Maps
            </a>
          </p>
          <Link className="btn secondary" to={`/evidence?record_id=${selected.id}`}>
            Open evidence review
          </Link>
        </div>
      ) : null}
    </div>
  );
}

/* ------------------------------------------------------- Fallback coordinate board */

/**
 * Fallback rendering when map tiles cannot start: delivery points are placed
 * on a normalized lat/lng grid derived only from returned coordinates. Each
 * marker is a real button and the list above remains the primary selector.
 */
function DeliveryFallbackBoard({
  deliveries,
  selectedId,
  onSelect,
}: {
  deliveries: MapDeliveryOut[];
  selectedId: string | null;
  onSelect: (deliveryId: string) => void;
}) {
  const bounds = useMemo(() => {
    return deliveries.reduce(
      (acc, delivery) => {
        const lng = Number(delivery.location_longitude);
        const lat = Number(delivery.location_latitude);
        return {
          minLng: Math.min(acc.minLng, lng),
          maxLng: Math.max(acc.maxLng, lng),
          minLat: Math.min(acc.minLat, lat),
          maxLat: Math.max(acc.maxLat, lat),
        };
      },
      { minLng: Infinity, maxLng: -Infinity, minLat: Infinity, maxLat: -Infinity },
    );
  }, [deliveries]);

  const spanLat = Math.max(0.0001, bounds.maxLat - bounds.minLat);
  const spanLng = Math.max(0.0001, bounds.maxLng - bounds.minLng);

  return (
    <div
      className="map-fallback"
      data-testid="map-fallback"
      aria-label="Delivery coordinate board (list format available)"
    >
      {deliveries.map((delivery) => {
        const left = ((Number(delivery.location_longitude) - bounds.minLng) / spanLng) * 92 + 4;
        const top = 96 - ((Number(delivery.location_latitude) - bounds.minLat) / spanLat) * 88;
        return (
          <button
            key={delivery.id}
            type="button"
            className="btn ghost"
            style={{
              position: "absolute",
              left: `${Math.max(16, Math.min(left, 84))}%`,
              top: `${Math.max(4, Math.min(top, 94))}%`,
              transform: "translate(-50%, -50%)",
              padding: "2px 6px",
              background: selectedId === delivery.id ? "var(--color-accent-100)" : "rgba(255,255,255,0.9)",
              color: deliveryColor(delivery.status),
              border:
                selectedId === delivery.id
                  ? "1px solid var(--color-brand-700)"
                  : "1px solid rgba(255,255,255,0.2)",
            }}
            onClick={() => onSelect(delivery.id)}
          >
            {delivery.site_code}
          </button>
        );
      })}
    </div>
  );
}
