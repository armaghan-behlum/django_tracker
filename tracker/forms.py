from django import forms
from django.forms import ClearableFileInput

from .models import (
    IncidentReport,
    AffectedPerson,
    CaliforniaDetails,
    SchoolIncident,
    FormalSchoolComplaint,
    AffectedPersonDemographics,
    ReportOption,
    ReportOptionSelection,
    ReferralOrganization,
    ReportReferral,
    ReportAttachment,
)


# ---------------------------------------------------------------------
# SHARED HELPERS
# ---------------------------------------------------------------------

YES_NO_RADIO = forms.RadioSelect(
    choices=[
        (True, "Yes"),
        (False, "No"),
    ]
)


class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if isinstance(data, (list, tuple)):
            return [
                single_file_clean(file, initial)
                for file in data
            ]

        if data:
            return [single_file_clean(data, initial)]

        return []


def option_queryset(category):
    return ReportOption.objects.filter(
        category=category,
        is_active=True,
    ).order_by(
        "sort_order",
        "label",
    )


def initial_option_ids(report, category):
    if not report or not report.pk:
        return []

    return ReportOptionSelection.objects.filter(
        report=report,
        option__category=category,
    ).values_list(
        "option_id",
        flat=True,
    )


def save_option_selections(report, category, options):
    ReportOptionSelection.objects.filter(
        report=report,
        option__category=category,
    ).delete()

    ReportOptionSelection.objects.bulk_create([
        ReportOptionSelection(
            report=report,
            option=option,
        )
        for option in options
    ])


# ---------------------------------------------------------------------
# CONTACT / CONSENT
# ---------------------------------------------------------------------

class IncidentContactForm(forms.ModelForm):

    class Meta:
        model = IncidentReport

        fields = [
            "has_consented",
            "state",
            "first_name",
            "last_name",
            "email",
            "phone",
        ]

        widgets = {
            "has_consented": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "state": forms.Select(
                attrs={"class": "form-select"}
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "form-control"}
            ),
            "phone": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }

    def clean_has_consented(self):
        value = self.cleaned_data["has_consented"]

        if not value:
            raise forms.ValidationError(
                "You must consent before submitting this form."
            )

        return value

    def clean(self):
        cleaned_data = super().clean()

        state = cleaned_data.get("state")
        phone = cleaned_data.get("phone")

        if state and state != "CA" and not phone:
            self.add_error(
                "phone",
                "Phone number is required for non-California reports.",
            )

        return cleaned_data


# ---------------------------------------------------------------------
# AFFECTED PERSON
# ---------------------------------------------------------------------

