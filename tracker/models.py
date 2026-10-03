import uuid

from django.core.exceptions import ValidationError
from django.core.validators import (
    MaxValueValidator,
    MinValueValidator,
)
from django.db import models

YES_NO_CHOICES = (
    ("yes", "Yes"),
    ("no", "No"),
)

YES_NO_UNSURE_CHOICES = (
    ("yes", "Yes"),
    ("no", "No"),
    ("unsure", "Unsure"),
)

YES_NO_MAYBE_CHOICES = (
    ("yes", "Yes"),
    ("no", "No"),
    ("maybe", "Maybe"),
)

US_STATE_CHOICES = (
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
)

class IncidentReport(models.Model):

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        ARCHIVED = "archived", "Archived"

    class DatePrecision(models.TextChoices):
        EXACT = "exact", "Exact date"
        MONTH = "month", "Month and year"
        ONGOING = "ongoing", "Ongoing"
        UNKNOWN = "unknown", "Best estimate / unknown"

    class SimilarIncidentFrequency(models.TextChoices):
        DONT_KNOW = "dont_know", "Don't know"
        NEVER = "never", "Never"
        ONCE = "once", "Once"
        OCCASIONALLY = "occasionally", "Occasionally"
        FREQUENTLY = "frequently", "Frequently"

    class ConnectionChange(models.TextChoices):
        LESS = "less", "I feel less connected"
        MORE = "more", "I feel more connected"
        NO_CHANGE = "no_change", "It did not change my connection"
        NOT_APPLICABLE = "not_applicable", "Not applicable"

    uuid = models.UUIDField(default=uuid.uuid4, editable=False,
        unique=True, db_index=True)
    has_consented = models.BooleanField(default=False,
        help_text=(
            "Reporter confirms they have read the consent information, "
            "are 13 or older, and agree to participate."
        ))
    state = models.CharField(max_length=2,
        choices=US_STATE_CHOICES, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    date_precision = models.CharField(max_length=20,
        choices=DatePrecision.choices, default=DatePrecision.EXACT)
    incident_date = models.DateField(blank=True,null=True,
        help_text="Used when a specific date is known.")
    incident_month = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[
            MinValueValidator(1),
            MaxValueValidator(12),
        ])
    incident_year = models.PositiveSmallIntegerField(
        blank=True, null=True, validators=[
            MinValueValidator(2000),
            MaxValueValidator(2030),
        ])
    incident_date_estimate = models.CharField(max_length=200,
        blank=True, help_text=(
            "Free-text best estimate, used when the date precision "
            "is \"Best estimate / unknown\"."
        ))
    description = models.TextField()
    city = models.CharField(max_length=150, blank=True)
    zip_code = models.CharField(max_length=20, blank=True)
    anti_palestinian_racism = models.CharField(max_length=10,
        choices=YES_NO_MAYBE_CHOICES, blank=True, db_index=True)
    anti_palestinian_racism_reason = models.TextField(blank=True,
        help_text=(
            "Why the respondent believes the incident was "
            "anti-Palestinian racism (asked on yes/maybe)."
        ))
    knows_of_other_apr_incidents = models.BooleanField(
        null=True, blank=True,
        help_text=(
            "Aside from this incident, does the respondent know of "
            "other incidents of anti-Palestinian racism?"
        ))
    similar_incidents = models.CharField(max_length=20, blank=True, 
        choices=SimilarIncidentFrequency.choices, db_index=True)
    previously_reported = models.BooleanField(null=True, blank=True,
        help_text=(
            "For respondents for whom the general reporting question applies."
        ))
    resolution_steps = models.TextField(blank=True,
        help_text=(
            "Steps taken to resolve the issue before or aside from "
            "filing a complaint."
        ))
    connection_change = models.CharField(max_length=20, blank=True,
        choices=ConnectionChange.choices, db_index=True)
    other_identity_information = models.TextField(blank=True)
    additional_information = models.TextField(blank=True)
    support_sought_elsewhere = models.TextField(blank=True,
        help_text=(
            "Organizations, institutions, or attorneys from whom the "
            "respondent has sought support."
        ))
    opt_out_of_followup = models.BooleanField(default=False,
        help_text=(
            "Primarily used for non-California respondents who opt out "
            "of private follow-up questions or clarification."
        ))
    signature_name = models.CharField(max_length=200, blank=True)
    signature_date = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices,
        default=Status.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.uuid} — {self.first_name} {self.last_name}"

    @property
    def is_california(self):
        return self.state == "CA"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def clean(self):
        # Incident-date validation lives on IncidentDetailsForm: this
        # model is edited through several partial ModelForms (contact,
        # incident, final), and a partial form crashes when model-wide
        # clean() raises errors for fields the form does not carry.
        super().clean()

        errors = {}

        if self.state and self.state != "CA" and not self.phone:
            errors["phone"] = (
                "Phone number is required for non-California reports."
            )

        if errors:
            raise ValidationError(errors)


