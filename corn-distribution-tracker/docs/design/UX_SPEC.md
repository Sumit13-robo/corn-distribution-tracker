# UX Specification

## Product personality
Trustworthy, calm, operational and field-friendly. The app is for accountable logistics, not a consumer social product. Use a restrained agricultural palette, strong typographic hierarchy, real whitespace, compact but legible tables, and purposeful imagery. Avoid giant gradients, glassmorphism, gratuitous animation, fake KPIs, and overly playful illustrations.

## Information architecture
### Admin navigation
- Overview
- Live Distribution Map
- Campaigns & Targets
- Distribution Sites
- Distributors
- Inventory & Ledger
- Evidence Review
- Analytics & Exports
- Settings / Audit Trail (only expose available features)

### Distributor navigation
- My Overview
- My Sites
- New Site Update (contextual action)
- My Submissions
- Drafts & Sync
- Profile / Help

Do not show admin links to distributors. Route guards are not a security boundary; server permissions must align.

## Admin overview
Top-level metric row: Central on hand, Distributor-held, Approved delivered, Pending review, Remaining target, Flagged evidence. Every metric includes unit and “as of”/filter context where useful. Below: campaign progress, map preview, review queue needing action, distributor activity, recent audit/activity feed. KPIs must have definitions and drill down into filtered records.

## Map
Map plus filter/list panel. Filters include campaign, site status, distributor, submission state and date as supported. Cluster at zoomed-out levels. Use distinct marker glyphs or labels as well as color. Legend visible. Clicking a site opens a side panel with target/submitted/approved/pending/remaining, last evidence preview, flags, distributor and open-detail action. Map must not dominate mobile admin screens; use list-first layout on small screens.

## Distributor overview
Simple cards for allocated/available stock, target remaining, submitted pending, approved deliveries and drafts waiting to sync. Prioritize “Continue draft” and “Update assigned site”. Show assigned site list with distance/site code, due status where used, target progress and last submission. No complex charts that require precise hover on mobile.

## Delivery form
Use short, clear steps or sections: Site confirmed → Location captured → Photo captured → Quantity entered → Review & submit. Show permission rationale before opening browser prompt. Show location accuracy in metres, site distance and warnings before submission. Quantity unit is explicit; bag conversion is displayed when used. Disable duplicate double-click submissions and show progress. Provide a confirmation summary and the server-confirmed submission reference.

## Photo review
Large evidence preview paired with structured details; make flags easy to scan but not alarming by default. Provide previous/next review navigation, keyboard access, approve and reject actions, mandatory reason for reject, reason for geo exception, and confirmation when action posts stock. Keep original image private and display its capture/source context.

## Tables and forms
- Search, filters, pagination, column headings, empty state with next action, inline validation and clear required indicators.
- Keep filters in URL where valuable for shareable/reloadable admin views.
- Display quantities in one consistent unit per view; make conversion clear.
- Use formatted dates/timezone explicitly. For UTC timestamps, render in configured organization/campaign timezone and label if ambiguity exists.
- Destructive actions require confirmation and show effect; stock adjustments require reason and summary.

## Responsive behavior
- Admin desktop: persistent sidebar, top bar with campaign context/profile, content panels and tables.
- Admin tablet/mobile: collapsible navigation, cards instead of overflowing dense tables, map switches to list-first mode.
- Distributor mobile: one-column layout, large touch targets (at least about 44×44 CSS px), sticky primary action only where it does not hide form content, safe bottom spacing, camera/location permission feedback and retry UI.

## States and accessibility
Every async page supports loading skeleton/spinner that does not shift the whole page, empty state, recoverable error and retry, permission denied, unauthorized redirect, offline status, and success confirmation. Use semantic headings, labels, focus states, keyboard controls, reduced-motion preferences, sufficient contrast, accessible dialogs, and text/icon status indicators.
