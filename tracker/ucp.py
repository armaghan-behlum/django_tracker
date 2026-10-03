"""
Hand-off to the UCP form portal.

After a report is submitted, we offer to prepare the reporter's
district Uniform Complaint Procedures (UCP) form. The portal service
holds one "spec" per California district: the list of blanks on that
district's own complaint form. This module:

1. talks to the portal's JSON API (district match, spec fetch,
   PDF generation), and
2. maps an ``IncidentReport`` and its satellite records onto the
   portal's canonical answer keys, so the reporter only has to answer
   whatever their district's form asks that the tracker did not.

The portal URL comes from ``settings.UCP_PORTAL_URL``. All calls are
server-to-server; no reporter data goes to the portal until the
reporter confirms they want the form.
"""

import http.client
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


class PortalError(Exception):
    """The UCP portal could not be reached or returned an error."""


# ---------------------------------------------------------------------
# PORTAL CLIENT
# ---------------------------------------------------------------------

def _portal_url(path, params=None):
    base = settings.UCP_PORTAL_URL.rstrip("/")
    url = f"{base}{path}"

    if params:
        url += "?" + urllib.parse.urlencode(params)

    return url


# Covers connection errors, timeouts, resets and truncation raised
# while OPENING or while READING the response body (URLError is an
# OSError subclass; IncompleteRead is an HTTPException), plus JSON
# decode errors.
_TRANSPORT_ERRORS = (OSError, http.client.HTTPException, ValueError)


def _get_json(path, params=None, timeout=15):
    try:
        with urllib.request.urlopen(
            _portal_url(path, params),
            timeout=timeout,
        ) as response:
            payload = json.load(response)

    except _TRANSPORT_ERRORS as exc:
        raise PortalError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise PortalError(
            f"portal returned an unexpected response for {path}"
        )

    return payload


def match_districts(query):
    """Return portal district matches for a free-text district name."""

    if not query or len(query.strip()) < 2:
        return []

    matches = _get_json(
        "/api/districts",
        {"q": query.strip()},
    ).get("matches")

    if not isinstance(matches, list):
        return []

    return [m for m in matches if isinstance(m, dict)]


def get_spec(cds):
    """Return the question plan for one district."""

    spec = _get_json(f"/api/spec/{cds}")

    fields = spec.get("fields")

    if not isinstance(fields, list):
        raise PortalError(f"portal spec for {cds} has no field list")

    spec["fields"] = [
        field for field in fields
        if isinstance(field, dict)
        and isinstance(field.get("key"), str)
        and field["key"]
    ]

    return spec


def get_school_info(cds, name):
    """
    Best-effort public school address lookup via the portal
    (GET /api/school). Returns {} on any failure — the hand-off
    simply asks the question instead.
    """

    if not (cds and name):
        return {}

    try:
        info = _get_json(
            "/api/school",
            {"cds": cds, "q": name},
        )
    except PortalError:
        return {}

    if not isinstance(info, dict) or not info.get("found"):
        return {}

    return info