class ReportOption(models.Model):

    class Category(models.TextChoices):
        RACISM_TYPE = ("racism_type", "Form of racism")
        LOCATION_TYPE = ("location_type", "Location type")
        INCIDENT_TYPE = ("incident_type", "Incident type")
        EDUCATIONAL_IMPACT = ("educational_impact", "Educational impact")
        WELLBEING_IMPACT = ("wellbeing_impact", "Well-being impact")
        DISCRIMINATION_EXPERIENCE = ("discrimination_experience",
            "Discrimination experience")
        TARGETED_IDENTITY = ("targeted_identity", "Targeted identity")
        RACE_ETHNICITY = ("race_ethnicity", "Race / ethnicity")
        ARAB_PALESTINIAN_IDENTITY = ("arab_palestinian_identity",
            "Arab / Palestinian identity")
        NONREPORT_REASON = ("nonreport_reason",
            "Reason incident was not reported")

    category = models.CharField(max_length=50, 
        choices=Category.choices, db_index=True)
    slug = models.SlugField(max_length=100)
    label = models.CharField(max_length=255)
    sort_order = models.PositiveIntegerField(default=0)
    allows_other_text = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [
            "category",
            "sort_order",
            "label",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"],
                name="unique_report_option_category_slug",
            ),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.label}"


class ReportOptionSelection(models.Model):

    report = models.ForeignKey(IncidentReport,
        on_delete=models.CASCADE, related_name="option_selections")
    option = models.ForeignKey(ReportOption, 
        on_delete=models.PROTECT, related_name="selections")
    other_text = models.CharField(max_length=500,blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["report", "option"],
                name="unique_report_option_selection",
            ),
        ]

    def __str__(self):
        return f"{self.report.uuid}: {self.option.label}"

    def clean(self):
        super().clean()

        if self.other_text and not self.option.allows_other_text:
            raise ValidationError({
                "other_text": (
                    "This option does not allow additional text."
                ),
            })

class CaliforniaDetails(models.Model):

    class ReporterRole(models.TextChoices):
        TEACHER = ("teacher", "Teacher")
        PARENT = ("parent", "Parent / Guardian")
        STUDENT = ("student", "Student")
        ADMIN = ("admin","School administrator or staff")
        EDUCATION_ORG = ("education_org", "Education organization staff")
        OTHER = ("other", "Other")

    report = models.OneToOneField(IncidentReport,
        on_delete=models.CASCADE, related_name="california_details")
    is_k12_incident = models.BooleanField(null=True, blank=True,
        db_index=True, help_text=(
            "Incident related to a California K-12 school system or "
            "affecting someone in that age range."
        ))
    reporter_role = models.CharField(max_length=30, blank=True,
        choices=ReporterRole.choices, db_index=True)
    reporter_role_other = models.CharField(max_length=200, blank=True)
    # If reporter is student
    student_date_of_birth = models.DateField(blank=True, null=True)
    # If reporter is parent/guardian
    child_full_name = models.CharField(max_length=200, blank=True)
    age = models.PositiveSmallIntegerField(blank=True, null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(120),
        ])

    def __str__(self):
        return f"California details — {self.report.uuid}"

    def clean(self):
        super().clean()

        if self.report_id and self.report.state != "CA":
            raise ValidationError(
                "CaliforniaDetails can only be attached to "
                "California reports."
            )

