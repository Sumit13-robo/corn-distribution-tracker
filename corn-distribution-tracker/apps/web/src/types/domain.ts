/**
 * Shared domain types mirroring docs/architecture/API_CONTRACT.md and the
 * Django/DRF serializers. Decimal quantities are JSON strings; they are kept
 * as strings here so no client code ever re-rounds canonical kg values. Do not
 * invent fields the API does not return.
 */

export type Role = "ADMIN" | "DISTRIBUTOR";

export type CampaignStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "CLOSED";

export type RecordStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"
  | "REVERSED";

export type GeoStatus = "PASS" | "WARNING" | "EXCEPTION" | "UNAVAILABLE";

export type MovementType =
  | "RECEIPT"
  | "TRANSFER"
  | "DELIVERY"
  | "RETURN"
  | "LOSS"
  | "ADJUSTMENT"
  | "REVERSAL";

export type AssignmentStatus = "ACTIVE" | "PAUSED" | "COMPLETE";

/** Generic paginated envelope (docs/architecture/API_CONTRACT.md). */
export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

/** Consistent error envelope: {"error": {...}} */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    request_id: string;
    details: Array<Record<string, unknown>>;
  };
}

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  must_reset_password: boolean;
  last_login_at: string | null;
}

/** POST /auth/login returns the current user; the session cookie is HttpOnly. */
export interface LoginOut {
  user: UserOut;
}

export interface AckOut {
  status: "ok";
  message: string;
}

