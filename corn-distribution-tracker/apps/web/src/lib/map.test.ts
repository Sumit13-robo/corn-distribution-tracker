import { describe, expect, it } from "vitest";
import {
  buildMapStyle,
  ESRI_WORLD_IMAGERY_ATTRIBUTION,
  ESRI_WORLD_IMAGERY_TILE_URL,
  googleMapsViewerUrl,
  hasBuiltInBasemaps,
  OPENSTREETMAP_ATTRIBUTION,
  OPENSTREETMAP_TILE_URL,
  osmViewerUrl,
} from "./map";

describe("buildMapStyle", () => {
  it("defaults to OpenStreetMap streets plus Esri satellite with visible attribution", () => {
    expect(buildMapStyle("", "", "")).toMatchObject({
      version: 8,
      sources: {
        "openstreetmap-raster": {
          type: "raster",
          tiles: [OPENSTREETMAP_TILE_URL],
          attribution: OPENSTREETMAP_ATTRIBUTION,
        },
        "esri-world-imagery": {
          type: "raster",
          tiles: [ESRI_WORLD_IMAGERY_TILE_URL],
          attribution: ESRI_WORLD_IMAGERY_ATTRIBUTION,
        },
      },
      layers: [
        { id: "openstreetmap-raster", type: "raster", source: "openstreetmap-raster" },
        {
          id: "esri-world-imagery",
          type: "raster",
          source: "esri-world-imagery",
          layout: { visibility: "none" },
        },
      ],
    });
  });

  it("uses a configured vector style instead of the built-in basemaps", () => {
    const url = "https://tiles.example.org/style.json";
    expect(buildMapStyle(url, "https://tiles.example.org/{z}/{x}/{y}.png")).toBe(url);
  });

  it("allows a street tile-server override", () => {
    const tileUrl = "https://tiles.example.org/{z}/{x}/{y}.png";
    expect(buildMapStyle("", tileUrl)).toMatchObject({
      sources: { "openstreetmap-raster": { tiles: [tileUrl] } },
    });
  });

  it("allows a satellite tile-server override", () => {
    const satelliteUrl = "https://imagery.example.org/{z}/{y}/{x}.jpg";
    expect(buildMapStyle("", "", satelliteUrl)).toMatchObject({
      sources: { "esri-world-imagery": { tiles: [satelliteUrl] } },
    });
  });
});

describe("hasBuiltInBasemaps", () => {
  it("is true only when no full style URL is configured", () => {
    expect(hasBuiltInBasemaps("")).toBe(true);
    expect(hasBuiltInBasemaps("https://tiles.example.org/style.json")).toBe(false);
  });
});

describe("osmViewerUrl", () => {
  it("links to the exact coordinate", () => {
    expect(osmViewerUrl("4.8491", "31.5712")).toBe(
      "https://www.openstreetmap.org/?mlat=4.849100&mlon=31.571200#map=17/4.849100/31.571200",
    );
  });

  it("falls back to the OSM home page for invalid coordinates", () => {
    expect(osmViewerUrl("not-a-number", "31.5712")).toBe("https://www.openstreetmap.org/");
    expect(osmViewerUrl("95", "31.5712")).toBe("https://www.openstreetmap.org/");
  });
});

describe("googleMapsViewerUrl", () => {
  it("links to the exact coordinate", () => {
    expect(googleMapsViewerUrl("4.8491", "31.5712")).toBe(
      "https://www.google.com/maps/search/?api=1&query=4.849100%2C31.571200",
    );
  });

  it("falls back to Google Maps for invalid coordinates", () => {
    expect(googleMapsViewerUrl("not-a-number", "31.5712")).toBe("https://www.google.com/maps");
    expect(googleMapsViewerUrl("4.8491", "200")).toBe("https://www.google.com/maps");
  });
});