class ReferralOrganization(models.Model):

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = [
            "sort_order",
            "name",
        ]

    def __str__(self):
        return self.name


class ReportReferral(models.Model):

    report = models.ForeignKey(IncidentReport,
        on_delete=models.CASCADE, related_name="referrals")
    organization = models.ForeignKey(ReferralOrganization,
        on_delete=models.PROTECT, related_name="report_referrals")
    submit = models.BooleanField(default=True)
    anonymous = models.BooleanField(default=False, help_text=(
        "Share anonymized incident information only, without "
        "individual follow-up."
    ))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "report",
                    "organization",
                ],
                name="unique_report_referral",
            ),
        ]

    def __str__(self):
        return (
            f"{self.report.uuid} → "
            f"{self.organization.name}"
        )

class SchoolIncident(models.Model):

    class SchoolType(models.TextChoices):
        PUBLIC = ("public", "Public")
        SECULAR = ("secular", "Secular")
        PRIVATE = ("private", "Private")
        CHARTER = ("charter", "Charter")
        PRIVATE_RELIGIOUS = ("private_religious",
            "Religious/Parochial Private")
        OTHER = ("other", "Other")

    class ResponseEffect(models.TextChoices):
        IMPROVED = ("improved", "Improved")
        WORSENED = ("worsened", "Worsened")
        NO_CHANGE = ("no_change", "No change")
        UNSURE = ("unsure", "Unsure")

    class AbsenceFrequency(models.TextChoices):
        NEVER = ("never", "Never")
        ONCE = ("once", "Once",)
        FEW_TIMES = ("few_times", "A few times")
        MONTHLY = ("monthly", "Monthly")
        WEEKLY = ("weekly", "Weekly")
        MORE_THAN_WEEKLY = ("more_than_weekly", "More than weekly")

    report = models.OneToOneField(IncidentReport,
        on_delete=models.CASCADE, related_name="school_incident")
    school_name = models.CharField(max_length=255, blank=True)
    school_district = models.CharField(max_length=255, blank=True)
    grade = models.CharField(max_length=100, blank=True)
    principal = models.CharField(max_length=200, blank=True)
    location_within_school = models.CharField(max_length=255, blank=True)
    school_type = models.CharField(max_length=30, blank=True,
        choices=SchoolType.choices, db_index=True)
    school_type_other = models.CharField(max_length=200, blank=True)
    school_was_aware = models.CharField(max_length=10, blank=True,
        choices=YES_NO_UNSURE_CHOICES, db_index=True)
    concerns_addressed_to = models.CharField(max_length=255, blank=True)
    concerns_addressed_date = models.DateField(blank=True, null=True)
    teacher_admin_response = models.TextField(blank=True)
    satisfied_with_response = models.CharField(max_length=10, blank=True,
        choices=YES_NO_UNSURE_CHOICES, db_index=True)
    satisfaction_explanation = models.TextField(blank=True)
    school_response_effect = models.CharField(max_length=20, blank=True,
        choices=ResponseEffect.choices, db_index=True)
    absence_due_to_racism_frequency = models.CharField(max_length=30,
        blank=True, choices=AbsenceFrequency.choices, db_index=True)
    educational_requirement_violated = models.TextField(blank=True,
        help_text=(
            "Educational or program requirement the respondent "
            "believes was violated."
        ))

    def __str__(self):
        if self.school_name:
            return f"{self.school_name} — {self.report.uuid}"

        return f"School incident — {self.report.uuid}"