def generate_pdf(cds, answers, timeout=60):
    """POST answers to the portal; return the filled PDF bytes."""

    data = urllib.parse.urlencode(
        answers,
        doseq=True,
    ).encode()

    request = urllib.request.Request(
        _portal_url(f"/generate/{cds}"),
        data=data,
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            pdf = response.read()

    except _TRANSPORT_ERRORS as exc:
        raise PortalError(str(exc)) from exc

    # An upstream proxy or the portal itself can answer 200 with an
    # HTML error page; never record that as a completed complaint.
    if not pdf.startswith(b"%PDF"):
        raise PortalError(
            f"portal returned a non-PDF response for {cds}"
        )

    return pdf


# ---------------------------------------------------------------------
# CROSSWALK: IncidentReport -> canonical portal answers
# ---------------------------------------------------------------------

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _fmt_date(value):
    return value.strftime("%m/%d/%Y") if value else ""


def _incident_date_text(report):
    precision = report.date_precision

    if precision == report.DatePrecision.EXACT:
        return _fmt_date(report.incident_date)

    if precision == report.DatePrecision.MONTH:
        if report.incident_month and report.incident_year:
            return (
                f"{MONTH_NAMES[report.incident_month]} "
                f"{report.incident_year}"
            )
        return ""

    if precision == report.DatePrecision.ONGOING:
        return "Ongoing"

    return "Date not known (best estimate)"


def _prior_contact_text(report, school):
    parts = []

    if report.resolution_steps:
        parts.append(report.resolution_steps)

    if school:
        if school.concerns_addressed_to:
            line = f"Concerns raised with {school.concerns_addressed_to}"
            if school.concerns_addressed_date:
                line += f" on {_fmt_date(school.concerns_addressed_date)}"
            parts.append(line + ".")

        if school.teacher_admin_response:
            parts.append(
                "School response: " + school.teacher_admin_response
            )

    return "\n".join(parts)


def known_answers(report):
    """
    Build {canonical_key: value} from the report and its satellites.

    Only keys with real values are returned; the follow-up page asks
    for whatever the district's spec needs beyond these.
    """

    california = getattr(report, "california_details", None)
    school = getattr(report, "school_incident", None)
    formal = getattr(report, "formal_school_complaint", None)
    affected = getattr(report, "affected_person", None)

    answers = {
        "complainant_name": report.full_name,
        "complainant_first_name": report.first_name,
        "complainant_last_name": report.last_name,
        "first_name": report.first_name,
        "last_name": report.last_name,
        "email": report.email,
        "phone": report.phone,
        "phone_work": report.phone,
        "phone_cell": report.phone,
        "city": report.city,
        "state": report.state,
        "zip": report.zip_code,
        "zip_code": report.zip_code,
        "incident_date": _incident_date_text(report),
        "description": report.description,
        "prior_contact": _prior_contact_text(report, school),
    }

    # Typed digital signature (legal opinion: a typed name counts;
    # pilot approved). 288/304 specs map the signing DATE as
    # date_signed (a few split it); none map a typed-name key yet —
    # "signature"/"complainant_signature" are emitted so district
    # specs can adopt them without a tracker change.
    if report.signature_name:
        answers["signature"] = report.signature_name
        answers["complainant_signature"] = report.signature_name

    if report.signature_date:
        answers["date_signed"] = _fmt_date(report.signature_date)
        answers["signed_day"] = str(report.signature_date.day)
        answers["sign_day"] = str(report.signature_date.day)
        answers["signed_month"] = report.signature_date.strftime("%B")
        answers["sign_month"] = report.signature_date.strftime("%B")
        answers["signed_year"] = str(report.signature_date.year)

    if formal:
        answers.update({
            "address": formal.complainant_address,
            "complainant_address": formal.complainant_address,
            "respondent": formal.complaint_against,
            "individuals_involved": formal.individuals_involved,
            "witnesses": formal.witnesses,
            "remedy": formal.requested_remedy,
        })

        if formal.concerns_addressed_date:
            answers["prior_contact_date"] = _fmt_date(
                formal.concerns_addressed_date
            )

    if california:
        if california.reporter_role:
            answers["relationship"] = (
                california.get_reporter_role_display()
            )

        if california.child_full_name:
            answers["student_name"] = california.child_full_name

        if california.student_date_of_birth:
            answers["student_dob"] = _fmt_date(
                california.student_date_of_birth
            )

    if affected and not affected.is_reporter:
        name = f"{affected.first_name} {affected.last_name}".strip()

        if name:
            answers.setdefault("student_name", name)

    # "You are filing this complaint on behalf of": the affected
    # person, or "Myself" when the reporter is the affected person.
    on_behalf = ""
    if affected:
        if affected.is_reporter:
            on_behalf = "Myself"
        else:
            on_behalf = (
                f"{affected.first_name} {affected.last_name}".strip()
            )
    if not on_behalf and california and california.child_full_name:
        on_behalf = california.child_full_name
    if on_behalf:
        # Every text-field spelling the district specs use.
        for key in (
            "on_behalf_of",
            "on_behalf_of_name",
            "filing_on_behalf_of",
            "behalf_of_name",
            "behalf_of",
        ):
            answers[key] = on_behalf

    if school:
        answers.update({
            "student_school": school.school_name,
            "school": school.school_name,
            "school_name": school.school_name,
            "school_district": school.school_district,
            "district": school.school_district,
            "student_grade": school.grade,
            "grade": school.grade,
            "principal": school.principal,
            "principal_name": school.principal,
            "incident_location": school.location_within_school,
            "discussion_result": school.teacher_admin_response,
        })

    # Discrimination basis as free text, from the selected options.
    # A selection's free-text detail ("Other: Anti-Black racism")
    # carries the reporter's actual claim, so it joins the label.
    basis_labels = [
        f"{label}: {other}" if other else label
        for label, other in report.option_selections.filter(
            option__category__in=[
                "racism_type",
                "targeted_identity",
            ],
        ).values_list("option__label", "other_text")
    ]

    # The direct questionnaire answer is stored on the report itself,
    # not as an option selection; without this an explicit "yes" would
    # vanish from the complaint.
    if report.anti_palestinian_racism == "yes" and not any(
        "palestin" in label.lower() for label in basis_labels
    ):
        basis_labels.insert(0, "Anti-Palestinian racism")

    if basis_labels:
        answers["discrimination_basis"] = ", ".join(basis_labels)

    return {
        key: value
        for key, value in answers.items()
        if value not in (None, "")
    }


# ---------------------------------------------------------------------
# CHECKBOX CROSSWALK
# ---------------------------------------------------------------------
#
# District forms name their checkboxes per-district. We match by terms:
# each selected tracker option contributes search terms, and a spec
# checkbox is pre-checked when its key or label contains one of them.

OPTION_TERMS = {
    # tracker option slug -> terms found in district checkbox keys/labels
    "anti_arab_racism": ["arab", "ancestry", "ethnic"],
    # "Anti-Muslim Hate or Islamophobia" (merged 2026-10-01): union
    # of the old anti_muslim_hate and racism_or_islamophobia terms.
    # Not "race"/"racism": historical anti_muslim_hate selections
    # predate the merge with "Racism or Islamophobia" and must not
    # pre-check Race on district forms their reporter never claimed.
    "anti_muslim_hate": ["muslim", "religio", "islam"],
    # Inactive since the merge; kept so historical selections map.
    "racism_or_islamophobia": ["race", "racism", "islam", "religio"],
    "anti_palestinian_racism": [
        "palestin", "national_origin", "national origin", "ancestry",
        "immigra", "ethnic",
    ],
}

# Reporter-role terms for on-behalf-of / filer checkboxes.
ROLE_TERMS = {
    "parent": ["parent", "guardian", "my_child", "my child", "child"],
    "student": ["student", "myself", "yourself"],
    "teacher": ["employee", "staff", "teacher"],
    "admin": ["employee", "staff", "admin"],
    "education_org": ["community", "other"],
    "other": ["other"],
}

BASIS_KEY_RX = re.compile(
    r"^(basis[:_]|category:basis_|category:.*(discrim|harass|bully|"
    r"race|racism|relig|national|origin|ethnic|immigr|muslim|arab|"
    r"palestin|color|ancestry|nationality))"
)

ROLE_KEY_RX = re.compile(
    r"^(behalf[:_]|filer_|role[:_]|on_behalf|filing_for_)"
)


def _terms_for_report(report):
    terms = set()

    slugs = report.option_selections.filter(
        option__category__in=["racism_type", "targeted_identity"],
    ).values_list("option__slug", "option__label")

    for slug, label in slugs:
        terms.update(OPTION_TERMS.get(slug, []))
        # The option label itself is often the best term.
        terms.update(
            w for w in re.findall(r"[a-z]+", label.lower())
            if len(w) > 3
        )

    # Direct questionnaire answer, stored on the report itself.
    if report.anti_palestinian_racism == "yes":
        terms.update(OPTION_TERMS["anti_palestinian_racism"])
        terms.add("palestinian")

    return terms


def checkbox_prechecks(report, spec_fields):
    """Return the set of spec checkbox keys to pre-check."""

    checked = set()
    terms = _terms_for_report(report)

    california = getattr(report, "california_details", None)
    role = california.reporter_role if california else ""
    role_terms = ROLE_TERMS.get(role, [])

    for field in spec_fields:
        if field.get("type") != "checkbox":
            continue

        key = field["key"]
        haystack = (
            key.lower() + " " + (field.get("label") or "").lower()
        )

        if BASIS_KEY_RX.match(key):
            if any(term in haystack for term in terms):
                checked.add(key)

        elif ROLE_KEY_RX.match(key):
            if any(term in haystack for term in role_terms):
                checked.add(key)

    return checked


# ---------------------------------------------------------------------
# QUESTION PLAN
# ---------------------------------------------------------------------

def build_plan(report, spec, cds=None):
    """
    Split the district's fields into what we already have and what we
    still need to ask.

    Returns a dict with:
      prefilled      [(label, value)]      shown for review
      followups      [field dicts]          asked on the page
      checkbox_fields [field dicts + checked flag]  shown for review
      answers        {key: value}           to submit
    """

    answers = known_answers(report)
    fields = spec.get("fields", [])

    # Public school address data: fill from the portal's school
    # lookup when the district form asks for it and the reporter's
    # answers do not already cover it. Silent on any failure.
    _SCHOOL_INFO_KEYS = {
        "school_address": "address",
        "school_city": "city",
        "school_zip": "zip",
    }
    wanted = [
        field["key"]
        for field in fields
        if field.get("key") in _SCHOOL_INFO_KEYS
        and not answers.get(field.get("key"))
    ]
    if wanted:
        school = getattr(report, "school_incident", None)
        info = get_school_info(
            cds,
            school.school_name if school else "",
        )
        for key in wanted:
            value = info.get(_SCHOOL_INFO_KEYS[key])
            if value:
                answers[key] = value
    checked = checkbox_prechecks(report, fields)

    prefilled = []
    followups = []
    checkbox_fields = []

    # Only what this district's form asks for — and therefore only
    # what the reporter sees on the review page — leaves the tracker.
    submit = {}

    for field in fields:
        key = field["key"]
        field_type = field.get("type")

        if field_type == "checkbox":
            checkbox_fields.append({
                **field,
                "checked": key in checked,
            })
            if key in checked:
                submit[key] = "1"
            continue

        value = answers.get(key)

        if value:
            prefilled.append(
                (field.get("label") or key, value)
            )
            submit[key] = value

        else:
            followups.append(field)

    # The portal hides date_signed from question plans and stamps
    # TODAY's date at generation when it is absent; the reporter's
    # attested signature date must win. /generate only collects keys
    # present in the district's raw spec, so sending the signature
    # answers beyond the plan is safe, and the signature is the
    # reporter's own attestation (shown to them on the page).
    for key in (
        "date_signed", "signature", "complainant_signature",
        "signed_day", "sign_day", "signed_month", "sign_month",
        "signed_year",
    ):
        if key in answers and key not in submit:
            submit[key] = answers[key]

    return {
        "prefilled": prefilled,
        "followups": followups,
        "checkbox_fields": checkbox_fields,
        "answers": submit,
    }
