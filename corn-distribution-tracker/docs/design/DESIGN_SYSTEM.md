# Design System

## Direction
Modern agricultural operations software: forest green + maize/gold accent + warm neutral surfaces + dark slate text. Keep colors tokenized; do not scatter literal hex codes across components. Treat color as a status cue plus icon/label, never the only differentiator.

## Suggested tokens
- `--color-brand-950`: deep forest green for primary text/brand areas.
- `--color-brand-700`: main action green.
- `--color-brand-100`: pale green surface.
- `--color-accent-500`: maize/golden accent for highlights, not long blocks of text.
- `--color-bg`: warm off-white / light neutral.
- `--color-surface`: white.
- `--color-text`: dark slate.
- `--color-muted`: slate gray for secondary labels.
- `--color-border`: low-contrast neutral border that remains visible.
- Status: success, pending, warning, danger, informational tokens with approved contrast combinations.

## Typography and spacing
Use a highly legible sans-serif system stack or a licensed bundled font. Create a clear hierarchy for page title, section title, table/body text, metadata and numeric KPIs. Use a 4/8 px spacing scale with consistent radii and restrained shadows. Tabular numerals should be used for quantity values where supported.

## Components
- Button: primary, secondary, tertiary/ghost, destructive, loading and disabled states.
- Input/select/textarea: label, optional helper, required marker, error message, disabled state and visible focus.
- StatusBadge: text + optional icon with semantic status colors.
- StatCard: label, number, unit, optional delta/trend with truthful comparison period.
- DataTable: accessible sortable headers, responsive card fallback, row actions and empty/error state. Sorting happens within the loaded page; most screens do not yet expose pagination controls.
- MapMarker/Legend: text or icons plus colour status mapping. The admin delivery map uses MapLibre markers only for distributor-recorded delivery locations, with OpenStreetMap streets plus an Esri satellite switch by default (or a configured style), a Map/Satellite control, and a labelled coordinate board if the map cannot start; site reference points and the admin's current location are not plotted, and there is no clustering.
- Evidence tile: authorized original image via a short-lived signed URL, content type/capture time and lifecycle status. No thumbnail derivatives are generated.
- Dialog/Drawer: labelled title, escape/backdrop close, focus restoration and mobile fallback.
- Toast/inline notice: concise action result; never use toast as the only place where a critical error appears.
- Location section: permission rationale, coordinates/accuracy, captured/missing status and retry action in the delivery form. No distance/geofence warning; location never blocks approval. Evidence-integrity flags are shown separately.

## Rules
- No emoji as the primary UI icon system.
- Avoid overusing cards; group related data on page surfaces.
- Prefer clear headings and tables for operational work over decorative charts.
- Show skeletons on loading and realistic empty states instead of spinner-only blank pages.
- All controls must be keyboard accessible and have accessible names.
- Ensure graph/map colors work in common color-vision deficiencies and pair colors with labels.
