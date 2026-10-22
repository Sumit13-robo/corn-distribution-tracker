import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../../lib/api-client";
import { queryKeys } from "../../../lib/query-client";
import { EmptyState } from "../../../components/common/EmptyState";
import { ErrorState } from "../../../components/common/ErrorState";
import { FormField } from "../../../components/common/FormField";
import { StatusBadge } from "../../../components/common/StatusBadge";
import { StatCard } from "../../../components/common/StatCard";
import { formatKg, humanizeStatus } from "../../../lib/format";
import type { CampaignOut, MapSiteOut } from "../../../types/domain";

const MAP_STYLE_URL = (import.meta.env.VITE_MAP_STYLE_URL as string | undefined) ?? "";

const LEGEND: Array<{ status: string; color: string; label: string }> = [
  { status: "APPROVED", color: "var(--color-success-text)", label: `Sites with approved deliveries` },
  { status: "PENDING", color: "var(--color-pending-text)", label: "Sites with pending submissions" },
  { status: "EMPTY", color: "var(--color-muted)", label: "Sites without submissions" },
];

function legendColor(status: string): string {
  if (status === "APPROVED") return "var(--color-success-text)";
  if (status === "PENDING") return "var(--color-pending-text)";
  return "var(--color-muted)";
}

/**
 * Distribution map (SCREEN_SPECS): MapLibre when a public style URL is
 * configured; otherwise a labelled coordinate fallback — no tile demo pins.
 * Sites come exclusively from the role-scoped map-sites endpoint, and the
 * synchronized list doubles as the accessible selection surface.
 */
