"""
Two admin surfaces (data-separation pilot — see DATA_ACCESS.md):

- "Data coordinators" see DeidentifiedReport: every report, but no
  direct identifiers for ANY report. The detail page is built from
  an explicit whitelist plus composed summaries, so a PII field can
  never leak through list_display, search, filters, or inlines.
- "Follow-up staff" see the full IncidentReport record, but ONLY for
  reports whose reporter consented to follow-up; opening a record
  writes a PIIAccessLog row.

The opt-out predicate and the direct-identifier list live in
tracker.models (deidentified_q, DIRECT_IDENTIFIER_FIELDS).
"""

from django.contrib import admin

from .models import (
    AffectedPerson,
    CaliforniaDetails,
    DeidentifiedReport,
    DIRECT_IDENTIFIER_FIELDS,
    FormalSchoolComplaint,
    IncidentReport,
    PIIAccessLog,
    ReportAttachment,
    ReportOptionSelection,
    ReportReferral,
    SchoolIncident,
    UCPFiling,
    deidentified_q,
)


# ---------------------------------------------------------------------
# COORDINATOR SURFACE (de-identified)
# ---------------------------------------------------------------------

# Whitelisted IncidentReport fields for the coordinator surface.
NON_PII_REPORT_FIELDS = [
    "uuid",
    "status",
    "submitted_at",
    "state",
    "city",
    "zip_code",
    "date_precision",
    "incident_date",
    "incident_month",
    "incident_year",
    "description",
    "anti_palestinian_racism",
    "anti_palestinian_racism_reason",
    "knows_of_other_apr_incidents",
    "similar_incidents",
    "previously_reported",
    "resolution_steps",
    "connection_change",
    "other_identity_information",
    "additional_information",
    "support_sought_elsewhere",
    "has_consented",
    "opt_out_of_followup",
]

# Import-time self-check: the whitelist and the direct-identifier
# list must never intersect.
assert not (
    set(NON_PII_REPORT_FIELDS)
    & set(DIRECT_IDENTIFIER_FIELDS["IncidentReport"])
), "PII field leaked into the coordinator whitelist"


@admin.register(DeidentifiedReport)
class DeidentifiedReportAdmin(admin.ModelAdmin):
    list_display = [
        "uuid",
        "status",
        "state",
        "city",
        "submitted_at",
        "deidentified",
    ]
    list_filter = ["status", "state", "anti_palestinian_racism"]
    search_fields = ["uuid", "city", "zip_code", "description"]
    ordering = ["-submitted_at"]

    readonly_fields = NON_PII_REPORT_FIELDS + [
        "deidentified",
        "school_summary",
        "california_summary",
        "formal_summary",
        "demographics_summary",
        "selections_summary",
        "referrals_summary",
        "ucp_filings_summary",
    ]

    fieldsets = [
        (None, {"fields": NON_PII_REPORT_FIELDS + ["deidentified"]}),
        ("School (quasi-identifiers — next-phase generalization)", {
            "fields": ["school_summary"],
        }),
        ("California details", {"fields": ["california_summary"]}),
        ("Formal complaint (non-identifying flags)", {
            "fields": ["formal_summary"],
        }),
        ("Demographics", {"fields": ["demographics_summary"]}),
        ("Selected options", {"fields": ["selections_summary"]}),
        ("Consent and routing", {
            "fields": ["referrals_summary", "ucp_filings_summary"],
        }),
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="De-identified")
    def deidentified(self, obj):
        return obj.is_deidentified

    def school_summary(self, obj):
        school = getattr(obj, "school_incident", None)

        if not school:
            return "—"

        return (
            f"School: {school.school_name or '—'} | "
            f"District: {school.school_district or '—'} | "
            f"Grade: {school.grade or '—'} | "
            f"Type: {school.get_school_type_display() or '—'} | "
            f"School aware: {school.school_was_aware or '—'} | "
            f"Satisfied: {school.satisfied_with_response or '—'} | "
            f"Effect: {school.school_response_effect or '—'} | "
            f"Absence: {school.absence_due_to_racism_frequency or '—'} | "
            f"Ed. requirement: "
            f"{school.educational_requirement_violated or '—'}"
        )

    def california_summary(self, obj):
        california = getattr(obj, "california_details", None)

        if not california:
            return "—"

        return (
            f"K-12: {california.is_k12_incident} | "
            f"Role: {california.reporter_role or '—'} | "
            f"Age: {california.age or '—'}"
        )

    def formal_summary(self, obj):
        formal = getattr(obj, "formal_school_complaint", None)

        if not formal:
            return "—"

        return (
            f"Previously submitted to district: "
            f"{formal.previously_submitted_to_district} | "
            f"Authorized autopopulation: "
            f"{formal.authorize_autopopulation} | "
            f"Discussed with principal/supervisor: "
            f"{formal.discussed_with_principal_or_supervisor}"
        )

    def demographics_summary(self, obj):
        affected = getattr(obj, "affected_person", None)
        demographics = getattr(affected, "demographics", None) if affected else None

        if not demographics:
            return "—"

        return (
            f"Gender: {demographics.gender or '—'} | "
            f"Religion: {demographics.religion or '—'}"
        )

    def selections_summary(self, obj):
        lines = []

        for selection in obj.option_selections.select_related(
            "option"
        ).order_by("option__category", "option__sort_order"):
            line = (
                f"{selection.option.category}: "
                f"{selection.option.label}"
            )

            if selection.other_text:
                line += f" ({selection.other_text})"

            lines.append(line)

        return "\n".join(lines) or "—"

    def referrals_summary(self, obj):
        lines = []

        for referral in obj.referrals.select_related("organization"):
            lines.append(
                f"{referral.organization.slug}: "
                f"submit={referral.submit}, "
                f"anonymous={referral.anonymous}"
            )

        return "\n".join(lines) or "—"

    def ucp_filings_summary(self, obj):
        lines = []

        for filing in obj.ucp_filings.all():
            lines.append(
                f"{filing.district_name} ({filing.tier}) "
                f"on {filing.created_at:%Y-%m-%d}"
            )

        return "\n".join(lines) or "—"


