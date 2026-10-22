"""Model registry: importing this package registers every model with the Base metadata."""

from app.models.audit_event import AuditEvent  # noqa: F401
from app.models.campaign import Campaign  # noqa: F401
from app.models.distribution_record import DistributionRecord  # noqa: F401
from app.models.distribution_site import DistributionSite  # noqa: F401
from app.models.distributor_assignment import DistributorAssignment  # noqa: F401
from app.models.enums import (  # noqa: F401
    AccountType,
    AssignmentStatus,
    CampaignStatus,
    CaptureSource,
    DisplayUnit,
    EvidenceLifecycle,
    GeoFlag,
    GeoStatus,
    IntentPurpose,
    MovementType,
    RecordStatus,
    Role,
)
from app.models.organization_settings import OrganizationSettings  # noqa: F401
from app.models.photo_evidence import PhotoEvidence, UploadIntent  # noqa: F401
from app.models.stock_account import StockAccount  # noqa: F401
from app.models.stock_movement import StockMovement  # noqa: F401
from app.models.user import Invitation, PasswordResetToken, RefreshToken, User  # noqa: F401
