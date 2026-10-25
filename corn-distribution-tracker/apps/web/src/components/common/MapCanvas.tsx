import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Map as MapLibreMap, Marker as MapLibreMarker } from "maplibre-gl";
import { BASEMAP_LAYER_IDS, buildMapStyle, hasBuiltInBasemaps, type BasemapId } from "../../lib/map";

export interface MapPoint {
  id: string;
  latitude: string | number;
  longitude: string | number;
  /** Accessible marker label; also used as the native tooltip. */
  label: string;
  color?: string;
  selected?: boolean;
  onSelect?: () => void;
}

interface MapCanvasProps {
  points: MapPoint[];
  ariaLabel: string;
  className?: string;
  fallback?: ReactNode;
  /** Adds a browser-geolocation control that recenters the map. */
  showLocateControl?: boolean;
}

/**
 * Shared MapLibre canvas. The default style has OpenStreetMap streets and Esri
 * satellite imagery (see `lib/map.ts`); a full custom style disables the
 * built-in basemap switch. Points are rendered as focusable buttons when
 * `onSelect` is supplied, so the synchronized list remains a keyboard-accessible
 * alternative to the map. If MapLibre cannot initialize (for example no WebGL),
 * the caller's fallback is rendered instead of a blank box.
 */
export function MapCanvas({
  points,
  ariaLabel,
  className = "map-container",
  fallback,
  showLocateControl = false,
}: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const maplibreRef = useRef<typeof import("maplibre-gl") | null>(null);
  const markersRef = useRef<MapLibreMarker[]>([]);
  const locateMarkerRef = useRef<MapLibreMarker | null>(null);
  const pointsRef = useRef(points);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [basemap, setBasemap] = useState<BasemapId>("streets");
  const [locateError, setLocateError] = useState<string | null>(null);
  const builtInBasemaps = useMemo(() => hasBuiltInBasemaps(), []);

  pointsRef.current = points;

  const geometryKey = useMemo(
    () =>
      points
        .filter((point) => Number.isFinite(Number(point.latitude)) && Number.isFinite(Number(point.longitude)))
        .map((point) => `${point.id}:${Number(point.latitude)}:${Number(point.longitude)}`)
        .join("|"),
    [points],
  );

  const markerKey = useMemo(
    () =>
      points
        .map(
          (point) =>
            `${point.id}:${Number(point.latitude)}:${Number(point.longitude)}:${point.selected === true ? 1 : 0}:${
              point.color ?? ""
            }:${point.label}`,
        )
        .join("|"),
    [points],
  );

  useEffect(() => {
    let disposed = false;

    void (async () => {
      try {
        // MapLibre resolves its worker relative to the bundled module. Vite's
        // dependency prebundling changes that path, so point MapLibre at the
        // worker asset emitted by Vite explicitly.
        const [maplibre, workerModule] = await Promise.all([
          import("maplibre-gl"),
          import("maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url"),
        ]);
        if (disposed || !containerRef.current) return;
        maplibre.setWorkerUrl(workerModule.default);
        maplibreRef.current = maplibre;

        const map = new maplibre.Map({
          container: containerRef.current,
          style: buildMapStyle(),
          center: [0, 0],
          zoom: 1,
          attributionControl: { compact: false },
        });
        mapRef.current = map;
        map.addControl(new maplibre.NavigationControl({ showZoom: true, showCompass: false }), "top-right");
        map.once("load", () => {
          if (!disposed) setReady(true);
        });
        map.on("error", () => {
          // Tile/style errors are non-fatal. Fresh tiles may still render; the
          // surrounding screen keeps its list and coordinate fallback.
        });
      } catch {
        if (!disposed) setFailed(true);
      }
    })();

    return () => {
      disposed = true;
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      locateMarkerRef.current?.remove();
      locateMarkerRef.current = null;
      try {
        mapRef.current?.remove();
      } catch {
        // MapLibre may already have torn the canvas down during navigation.
      }
      mapRef.current = null;
      maplibreRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map || !builtInBasemaps) return;

    for (const layerId of Object.values(BASEMAP_LAYER_IDS)) {
      if (!map.getLayer(layerId)) continue;
      map.setLayoutProperty(
        layerId,
        "visibility",
        layerId === BASEMAP_LAYER_IDS[basemap] ? "visible" : "none",
      );
    }
  }, [ready, basemap, builtInBasemaps]);

  useEffect(() => {
    const map = mapRef.current;
    const maplibre = maplibreRef.current;
    if (!ready || !map || !maplibre) return;

    markersRef.current.forEach((marker) => marker.remove());
    // Selected/last markers are created last so they sit above coincident points.
    const orderedPoints = [...pointsRef.current].sort(
      (left, right) => Number(left.selected === true) - Number(right.selected === true),
    );
    markersRef.current = orderedPoints.flatMap((point) => {
      const latitude = Number(point.latitude);
      const longitude = Number(point.longitude);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return [];

      const element = document.createElement(point.onSelect ? "button" : "span");
      element.className = `map-pin${point.selected ? " is-selected" : ""}`;
      element.setAttribute("aria-label", point.label);
      element.title = point.label;

      if (element instanceof HTMLButtonElement) {
        element.type = "button";
        element.setAttribute("aria-pressed", point.selected ? "true" : "false");
        if (point.onSelect) element.addEventListener("click", point.onSelect);
      } else {
        element.setAttribute("role", "img");
      }

      const dot = document.createElement("span");
      dot.className = "map-pin-dot";
      dot.style.background = point.color ?? "var(--color-brand-600)";
      element.append(dot);

      const marker = new maplibre.Marker({ element, anchor: "bottom" })
        .setLngLat([longitude, latitude])
        .addTo(map);
      return [marker];
    });

    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
    };
  }, [ready, markerKey]);

  useEffect(() => {
    const map = mapRef.current;
    const maplibre = maplibreRef.current;
    if (!ready || !map || !maplibre || !geometryKey) return;

    const coordinates = pointsRef.current.flatMap((point) => {
      const latitude = Number(point.latitude);
      const longitude = Number(point.longitude);
      return Number.isFinite(latitude) && Number.isFinite(longitude)
        ? ([[longitude, latitude]] as Array<[number, number]>)
        : [];
    });
    if (coordinates.length === 0) return;

    const first = coordinates[0];
    if (!first) return;
    if (coordinates.length === 1) {
      map.jumpTo({ center: first, zoom: 14 });
      return;
    }

    const bounds = new maplibre.LngLatBounds(first, first);
    coordinates.slice(1).forEach((coordinate) => bounds.extend(coordinate));
    map.fitBounds(bounds, { padding: 48, maxZoom: 15, duration: 0 });
  }, [ready, geometryKey]);

  function handleLocate() {
    const map = mapRef.current;
    if (!map) return;
    if (!("geolocation" in navigator)) {
      setLocateError("Location is not available in this browser.");
      return;
    }

    setLocateError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const currentMap = mapRef.current;
        const maplibre = maplibreRef.current;
        if (!currentMap || !maplibre) return;

        const { latitude, longitude } = position.coords;
        currentMap.flyTo({ center: [longitude, latitude], zoom: 15, duration: 800 });

        locateMarkerRef.current?.remove();
        const element = document.createElement("span");
        element.className = "map-pin is-locate";
        element.setAttribute("role", "img");
        element.setAttribute("aria-label", "Your current location");
        element.title = "Your current location";
        const dot = document.createElement("span");
        dot.className = "map-pin-dot";
        dot.style.background = "var(--color-info-text)";
        element.append(dot);
        locateMarkerRef.current = new maplibre.Marker({ element, anchor: "bottom" })
          .setLngLat([longitude, latitude])
          .addTo(currentMap);
      },
      (error) => {
        if (!mapRef.current) return;
        setLocateError(
          error.code === error.PERMISSION_DENIED
            ? "Location permission was denied."
            : "Could not get your current location.",
        );
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 30_000 },
    );
  }

  if (failed) {
    return <>{fallback ?? <div className={`${className} map-fallback`} role="status">Map unavailable in this browser.</div>}</>;
  }

  return (
    <div className="map-shell">
      <div
        ref={containerRef}
        className={className}
        role="application"
        aria-label={ariaLabel}
        aria-busy={!ready}
        data-testid="map-canvas"
      />
      {ready && (builtInBasemaps || showLocateControl) ? (
        <div className="map-controls">
          {builtInBasemaps ? (
            <div className="map-basemap-toggle" role="group" aria-label="Basemap">
              <button
                type="button"
                aria-pressed={basemap === "streets"}
                onClick={() => setBasemap("streets")}
              >
                Map
              </button>
              <button
                type="button"
                aria-pressed={basemap === "satellite"}
                onClick={() => setBasemap("satellite")}
              >
                Satellite
              </button>
            </div>
          ) : null}
          {showLocateControl ? (
            <button type="button" className="map-control-button" onClick={handleLocate}>
              My location
            </button>
          ) : null}
        </div>
      ) : null}
      {locateError ? (
        <p className="map-control-message" role="status">
          {locateError}
        </p>
      ) : null}
    </div>
  );
}
