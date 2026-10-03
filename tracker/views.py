from django.conf import settings
from django.db import transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.utils import timezone

from .forms import (
    IncidentContactForm,
    AffectedPersonForm,
    IncidentDetailsForm,
    CaliforniaDetailsForm,
    SchoolIncidentForm,
    FormalSchoolComplaintForm,
    DemographicsImpactForm,
    FinalQuestionsForm,
    ReferralForm,
    AttachmentForm,
)

from .models import (
    AffectedPerson,
    IncidentReport,
)


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------

def location_includes_school(incident_form):
    """
    Assumes that the school location ReportOption uses slug='school'.
    """

    if not incident_form.is_valid():
        return False

    location_types = incident_form.cleaned_data.get(
        "location_types"
    )

    if not location_types:
        return False

    return location_types.filter(
        slug="school"
    ).exists()


def should_show_school_form(
    state,
    incident_form,
    california_form=None,
):
    school_location = location_includes_school(
        incident_form
    )

    california_k12 = False

    if (
        state == "CA"
        and california_form
        and california_form.is_valid()
    ):
        california_k12 = bool(
            california_form.cleaned_data.get(
                "is_k12_incident"
            )
        )

    return school_location or california_k12


# ---------------------------------------------------------------------
# CREATE REPORT
# ---------------------------------------------------------------------

