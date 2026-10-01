from django.core.management.base import BaseCommand

from ...models import (
    ReportOption,
    ReferralOrganization,
)


class Command(BaseCommand):
    help = "Seed ReportOption and ReferralOrganization data."

    def handle(self, *args, **options):

        self.seed_report_options()
        self.seed_referral_organizations()

        self.stdout.write(
            self.style.SUCCESS(
                "Report options and referral organizations seeded successfully."
            )
        )

    def seed_report_options(self):

        options = {

            # =========================================================
            # FORMS OF RACISM
            # =========================================================
            #
            # Original questionnaire:
            # "Did the incident involve any of these forms of racism?"
            #
            ReportOption.Category.RACISM_TYPE: [

                (
                    "anti_arab_racism",
                    "Anti-Arab Racism",
                    False,
                ),

                (
                    "anti_muslim_hate",
                    "Anti-Muslim Hate",
                    False,
                ),

                (
                    "racism_or_islamophobia",
                    "Racism or Islamophobia",
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # LOCATION TYPE
            # =========================================================
            #
            # Original questionnaire:
            # "What kind of location did the incident take place at?"
            #
            ReportOption.Category.LOCATION_TYPE: [

                (
                    "university",
                    "University",
                    False,
                ),

                (
                    "place_of_worship",
                    "Place of Worship",
                    False,
                ),

                (
                    "school",
                    "School or school-related event or property",
                    False,
                ),

                (
                    "public_area",
                    "Public Area (street, park, etc.)",
                    False,
                ),

                (
                    "private_residence",
                    "Private Residence",
                    False,
                ),

                (
                    "healthcare",
                    "Healthcare system or setting",
                    False,
                ),

                (
                    "government_property",
                    "Government property, such as a court, etc.",
                    False,
                ),

                (
                    "transit",
                    "Transit",
                    False,
                ),

                (
                    "online",
                    "Online",
                    False,
                ),

                (
                    "business",
                    "Business",
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # INCIDENT TYPE
            # =========================================================
            #
            # Original questionnaire:
            # "What type of incident was it?"
            #
            ReportOption.Category.INCIDENT_TYPE: [

                (
                    "lost_job",
                    "Lost a job",
                    False,
                ),

                (
                    "course_cancelled",
                    "A course cancelled",
                    False,
                ),

                (
                    "event_cancelled",
                    "An event cancelled",
                    False,
                ),

                (
                    "disciplinary_action",
                    (
                        "Disciplinary action "
                        "(e.g. detention, suspension or expulsion)"
                    ),
                    False,
                ),

                (
                    "grade_penalty",
                    (
                        "Disciplined or docked a grade "
                        "for an assignment"
                    ),
                    False,
                ),

                (
                    "vandalism",
                    "Vandalism",
                    False,
                ),

                (
                    "physical_violence",
                    "Physical violence",
                    False,
                ),

                (
                    "sexual_violence_or_harassment",
                    "Sexual violence or harassment",
                    False,
                ),

                (
                    "censored_or_silenced",
                    (
                        "Told not to speak or to change my speech, "
                        "assignment or school-related project "
                        "(censored or silenced)"
                    ),
                    False,
                ),

                (
                    "group_repression",
                    (
                        "School group or extracurricular group faced "
                        "repression, shut-down, or double standard"
                    ),
                    False,
                ),

                (
                    "work_edited",
                    (
                        "Had my work edited to exclude "
                        "or reframe topics"
                    ),
                    False,
                ),

                (
                    "bullied_for_views",
                    "Bullied or put down for my views",
                    False,
                ),

                (
                    "identity_marker_removal",
                    (
                        "Told to remove some form of Palestinian "
                        "or Arab identity marker, such as a kuffiyeh, "
                        "a poster, a necklace or bracelet, etc."
                    ),
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # EDUCATIONAL IMPACTS
            # =========================================================
            #
            # Original questionnaire:
            # "What were the impacts of this incident on your
            # experience in school?"
            #
            ReportOption.Category.EDUCATIONAL_IMPACT: [

                (
                    "avoid_school_class_or_activity",
                    (
                        "Avoid school, class, or extracurricular "
                        "activity/club"
                    ),
                    False,
                ),

                (
                    "miss_school",
                    "Miss school",
                    False,
                ),

                (
                    "leave_class",
                    "Leave class",
                    False,
                ),

                (
                    "transfer_classes",
                    "Transfer classes",
                    False,
                ),

                (
                    "drop_activities",
                    "Drop activities",
                    False,
                ),

                (
                    "hide_identity",
                    "Hide identity",
                    False,
                ),

                (
                    "stop_discussing_palestine",
                    "Stop discussing Palestine",
                    False,
                ),

                (
                    "feel_unsafe",
                    "Feel unsafe",
                    False,
                ),

                (
                    "difficulty_concentrating",
                    "Difficulty concentrating",
                    False,
                ),

                (
                    "decline_in_grades",
                    "Decline in grades",
                    False,
                ),

                (
                    "counseling",
                    "Counseling",
                    False,
                ),

                (
                    "transfer_school_or_online",
                    (
                        "Transfer schools or moved "
                        "to online schooling"
                    ),
                    False,
                ),

                (
                    "unique_accommodations",
                    "Unique accommodations",
                    False,
                ),

                (
                    "moved_online_schooling",
                    "Moved to online schooling",
                    False,
                ),

                (
                    "suspension_or_punishment",
                    "Suspension or other punishment",
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # REASONS INCIDENT WAS NOT REPORTED
            # =========================================================
            #
            # Original questionnaire:
            # "If you did not report this incident before, can you
            # indicate your reason?"
            #
            ReportOption.Category.NONREPORT_REASON: [

                (
                    "fear_retaliation",
                    "Fear of punishment or retaliation",
                    False,
                ),

                (
                    "did_not_know_process",
                    (
                        "Did not know if there is a complaint "
                        "process or who to report to"
                    ),
                    False,
                ),

                (
                    "not_taken_seriously",
                    (
                        "My complaint would not be "
                        "taken seriously"
                    ),
                    False,
                ),

                (
                    "did_not_trust_person",
                    (
                        "Did not trust the person I would "
                        "need to speak to"
                    ),
                    False,
                ),

                (
                    "would_make_problem_worse",
                    "Would make the problem worse",
                    False,
                ),

                (
                    "impact_future_opportunities",
                    (
                        "Reporting would impact future "
                        "opportunities"
                    ),
                    False,
                ),

                (
                    "discouraged_by_others",
                    (
                        "My friends, family or colleagues "
                        "told me not to report"
                    ),
                    False,
                ),

                (
                    "would_not_be_believed",
                    "I would not be believed",
                    False,
                ),

                (
                    "previous_reporting_failed",
                    (
                        "Raising the problem before "
                        "did not go anywhere"
                    ),
                    False,
                ),

                (
                    "institution_does_not_recognize_apr",
                    (
                        "My human resources, DEI, or equity office "
                        "does not recognize anti-Palestinian racism"
                    ),
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # DISCRIMINATION / REPRESSION EXPERIENCES
            # =========================================================
            #
            # Original questionnaire:
            # "In this or other instances, did you experience any
            # of the following..."
            #
            ReportOption.Category.DISCRIMINATION_EXPERIENCE: [

                (
                    "verbal_harassment_or_threats",
                    "Verbal harassment or threats",
                    False,
                ),

                (
                    "refusal_of_service",
                    "Refusal of service",
                    False,
                ),

                (
                    "physical_assault",
                    "Physical assault",
                    False,
                ),

                (
                    "workplace_discrimination",
                    (
                        "Workplace discrimination, "
                        "hostility, or retaliation"
                    ),
                    False,
                ),

                (
                    "fear_of_speaking",
                    (
                        "Fear of speaking about an issue or topic, "
                        "including fear of repercussions "
                        "institutionally and interpersonally"
                    ),
                    False,
                ),

                (
                    "false_antisemitism_accusation",
                    "False accusation of anti-semitism",
                    False,
                ),

                (
                    "legal_system_abuse",
                    (
                        "Weaponization or abuse of the law or "
                        "legal system (civil and criminal case)"
                    ),
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # WELL-BEING / HEALTH IMPACTS
            # =========================================================
            #
            # Original questionnaire:
            # "Regarding your personal well-being and health,
            # what impacts did you experience..."
            #
            ReportOption.Category.WELLBEING_IMPACT: [

                (
                    "stress_anxiety",
                    "Stress or Anxiety",
                    False,
                ),

                (
                    "depression",
                    "Depression",
                    False,
                ),

                (
                    "withdrawal_isolation",
                    (
                        "Withdrawal/Isolation from "
                        "activities or people"
                    ),
                    False,
                ),

                (
                    "hypervigilance_fearfulness",
                    "Hypervigilance or fearfulness",
                    False,
                ),

                (
                    "physical_pain",
                    "Physical pain",
                    False,
                ),

                (
                    "worsening_health_conditions",
                    "Worsening of other health conditions",
                    False,
                ),

                (
                    "headaches",
                    "Headaches",
                    False,
                ),

                (
                    "loss_of_appetite",
                    "Loss of appetite",
                    False,
                ),

                (
                    "loss_of_relationships",
                    "Loss of relationships",
                    False,
                ),

                (
                    "self_censorship",
                    (
                        "Self-censorship or feeling "
                        "intimidated"
                    ),
                    False,
                ),

                (
                    "insomnia",
                    "Insomnia",
                    False,
                ),

                (
                    "low_self_esteem",
                    "Low-self esteem or self-doubt",
                    False,
                ),

                (
                    "lost_employment_or_career",
                    (
                        "Loss of employment or "
                        "career opportunity"
                    ),
                    False,
                ),

                (
                    "doxxing",
                    "Doxxing",
                    False,
                ),

                (
                    "missing_school",
                    "Missing school",
                    False,
                ),

                (
                    "none",
                    "None of these",
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),
            ],


            # =========================================================
            # TARGETED IDENTITIES
            # =========================================================
            #
            # Original questionnaire:
            # "What aspects of your identity do you believe may have
            # been targeted in this incident?"
            #
            ReportOption.Category.TARGETED_IDENTITY: [

                (
                    "ancestry_nationality_origin",
                    (
                        "Ancestry / Nationality "
                        "or National Origin"
                    ),
                    False,
                ),

                (
                    "ethnicity",
                    "Ethnicity (Culture)",
                    False,
                ),

                (
                    "immigration_status",
                    "Immigration Status",
                    False,
                ),

                (
                    "language",
                    "Language",
                    False,
                ),

                (
                    "race_color",
                    "Race / Color",
                    False,
                ),

                (
                    "religion",
                    "Religion",
                    False,
                ),

                (
                    "sexuality",
                    "Sexuality",
                    False,
                ),

                (
                    "sex_gender_identity",
                    (
                        "Sex, Gender or Gender "
                        "Expression / Identity"
                    ),
                    False,
                ),

                (
                    "support_of_palestine",
                    "Support of Palestine",
                    False,
                ),

                (
                    "pregnancy_childbirth_lactation",
                    (
                        "Pregnancy, Childbirth, False Pregnancy, "
                        "or Lactation"
                    ),
                    False,
                ),

                (
                    "disability_medical_condition",
                    "Disability or Medical Condition",
                    False,
                ),

                (
                    "age",
                    "Age",
                    False,
                ),

                (
                    "association",
                    (
                        "Association with a person or group listed "
                        "here, whether perceived or actual"
                    ),
                    False,
                ),

                (
                    "other",
                    "Other",
                    True,
                ),

                (
                    "none",
                    "None",
                    False,
                ),
            ],


            # =========================================================
            # RACE / ETHNICITY
            # =========================================================
            #
            # Original questionnaire:
            # "What is your race and/or ethnicity?
            # Choose up to three..."
            #
            ReportOption.Category.RACE_ETHNICITY: [

                (
                    "black_african_american",
                    "Black or African American",
                    False,
                ),

                (
                    "white",
                    "White",
                    False,
                ),

                (
                    "asian_asian_american",
                    "Asian or Asian American",
                    False,
                ),

                (
                    "native_american_alaska_native",
                    "Native American or Alaska Native",
                    False,
                ),

                (
                    "native_hawaiian_pacific_islander",
                    "Native Hawaiian or Pacific Islander",
                    False,
                ),

                (
                    "hispanic_latino",
                    "Hispanic / Latino",
                    False,
                ),

                (
                    "swana_mena",
                    (
                        "Southwest Asian, Arab, Middle Eastern, "
                        "or North African"
                    ),
                    False,
                ),

                (
                    "other_or_prefer_not",
                    "Other or Prefer not to say",
                    False,
                ),
            ],


            # =========================================================
            # ARAB / PALESTINIAN IDENTITY
            # =========================================================
            #
            # Asked if SWANA/MENA is selected.
            #
            ReportOption.Category.ARAB_PALESTINIAN_IDENTITY: [

                (
                    "palestinian",
                    "Palestinian",
                    False,
                ),

                (
                    "other_arab",
                    "Other Arab",
                    False,
                ),

                (
                    "perceived_as_arab_or_palestinian",
                    (
                        "Don't identify, but I am sometimes "
                        "perceived as such."
                    ),
                    False,
                ),

                (
                    "not_arab_or_palestinian",
                    (
                        "Don't identify as Palestinian or Arab / "
                        "no known ancestry"
                    ),
                    False,
                ),
            ],
        }

        created_count = 0
        updated_count = 0

        for category, category_options in options.items():

            for sort_order, option_data in enumerate(
                category_options,
                start=1,
            ):
                slug, label, allows_other_text = option_data

                obj, created = ReportOption.objects.update_or_create(
                    category=category,
                    slug=slug,
                    defaults={
                        "label": label,
                        "sort_order": sort_order * 10,
                        "allows_other_text": allows_other_text,
                        "is_active": True,
                    },
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            f"ReportOption: "
            f"{created_count} created, "
            f"{updated_count} updated."
        )

    def seed_referral_organizations(self):

        organizations = [

            (
                "k12_legal_defense",
                "K-12 Legal Defense",
                (
                    "A trusted pro-Palestine organization "
                    "that can pursue legal action."
                ),
                True,
            ),

            # The 9.21 question lists three choices; PalLegal is
            # named in the intro text only. Kept for data continuity
            # on existing referrals, but not offered.
            (
                "palestine_legal",
                "Palestine Legal",
                "",
                False,
            ),

            (
                "cair",
                "Local CAIR Chapter",
                "",
                True,
            ),

            (
                "aroc_iuapr",
                "AROC / IUAPR",
                "",
                True,
            ),
        ]

        created_count = 0
        updated_count = 0

        for sort_order, (
            slug,
            name,
            description,
            is_active,
        ) in enumerate(
            organizations,
            start=1,
        ):

            obj, created = (
                ReferralOrganization.objects.update_or_create(
                    slug=slug,
                    defaults={
                        "name": name,
                        "description": description,
                        "sort_order": sort_order * 10,
                        "is_active": is_active,
                    },
                )
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            f"ReferralOrganization: "
            f"{created_count} created, "
            f"{updated_count} updated."
        )