export function DistributionMapPage() {
  const [campaignId, setCampaignId] = useState("");
  const [selectedSiteId, setSelectedSiteId] = useState<string | null>(null);

  const campaigns = useQuery({
    queryKey: queryKeys.campaigns(undefined),
    queryFn: () => api.listCampaigns(undefined),
  });

  const mapSites = useQuery({
    queryKey: queryKeys.mapSites(campaignId || null, null),
    queryFn: () => api.mapSites(campaignId ? { campaign_id: campaignId } : {}),
  });

  const sites = useMemo(() => mapSites.data ?? [], [mapSites.data]);

  const selected: MapSiteOut | null = useMemo(
    () => sites.find((site) => site.id === selectedSiteId) ?? null,
    [sites, selectedSiteId],
  );

  const details = useQuery({
    queryKey: queryKeys.deliveries({ site_id: selectedSiteId ?? "", status: "SUBMITTED", limit: 5, offset: 0 }),
    queryFn: () => api.listDeliveries({ site_id: selectedSiteId ?? "", status: "SUBMITTED", limit: 5, offset: 0 }),
    enabled: selectedSiteId !== null,
  });

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Distribution map</h1>
          <p className="subtitle">Sites visible to your admin scope; selection is keyboard-accessible via the list.</p>
        </div>
      </div>

      <div className="section">
        <div className="row">
          <FormField
            id="map-campaign"
            label="Campaign filter"
            helper="Scope map points to one campaign assignment set."
            className="grow"
          >
            {(ids) => (
              <select id="map-campaign" aria-describedby={ids.describedBy} value={campaignId} onChange={(event) => setCampaignId(event.target.value)}>
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

      {sites.length > 0 ? (
        <div className="section">
          <h2>Sites in scope</h2>
          <div className="stack small">
            {sites.map((site) => (
              <button
                key={site.id}
                type="button"
                className={`map-site-item${selectedSiteId === site.id ? " is-selected" : ""}`}
                aria-pressed={selectedSiteId === site.id}
                onClick={() => setSelectedSiteId(site.id)}
                data-testid={`site-list-item-${site.site_code}`}
              >
                <span className="map-site-title">
                  <span aria-hidden="true">{selectedSiteId === site.id ? "▸" : "○"}</span>
                  <strong>{site.site_code}</strong>
                  <span className="map-site-name">{site.name}</span>
                </span>
                <span className="map-site-meta">
                  <StatusBadge status={site.status} />
                  <span className="num">approved {formatKg(site.approved_kg)} kg</span>
                  <span className="num">pending {formatKg(site.pending_kg)} kg</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {mapSites.isError ? (
        <ErrorState error={mapSites.error} onRetry={() => void mapSites.refetch()} />
      ) : mapSites.isLoading ? (
        <div className="skeleton" style={{ height: 420 }} />
      ) : sites.length === 0 ? (
        <EmptyState title="No sites match the current filters." description="Create sites or clear the campaign filter." />
      ) : (
        <div className="section">
          {MAP_STYLE_URL ? (
            <MapLibreCanvas
              sites={sites}
              selectedSiteId={selectedSiteId}
              onSelect={(id) => setSelectedSiteId(id)}
            />
          ) : (
            <div>
              <FallbackCoordinateBoard sites={sites} selectedSiteId={selectedSiteId} onSelect={(id) => setSelectedSiteId(id)} />
              <p className="notice" style={{ marginTop: "var(--space-2)" }} role="status">
                Static coordinate board: no map tile style is configured (VITE_MAP_STYLE_URL). Positions are relative
                labels within the sites' own bounds — no forecasting, no invented geography.
              </p>
            </div>
          )}
          <div className="map-legend" aria-label="Map legend">
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
        <div className="section" data-testid="site-drawer">
          <div className="row">
            <h2 className="grow">
              {selected.site_code} — {selected.name}
            </h2>
            <StatusBadge status={selected.status} />
          </div>
          <div className="metric-row">
            <StatCard label="Target" value={formatKg(selected.target_kg)} unit="kg" />
            <StatCard label="Approved" value={formatKg(selected.approved_kg)} unit="kg" />
            <StatCard label="Pending" value={formatKg(selected.pending_kg)} unit="kg" />
            <StatCard label="Remaining" value={formatKg(selected.remaining_target_kg)} unit="kg" />
          </div>
          <h3>Pending submissions awaiting review</h3>
          {details.isLoading ? (
            <div className="skeleton" style={{ height: 60 }} />
          ) : (details.data?.items.length ?? 0) === 0 ? (
            <p className="muted small">No pending submissions for this site right now.</p>
          ) : (
            <ul className="stack small" style={{ margin: 0, paddingLeft: 0, listStyle: "none" }}>
              {(details.data?.items ?? []).map((record) => (
                <li key={record.id} className="row">
                  <code className="num">{record.id.slice(0, 8)}…</code>
                  <StatusBadge status={record.geo_status} />
                  <span className="num">{formatKg(record.quantity_kg)} kg</span>
                  <span className="muted">{humanizeStatus(record.status)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}

/* -------------------------------------------------------------- MapLibre path */

function MapLibreCanvas({
  sites,
  selectedSiteId,
  onSelect,
}: {
  sites: MapSiteOut[];
  selectedSiteId: string | null;
  onSelect: (siteId: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let disposed = false;
    let cleanupMarkers: (() => void) | null = null;
    let mapRef: import("maplibre-gl").Map | null = null;

    void (async () => {
      const maplibre = await import("maplibre-gl");
      if (disposed || !containerRef.current) return;
      const map = new maplibre.Map({
        container: containerRef.current,
        style: MAP_STYLE_URL,
        center: [0, 0],
        zoom: 1,
      });
      map.addControl(new maplibre.NavigationControl({ showZoom: true, showCompass: false }), "top-right");
      map.on("load", () => {
        mapRef = map;
        if (disposed) return;
        const markers = sites.map((site) => {
          const element = document.createElement("button");
          element.type = "button";
          element.className = "map-pin";
          element.setAttribute("aria-label", `Site ${site.site_code}: ${humanizeStatus(site.status)}, approved ${site.approved_kg} kg`);
          const pin = document.createElement("span");
          pin.style.background = legendColor(site.status);
          pin.style.display = "block";
          pin.style.width = "14px";
          pin.style.height = "14px";
          pin.style.borderRadius = "50% 50% 50% 0";
          pin.style.transform = "rotate(-45deg)";
          pin.style.border = "2px solid #ffffff";
          pin.style.boxShadow = "var(--shadow-pop)";
          element.append(pin);
          element.addEventListener("click", () => onSelect(site.id));
          if (site.id === selectedSiteId) {
            element.style.filter = "brightness(1.25)";
          }
          const marker = new maplibre.Marker({ element })
            .setLngLat([Number(site.longitude), Number(site.latitude)])
            .addTo(map);
          return () => marker.remove();
        });
        cleanupMarkers = () => markers.forEach((remove) => remove());
        const bounds = sites.reduce(
          (acc, site) => {
            const lng = Number(site.longitude);
            const lat = Number(site.latitude);
            return {
              minLng: Math.min(acc.minLng, lng),
              minLat: Math.min(acc.minLat, lat),
              maxLng: Math.max(acc.maxLng, lng),
              maxLat: Math.max(acc.maxLat, lat),
            };
          },
          { minLng: Infinity, minLat: Infinity, maxLng: -Infinity, maxLat: -Infinity },
        );
        if (Number.isFinite(bounds.minLng)) {
          map.fitBounds(
            [
              [bounds.minLng, bounds.minLat],
              [bounds.maxLng, bounds.maxLat],
            ],
            { padding: 48, maxZoom: 14 },
          );
        }
      });
      map.on("error", () => {
        /* MapLibre logs its own console error; keep tiles failing visible but non-fatal. */
      });

      return;
    })();

    return () => {
      disposed = true;
      cleanupMarkers?.();
      mapRef?.remove();
    };
  }, [sites, selectedSiteId, onSelect]);

  return (
    <div
      ref={containerRef}
      className="map-container"
      style={{ minHeight: 420 }}
      role="application"
      aria-label="Distribution site map"
    />
  );
}

/* ------------------------------------------------------- Fallback coordinate board */

/**
 * Fallback rendering when no tile style is configured: sites are placed on a
 * normalized lat/lng grid derived only from the returned coordinates, and each
 * marker is a real button (keyboard selectable). No tiles, no fake pins.
 */
function FallbackCoordinateBoard({
  sites,
  selectedSiteId,
  onSelect,
}: {
  sites: MapSiteOut[];
  selectedSiteId: string | null;
  onSelect: (siteId: string) => void;
}) {
  const bounds = useMemo(() => {
    return sites.reduce(
      (acc, site) => {
        const lng = Number(site.longitude);
        const lat = Number(site.latitude);
        return {
          minLng: Math.min(acc.minLng, lng),
          maxLng: Math.max(acc.maxLng, lng),
          minLat: Math.min(acc.minLat, lat),
          maxLat: Math.max(acc.maxLat, lat),
        };
      },
      { minLng: Infinity, maxLng: -Infinity, minLat: Infinity, maxLat: -Infinity },
    );
  }, [sites]);

  const spanLat = Math.max(0.0001, bounds.maxLat - bounds.minLat);
  const spanLng = Math.max(0.0001, bounds.maxLng - bounds.minLng);

  return (
    <div className="map-fallback" data-testid="map-fallback" aria-label="Site coordinate board (list format available)">
      {sites.map((site) => {
        const left = ((Number(site.longitude) - bounds.minLng) / spanLng) * 92 + 4;
        const top = 96 - ((Number(site.latitude) - bounds.minLat) / spanLat) * 88;
        return (
          <button
            key={site.id}
            type="button"
            className="btn ghost"
            style={{
              position: "absolute",
              left: `${Math.max(16, Math.min(left, 84))}%`,
              top: `${Math.max(4, Math.min(top, 94))}%`,
              transform: "translate(-50%, -50%)",
              padding: "2px 6px",
              background: selectedSiteId === site.id ? "var(--color-accent-100)" : "rgba(255,255,255,0.9)",
              color: legendColor(site.status),
              border: selectedSiteId === site.id ? "1px solid var(--color-brand-700)" : "1px solid rgba(255,255,255,0.2)",
            }}
            onClick={() => onSelect(site.id)}
          >
            {site.site_code}
          </button>
        );
      })}
    </div>
  );
}
