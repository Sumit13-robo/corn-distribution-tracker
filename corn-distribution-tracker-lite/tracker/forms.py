"""Forms for the Lite edition. Validation lives close to the server boundary."""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from .models import Assignment, Campaign, Role, Site, User, validate_photo_size
from .services import available_kg_for, central_account, format_kg


class LoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(
            attrs={"autofocus": True, "autocomplete": "email", "placeholder": "you@example.org"}
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "code", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"code": "Short unique reference, for example RAINS-26."}

    def clean_code(self) -> str:
        return self.cleaned_data["code"].strip().upper()


class SiteForm(forms.ModelForm):
    class Meta:
        model = Site
        fields = ["name", "code", "region", "address", "is_active", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"code": "Short unique site code, for example SITE-001."}

    def clean_code(self) -> str:
        return self.cleaned_data["code"].strip().upper()


class DistributorForm(forms.Form):
    email = forms.EmailField(label="Email")
    display_name = forms.CharField(label="Display name", max_length=120)
    password1 = forms.CharField(
        label="Initial password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Share it through a secure channel. Only an administrator can reset it in the Lite edition.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        confirm = cleaned.get("password2")
        if password and confirm and password != confirm:
            self.add_error("password2", "The passwords do not match.")
        if password:
            candidate = User(
                email=cleaned.get("email", ""), display_name=cleaned.get("display_name", "")
            )
            try:
                validate_password(password, user=candidate)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self) -> User:
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            display_name=self.cleaned_data["display_name"].strip(),
            role=Role.DISTRIBUTOR,
            is_active=True,
        )


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ["campaign", "site", "distributor", "target_kg", "due_on", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {"target_kg": "Expected kilograms for this site and campaign."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["campaign"].queryset = Campaign.objects.filter(status=Campaign.Status.ACTIVE)
        self.fields["site"].queryset = Site.objects.filter(is_active=True)
        self.fields["distributor"].queryset = User.objects.filter(
            role=Role.DISTRIBUTOR, is_active=True
        )

    def clean(self):
        cleaned = super().clean()
        campaign = cleaned.get("campaign")
        site = cleaned.get("site")
        distributor = cleaned.get("distributor")
        if campaign and site and distributor:
            duplicate = Assignment.objects.filter(
                campaign=campaign, site=site, distributor=distributor
            )
            if self.instance.pk:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError(
                    "An assignment already exists for that campaign, site and distributor."
                )
        return cleaned


class ReceiptForm(forms.Form):
    quantity_kg = forms.DecimalField(
        label="Quantity (kg)",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    note = forms.CharField(
        label="Reference or note",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={"placeholder": "Receipt / supplier reference"}),
    )


class AllocationForm(forms.Form):
    distributor = forms.ModelChoiceField(
        label="Distributor",
        queryset=User.objects.none(),
    )
    quantity_kg = forms.DecimalField(
        label="Quantity (kg)",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    note = forms.CharField(
        label="Note",
        required=False,
        max_length=300,
        widget=forms.TextInput(attrs={"placeholder": "Optional reference"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["distributor"].queryset = User.objects.filter(
            role=Role.DISTRIBUTOR, is_active=True
        )
        central = central_account()
        self.fields[
            "quantity_kg"
        ].help_text = f"Central stock available: {format_kg(central.balance_kg)} kg."

    def clean_quantity_kg(self) -> Decimal:
        quantity = self.cleaned_data["quantity_kg"]
        available = central_account().balance_kg
        if quantity > available:
            raise ValidationError(f"Only {format_kg(available)} kg is available in central stock.")
        return quantity


class DeliveryForm(forms.Form):
    assignment = forms.ModelChoiceField(label="Assignment", queryset=Assignment.objects.none())
    quantity_kg = forms.DecimalField(
        label="Quantity (kg)",
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    notes = forms.CharField(
        label="Notes",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Optional context for the reviewer"}
        ),
    )
    photo = forms.ImageField(
        label="Evidence photo",
        required=False,
        help_text="JPG, PNG or WebP up to 5 MB. Stored privately and shown only to authorized users.",
        widget=forms.ClearableFileInput(attrs={"accept": "image/jpeg,image/png,image/webp"}),
        validators=[
            FileExtensionValidator(allowed_extensions=["jpg", "jpeg", "png", "webp"]),
            validate_photo_size,
        ],
    )

    def __init__(self, *args, user: User, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["assignment"].queryset = (
            Assignment.objects.filter(
                distributor=user,
                status=Assignment.Status.ACTIVE,
                campaign__status=Campaign.Status.ACTIVE,
                site__is_active=True,
            )
            .select_related("site", "campaign")
            .order_by("site__code")
        )
        available = available_kg_for(user)
        self.fields[
            "quantity_kg"
        ].help_text = f"Available after pending submissions: {format_kg(available)} kg."

    def clean(self):
        cleaned = super().clean()
        assignment = cleaned.get("assignment")
        quantity = cleaned.get("quantity_kg")
        if assignment and quantity:
            available = available_kg_for(self.user)
            if quantity > available:
                raise ValidationError(
                    f"Only {format_kg(available)} kg is available after pending submissions."
                )
        return cleaned


class ReviewForm(forms.Form):
    APPROVE = "APPROVE"
    REJECT = "REJECT"

    decision = forms.ChoiceField(
        choices=[(APPROVE, "Approve and post stock"), (REJECT, "Reject with a reason")],
        widget=forms.RadioSelect,
        initial=APPROVE,
    )
    note = forms.CharField(
        label="Review note",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "placeholder": "Required when rejecting; optional when approving."}
        ),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == self.REJECT and not cleaned.get("note", "").strip():
            self.add_error("note", "Give the distributor a reason before rejecting.")
        return cleaned


def delivery_form_for(user: User, data=None, files=None, initial=None) -> DeliveryForm:
    """Convenience wrapper keeps the view free of form-construction details."""
    return DeliveryForm(data=data, files=files, initial=initial, user=user)
