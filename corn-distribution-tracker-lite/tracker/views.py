"""Server-rendered views for the Lite edition."""

from __future__ import annotations

import mimetypes
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .forms import (
    AllocationForm,
    AssignmentForm,
    CampaignForm,
    DeliveryForm,
    DistributorForm,
    LoginForm,
    ReceiptForm,
    ReviewForm,
    SiteForm,
)
from .models import (
    Activity,
    Assignment,
    Campaign,
    Delivery,
    Role,
    Site,
    StockAccount,
    StockMovement,
    User,
)
from .services import (
    approve_delivery,
    approved_kg,
    available_kg_for,
    central_account,
    distributor_account,
    distributor_held_kg,
    pending_kg_for,
    post_allocation,
    post_receipt,
    progress_percent,
    reject_delivery,
    site_account,
    site_held_kg,
    submit_delivery,
    target_kg,
)

LOGIN_THROTTLE_LIMIT = 5
LOGIN_THROTTLE_WINDOW = 300


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def distributor_required(view):
    @login_required
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if request.user.is_admin:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def _client_ip(request) -> str:
    if settings.USE_X_FORWARDED_FOR:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    form = LoginForm(request=request, data=request.POST or None)
    status = 200

    if request.method == "POST":
        throttle_key = f"lite-login:{_client_ip(request)}"
        attempts = int(cache.get(throttle_key, 0))
        if attempts >= LOGIN_THROTTLE_LIMIT:
            form.add_error(
                None,
                "Too many sign-in attempts. Wait a few minutes and try again.",
            )
            status = 429
        elif form.is_valid():
            auth_login(request, form.get_user())
            cache.delete(throttle_key)
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("dashboard")
        else:
            cache.set(throttle_key, attempts + 1, LOGIN_THROTTLE_WINDOW)
            status = 401

    return render(
        request,
        "tracker/login.html",
        {"form": form, "next": next_url},
        status=status,
    )


@require_POST
def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("login")


@login_required
def dashboard(request):
    if request.user.is_admin:
        return admin_dashboard(request)
    return distributor_dashboard(request)


def admin_dashboard(request):
    pending = Delivery.objects.filter(status=Delivery.Status.SUBMITTED).select_related(
        "site", "distributor", "assignment"
    )
    pending_count = pending.count()
    pending_total = sum((row.quantity_kg for row in pending), 0)
    approved = approved_kg()
    target = target_kg()
    distributors = User.objects.filter(role=Role.DISTRIBUTOR, is_active=True)
    distributor_rows = []
    for distributor in distributors:
        account = distributor_account(distributor)
        distributor_rows.append(
            {
                "user": distributor,
                "held": account.balance_kg,
                "pending": pending_kg_for(distributor),
                "approved": approved_kg(distributor=distributor),
                "assignments": Assignment.objects.filter(
                    distributor=distributor,
                    status=Assignment.Status.ACTIVE,
                    campaign__status=Campaign.Status.ACTIVE,
                ).count(),
            }
        )

    return render(
        request,
        "tracker/admin_dashboard.html",
        {
            "active_nav": "dashboard",
            "central": central_account().balance_kg,
            "distributor_held": distributor_held_kg(),
            "site_held": site_held_kg(),
            "pending_count": pending_count,
            "pending_total": pending_total,
            "approved": approved,
            "target": target,
            "progress": progress_percent(approved, target),
            "remaining": max(target - approved, 0),
            "distributor_rows": distributor_rows,
            "pending_deliveries": pending.order_by("submitted_at")[:6],
            "recent_deliveries": Delivery.objects.select_related("site", "distributor").order_by(
                "-submitted_at"
            )[:6],
            "activities": Activity.objects.select_related("actor")[:6],
        },
    )