class FormalSchoolComplaint(models.Model):

    report = models.OneToOneField(IncidentReport,
        on_delete=models.CASCADE, related_name="formal_school_complaint")
    previously_submitted_to_district = models.BooleanField(
        null=True, blank=True, db_index=True)
    authorize_autopopulation = models.BooleanField(null=True, blank=True,
        help_text=(
            "Respondent authorizes the form to populate a formal "
            "complaint to the district authority or state."
    ))
    complaint_against = models.TextField(blank=True, help_text=(
        "Name, job title, school, department, or other identifying "
        "information for the person/entity complained against."
    ))
    individuals_involved = models.TextField(blank=True)
    witnesses = models.TextField(blank=True)
    discussed_with_principal_or_supervisor = models.BooleanField(
        null=True, blank=True, db_index=True)
    concerns_addressed_to = models.CharField(max_length=255, blank=True)
    concerns_addressed_date = models.DateField(blank=True, null=True)
    requested_remedy = models.TextField(blank=True)
    complainant_address = models.TextField(blank=True, help_text=(
        "Full address including apartment/unit number when required "
        "for submitting a formal complaint."
    ))

    def __str__(self):
        return f"Formal complaint — {self.report.uuid}"

    def clean(self):
        super().clean()

        errors = {}

        if self.report_id and self.report.state != "CA":
            raise ValidationError(
                "FormalSchoolComplaint can only be attached to "
                "California reports."
            )

        if self.authorize_autopopulation:
            if not self.complaint_against:
                errors["complaint_against"] = (
                    "Please identify who the complaint is against."
                )

            if not self.requested_remedy:
                errors["requested_remedy"] = (
                    "Please specify the requested remedy."
                )

            if not self.complainant_address:
                errors["complainant_address"] = (
                    "Address is required to generate the formal complaint."
                )

        if errors:
            raise ValidationError(errors)

class AffectedPerson(models.Model):
    report = models.OneToOneField(IncidentReport,
        on_delete=models.CASCADE, related_name="affected_person")
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    is_reporter = models.BooleanField(default=True)

class AffectedPersonDemographics(models.Model):
    """
    Demographic information should describe the person affected by
    the incident.

    For example, if a parent files on behalf of their child, these
    answers should describe the child rather than the parent.
    """

    class Gender(models.TextChoices):
        FEMALE = ("female", "Female")
        MALE = ("male", "Male")
        NONBINARY = ("nonbinary", "Nonbinary / gender expansive")
        OTHER = ("other", "Other")
        PREFER_NOT = ("prefer_not", "Prefer not to answer")

    class Religion(models.TextChoices):
        BUDDHISM = ("buddhism", "Buddhism")
        CHRISTIANITY = ("christianity", "Christianity")
        HINDUISM = ("hinduism", "Hinduism")
        ISLAM = ("islam", "Islam")
        JUDAISM = ("judaism", "Judaism")
        SIKHISM = ("sikhism", "Sikhism")
        TAOISM = ("taoism", "Taoism")
        NONE = ("none", "None / no faith tradition")
        OTHER = ("other", "Other")
        PREFER_NOT = ("prefer_not", "Prefer not to say")

    affected_person = models.OneToOneField(AffectedPerson,
        on_delete=models.CASCADE, related_name="demographics")
    gender = models.CharField(max_length=30, blank=True,
        choices=Gender.choices, db_index=True)
    gender_other = models.CharField(max_length=150, blank=True)
    religion = models.CharField(max_length=30, blank=True,
        choices=Religion.choices, db_index=True)
    religion_other = models.CharField(max_length=150, blank=True)

    def __str__(self):
        # The old f-string read self.report, which does not exist,
        # so every admin delete-confirmation render crashed. Kept
        # PII-free: this string reaches admin lists and breadcrumbs.
        return (
            f"Demographics — affected person "
            f"#{self.affected_person_id}"
        )

def report_attachment_upload_to(instance, filename):
    return (
        f"incident_reports/"
        f"{instance.report.uuid}/"
        f"{filename}"
    )


