"""Boundary validation serializers for all API writes.

DRF serializers validate types, lengths, choices and decimal scale before any
domain service sees the payload. Server authorization remains in views; this
module is only about well-formed input.
"""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    """Reject unknown keys instead of silently ignoring client typos."""

    def to_internal_value(self, data):
        if isinstance(data, dict):
            unknown = set(data) - set(self.fields)
            if unknown:
                raise serializers.ValidationError(
                    {key: "Unknown field." for key in sorted(unknown)}
                )
        return super().to_internal_value(data)


class LoginSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=320)
    password = serializers.CharField(max_length=200, trim_whitespace=False)


class ChangePasswordSerializer(StrictSerializer):
    current_password = serializers.CharField(max_length=200, trim_whitespace=False)
    new_password = serializers.CharField(max_length=200, trim_whitespace=False)


class ForgotPasswordSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=320)


class ResetPasswordSerializer(StrictSerializer):
    token = serializers.CharField(min_length=10, max_length=200)
    password = serializers.CharField(max_length=200, trim_whitespace=False)


class AcceptInvitationSerializer(StrictSerializer):
    token = serializers.CharField(min_length=10, max_length=200)
    password = serializers.CharField(max_length=200, trim_whitespace=False)
    display_name = serializers.CharField(max_length=120, required=False, allow_null=True)


class InvitationCreateSerializer(StrictSerializer):
    email = serializers.EmailField(max_length=320)
    display_name = serializers.CharField(min_length=1, max_length=120)
    role = serializers.ChoiceField(choices=["ADMIN", "DISTRIBUTOR"], default="DISTRIBUTOR")


class CampaignCreateSerializer(StrictSerializer):
    name = serializers.CharField(min_length=1, max_length=160)
    reference_code = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=40)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=["DRAFT", "ACTIVE", "PAUSED", "CLOSED"], default="DRAFT"
    )
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=False, default="UTC")
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)
    # Name-only sites can be created together with the campaign. Coordinates
    # and site codes are optional; the service generates a stable code.
    sites = serializers.ListField(
        child=serializers.CharField(max_length=160, allow_blank=False),
        required=False,
        default=list,
        max_length=200,
    )

    def validate_sites(self, value):
        unique: list[str] = []
        seen: set[str] = set()
        for raw in value:
            name = raw.strip()
            key = name.casefold()
            if name and key not in seen:
                unique.append(name)
                seen.add(key)
        return unique


class CampaignPatchSerializer(StrictSerializer):
    name = serializers.CharField(min_length=1, max_length=160, required=False)
    starts_at = serializers.DateTimeField(required=False, allow_null=True)
    ends_at = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=["DRAFT", "ACTIVE", "PAUSED", "CLOSED"], required=False
    )
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=False)
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)


class SiteCreateSerializer(StrictSerializer):
    name = serializers.CharField(min_length=1, max_length=160)
    site_code = serializers.RegexField(
        r"^[A-Za-z0-9_-]+$", max_length=40, required=False, allow_blank=False
    )
    campaign_id = serializers.UUIDField(required=False, allow_null=True)
    address_text = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )
    region = serializers.CharField(max_length=120, required=False, allow_null=True, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        required=False,
        allow_null=True,
    )
    geofence_radius_m = serializers.IntegerField(
        min_value=1, max_value=100_000, required=False, default=200
    )
    max_acceptable_accuracy_m = serializers.IntegerField(
        min_value=1, max_value=5000, required=False, allow_null=True
    )
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        has_lat = attrs.get("latitude") is not None
        has_lng = attrs.get("longitude") is not None
        if has_lat != has_lng:
            raise serializers.ValidationError(
                "Site location requires both latitude and longitude (or neither)."
            )
        return attrs


class SitePatchSerializer(StrictSerializer):
    name = serializers.CharField(min_length=1, max_length=160, required=False)
    site_code = serializers.RegexField(r"^[A-Za-z0-9_-]+$", max_length=40, required=False)
    address_text = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )
    region = serializers.CharField(max_length=120, required=False, allow_null=True, allow_blank=True)
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        required=False,
        allow_null=True,
    )
    geofence_radius_m = serializers.IntegerField(
        min_value=1, max_value=100_000, required=False, allow_null=True
    )
    max_acceptable_accuracy_m = serializers.IntegerField(
        min_value=1, max_value=5000, required=False, allow_null=True
    )
    is_active = serializers.BooleanField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)


