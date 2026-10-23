"""Optional Django-admin surface for operators.

The product itself uses the server-rendered pages; this is a convenience for
debugging and emergency account maintenance. Ledger and delivery rows are
read-only here so the admin cannot bypass the stock workflow.
"""

from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.core.exceptions import ValidationError

from .models import (
    Activity,
    Assignment,
    Campaign,
    Delivery,
    Site,
    StockAccount,
    StockMovement,
    User,
)


class LiteUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"})
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("email", "display_name", "role")

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get("password1")
        if password and password != cleaned.get("password2"):
            self.add_error("password2", "The passwords do not match.")
        if password:
            try:
                from django.contrib.auth.password_validation import validate_password

                validate_password(password, user=self.instance)
            except ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class LiteUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = "__all__"


@admin.register(User)
class LiteUserAdmin(BaseUserAdmin):
    form = LiteUserChangeForm
    add_form = LiteUserCreationForm
    ordering = ("email",)
    list_display = ("email", "display_name", "role", "is_active", "is_staff")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("email", "display_name")
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name", "role")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "display_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("code", "name")


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "region", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "region")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("site", "distributor", "campaign", "target_kg", "status")
    list_filter = ("status", "campaign")
    search_fields = ("site__code", "distributor__email", "distributor__display_name")


@admin.register(StockAccount)
class StockAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "owner", "site")
    list_filter = ("kind",)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "source", "destination", "quantity_kg")
    list_filter = ("kind",)
    readonly_fields = (
        "kind",
        "source",
        "destination",
        "quantity_kg",
        "note",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("submitted_at", "site", "distributor", "quantity_kg", "status")
    list_filter = ("status", "site")
    search_fields = ("site__code", "distributor__email", "distributor__display_name")
    readonly_fields = (
        "assignment",
        "site",
        "distributor",
        "quantity_kg",
        "notes",
        "photo",
        "status",
        "submitted_at",
        "reviewed_at",
        "reviewed_by",
        "review_note",
        "stock_movement",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("created_at", "action", "detail", "actor")
    list_filter = ("action",)
    readonly_fields = ("actor", "action", "detail", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