# ---------------------------------------------------------------------
# FOLLOW-UP SURFACE (full record, consented reports only)
# ---------------------------------------------------------------------

class CaliforniaDetailsInline(admin.StackedInline):
    model = CaliforniaDetails
    extra = 0


class SchoolIncidentInline(admin.StackedInline):
    model = SchoolIncident
    extra = 0


class FormalSchoolComplaintInline(admin.StackedInline):
    model = FormalSchoolComplaint
    extra = 0


class AffectedPersonInline(admin.StackedInline):
    model = AffectedPerson
    extra = 0


class ReportReferralInline(admin.TabularInline):
    model = ReportReferral
    extra = 0


class ReportOptionSelectionInline(admin.TabularInline):
    model = ReportOptionSelection
    extra = 0


class ReportAttachmentInline(admin.TabularInline):
    model = ReportAttachment
    extra = 0


class UCPFilingInline(admin.TabularInline):
    model = UCPFiling
    extra = 0


@admin.register(IncidentReport)
class IncidentReportAdmin(admin.ModelAdmin):
    """Full record; excludes de-identified reports entirely."""

    list_display = [
        "uuid",
        "full_name",
        "email",
        "state",
        "status",
        "submitted_at",
    ]
    list_filter = ["status", "state"]
    search_fields = [
        "uuid", "first_name", "last_name", "email", "city",
    ]
    ordering = ["-submitted_at"]
    readonly_fields = ["uuid", "created_at", "updated_at"]

    inlines = [
        AffectedPersonInline,
        CaliforniaDetailsInline,
        SchoolIncidentInline,
        FormalSchoolComplaintInline,
        ReportOptionSelectionInline,
        ReportReferralInline,
        UCPFilingInline,
        ReportAttachmentInline,
    ]

    def get_queryset(self, request):
        # The reporter's opt-out removes the linked record from every
        # app surface, including this one.
        return (
            super()
            .get_queryset(request)
            .exclude(deidentified_q())
            .distinct()
        )

    def change_view(
        self, request, object_id, form_url="", extra_context=None
    ):
        report = IncidentReport.objects.filter(pk=object_id).first()

        if report:
            PIIAccessLog.objects.create(
                user=request.user,
                username=request.user.get_username(),
                report=report,
                report_uuid=str(report.uuid),
                surface="admin_full_detail",
            )

        return super().change_view(
            request, object_id, form_url, extra_context
        )


# ---------------------------------------------------------------------
# ACCESS LOG (superusers, read-only)
# ---------------------------------------------------------------------

@admin.register(PIIAccessLog)
class PIIAccessLogAdmin(admin.ModelAdmin):
    list_display = [
        "accessed_at", "username", "report_uuid", "surface",
    ]
    search_fields = ["username", "report_uuid"]
    readonly_fields = [
        "user", "username", "report", "report_uuid",
        "surface", "accessed_at",
    ]

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