class AssignmentCreateSerializer(StrictSerializer):
    site_id = serializers.UUIDField()
    campaign_id = serializers.UUIDField(required=False, allow_null=True)
    distributor_user_id = serializers.UUIDField()
    target_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, required=False, default="KG")
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_null=True, allow_blank=True)


class AssignmentPatchSerializer(StrictSerializer):
    target_quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0.001"), required=False
    )
    unit = serializers.CharField(max_length=10, required=False)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(choices=["ACTIVE", "PAUSED", "COMPLETE"], required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_null=True, allow_blank=True)


class ReceiptSerializer(StrictSerializer):
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, required=False, default="KG")
    source_reference = serializers.CharField(min_length=1, max_length=200)
    received_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_null=True, allow_blank=True)


class AllocationSerializer(StrictSerializer):
    distributor_user_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, required=False, default="KG")
    campaign_id = serializers.UUIDField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=1000, required=False, allow_null=True, allow_blank=True)


class AdjustmentSerializer(StrictSerializer):
    account_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, required=False, default="KG")
    movement_type = serializers.ChoiceField(choices=["LOSS", "RETURN"])
    reason = serializers.CharField(min_length=3, max_length=2000)
    destination_account_id = serializers.UUIDField(required=False, allow_null=True)


class ReversalSerializer(StrictSerializer):
    reason = serializers.CharField(min_length=3, max_length=2000)


class EvidenceSpecSerializer(StrictSerializer):
    intent_id = serializers.UUIDField()
    capture_source = serializers.CharField(max_length=20)
    client_captured_at = serializers.DateTimeField(required=False, allow_null=True)


class LocationSerializer(StrictSerializer):
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
        required=False,
        allow_null=True,
    )
    longitude = serializers.DecimalField(
        max_digits=10,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
        required=False,
        allow_null=True,
    )
    accuracy_m = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    timestamp = serializers.DateTimeField(required=False, allow_null=True)
    device_time = serializers.DateTimeField(required=False, allow_null=True)
    client_created_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        has_lat = attrs.get("latitude") is not None
        has_lng = attrs.get("longitude") is not None
        if has_lat != has_lng:
            raise serializers.ValidationError(
                "Location requires both latitude and longitude (or neither)."
            )
        return attrs


class DeliveryCreateSerializer(StrictSerializer):
    assignment_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(max_length=10, default="KG")
    notes = serializers.CharField(max_length=2000, required=False, allow_null=True, allow_blank=True)
    evidence = EvidenceSpecSerializer(many=True, min_length=1, max_length=5)
    location = LocationSerializer(required=False, allow_null=True)


class ApprovalSerializer(StrictSerializer):
    exception_reason = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )
    review_note = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )


class RejectSerializer(StrictSerializer):
    reason = serializers.CharField(min_length=3, max_length=2000)


class CancelSerializer(StrictSerializer):
    reason = serializers.CharField(
        max_length=2000, required=False, allow_null=True, allow_blank=True
    )


class UploadIntentSerializer(StrictSerializer):
    content_type = serializers.CharField(max_length=64)
    purpose = serializers.CharField(max_length=32, required=False, default="DISTRIBUTION_EVIDENCE")


class SettingsPatchSerializer(StrictSerializer):
    timezone = serializers.CharField(max_length=64, required=False, allow_blank=False)
    default_display_unit = serializers.ChoiceField(
        choices=["KG", "QUINTAL", "TONNE", "BAG"], required=False
    )
    kg_per_bag = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=Decimal("0.01"),
        max_value=Decimal("1000"),
        required=False,
        allow_null=True,
    )
    default_geofence_radius_m = serializers.IntegerField(
        min_value=1, max_value=100_000, required=False
    )
    max_acceptable_gps_accuracy_m = serializers.IntegerField(
        min_value=1, max_value=5000, required=False
    )
    max_location_age_seconds = serializers.IntegerField(min_value=1, max_value=86400, required=False)
    max_capture_time_drift_seconds = serializers.IntegerField(
        min_value=1, max_value=86400, required=False
    )


class DistributorUpdateSerializer(StrictSerializer):
    display_name = serializers.CharField(min_length=1, max_length=120, required=False)