class AffectedPersonForm(forms.ModelForm):

    class Meta:
        model = AffectedPerson

        fields = [
            "is_reporter",
            "first_name",
            "last_name",
        ]

        widgets = {
            "is_reporter": forms.RadioSelect(
                choices=[
                    (
                        True,
                        "I am reporting an incident that happened to me",
                    ),
                    (
                        False,
                        "I am reporting on behalf of someone else",
                    ),
                ]
            ),
            "first_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        is_reporter = cleaned_data.get("is_reporter")

        if is_reporter is False:
            if not cleaned_data.get("first_name"):
                self.add_error(
                    "first_name",
                    "Please provide the affected person's first name.",
                )

            if not cleaned_data.get("last_name"):
                self.add_error(
                    "last_name",
                    "Please provide the affected person's last name.",
                )

        return cleaned_data


# ---------------------------------------------------------------------
# MAIN INCIDENT DETAILS
# ---------------------------------------------------------------------

class IncidentDetailsForm(forms.ModelForm):

    racism_types = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    location_types = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    incident_types = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = IncidentReport

        fields = [
            "date_precision",
            "incident_date",
            "incident_month",
            "incident_year",
            "description",
            "city",
            "zip_code",
            "anti_palestinian_racism",
            "knows_of_other_apr_incidents",
            "similar_incidents",
            "previously_reported",
            "resolution_steps",
        ]

        widgets = {
            "date_precision": forms.Select(
                attrs={"class": "form-select"}
            ),
            "incident_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "incident_month": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                    "max": 12,
                }
            ),
            "incident_year": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 7,
                }
            ),
            "city": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "zip_code": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "anti_palestinian_racism": forms.Select(
                attrs={"class": "form-select"}
            ),
            "knows_of_other_apr_incidents": YES_NO_RADIO,
            "previously_reported": YES_NO_RADIO,
            "similar_incidents": forms.Select(
                attrs={"class": "form-select"}
            ),
            "resolution_steps": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.report = report or (
            self.instance
            if self.instance and self.instance.pk
            else None
        )

        self.fields["racism_types"].queryset = option_queryset(
            ReportOption.Category.RACISM_TYPE
        )

        self.fields["location_types"].queryset = option_queryset(
            ReportOption.Category.LOCATION_TYPE
        )

        self.fields["incident_types"].queryset = option_queryset(
            ReportOption.Category.INCIDENT_TYPE
        )

        if self.report:
            self.fields["racism_types"].initial = initial_option_ids(
                self.report,
                ReportOption.Category.RACISM_TYPE,
            )

            self.fields["location_types"].initial = initial_option_ids(
                self.report,
                ReportOption.Category.LOCATION_TYPE,
            )

            self.fields["incident_types"].initial = initial_option_ids(
                self.report,
                ReportOption.Category.INCIDENT_TYPE,
            )

    def clean(self):
        cleaned_data = super().clean()

        precision = cleaned_data.get("date_precision")

        if precision == IncidentReport.DatePrecision.EXACT:
            if not cleaned_data.get("incident_date"):
                self.add_error(
                    "incident_date",
                    "Please provide the incident date.",
                )

        elif precision == IncidentReport.DatePrecision.MONTH:
            if not cleaned_data.get("incident_month"):
                self.add_error(
                    "incident_month",
                    "Please provide the incident month.",
                )

            if not cleaned_data.get("incident_year"):
                self.add_error(
                    "incident_year",
                    "Please provide the incident year.",
                )

        return cleaned_data

    def save_options(self, report):
        save_option_selections(
            report,
            ReportOption.Category.RACISM_TYPE,
            self.cleaned_data["racism_types"],
        )

        save_option_selections(
            report,
            ReportOption.Category.LOCATION_TYPE,
            self.cleaned_data["location_types"],
        )

        save_option_selections(
            report,
            ReportOption.Category.INCIDENT_TYPE,
            self.cleaned_data["incident_types"],
        )


# ---------------------------------------------------------------------
# CALIFORNIA DETAILS
# ---------------------------------------------------------------------

class CaliforniaDetailsForm(forms.ModelForm):

    class Meta:
        model = CaliforniaDetails

        fields = [
            "is_k12_incident",
            "reporter_role",
            "reporter_role_other",
            "student_date_of_birth",
            "child_full_name",
            "age",
        ]

        widgets = {
            "is_k12_incident": YES_NO_RADIO,
            "reporter_role": forms.Select(
                attrs={"class": "form-select"}
            ),
            "reporter_role_other": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "student_date_of_birth": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "child_full_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "age": forms.NumberInput(
                attrs={"class": "form-control"}
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        role = cleaned_data.get("reporter_role")

        if role == CaliforniaDetails.ReporterRole.STUDENT:
            if not cleaned_data.get("student_date_of_birth"):
                self.add_error(
                    "student_date_of_birth",
                    "Please provide the student's date of birth.",
                )

        if role == CaliforniaDetails.ReporterRole.PARENT:
            if not cleaned_data.get("child_full_name"):
                self.add_error(
                    "child_full_name",
                    "Please provide the child's name.",
                )

        if role == CaliforniaDetails.ReporterRole.OTHER:
            if not cleaned_data.get("reporter_role_other"):
                self.add_error(
                    "reporter_role_other",
                    "Please describe your role.",
                )

        return cleaned_data


# ---------------------------------------------------------------------
# SCHOOL DETAILS
# ---------------------------------------------------------------------

class SchoolIncidentForm(forms.ModelForm):

    educational_impacts = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    nonreport_reasons = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = SchoolIncident

        fields = [
            "school_name",
            "school_district",
            "grade",
            "principal",
            "location_within_school",
            "school_type",
            "school_type_other",
            "school_was_aware",
            "concerns_addressed_to",
            "concerns_addressed_date",
            "teacher_admin_response",
            "satisfied_with_response",
            "satisfaction_explanation",
            "school_response_effect",
            "absence_due_to_racism_frequency",
            "educational_requirement_violated",
        ]

        widgets = {
            "school_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "school_district": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "grade": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "principal": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "location_within_school": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "school_type": forms.Select(
                attrs={"class": "form-select"}
            ),
            "school_type_other": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "school_was_aware": forms.Select(
                attrs={"class": "form-select"}
            ),
            "concerns_addressed_to": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "concerns_addressed_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "teacher_admin_response": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "satisfied_with_response": forms.Select(
                attrs={"class": "form-select"}
            ),
            "satisfaction_explanation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "school_response_effect": forms.Select(
                attrs={"class": "form-select"}
            ),
            "absence_due_to_racism_frequency": forms.Select(
                attrs={"class": "form-select"}
            ),
            "educational_requirement_violated": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
        }

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.report = report

        self.fields["educational_impacts"].queryset = option_queryset(
            ReportOption.Category.EDUCATIONAL_IMPACT
        )

        self.fields["nonreport_reasons"].queryset = option_queryset(
            ReportOption.Category.NONREPORT_REASON
        )

        if report and report.pk:
            self.fields["educational_impacts"].initial = initial_option_ids(
                report,
                ReportOption.Category.EDUCATIONAL_IMPACT,
            )

            self.fields["nonreport_reasons"].initial = initial_option_ids(
                report,
                ReportOption.Category.NONREPORT_REASON,
            )

    def save_options(self, report):
        save_option_selections(
            report,
            ReportOption.Category.EDUCATIONAL_IMPACT,
            self.cleaned_data["educational_impacts"],
        )

        save_option_selections(
            report,
            ReportOption.Category.NONREPORT_REASON,
            self.cleaned_data["nonreport_reasons"],
        )