class ReportAttachment(models.Model):

    report = models.ForeignKey(IncidentReport,
        on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to=report_attachment_upload_to)
    description = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment — {self.report.uuid} — {self.file.name}"

class UCPFiling(models.Model):
    """
    Record of a UCP form generated for a report via the hand-off page.

    The PDF itself is returned to the reporter for signature and is
    not stored here; this row tracks that the hand-off happened and
    for which district.
    """

    report = models.ForeignKey(IncidentReport,
        on_delete=models.CASCADE, related_name="ucp_filings")
    district_cds = models.CharField(max_length=14, db_index=True,
        help_text="CDS code of the district whose form was generated.")
    district_name = models.CharField(max_length=255)
    tier = models.CharField(max_length=20, blank=True, help_text=(
        "How the portal produced the document: 'official' when the "
        "district's own form was filled, otherwise a generated "
        "complaint letter."
    ))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.report.uuid} → {self.district_name}"


# ---------------------------------------------------------------------
# DATA SEPARATION (pilot)
# ---------------------------------------------------------------------
#
# Single source of truth for the access model (see DATA_ACCESS.md).
# Direct identifiers: fields that name or contact a person by
# construction. Open-text scrubbing (description etc.) and
# quasi-identifier generalization (school, grade, role, city) are
# the next phase.

DIRECT_IDENTIFIER_FIELDS = {
    "IncidentReport": [
        "first_name", "last_name", "email", "phone",
        "signature_name", "signature_date",
    ],
    "AffectedPerson": ["first_name", "last_name"],
    "CaliforniaDetails": ["child_full_name", "student_date_of_birth"],
    "SchoolIncident": ["principal", "concerns_addressed_to"],
    "FormalSchoolComplaint": [
        "complaint_against", "individuals_involved", "witnesses",
        "concerns_addressed_to", "complainant_address",
    ],
    "ReportAttachment": ["file"],
}


def deidentified_q():
    """
    Q matching reports whose reporter opted out of follow-up.

    Uses a correlated Exists so BOTH conditions must hold on the
    SAME referral row; a joined predicate lets separate rows satisfy
    them, which both hid the wrong reports from follow-up staff and
    broke under negation (codex round 5 #3).
    """

    anonymous_aroc = ReportReferral.objects.filter(
        report=models.OuterRef("pk"),
        organization__slug="aroc_iuapr",
        anonymous=True,
    )

    return (
        models.Q(opt_out_of_followup=True)
        | models.Q(models.Exists(anonymous_aroc))
    )


def _incident_report_is_deidentified(report):
    if report.opt_out_of_followup:
        return True

    return report.referrals.filter(
        organization__slug="aroc_iuapr",
        anonymous=True,
    ).exists()


IncidentReport.is_deidentified = property(
    _incident_report_is_deidentified
)


class DeidentifiedReport(IncidentReport):
    """
    Coordinator-facing representation: same rows, but the admin
    registered for this proxy exposes no direct identifiers for ANY
    report. A separate scrubbed table is the next phase; this proxy
    keeps the surface separate from the full-record admin rather
    than a bypassable toggle.
    """

    class Meta:
        proxy = True
        verbose_name = "De-identified report"
        verbose_name_plural = "De-identified reports"

    def __str__(self):
        # The parent __str__ carries the reporter's name, and the
        # admin renders __str__ in titles and breadcrumbs.
        return f"De-identified report #{self.pk}"


class PIIAccessLog(models.Model):
    """One row per view of a full (identifying) report record."""

    user = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="pii_access_logs",
    )
    username = models.CharField(max_length=150)
    report = models.ForeignKey(
        IncidentReport,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pii_access_logs",
    )
    report_uuid = models.CharField(max_length=36)
    surface = models.CharField(max_length=50)
    accessed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-accessed_at"]
        verbose_name = "PII access log entry"
        verbose_name_plural = "PII access log"

    def __str__(self):
        return (
            f"{self.username} viewed {self.report_uuid} "
            f"({self.surface}) at {self.accessed_at:%Y-%m-%d %H:%M}"
        )