def distributor_dashboard(request):
    user = request.user
    available = available_kg_for(user)
    pending = pending_kg_for(user)
    approved = approved_kg(distributor=user)
    target = target_kg(distributor=user)
    assignments = (
        Assignment.objects.filter(
            distributor=user,
            status=Assignment.Status.ACTIVE,
            campaign__status=Campaign.Status.ACTIVE,
        )
        .select_related("site", "campaign")
        .order_by("site__code")
    )
    return render(
        request,
        "tracker/distributor_dashboard.html",
        {
            "active_nav": "dashboard",
            "available": available,
            "held": distributor_account(user).balance_kg,
            "pending": pending,
            "approved": approved,
            "target": target,
            "progress": progress_percent(approved, target),
            "remaining": max(target - approved, 0),
            "assignments": assignments,
            "recent_deliveries": Delivery.objects.filter(distributor=user)
            .select_related("site")
            .order_by("-submitted_at")[:6],
        },
    )


@admin_required
def campaigns(request):
    return render(
        request,
        "tracker/campaigns.html",
        {
            "active_nav": "campaigns",
            "campaigns": Campaign.objects.all().order_by("-created_at"),
        },
    )


@admin_required
def campaign_create(request):
    form = CampaignForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        campaign = form.save()
        messages.success(request, f"Campaign {campaign.code} created.")
        return redirect("campaigns")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "campaigns",
            "title": "New campaign",
            "subtitle": "Group sites and targets under a distribution round.",
            "form": form,
            "submit_label": "Create campaign",
            "cancel_url": reverse("campaigns"),
        },
    )


@admin_required
@require_POST
def campaign_toggle(request, pk: int):
    campaign = get_object_or_404(Campaign, pk=pk)
    campaign.status = (
        Campaign.Status.CLOSED
        if campaign.status == Campaign.Status.ACTIVE
        else Campaign.Status.ACTIVE
    )
    campaign.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{campaign.code} is now {campaign.get_status_display().lower()}.")
    return redirect("campaigns")


@admin_required
def sites(request):
    return render(
        request,
        "tracker/sites.html",
        {
            "active_nav": "sites",
            "sites": Site.objects.all().order_by("code"),
        },
    )


@admin_required
def site_create(request):
    form = SiteForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        site = form.save()
        site_account(site)
        messages.success(request, f"Site {site.code} created.")
        return redirect("sites")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "sites",
            "title": "New site",
            "subtitle": "Add a distribution point that can receive approved deliveries.",
            "form": form,
            "submit_label": "Create site",
            "cancel_url": reverse("sites"),
        },
    )


@admin_required
@require_POST
def site_toggle(request, pk: int):
    site = get_object_or_404(Site, pk=pk)
    site.is_active = not site.is_active
    site.save(update_fields=["is_active", "updated_at"])
    messages.success(request, f"{site.code} is now {'active' if site.is_active else 'inactive'}.")
    return redirect("sites")


@admin_required
def people(request):
    distributors = User.objects.filter(role=Role.DISTRIBUTOR).order_by("display_name", "email")
    rows = []
    for distributor in distributors:
        rows.append(
            {
                "user": distributor,
                "held": distributor_account(distributor).balance_kg,
                "pending": pending_kg_for(distributor),
                "assignments": Assignment.objects.filter(
                    distributor=distributor,
                    status=Assignment.Status.ACTIVE,
                    campaign__status=Campaign.Status.ACTIVE,
                ).count(),
            }
        )
    return render(
        request,
        "tracker/people.html",
        {"active_nav": "people", "distributors": rows},
    )


@admin_required
def distributor_create(request):
    form = DistributorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        distributor = form.save()
        distributor_account(distributor)
        messages.success(request, f"Distributor {distributor.email} created.")
        return redirect("people")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "people",
            "title": "New distributor",
            "subtitle": "Create an account and share the initial password securely.",
            "form": form,
            "submit_label": "Create distributor",
            "cancel_url": reverse("people"),
        },
    )