def incident_report_create(request):

    error_sections = []

    if request.method == "POST":

        # ---------------------------------------------------------
        # BASE FORMS
        # ---------------------------------------------------------

        contact_form = IncidentContactForm(
            request.POST,
            prefix="contact",
        )

        # Validate contact first: the state answer decides which
        # later questions are required.
        contact_valid = contact_form.is_valid()

        state = (
            contact_form.cleaned_data.get("state")
            if contact_valid
            else None
        )

        incident_form = IncidentDetailsForm(
            request.POST,
            prefix="incident",
            state=state,
        )

        demographics_form = DemographicsImpactForm(
            request.POST,
            prefix="demographics",
        )

        attachment_form = AttachmentForm(
            request.POST,
            request.FILES,
            prefix="attachments",
        )

        # Validate these once so we can safely inspect cleaned_data.
        incident_valid = incident_form.is_valid()
        demographics_valid = demographics_form.is_valid()
        attachment_valid = attachment_form.is_valid()

        # Path signals for conditional requirements. The raw
        # authorization answer is only a gating hint; the formal
        # form itself validates it properly.
        school_location = (
            incident_valid
            and location_includes_school(incident_form)
        )

        # Bound after the school signal: the connection question
        # renders in the school section and is required only there.
        final_form = FinalQuestionsForm(
            request.POST,
            prefix="final",
            school_location=school_location,
        )

        final_valid = final_form.is_valid()

        authorize = (
            request.POST.get("formal-authorize_autopopulation")
            == "True"
        )

        # ---------------------------------------------------------
        # CALIFORNIA FORM
        # ---------------------------------------------------------

        california_form = None
        california_valid = True

        if state == "CA":
            california_form = CaliforniaDetailsForm(
                request.POST,
                prefix="california",
                school_location=school_location,
            )

            california_valid = california_form.is_valid()

        is_ca_k12 = False

        if (
            state == "CA"
            and california_form
            and california_valid
        ):
            is_ca_k12 = bool(
                california_form.cleaned_data.get(
                    "is_k12_incident"
                )
            )

        # ---------------------------------------------------------
        # SCHOOL FORM
        # ---------------------------------------------------------

        school_form = None
        school_valid = True

        show_school = False

        if incident_valid:
            show_school = should_show_school_form(
                state,
                incident_form,
                california_form,
            )

        if show_school:
            school_form = SchoolIncidentForm(
                request.POST,
                prefix="school",
                school_location=school_location,
                ca_k12=is_ca_k12,
                authorize=authorize,
            )

            school_valid = school_form.is_valid()

        # ---------------------------------------------------------
        # FORMAL CA SCHOOL COMPLAINT
        # ---------------------------------------------------------

        formal_complaint_form = None
        formal_valid = True

        if is_ca_k12:
            formal_complaint_form = FormalSchoolComplaintForm(
                request.POST,
                prefix="formal",
            )

            formal_valid = (
                formal_complaint_form.is_valid()
            )

        # ---------------------------------------------------------
        # REFERRALS
        # ---------------------------------------------------------

        # Every state gets the organization consent block: CA offers
        # K-12 Legal Defense and CAIR, other states Palestine Legal;
        # save() writes only the organizations for the report's state.
        referral_form = ReferralForm(
            request.POST,
            prefix="referral",
        )

        referral_valid = referral_form.is_valid()

        # ---------------------------------------------------------
        # CHECK EVERYTHING
        # ---------------------------------------------------------

        all_valid = all([
            contact_valid,
            incident_valid,
            demographics_valid,
            final_valid,
            attachment_valid,
            california_valid,
            school_valid,
            formal_valid,
            referral_valid,
        ])

        # ---------------------------------------------------------
        # SAVE
        # ---------------------------------------------------------

        if all_valid:

            with transaction.atomic():

                # -------------------------------------------------
                # INCIDENT REPORT
                # -------------------------------------------------

                report = contact_form.save(
                    commit=False
                )

                incident_fields = [
                    "date_precision",
                    "incident_date",
                    "incident_month",
                    "incident_year",
                    "incident_date_estimate",
                    "description",
                    "city",
                    "zip_code",
                    "anti_palestinian_racism",
                    "anti_palestinian_racism_reason",
                    "knows_of_other_apr_incidents",
                    "similar_incidents",
                    "previously_reported",
                    "resolution_steps",
                ]

                for field in incident_fields:
                    setattr(
                        report,
                        field,
                        incident_form.cleaned_data.get(
                            field
                        ),
                    )

                final_fields = [
                    "connection_change",
                    "other_identity_information",
                    "additional_information",
                    "support_sought_elsewhere",
                    "opt_out_of_followup",
                    "signature_name",
                    "signature_date",
                ]

                for field in final_fields:
                    setattr(
                        report,
                        field,
                        final_form.cleaned_data.get(
                            field
                        ),
                    )

                report.status = (
                    IncidentReport.Status.SUBMITTED
                )

                report.submitted_at = timezone.now()

                report.full_clean()
                report.save()

                # -------------------------------------------------
                # INCIDENT MULTI-SELECT OPTIONS
                # -------------------------------------------------

                incident_form.save_options(
                    report
                )

                # -------------------------------------------------
                # AFFECTED PERSON
                # -------------------------------------------------
                # The form no longer asks who was affected directly.
                # A CA parent names their child, and the doc says the
                # identity/demographics questions then describe the
                # child — so the child is the affected person. In
                # every other case the reporter is.

                reporter_role = ""
                child_name = ""

                if california_form:
                    reporter_role = (
                        california_form.cleaned_data.get(
                            "reporter_role"
                        )
                    )

                    child_name = (
                        california_form.cleaned_data.get(
                            "child_full_name",
                            "",
                        ).strip()
                    )

                if reporter_role == "parent" and child_name:
                    child_first, _, child_last = (
                        child_name.rpartition(" ")
                    )

                    if not child_first:
                        child_first, child_last = child_last, ""

                    affected_person = AffectedPerson(
                        report=report,
                        is_reporter=False,
                        first_name=child_first,
                        last_name=child_last,
                    )

                else:
                    affected_person = AffectedPerson(
                        report=report,
                        is_reporter=True,
                        first_name=report.first_name,
                        last_name=report.last_name,
                    )

                affected_person.full_clean()
                affected_person.save()

                # -------------------------------------------------
                # DEMOGRAPHICS
                # -------------------------------------------------

                demographics = (
                    demographics_form.save(
                        commit=False
                    )
                )

                demographics.affected_person = (
                    affected_person
                )

                demographics.full_clean()
                demographics.save()

                demographics_form.save_options(
                    report
                )

                # -------------------------------------------------
                # CALIFORNIA DETAILS
                # -------------------------------------------------

                if california_form:
                    california = (
                        california_form.save(
                            commit=False
                        )
                    )

                    california.report = report

                    california.full_clean()
                    california.save()

                # -------------------------------------------------
                # SCHOOL INCIDENT
                # -------------------------------------------------

                if school_form:
                    school = school_form.save(
                        commit=False
                    )

                    school.report = report

                    school.full_clean()
                    school.save()

                    school_form.save_options(
                        report
                    )

                # -------------------------------------------------
                # FORMAL COMPLAINT
                # -------------------------------------------------

                if formal_complaint_form:
                    formal_complaint = (
                        formal_complaint_form.save(
                            commit=False
                        )
                    )

                    formal_complaint.report = report

                    formal_complaint.full_clean()
                    formal_complaint.save()

                # -------------------------------------------------
                # REFERRALS
                # -------------------------------------------------

                if referral_form:
                    referral_form.save(
                        report
                    )

                # -------------------------------------------------
                # ATTACHMENTS
                # -------------------------------------------------

                attachment_form.save(
                    report
                )

            # Offer the UCP hand-off only to reporters who said yes
            # to autopopulating a formal complaint; everyone else
            # (including an explicit "No") goes to the success page.
            # The /ucp/ endpoint itself stays CA-K-12 gated, so a
            # saved link still works if they change their mind.
            authorized = bool(
                formal_complaint_form
                and formal_complaint_form.cleaned_data.get(
                    "authorize_autopopulation"
                )
            )

            # The hand-off pages show the report's own data, so
            # access is bound to the submitting browser session; the
            # uuid alone is not an access credential (codex round 5
            # #1). The grant expires on its own, and the session key
            # is rotated so a pre-submission session id cannot carry
            # it (codex system audit).
            _grant_ucp_access(request, report)

            return redirect(
                "ucp_offer"
                if ucp_eligible(report) and authorized
                else "incident_report_success",
                uuid=report.uuid,
            )

        # ---------------------------------------------------------
        # ERROR SUMMARY
        # ---------------------------------------------------------
        # Collected BEFORE the fallback binding below: a fallback
        # form exists only so the re-render survives, and its
        # "errors" are for sections that never applied to this path.

        for form, section in [
            (contact_form, "Consent and contact information"),
            (referral_form, "Where should we report this incident"),
            (incident_form, "Incident details"),
            (california_form, "California K-12"),
            (school_form, "School information"),
            (formal_complaint_form, "California K-12 complaint"),
            (demographics_form, "Experiences, impacts and identity"),
            (final_form, "Signature and final questions"),
            (attachment_form, "Supporting materials"),
        ]:
            if form is not None and form.is_bound and form.errors:
                error_sections.append(section)

        # The connection question renders inside School information
        # even though it lives on the final form.
        if (
            final_form.is_bound
            and "connection_change" in final_form.errors
        ):
            if "School information" not in error_sections:
                error_sections.append("School information")
            if (
                list(final_form.errors) == ["connection_change"]
                and "Signature and final questions" in error_sections
            ):
                error_sections.remove(
                    "Signature and final questions"
                )

        # ---------------------------------------------------------
        # INVALID: GUARD THE RE-RENDER
        # ---------------------------------------------------------
        # Conditional forms stay None when their gate (state,
        # K-12 answer, ...) could not be evaluated, but the template
        # renders them unconditionally. Bind them to the POST so the
        # error page renders and the reporter's entries survive.

        if california_form is None:
            california_form = CaliforniaDetailsForm(
                request.POST,
                prefix="california",
            )

        if school_form is None:
            school_form = SchoolIncidentForm(
                request.POST,
                prefix="school",
            )

        if formal_complaint_form is None:
            formal_complaint_form = (
                FormalSchoolComplaintForm(
                    request.POST,
                    prefix="formal",
                )
            )

        if referral_form is None:
            referral_form = ReferralForm(
                request.POST,
                prefix="referral",
            )

    else:

        # ---------------------------------------------------------
        # GET
        # ---------------------------------------------------------

        contact_form = IncidentContactForm(
            prefix="contact",
        )

        incident_form = IncidentDetailsForm(
            prefix="incident",
        )

        california_form = CaliforniaDetailsForm(
            prefix="california",
        )

        school_form = SchoolIncidentForm(
            prefix="school",
        )

        formal_complaint_form = (
            FormalSchoolComplaintForm(
                prefix="formal",
            )
        )

        demographics_form = DemographicsImpactForm(
            prefix="demographics",
        )

        final_form = FinalQuestionsForm(
            prefix="final",
        )

        referral_form = ReferralForm(
            prefix="referral",
        )

        attachment_form = AttachmentForm(
            prefix="attachments",
        )

    # -------------------------------------------------------------
    # CONTEXT
    # -------------------------------------------------------------

    context = {
        "contact_form": contact_form,
        "incident_form": incident_form,
        "california_form": california_form,
        "school_form": school_form,
        "formal_complaint_form": formal_complaint_form,
        "demographics_form": demographics_form,
        "final_form": final_form,
        "referral_form": referral_form,
        "attachment_form": attachment_form,
        "data_retention_doc_url": settings.DATA_RETENTION_DOC_URL,
        "error_sections": error_sections,
    }

    return render(
        request,
        "tracker/incident_report_form.html",
        context,
    )


