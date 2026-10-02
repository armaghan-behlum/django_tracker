from django import forms
from django.conf import settings
from django.forms import ClearableFileInput

from hcaptcha.fields import hCaptchaField


class SafeHCaptchaField(hCaptchaField):
    """
    The upstream field only catches HTTPError during verification; a
    connection failure, timeout, or malformed response escapes and
    turns the whole submission into a server error, destroying the
    reporter's entries. Turn those into a field error instead so the
    form re-renders populated and can be retried.
    """

    def validate(self, value):
        try:
            super().validate(value)
        except forms.ValidationError:
            raise
        except Exception as exc:
            raise forms.ValidationError(
                "We could not reach the verification service. "
                "Your answers are still here — please try "
                "submitting again in a moment.",
                code="error_hcaptcha",
            ) from exc

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


class OptionMultipleChoiceField(forms.ModelMultipleChoiceField):
    """
    Checkbox labels show the option's own label ("University"),
    not str(option) ("Location type: University").
    """

    def label_from_instance(self, obj):
        return obj.label


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


def length_ordered(queryset):
    """
    Display order for ragged checkbox grids: shortest label first so
    items of similar height share a grid row; "Other..." stays last.
    Seed sort_order is untouched — this is presentation only.
    """
    from django.db.models import Case, IntegerField, Value, When
    from django.db.models.functions import Length

    return queryset.annotate(
        _other=Case(
            When(slug__icontains="other", then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        _len=Length("label"),
    ).order_by("_other", "_len", "label")


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


def save_option_selections(report, category, options, other_text=""):
    ReportOptionSelection.objects.filter(
        report=report,
        option__category=category,
    ).delete()

    # other_text lands only on the option that allows it (the
    # category's "Other" choice), never on fixed options.
    ReportOptionSelection.objects.bulk_create([
        ReportOptionSelection(
            report=report,
            option=option,
            other_text=(
                other_text.strip()
                if option.allows_other_text
                else ""
            ),
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

        labels = {
            "has_consented": (
                "I have read the above information, I am 13 or "
                "older, and I agree to participate."
            ),
            "first_name": "First name",
            "last_name": "Last name",
            "email": "Email",
            "phone": "Phone",
        }

        help_texts = {
            # The label already carries the full consent statement.
            "has_consented": "",
            "email": (
                "As a reminder, this form is end to end encrypted "
                "and you may opt out of any contact."
            ),
            "phone": (
                "Required for reports outside of California."
            ),
        }

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The doc starts the state drop-down on California.
        self.fields["state"].initial = "CA"

        # Consent is server-required (clean_has_consented); mark it
        # required so the asterisk convention shows it, with the
        # same message. Crispy's checkbox template renders no
        # asterisk, so the label carries it directly.
        self.fields["has_consented"].required = True
        self.fields["has_consented"].error_messages["required"] = (
            "You must consent before submitting this form."
        )
        self.fields["has_consented"].label = (
            "I have read the above information, I am 13 or "
            "older, and I agree to participate.*"
        )

    def clean_has_consented(self):
        value = self.cleaned_data["has_consented"]

        if not value:
            raise forms.ValidationError(
                "You must consent before submitting this form."
            )

        return value

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

    racism_types = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    location_types = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    incident_types = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    racism_types_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
    )

    location_types_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
    )

    incident_types_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
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

        labels = {
            "date_precision": (
                "When did the incident take place? Please give us "
                "your best estimate."
            ),
            "incident_date": "Date",
            "incident_month": "Month",
            "incident_year": "Year",
            "description": (
                "Please describe what happened. Provide as much "
                "detail as possible."
            ),
            "city": "In what city did the incident take place?",
            "zip_code": (
                "In what zip code did the incident take place?"
            ),
            "anti_palestinian_racism": (
                "Are you reporting an incident or experience that "
                "you believe constitutes anti-Palestinian racism?"
            ),
            "knows_of_other_apr_incidents": (
                "Aside from this incident, have you witnessed other "
                "incidents of anti-Palestinian racism or do you "
                "personally know of others who have experienced "
                "anti-Palestinian racism?"
            ),
            "similar_incidents": (
                "Have similar incidents occurred before?"
            ),
            "previously_reported": "Did you report this incident?",
            "resolution_steps": (
                "What steps, if any, did you take to resolve the "
                "issue before or aside from filing a complaint?"
            ),
        }

        help_texts = {
            "description": (
                "For example: what happened, where it happened, who "
                "was involved, what did you do, did you get a "
                "resolution, etc."
            ),
            "knows_of_other_apr_incidents": "",
            "previously_reported": "",
            "resolution_steps": "",
        }

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

    def __init__(self, *args, report=None, state=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.report = report or (
            self.instance
            if self.instance and self.instance.pk
            else None
        )

        self.state = state

        # Doc-starred questions are genuinely required.
        for name, message in {
            "zip_code": (
                "Please provide the zip code where the incident "
                "took place."
            ),
            "anti_palestinian_racism": (
                "Please answer the anti-Palestinian racism question."
            ),
            "knows_of_other_apr_incidents": (
                "Please answer yes or no."
            ),
            "similar_incidents": (
                "Please tell us whether similar incidents occurred "
                "before."
            ),
        }.items():
            self.fields[name].required = True
            self.fields[name].error_messages["required"] = message

        # The doc stars the city question for California.
        if state == "CA":
            self.fields["city"].required = True
            self.fields["city"].error_messages["required"] = (
                "Please provide the California city where the "
                "incident took place."
            )

        self.fields["racism_types"].queryset = option_queryset(
            ReportOption.Category.RACISM_TYPE
        )

        self.fields["location_types"].queryset = length_ordered(
            option_queryset(ReportOption.Category.LOCATION_TYPE)
        )

        self.fields["incident_types"].queryset = length_ordered(
            option_queryset(ReportOption.Category.INCIDENT_TYPE)
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

        # The three option questions are doc-starred: at least one
        # selection each (every list carries an "Other" option).
        for name, message in {
            "racism_types": (
                "Please select at least one form of racism, or "
                "choose Other and describe it."
            ),
            "location_types": (
                "Please select at least one location, or choose "
                "Other and describe it."
            ),
            "incident_types": (
                "Please select at least one incident type, or "
                "choose Other and describe it."
            ),
        }.items():
            if name not in self.errors and not cleaned_data.get(name):
                self.add_error(name, message)

        # NullBooleanField ignores required=True (its validate is a
        # no-op), so the yes/no radio is enforced here.
        if (
            "knows_of_other_apr_incidents" not in self.errors
            and cleaned_data.get("knows_of_other_apr_incidents")
            is None
        ):
            self.add_error(
                "knows_of_other_apr_incidents",
                "Please answer yes or no.",
            )

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
            self.cleaned_data.get("racism_types_other", ""),
        )

        save_option_selections(
            report,
            ReportOption.Category.LOCATION_TYPE,
            self.cleaned_data["location_types"],
            self.cleaned_data.get("location_types_other", ""),
        )

        save_option_selections(
            report,
            ReportOption.Category.INCIDENT_TYPE,
            self.cleaned_data["incident_types"],
            self.cleaned_data.get("incident_types_other", ""),
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

        labels = {
            "is_k12_incident": (
                "Are you reporting an incident related to a "
                "California K-12 school system, or affecting someone "
                "in that age range (kindergarten to 12th grade)?"
            ),
            "reporter_role": "Are you a:",
            "reporter_role_other": "Please describe your role",
            "student_date_of_birth": "Date of birth",
            "child_full_name": (
                "Please list the full name of the child you are "
                "reporting on behalf of"
            ),
            "age": "Age",
        }

        help_texts = {
            "is_k12_incident": (
                "This could include something that happens online, "
                "interpersonally outside of the school or district, "
                "as well as incidents within K-12 schools statewide."
            ),
            "reporter_role": (
                "Please note if you are a parent or guardian filling "
                "out on behalf of your child, the questions on race, "
                "identity, etc. should represent the child."
            ),
        }

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

    def __init__(self, *args, school_location=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.school_location = school_location

        # Doc-starred for California reports.
        self.fields["is_k12_incident"].required = True
        self.fields["is_k12_incident"].error_messages["required"] = (
            "Please answer yes or no."
        )

        self.fields["age"].required = True
        self.fields["age"].error_messages["required"] = (
            "Please provide the age of the person affected."
        )

        # "Are you a:" renders in the School information block, so
        # it is only answerable (and required) for school incidents.
        if school_location:
            self.fields["reporter_role"].required = True
            self.fields["reporter_role"].error_messages[
                "required"
            ] = "Please tell us your role."

    def clean(self):
        cleaned_data = super().clean()

        # NullBooleanField ignores required=True; enforce the radio.
        if (
            "is_k12_incident" not in self.errors
            and cleaned_data.get("is_k12_incident") is None
        ):
            self.add_error(
                "is_k12_incident",
                "Please answer yes or no.",
            )

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

    educational_impacts = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    nonreport_reasons = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label=(
            "If you did not report this incident before, can you "
            "indicate your reason? Select any that apply."
        ),
    )

    nonreport_reasons_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
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

        labels = {
            "school_name": "School Name",
            "school_district": "School district",
            "grade": (
                "Grade of student or grade you teach; if not "
                "applicable, write n/a"
            ),
            "location_within_school": (
                "Where in the school did it happen?"
            ),
            "school_type": "School Type",
            "school_type_other": "Other school type",
            "school_was_aware": (
                "Was the school aware of the incident? For example, "
                "did you discuss your concerns with a Principal, "
                "Supervisor, or Administrator?"
            ),
            "concerns_addressed_to": (
                "Who did you address your concerns to?"
            ),
            "concerns_addressed_date": (
                "Your best guess at the date"
            ),
            "teacher_admin_response": (
                "What were the responses of teachers or "
                "administrators, witnesses or bystanders, if any?"
            ),
            "satisfied_with_response": (
                "Were you satisfied with the school's response "
                "after the incident?"
            ),
            "satisfaction_explanation": "Why or why not?",
            "school_response_effect": (
                "Did the school's response improve or worsen the "
                "school environment for you?"
            ),
            "absence_due_to_racism_frequency": (
                "How often did fear of anti-Palestinian or other "
                "racism cause you to miss school?"
            ),
            "educational_requirement_violated": (
                "Was there any educational or program requirement "
                "you feel was violated in this incident?"
            ),
        }

        help_texts = {
            "concerns_addressed_to": "Please provide a name.",
            "educational_requirement_violated": (
                "For example: second-language, low income, or other "
                "accommodations; graduation requirements; school "
                "safety plans; fees or charges; course periods "
                "without educational content; required consequences "
                "for bullying or educational safety, etc."
            ),
        }

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

    def __init__(
        self,
        *args,
        report=None,
        school_location=False,
        ca_k12=False,
        authorize=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.report = report
        self.school_location = school_location
        self.ca_k12 = ca_k12
        self.authorize = authorize

        # Doc-starred, gated on the path that reveals each field so
        # a hidden field can never block submission.
        required = {}

        if school_location:
            required.update({
                "school_name": "Please provide the school's name.",
                "school_type": "Please select the school type.",
                "educational_requirement_violated": (
                    "Please answer; if none applies, write \"none\"."
                ),
                "grade": (
                    "Please provide the grade; if not applicable, "
                    "write n/a."
                ),
                "principal": "Please provide the principal's name.",
                "location_within_school": (
                    "Please tell us where in the school it happened."
                ),
            })

        if ca_k12:
            required["school_district"] = (
                "Please provide the school district."
            )

        for name, message in required.items():
            self.fields[name].required = True
            self.fields[name].error_messages["required"] = message

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
            self.cleaned_data.get("nonreport_reasons_other", ""),
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

        labels = {
            "previously_submitted_to_district": (
                "Have you already submitted a complaint to the "
                "district (such as through the Uniform Complaints "
                "Procedure)?"
            ),
            "authorize_autopopulation": (
                "Would you like to authorize this form to "
                "autopopulate a formal complaint to the district "
                "authority or state?"
            ),
            "complaint_against": (
                "Who are you filing the complaint against?"
            ),
            "individuals_involved": "List of individuals involved",
            "witnesses": "List any witnesses to the incident",
            "discussed_with_principal_or_supervisor": (
                "Did you discuss your concerns with the Principal "
                "or a Supervisor?"
            ),
            "concerns_addressed_to": (
                "Who did you address your concerns to?"
            ),
            "concerns_addressed_date": (
                "Your best guess at the date"
            ),
            "requested_remedy": (
                "If you want the District or school to take "
                "particular action to remedy what happened, please "
                "specify"
            ),
            "complainant_address": "What is your address?",
        }

        help_texts = {
            "authorize_autopopulation": (
                "Please note, official complaints to local "
                "authorities must be submitted within six (6) "
                "months of the incident."
            ),
            "complaint_against": (
                "Include Name, Job Title, and School / Department "
                "if relevant."
            ),
            "concerns_addressed_to": "Please provide a name.",
            "complainant_address": (
                "Please include full address and apartment number. "
                "This is required for submitting the formal "
                "complaint."
            ),
        }

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

    # Everything the reporter only sees after authorizing the formal
    # complaint. Without authorization these fields are hidden, so
    # they must neither block submission nor be saved.
    DETAIL_FIELDS = [
        "complaint_against",
        "individuals_involved",
        "witnesses",
        "discussed_with_principal_or_supervisor",
        "concerns_addressed_to",
        "concerns_addressed_date",
        "requested_remedy",
        "complainant_address",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # This form only exists on the CA K-12 path, where the doc
        # stars both yes/no questions.
        self.fields["previously_submitted_to_district"].required = True
        self.fields["previously_submitted_to_district"].error_messages[
            "required"
        ] = "Please answer yes or no."

        self.fields["authorize_autopopulation"].required = True
        self.fields["authorize_autopopulation"].error_messages[
            "required"
        ] = "Please answer yes or no."

    def clean(self):
        cleaned_data = super().clean()

        authorize = cleaned_data.get("authorize_autopopulation")

        # NullBooleanField ignores required=True; enforce both
        # yes/no radios here.
        for radio in (
            "previously_submitted_to_district",
            "authorize_autopopulation",
        ):
            if (
                radio not in self.errors
                and cleaned_data.get(radio) is None
            ):
                self.add_error(radio, "Please answer yes or no.")

        if authorize:
            required = {
                "complaint_against":
                    "Please identify who the complaint is against.",
                "individuals_involved":
                    "Please list the individuals involved.",
                "witnesses": (
                    "Please list any witnesses; if none, write "
                    "\"none\"."
                ),
                "discussed_with_principal_or_supervisor":
                    "Please answer yes or no.",
                "requested_remedy":
                    "Please describe the action you would like taken.",
                "complainant_address":
                    "Your address is required for a formal complaint.",
            }

            for field, message in required.items():
                # "No" (False) is a real answer; only missing/blank
                # values count as unanswered.
                if cleaned_data.get(field) in (None, ""):
                    self.add_error(
                        field,
                        message,
                    )

        else:
            for field in self.DETAIL_FIELDS:
                # A hidden field can carry a stale or invalid value
                # (e.g. a half-typed date before the reporter
                # answered "No"); drop its error and its value.
                self.errors.pop(field, None)

                model_field = (
                    self._meta.model._meta.get_field(field)
                )

                cleaned_data[field] = (
                    "" if not model_field.null else None
                )

        return cleaned_data


# ---------------------------------------------------------------------
# DEMOGRAPHICS + IMPACT
# ---------------------------------------------------------------------

class DemographicsImpactForm(forms.ModelForm):

    race_ethnicity = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    arab_palestinian_identity = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    targeted_identities = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    discrimination_experiences = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    wellbeing_impacts = OptionMultipleChoiceField(
        queryset=ReportOption.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    targeted_identities_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
    )

    discrimination_experiences_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
    )

    wellbeing_impacts_other = forms.CharField(
        required=False,
        max_length=500,
        label="If Other, please specify",
    )

    class Meta:
        model = AffectedPersonDemographics

        fields = [
            "gender",
            "gender_other",
            "religion",
            "religion_other",
        ]

        labels = {
            "gender": "What's your gender?",
            "gender_other": "Gender (other)",
            "religion": (
                "Which option below do you most identify with in "
                "regard to faith or religion?"
            ),
            "religion_other": "Faith or religion (other)",
        }

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

        # Doc-starred; both have "Prefer not to..." options.
        self.fields["gender"].required = True
        self.fields["gender"].error_messages["required"] = (
            "Please answer, or choose \"Prefer not to answer\"."
        )
        self.fields["religion"].required = True
        self.fields["religion"].error_messages["required"] = (
            "Please answer, or choose \"Prefer not to say\"."
        )

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

    def clean(self):
        cleaned_data = super().clean()

        # Doc-starred option questions; both lists carry a safe
        # catch-all ("None" / "Other or Prefer not to say").
        if (
            "race_ethnicity" not in self.errors
            and not cleaned_data.get("race_ethnicity")
        ):
            self.add_error(
                "race_ethnicity",
                "Please choose up to three, or \"Other or Prefer "
                "not to say\".",
            )

        if (
            "targeted_identities" not in self.errors
            and not cleaned_data.get("targeted_identities")
        ):
            self.add_error(
                "targeted_identities",
                "Please select at least one; \"None\" is an option.",
            )

        # The SWANA follow-up is starred and only applies when
        # SWANA/MENA is selected above.
        races = cleaned_data.get("race_ethnicity")

        if races is not None and races.filter(
            slug="swana_mena"
        ).exists():
            if (
                "arab_palestinian_identity" not in self.errors
                and not cleaned_data.get("arab_palestinian_identity")
            ):
                self.add_error(
                    "arab_palestinian_identity",
                    "Please answer the Arab or Palestinian identity "
                    "question (there is a \"don't identify\" option).",
                )

        return cleaned_data

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
                self.cleaned_data.get(
                    f"{field_name}_other",
                    "",
                ),
            )


# ---------------------------------------------------------------------
# FINAL QUESTIONS
# ---------------------------------------------------------------------

class FinalQuestionsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Doc-starred.
        self.fields["connection_change"].required = True
        self.fields["connection_change"].error_messages["required"] = (
            "Please answer the connection question."
        )

        # The signature is server-required (clean_* below); mark the
        # fields required so the asterisk convention shows it. The
        # messages match the clean_* ones the reporter already saw.
        self.fields["signature_name"].required = True
        self.fields["signature_name"].error_messages["required"] = (
            "Please provide your digital signature."
        )
        self.fields["signature_date"].required = True
        self.fields["signature_date"].error_messages["required"] = (
            "Please provide the signature date."
        )

        # Human verification, only when keys are configured so local
        # development without hCaptcha keys keeps working.
        if settings.HCAPTCHA_SITEKEY:
            self.fields["captcha"] = SafeHCaptchaField(
                label="Verify you are human",
            )

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

        labels = {
            "connection_change": (
                "Did the incident change your feeling of connection "
                "to your school or others in your school?"
            ),
            "other_identity_information": (
                "Is there anything else about your identity that "
                "you believe is relevant to the incident?"
            ),
            "additional_information": (
                "Is there anything else you would like to share?"
            ),
            "support_sought_elsewhere": (
                "Have you sought support from other organizations / "
                "institutions / attorneys?"
            ),
            "opt_out_of_followup": (
                "Check here to opt out of private follow-up "
                "questions or clarifications from the research team."
            ),
            "signature_name": "Name",
            "signature_date": "Date",
        }

        help_texts = {
            "other_identity_information": (
                "For example: Trans / gender-expansive, etc."
            ),
            "additional_information": "Optional!",
            "support_sought_elsewhere": "",
            # The label already says everything.
            "opt_out_of_followup": "",
        }

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
    """
    Where, if at all, the incident should be reported.

    By submitting the form, the reporter is already sharing the
    incident with AROC and IUAPR; the only AROC/IUAPR decision here
    is whether to anonymize (which opts out of follow-up). The other
    organizations are opt-in, each with its own anonymize choice.
    California reporters choose among K-12 Legal Defense and the
    local CAIR chapter; reporters in other states choose Palestine
    Legal. Saving only writes the organizations that apply to the
    report's state.

    Anonymize choices are nested under their organization in the
    template; an anonymize box without its organization selected is
    ignored rather than rejected, so nobody can accidentally opt
    themselves out of submitting.
    """

    submit_k12_legal = forms.BooleanField(
        required=False,
        label="K-12 Legal Defense",
        help_text=(
            "A trusted pro-Palestine organization that can pursue "
            "legal action."
        ),
    )

    anonymous_k12_legal = forms.BooleanField(
        required=False,
        label="Make anonymous (not seeking legal counsel)",
    )

    submit_cair = forms.BooleanField(
        required=False,
        label="Local CAIR Chapter",
    )

    anonymous_cair = forms.BooleanField(
        required=False,
        label="Make anonymous (not seeking legal counsel)",
    )

    submit_pal_legal = forms.BooleanField(
        required=False,
        label="Palestine Legal",
    )

    anonymous_pal_legal = forms.BooleanField(
        required=False,
        label="Make anonymous (not seeking legal counsel)",
    )

    aroc_anonymous = forms.BooleanField(
        required=False,
        label="Make anonymous (not seeking follow-up)",
    )

    ORGANIZATION_FIELDS = {
        # org slug -> (submit field or None for always, anonymous field)
        "k12_legal_defense": ("submit_k12_legal", "anonymous_k12_legal"),
        "cair": ("submit_cair", "anonymous_cair"),
        "palestine_legal": ("submit_pal_legal", "anonymous_pal_legal"),
        "aroc_iuapr": (None, "aroc_anonymous"),
    }

    # Which organizations apply, by report state.
    CA_ORG_SLUGS = {
        "k12_legal_defense", "cair", "palestine_legal", "aroc_iuapr",
    }
    NON_CA_ORG_SLUGS = {"palestine_legal", "aroc_iuapr"}

    def __init__(self, *args, report=None, **kwargs):
        super().__init__(*args, **kwargs)

        if report and report.pk:
            referrals = {
                referral.organization.slug: referral
                for referral in report.referrals.select_related(
                    "organization"
                )
            }

            for slug, (submit_field, anon_field) in (
                self.ORGANIZATION_FIELDS.items()
            ):
                referral = referrals.get(slug)

                if referral:
                    if submit_field:
                        self.fields[submit_field].initial = True

                    self.fields[anon_field].initial = (
                        referral.anonymous
                    )

    def save(self, report):
        # Only the organizations that apply to this report's state
        # are written; POST keys for the other state's organizations
        # are ignored.
        allowed = (
            self.CA_ORG_SLUGS
            if report.state == "CA"
            else self.NON_CA_ORG_SLUGS
        )

        organizations = {
            organization.slug: organization
            for organization in ReferralOrganization.objects.filter(
                slug__in=allowed,
            )
        }

        # Only this save's organizations: referral rows for other
        # organizations must survive a re-save.
        ReportReferral.objects.filter(
            report=report,
            organization__slug__in=allowed,
        ).delete()

        referrals = []

        for slug, (submit_field, anon_field) in (
            self.ORGANIZATION_FIELDS.items()
        ):
            if slug not in allowed:
                continue

            organization = organizations.get(slug)

            if organization is None:
                continue

            submitted = (
                True
                if submit_field is None
                else self.cleaned_data.get(submit_field, False)
            )

            if not submitted:
                continue

            referrals.append(
                ReportReferral(
                    report=report,
                    organization=organization,
                    submit=True,
                    anonymous=self.cleaned_data.get(
                        anon_field,
                        False,
                    ),
                )
            )

        ReportReferral.objects.bulk_create(referrals)

        # The questionnaire defines "Make anonymous (not seeking
        # follow-up)" on AROC/IUAPR as opting out of follow-up, so
        # keep the report flag in step. Never cleared here: the
        # reporter's explicit opt-out elsewhere must stand.
        if (
            self.cleaned_data.get("aroc_anonymous")
            and not report.opt_out_of_followup
        ):
            report.opt_out_of_followup = True
            report.save(
                update_fields=["opt_out_of_followup"]
            )


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