@admin_required
def assignments(request):
    rows = Assignment.objects.select_related("campaign", "site", "distributor").order_by(
        "-created_at"
    )
    return render(
        request,
        "tracker/assignments.html",
        {"active_nav": "assignments", "assignments": rows},
    )


@admin_required
def assignment_create(request):
    form = AssignmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        assignment = form.save()
        messages.success(
            request,
            f"{assignment.distributor.short_name} assigned to {assignment.site.code}.",
        )
        return redirect("assignments")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "assignments",
            "title": "New assignment",
            "subtitle": "Set who delivers to which site, and the target in kilograms.",
            "form": form,
            "submit_label": "Create assignment",
            "cancel_url": reverse("assignments"),
        },
    )


@admin_required
@require_POST
def assignment_toggle(request, pk: int):
    assignment = get_object_or_404(Assignment, pk=pk)
    assignment.status = (
        Assignment.Status.COMPLETE
        if assignment.status == Assignment.Status.ACTIVE
        else Assignment.Status.ACTIVE
    )
    assignment.save(update_fields=["status", "updated_at"])
    messages.success(request, f"Assignment is now {assignment.get_status_display().lower()}.")
    return redirect("assignments")


@admin_required
def inventory(request):
    distributor_accounts = StockAccount.objects.filter(
        kind=StockAccount.Kind.DISTRIBUTOR
    ).select_related("owner")
    site_accounts = StockAccount.objects.filter(kind=StockAccount.Kind.SITE).select_related("site")
    return render(
        request,
        "tracker/inventory.html",
        {
            "active_nav": "inventory",
            "central": central_account().balance_kg,
            "distributor_accounts": distributor_accounts,
            "site_accounts": site_accounts,
            "movements": StockMovement.objects.select_related(
                "source",
                "source__owner",
                "destination",
                "destination__owner",
                "destination__site",
                "created_by",
            )[:100],
        },
    )


@admin_required
def receipt_create(request):
    form = ReceiptForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        post_receipt(
            quantity_kg=form.cleaned_data["quantity_kg"],
            actor=request.user,
            note=form.cleaned_data.get("note", ""),
        )
        messages.success(request, "Central stock receipt posted.")
        return redirect("inventory")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "inventory",
            "title": "Record stock receipt",
            "subtitle": "Add stock to the central account. This posts an immutable ledger row.",
            "form": form,
            "submit_label": "Post receipt",
            "cancel_url": reverse("inventory"),
        },
    )


@admin_required
def allocation_create(request):
    form = AllocationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            post_allocation(
                distributor=form.cleaned_data["distributor"],
                quantity_kg=form.cleaned_data["quantity_kg"],
                actor=request.user,
                note=form.cleaned_data.get("note", ""),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Distributor stock allocated.")
            return redirect("inventory")
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "inventory",
            "title": "Allocate stock",
            "subtitle": "Move stock from central storage to a distributor.",
            "form": form,
            "submit_label": "Post allocation",
            "cancel_url": reverse("inventory"),
        },
    )


@login_required
def deliveries(request):
    status = request.GET.get("status", "")
    allowed = {Delivery.Status.SUBMITTED, Delivery.Status.APPROVED, Delivery.Status.REJECTED}
    if status not in allowed:
        status = ""
    base = Delivery.objects.all()
    if not request.user.is_admin:
        base = base.filter(distributor=request.user)
    counts = {
        "all": base.count(),
        Delivery.Status.SUBMITTED: base.filter(status=Delivery.Status.SUBMITTED).count(),
        Delivery.Status.APPROVED: base.filter(status=Delivery.Status.APPROVED).count(),
        Delivery.Status.REJECTED: base.filter(status=Delivery.Status.REJECTED).count(),
    }
    rows = base.select_related("site", "distributor", "assignment")
    if status:
        rows = rows.filter(status=status)
    return render(
        request,
        "tracker/deliveries.html",
        {
            "active_nav": "deliveries",
            "deliveries": rows.order_by("-submitted_at"),
            "status": status,
            "counts": counts,
            "is_admin": request.user.is_admin,
        },
    )