# ---------------------------------------------------------------------
# SUCCESS
# ---------------------------------------------------------------------

def incident_report_success(
    request,
    uuid,
):

    report = get_object_or_404(
        IncidentReport,
        uuid=uuid,
        status=IncidentReport.Status.SUBMITTED,
    )

    return render(
        request,
        "tracker/incident_report_success.html",
        {
            "report": report,
        },
    )

# ---------------------------------------------------------------------
# UCP HAND-OFF
# ---------------------------------------------------------------------

import logging
import time

from django.http import Http404, HttpResponse

from . import ucp
from .models import UCPFiling

logger = logging.getLogger(__name__)


# The hand-off grant outlives neither the browser session nor this
# window; after that the reporter resubmits or contacts support.
UCP_GRANT_SECONDS = 48 * 3600


def _grant_ucp_access(request, report):
    grants = request.session.get("ucp_reports")

    if not isinstance(grants, dict):
        grants = {}

    grants[str(report.uuid)] = int(time.time()) + UCP_GRANT_SECONDS

    # Keep only the newest grants so the session stays small.
    while len(grants) > 10:
        del grants[min(grants, key=grants.get)]

    request.session["ucp_reports"] = grants
    request.session.cycle_key()


def _has_ucp_access(request, report):
    grants = request.session.get("ucp_reports")

    if isinstance(grants, dict):
        expires = grants.get(str(report.uuid))
        return bool(expires) and time.time() < expires

    if isinstance(grants, list):
        # Session written before grants carried an expiry.
        return str(report.uuid) in grants

    return False