# ---------------------------------------------------------------------
# FORMAL SCHOOL COMPLAINT
# ---------------------------------------------------------------------

class FormalSchoolComplaintForm(forms.ModelForm):

    class Meta:
        model = FormalSchoolComplaint

        fields = [
            "previously_submitted_to_district",
            "authorize_autopopulation",
            "complaint_against",
            "individuals_involved",
            "witnesses",
            "discussed_with_principal_or_supervisor",
            "concerns_addressed_to",
            "concerns_addressed_date",
            "requested_remedy",
            "complainant_address",
        ]

        widgets = {
            "previously_submitted_to_district": YES_NO_RADIO,
            "authorize_autopopulation": YES_NO_RADIO,
            "complaint_against": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "individuals_involved": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "witnesses": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "discussed_with_principal_or_supervisor": YES_NO_RADIO,
            "concerns_addressed_to": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "concerns_addressed_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "requested_remedy": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "complainant_address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        authorize = cleaned_data.get("authorize_autopopulation")

        if authorize:
            required = {
                "complaint_against":
                    "Please identify who the complaint is against.",
                "requested_remedy":
                    "Please describe the action you would like taken.",
                "complainant_address":
                    "Your address is required for a formal complaint.",
            }

            for field, message in required.items():
                if not cleaned_data.get(field):
                    self.add_error(
                        field,
                        message,
                    )

        return cleaned_data


# ---------------------------------------------------------------------
# DEMOGRAPHICS + IMPACT
# ---------------------------------------------------------------------

class DemographicsImpactForm(forms.ModelForm):

    race_ethnicity = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    arab_palestinian_identity = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    targeted_identities = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    discrimination_experiences = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    wellbeing_impacts = forms.ModelMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = AffectedPersonDemographics

        fields = [
            "gender",
            "gender_other",
            "religion",
            "religion_other",
        ]

        widgets = {
            "gender": forms.Select(
                attrs={"class": "form-select"}
            ),
            "gender_other": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "religion": forms.Select(
                attrs={"class": "form-select"}
            ),
            "religion_other": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.report = report

        categories = {
            "race_ethnicity":
                ReportOption.Category.RACE_ETHNICITY,

            "arab_palestinian_identity":
                ReportOption.Category.ARAB_PALESTINIAN_IDENTITY,

            "targeted_identities":
                ReportOption.Category.TARGETED_IDENTITY,

            "discrimination_experiences":
                ReportOption.Category.DISCRIMINATION_EXPERIENCE,

            "wellbeing_impacts":
                ReportOption.Category.WELLBEING_IMPACT,
        }

        for field_name, category in categories.items():
            self.fields[field_name].queryset = option_queryset(
                category
            )

            if report and report.pk:
                self.fields[field_name].initial = initial_option_ids(
                    report,
                    category,
                )

    def clean_race_ethnicity(self):
        races = self.cleaned_data["race_ethnicity"]

        if races.count() > 3:
            raise forms.ValidationError(
                "Please choose no more than three."
            )

        return races

    def save_options(self, report):
        mappings = {
            "race_ethnicity":
                ReportOption.Category.RACE_ETHNICITY,

            "arab_palestinian_identity":
                ReportOption.Category.ARAB_PALESTINIAN_IDENTITY,

            "targeted_identities":
                ReportOption.Category.TARGETED_IDENTITY,

            "discrimination_experiences":
                ReportOption.Category.DISCRIMINATION_EXPERIENCE,

            "wellbeing_impacts":
                ReportOption.Category.WELLBEING_IMPACT,
        }

        for field_name, category in mappings.items():
            save_option_selections(
                report,
                category,
                self.cleaned_data[field_name],
            )


# ---------------------------------------------------------------------
# FINAL QUESTIONS
# ---------------------------------------------------------------------

class FinalQuestionsForm(forms.ModelForm):

    class Meta:
        model = IncidentReport

        fields = [
            "connection_change",
            "other_identity_information",
            "additional_information",
            "support_sought_elsewhere",
            "opt_out_of_followup",
            "signature_name",
            "signature_date",
        ]

        widgets = {
            "connection_change": forms.Select(
                attrs={"class": "form-select"}
            ),
            "other_identity_information": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "additional_information": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                }
            ),
            "support_sought_elsewhere": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "opt_out_of_followup": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "signature_name": forms.TextInput(
                attrs={"class": "form-control"}
            ),
            "signature_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

    def clean_signature_name(self):
        value = self.cleaned_data["signature_name"]

        if not value:
            raise forms.ValidationError(
                "Please provide your digital signature."
            )

        return value

    def clean_signature_date(self):
        value = self.cleaned_data["signature_date"]

        if not value:
            raise forms.ValidationError(
                "Please provide the signature date."
            )

        return value


# ---------------------------------------------------------------------
# REFERRALS
# ---------------------------------------------------------------------

class ReferralForm(forms.Form):

    organizations = forms.ModelMultipleChoiceField(
        queryset=ReferralOrganization.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Organizations to receive this report",
    )

    anonymous_organizations = forms.ModelMultipleChoiceField(
        queryset=ReferralOrganization.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Submit anonymously to these organizations",
    )

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)

        organizations = ReferralOrganization.objects.filter(
            is_active=True
        ).order_by(
            "sort_order",
            "name",
        )

        self.fields["organizations"].queryset = organizations
        self.fields["anonymous_organizations"].queryset = organizations

        if report and report.pk:
            referrals = report.referrals.select_related(
                "organization"
            )

            self.fields["organizations"].initial = [
                referral.organization_id
                for referral in referrals
            ]

            self.fields["anonymous_organizations"].initial = [
                referral.organization_id
                for referral in referrals
                if referral.anonymous
            ]

    def clean(self):
        cleaned_data = super().clean()

        organizations = cleaned_data.get("organizations")
        anonymous = cleaned_data.get("anonymous_organizations")

        if organizations is not None and anonymous is not None:
            organization_ids = set(
                organizations.values_list(
                    "pk",
                    flat=True,
                )
            )

            anonymous_ids = set(
                anonymous.values_list(
                    "pk",
                    flat=True,
                )
            )

            if not anonymous_ids.issubset(organization_ids):
                self.add_error(
                    "anonymous_organizations",
                    (
                        "An organization must first be selected "
                        "to receive the report."
                    ),
                )

        return cleaned_data

    def save(self, report):
        organizations = self.cleaned_data["organizations"]
        anonymous = self.cleaned_data["anonymous_organizations"]

        anonymous_ids = set(
            anonymous.values_list(
                "pk",
                flat=True,
            )
        )

        ReportReferral.objects.filter(
            report=report
        ).delete()

        ReportReferral.objects.bulk_create([
            ReportReferral(
                report=report,
                organization=organization,
                submit=True,
                anonymous=organization.pk in anonymous_ids,
            )
            for organization in organizations
        ])


# ---------------------------------------------------------------------
# ATTACHMENTS
# ---------------------------------------------------------------------

class AttachmentForm(forms.Form):

    files = MultipleFileField(
        required=False,
        label="Photos or documents",
    )

    def save(self, report):
        attachments = []

        for uploaded_file in self.cleaned_data.get(
            "files",
            [],
        ):
            attachments.append(
                ReportAttachment.objects.create(
                    report=report,
                    file=uploaded_file,
                )
            )

        return attachments