export interface InvitationOut {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

/** Invitation creation returns the raw token exactly once (never persisted). */
export interface InvitationCreatedOut extends InvitationOut {
  invite_token: string;
}

export interface DistributorOut {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  must_reset_password: boolean;
  last_login_at: string | null;
  created_at: string;
}

export interface DistributorDetailOut extends DistributorOut {
  stock_balance_kg: string;
  reserved_kg: string;
  available_kg: string;
  assigned_campaign_count?: number;
  open_assignment_count?: number;
  has_open_invitation?: boolean;
}

export interface DistributorListOut {
  items: DistributorDetailOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface CampaignOut {
  id: string;
  name: string;
  reference_code: string;
  starts_at: string | null;
  ends_at: string | null;
  status: CampaignStatus | string;
  timezone: string;
  notes: string | null;
  created_at: string;
}

export interface CampaignIn {
  name: string;
  reference_code: string;
  starts_at?: string | null;
  ends_at?: string | null;
  status?: CampaignStatus;
  timezone?: string;
  notes?: string | null;
  /** Name-only sites created together with the campaign in one transaction. */
  sites?: string[];
}

export interface CampaignPatchIn {
  name?: string;
  starts_at?: string | null;
  ends_at?: string | null;
  status?: CampaignStatus;
  timezone?: string;
  notes?: string | null;
}

export interface SiteOut {
  id: string;
  name: string;
  site_code: string;
  campaign_id: string | null;
  address_text: string | null;
  region: string | null;
  /** Null until an admin optionally records the site reference point. */
  latitude: string | null;
  longitude: string | null;
  geofence_radius_m: number;
  max_acceptable_accuracy_m: number | null;
  is_active: boolean;
  notes: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface SiteIn {
  name: string;
  site_code?: string;
  campaign_id?: string | null;
  address_text?: string | null;
  region?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  geofence_radius_m?: number;
  max_acceptable_accuracy_m?: number | null;
  notes?: string | null;
}

export interface SitePatchIn {
  name?: string | null;
  site_code?: string | null;
  address_text?: string | null;
  region?: string | null;
  latitude?: string | null;
  longitude?: string | null;
  geofence_radius_m?: number | null;
  max_acceptable_accuracy_m?: number | null;
  is_active?: boolean | null;
  notes?: string | null;
}

export interface SiteProgressOut {
  target_kg: string;
  submitted_kg: string;
  approved_kg: string;
  pending_kg: string;
  rejected_kg: string;
  remaining_target_kg: string;
  submission_count: number;
  last_visit_at: string | null;
  evidence_status: string;
  has_flagged_evidence: boolean;
}

export interface AssignmentOut {
  id: string;
  campaign_id: string | null;
  site_id: string;
  distributor_user_id: string;
  target_quantity_kg: string;
  due_at: string | null;
  status: AssignmentStatus | string;
  notes: string | null;
  created_at: string;
}

export interface AssignmentIn {
  site_id: string;
  campaign_id?: string | null;
  distributor_user_id: string;
  target_quantity: string;
  unit?: string;
  due_at?: string | null;
  notes?: string | null;
}

export interface AssignmentPatchIn {
  target_quantity?: string;
  unit?: string;
  due_at?: string | null;
  status?: AssignmentStatus;
  notes?: string | null;
}

/** GET /distributors/me/assignments (distributor self-service read). */
export interface DistributorAssignmentItemOut {
  assignment_id: string;
  campaign_id: string | null;
  due_at: string | null;
  status: string;
  target_kg: string;
  approved_kg: string;
  pending_kg: string;
  remaining_target_kg: string;
  over_target_kg: string;
  site: SiteOut | null;
}

export interface AccountOut {
  id: string;
  account_type: "CENTRAL" | "DISTRIBUTOR" | "SITE" | string;
  name: string;
  owner_user_id: string | null;
  site_id: string | null;
  posted_balance_kg: string;
  reserved_kg: string;
  available_kg: string;
}

export interface ReconciliationOut {
  received_kg: string;
  reversed_receipt_kg: string;
  loss_kg: string;
  reversed_loss_kg: string;
  net_external_kg: string;
  sum_account_balances_kg: string;
  balanced: boolean;
}

export interface InventorySummaryOut {
  accounts: AccountOut[];
  reconciliation: ReconciliationOut | null;
}

export interface StockMovementOut {
  id: string;
  movement_type: MovementType | string;
  source_account_id: string | null;
  destination_account_id: string | null;
  quantity_kg: string;
  reference_type: string;
  reference_id: string | null;
  idempotency_key: string | null;
  occurred_at: string | null;
  posted_at: string;
  created_by: string | null;
  reason: string | null;
  reversal_of_id: string | null;
  reversed_by_id: string | null;
  movement_metadata: Record<string, unknown>;
}

export interface ReceiptIn {
  quantity: string;
  unit?: string;
  source_reference: string;
  received_at?: string | null;
  notes?: string | null;
}

export interface AllocationIn {
  distributor_user_id: string;
  quantity: string;
  unit?: string;
  campaign_id?: string | null;
  notes?: string | null;
}

export interface AdjustmentIn {
  account_id: string;
  quantity: string;
  unit?: string;
  movement_type: "LOSS" | "RETURN";
  reason: string;
  destination_account_id?: string | null;
}

export interface ReversalIn {
  reason: string;
}

export interface DisplayUnitOut {
  quantity_kg: string;
  unit: string;
  factor_label: string;
  display_value: string;
}

export interface EvidenceOut {
  id: string;
  content_type: string;
  size_bytes: number;
  sha256_hex: string;
  capture_source: string;
  client_captured_at: string | null;
  server_received_at: string | null;
  exif_latitude: string | null;
  exif_longitude: string | null;
  exif_taken_at: string | null;
  metadata_check_result: Record<string, unknown>;
  validation_flags: string[];
  lifecycle_status: string;
}

export interface DistributionOut {
  id: string;
  campaign_id: string | null;
  assignment_id: string;
  site_id: string;
  site_code: string;
  site_name: string;
  distributor_user_id: string;
  distributor_name: string;
  quantity_kg: string;
  status: RecordStatus | string;
  client_created_at: string | null;
  submitted_at: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  review_reason: string | null;
  review_exception_reason: string | null;
  reversed_at: string | null;
  reversed_by: string | null;
  reversal_reason: string | null;
  stock_movement_id: string | null;
  notes: string | null;
  location_latitude: string | null;
  location_longitude: string | null;
  location_accuracy_m: string | null;
  location_timestamp: string | null;
  device_reported_location_time: string | null;
  distance_to_site_m: string | null;
  geo_status: GeoStatus | string;
  geo_flags: string[];
  evidence: EvidenceOut[];
  created_at: string;
  updated_at: string | null;
}

export interface EvidenceSpecIn {
  intent_id: string;
  capture_source: string;
  client_captured_at?: string | null;
}

export interface LocationIn {
  latitude?: string | null;
  longitude?: string | null;
  accuracy_m?: string | null;
  timestamp?: string | null;
  device_time?: string | null;
  client_created_at?: string | null;
}

export interface DeliveryCreateIn {
  assignment_id: string;
  quantity: string;
  unit: string;
  notes?: string | null;
  evidence: EvidenceSpecIn[];
  location?: LocationIn | null;
}

export interface DeliveryApproveIn {
  exception_reason?: string | null;
  review_note?: string | null;
}

export interface DeliveryListFilters {
  status?: string;
  campaign_id?: string;
  site_id?: string;
  distributor_user_id?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}

export interface UploadIntentOut {
  intent_id: string;
  expires_at: string;
  upload_method: string;
  upload_url: string;
  headers: Record<string, string>;
}

export interface UploadCompletionOut {
  intent_id: string;
  completed: boolean;
  newly_verified: boolean;
  size_bytes: number | null;
  sha256_hex: string | null;
  content_type: string;
}

export interface ViewURLOut {
  evidence_id: string;
  url: string;
  expires_in_seconds: number;
}

export interface StockPositionOut {
  central_on_hand_kg: string;
  distributor_held_kg: string;
  site_stock_kg: string;
  reserved_pending_kg: string;
}

export interface EvidenceCompletenessOut {
  approved_with_evidence: number;
  approved_total: number;
  ratio: number | null;
}

export interface OverviewOut {
  filters: Record<string, unknown>;
  stock: StockPositionOut;
  submitted_pending_kg: string;
  approved_delivered_kg: string;
  rejected_kg: string;
  open_review_count: number;
  target_kg: string;
  remaining_target_kg: string;
  over_target_kg: string;
  evidence_completeness: EvidenceCompletenessOut;
  flagged_record_count: number;
  unit: string;
}

export interface DistributorPerfOut {
  distributor_user_id: string;
  display_name: string;
  email: string;
  is_active: boolean;
  target_kg: string;
  submitted_kg: string;
  approved_kg: string;
  pending_kg: string;
  rejected_kg: string;
  remaining_target_kg: string;
  over_target_kg: string;
  stock_balance_kg: string;
  flagged_submissions: number;
  approved_with_exception: number;
  denominator_note: string;
}

export interface SitePerfOut {
  site_id: string;
  site_code: string;
  site_name: string;
  is_active: boolean;
  target_kg: string;
  approved_kg: string;
  pending_kg: string;
  rejected_kg: string;
  remaining_target_kg: string;
  last_visit_at: string | null;
  evidence_status: string;
  denominator_note: string;
}

export interface MapSiteOut {
  id: string;
  site_code: string;
  name: string;
  latitude: string;
  longitude: string;
  is_active: boolean;
  target_kg: string;
  approved_kg: string;
  pending_kg: string;
  remaining_target_kg: string;
  submission_count: number;
  status: string;
  last_visit_at: string | null;
  has_flagged_evidence: boolean;
}

export interface MapDeliveryOut {
  id: string;
  site_id: string;
  site_code: string;
  site_name: string;
  campaign_id: string | null;
  distributor_user_id: string;
  distributor_name: string;
  quantity_kg: string;
  status: string;
  submitted_at: string;
  location_latitude: string;
  location_longitude: string;
  location_accuracy_m: string | null;
  location_timestamp: string | null;
}

export interface SettingsOut {
  timezone: string;
  default_display_unit: "KG" | "QUINTAL" | "TONNE" | "BAG" | string;
  kg_per_bag: string | null;
  default_geofence_radius_m: number;
  max_acceptable_gps_accuracy_m: number;
  max_location_age_seconds: number;
  max_capture_time_drift_seconds: number;
  updated_at: string | null;
}

export interface SettingsPatchIn {
  timezone?: string;
  default_display_unit?: string;
  kg_per_bag?: string | null;
  default_geofence_radius_m?: number;
  max_acceptable_gps_accuracy_m?: number;
  max_location_age_seconds?: number;
  max_capture_time_drift_seconds?: number;
}

export interface AuditEventOut {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  occurred_at: string;
  reason: string | null;
  details: Record<string, unknown> | null;
}

export interface AuditEventFilters {
  action?: string;
  actor_user_id?: string;
  target_type?: string;
  target_id?: string;
  from?: string;
  to?: string;
  limit?: number;
  offset?: number;
}
