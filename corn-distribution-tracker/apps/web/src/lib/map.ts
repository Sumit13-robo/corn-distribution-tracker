import type { StyleSpecification } from "maplibre-gl";

/**
 * Basemap configuration.
 *
 * A full vector style can be supplied with `VITE_MAP_STYLE_URL`. When it is
 * empty, MapLibre renders two built-in raster basemaps:
 * - OpenStreetMap streets (default)
 * - Esri World Imagery satellite (toggle in the map UI)
 *
 * OpenStreetMap has good road data in many Indian cities, while satellite
 * imagery makes the exact ground location and building footprints easier to
 * verify. Google Maps remains the most accurate general-purpose map for India,
 * but embedding it requires a Google Maps API key and billing; exact-coordinate
 * "Google Maps" links are provided next to every location instead.
 */
export const OPENSTREETMAP_TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

export const OPENSTREETMAP_ATTRIBUTION =
  '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors';

export const ESRI_WORLD_IMAGERY_TILE_URL =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";

export const ESRI_WORLD_IMAGERY_ATTRIBUTION =
  'Imagery © <a href="https://www.esri.com/" target="_blank" rel="noopener noreferrer">Esri</a>, Maxar, Earthstar Geographics, and the GIS User Community';

export const BASEMAP_LAYER_IDS = {
  streets: "openstreetmap-raster",
  satellite: "esri-world-imagery",
} as const;

export type BasemapId = keyof typeof BASEMAP_LAYER_IDS;

function envValue(
  name: "VITE_MAP_STYLE_URL" | "VITE_MAP_TILE_URL" | "VITE_MAP_SATELLITE_TILE_URL",
): string {
  const value = import.meta.env[name];
  return typeof value === "string" ? value.trim() : "";
}

/** Full custom styles cannot be toggled because their layer ids are unknown. */
export function hasBuiltInBasemaps(styleUrl = envValue("VITE_MAP_STYLE_URL")): boolean {
  return styleUrl.length === 0;
}

/**
 * Resolve the MapLibre style. Arguments are injectable so the default and
 * override paths can be tested without mutating `import.meta.env`.
 */
export function buildMapStyle(
  styleUrl = envValue("VITE_MAP_STYLE_URL"),
  tileUrl = envValue("VITE_MAP_TILE_URL"),
  satelliteTileUrl = envValue("VITE_MAP_SATELLITE_TILE_URL"),
): string | StyleSpecification {
  if (styleUrl) return styleUrl;

  return {
    version: 8,
    sources: {
      [BASEMAP_LAYER_IDS.streets]: {
        type: "raster",
        tiles: [tileUrl || OPENSTREETMAP_TILE_URL],
        tileSize: 256,
        maxzoom: 19,
        attribution: OPENSTREETMAP_ATTRIBUTION,
      },
      [BASEMAP_LAYER_IDS.satellite]: {
        type: "raster",
        tiles: [satelliteTileUrl || ESRI_WORLD_IMAGERY_TILE_URL],
        tileSize: 256,
        maxzoom: 19,
        attribution: ESRI_WORLD_IMAGERY_ATTRIBUTION,
      },
    },
    layers: [
      { id: BASEMAP_LAYER_IDS.streets, type: "raster", source: BASEMAP_LAYER_IDS.streets },
      {
        id: BASEMAP_LAYER_IDS.satellite,
        type: "raster",
        source: BASEMAP_LAYER_IDS.satellite,
        layout: { visibility: "none" },
      },
    ],
  };
}

function parsedCoordinates(
  latitude: string | number,
  longitude: string | number,
): { lat: string; lng: string } | null {
  const lat = Number(latitude);
  const lng = Number(longitude);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || lat < -90 || lat > 90 || lng < -180 || lng > 180) {
    return null;
  }
  return { lat: lat.toFixed(6), lng: lng.toFixed(6) };
}

/** Link to the exact coordinate on the OpenStreetMap website. */
export function osmViewerUrl(latitude: string | number, longitude: string | number): string {
  const coordinates = parsedCoordinates(latitude, longitude);
  if (!coordinates) return "https://www.openstreetmap.org/";
  return `https://www.openstreetmap.org/?mlat=${coordinates.lat}&mlon=${coordinates.lng}#map=17/${coordinates.lat}/${coordinates.lng}`;
}

/**
 * Link to the exact coordinate in Google Maps. This uses the public consumer
 * URL and needs no API key; it is not an embedded map.
 */
export function googleMapsViewerUrl(latitude: string | number, longitude: string | number): string {
  const coordinates = parsedCoordinates(latitude, longitude);
  if (!coordinates) return "https://www.google.com/maps";
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${coordinates.lat},${coordinates.lng}`)}`;
}