@distributor_required
def delivery_create(request):
    initial = {}
    assignment_id = request.GET.get("assignment")
    if assignment_id:
        initial["assignment"] = Assignment.objects.filter(
            pk=assignment_id, distributor=request.user
        ).first()
    form = DeliveryForm(
        request.POST or None, request.FILES or None, user=request.user, initial=initial
    )
    if request.method == "POST" and form.is_valid():
        try:
            delivery = submit_delivery(
                assignment=form.cleaned_data["assignment"],
                distributor=request.user,
                quantity_kg=form.cleaned_data["quantity_kg"],
                notes=form.cleaned_data.get("notes", ""),
                photo=form.cleaned_data.get("photo"),
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Delivery submitted for review.")
            return redirect("delivery_detail", pk=delivery.pk)
    return render(
        request,
        "tracker/form_page.html",
        {
            "active_nav": "delivery_new",
            "title": "New delivery update",
            "subtitle": "Record what you delivered to an assigned site.",
            "form": form,
            "submit_label": "Submit for review",
            "cancel_url": reverse("deliveries"),
            "form_help": [
                "Submitted quantities are reserved but are not posted to site stock yet.",
                "An administrator reviews the evidence and approves or rejects the record.",
                "If the photo is skipped, the reviewer still sees an honest 'no photo' state.",
            ],
        },
    )


@login_required
def delivery_detail(request, pk: int):
    row = get_object_or_404(
        Delivery.objects.select_related(
            "site", "distributor", "assignment", "assignment__campaign", "reviewed_by"
        ),
        pk=pk,
    )
    if not request.user.is_admin and row.distributor_id != request.user.id:
        raise Http404
    return render(
        request,
        "tracker/delivery_detail.html",
        {
            "active_nav": "deliveries",
            "delivery": row,
            "review_form": ReviewForm()
            if request.user.is_admin and row.status == Delivery.Status.SUBMITTED
            else None,
        },
    )


@admin_required
@require_POST
def delivery_review(request, pk: int):
    row = get_object_or_404(Delivery, pk=pk)
    form = ReviewForm(request.POST)
    if not form.is_valid():
        return render(
            request,
            "tracker/delivery_detail.html",
            {
                "active_nav": "deliveries",
                "delivery": row,
                "review_form": form,
            },
            status=400,
        )
    try:
        if form.cleaned_data["decision"] == ReviewForm.APPROVE:
            approve_delivery(
                delivery=row,
                reviewer=request.user,
                note=form.cleaned_data.get("note", "").strip(),
            )
            messages.success(request, "Delivery approved and stock posted.")
        else:
            reject_delivery(
                delivery=row,
                reviewer=request.user,
                note=form.cleaned_data["note"].strip(),
            )
            messages.success(request, "Delivery rejected; the reserved quantity was released.")
    except ValidationError as exc:
        messages.error(
            request, exc.messages[0] if exc.messages else "Review could not be completed."
        )
    return redirect("delivery_detail", pk=row.pk)


@login_required
def delivery_photo(request, pk: int):
    row = get_object_or_404(Delivery, pk=pk)
    if not request.user.is_admin and row.distributor_id != request.user.id:
        raise Http404
    if not row.photo:
        raise Http404
    content_type, _ = mimetypes.guess_type(row.photo.name.lower())
    if not content_type or not content_type.startswith("image/"):
        raise Http404
    suffix = "." + row.photo.name.rsplit(".", 1)[-1].lower()
    response = FileResponse(
        row.photo.open("rb"),
        content_type=content_type,
        as_attachment=False,
        filename=f"delivery-{row.pk}{suffix}",
    )
    response["Cache-Control"] = "private, no-store"
    return response


@admin_required
def activity(request):
    return render(
        request,
        "tracker/activity.html",
        {"active_nav": "activity", "activities": Activity.objects.select_related("actor")[:200]},
    )