def _submitted_report(uuid):
    return get_object_or_404(
        IncidentReport,
        uuid=uuid,
        status=IncidentReport.Status.SUBMITTED,
    )


def ucp_eligible(report):
    """
    UCP complaints only exist for California K-12 school incidents;
    other reports go straight to the success page.
    """

    california = getattr(report, "california_details", None)

    return bool(
        report.state == "CA"
        and california
        and california.is_k12_incident
    )


def ucp_offer(request, uuid):
    """
    Post-submit page: offer to prepare the reporter's district UCP
    form. Three stages on one URL:

      GET  (no cds)   confirm the district (matched from the report)
      GET  ?cds=...   review carried-over answers + follow-up questions
      POST ?cds=...   generate the filled PDF
    """

    report = _submitted_report(uuid)

    if not _has_ucp_access(request, report):
        raise Http404("Not available")

    if not ucp_eligible(report):
        return redirect(
            "incident_report_success",
            uuid=report.uuid,
        )

    cds = (
        request.POST.get("cds")
        or request.GET.get("cds")
    )

    # -----------------------------------------------------------------
    # STAGE 3: GENERATE
    # -----------------------------------------------------------------

    if request.method == "POST" and cds:

        try:
            spec = ucp.get_spec(cds)
            plan = ucp.build_plan(report, spec, cds=cds)

        except ucp.PortalError:
            logger.exception("UCP portal unavailable")
            return render(
                request,
                "tracker/ucp_offer.html",
                {
                    "report": report,
                    "portal_down": True,
                },
            )

        answers = plan["answers"]

        # Follow-up answers and checkbox review from the page win
        # over anything we derived.
        for field in plan["followups"]:
            value = request.POST.get(field["key"], "").strip()

            if value:
                answers[field["key"]] = value

        for field in plan["checkbox_fields"]:
            if request.POST.get(field["key"]):
                answers[field["key"]] = "1"
            else:
                answers.pop(field["key"], None)

        try:
            pdf = ucp.generate_pdf(cds, answers)

        except ucp.PortalError:
            logger.exception("UCP portal generate failed")
            return render(
                request,
                "tracker/ucp_offer.html",
                {
                    "report": report,
                    "portal_down": True,
                },
            )

        UCPFiling.objects.create(
            report=report,
            district_cds=cds,
            district_name=spec.get("name", ""),
            tier=spec.get("tier", ""),
        )

        safe_name = "".join(
            c for c in spec.get("name", "district")
            if c.isalnum() or c in " -"
        )

        response = HttpResponse(
            pdf,
            content_type="application/pdf",
        )

        response["Content-Disposition"] = (
            f'attachment; filename="UCP Complaint - {safe_name}.pdf"'
        )

        return response

    # -----------------------------------------------------------------
    # STAGE 2: REVIEW + FOLLOW-UPS
    # -----------------------------------------------------------------

    if cds:

        try:
            spec = ucp.get_spec(cds)
            plan = ucp.build_plan(report, spec, cds=cds)

        except ucp.PortalError:
            logger.exception("UCP portal unavailable")
            return render(
                request,
                "tracker/ucp_offer.html",
                {
                    "report": report,
                    "portal_down": True,
                },
            )

        return render(
            request,
            "tracker/ucp_followup.html",
            {
                "report": report,
                "spec": spec,
                "cds": cds,
                "prefilled": plan["prefilled"],
                "followups": plan["followups"],
                "checkbox_fields": plan["checkbox_fields"],
            },
        )

    # -----------------------------------------------------------------
    # STAGE 1: DISTRICT CONFIRMATION
    # -----------------------------------------------------------------

    school = getattr(report, "school_incident", None)

    district_query = (
        request.GET.get("district_query")
        or (school.school_district if school else "")
        or (school.school_name if school else "")
    )

    matches = []
    portal_down = False

    if district_query:
        try:
            matches = ucp.match_districts(district_query)

        except ucp.PortalError:
            logger.exception("UCP portal unavailable")
            portal_down = True

    return render(
        request,
        "tracker/ucp_offer.html",
        {
            "report": report,
            "district_query": district_query,
            "matches": matches,
            "portal_down": portal_down,
        },
    )
