# Data access model (pilot)

Goal, per the team's requirement: when a reporter opts out of
follow-up (chooses anonymity / no follow-up), nobody working with
the data sees their identifying information linked to their
responses.

## Roles

Run `python manage.py setup_access_groups` once after deploy
(idempotent), then put staff accounts in the right group in the
Django admin.

| Group | Surface | What they see |
|---|---|---|
| Data coordinators | "De-identified reports" admin | Every report's responses, with NO direct identifiers for any report (whether or not the reporter opted out). Read-only. |
| Follow-up staff | "Incident reports" admin | The full record — but only for reporters who consented to follow-up. Opted-out reports do not appear at all. Every record view is logged. |
| Superusers | Everything, plus the PII access log | Site administration. |

## What counts as opted out

`opt_out_of_followup` is true, or the AROC/IUAPR referral row is
marked anonymous. Defined once in `tracker.models.deidentified_q`.

## Direct identifiers (never on the coordinator surface)

Defined once in `tracker.models.DIRECT_IDENTIFIER_FIELDS`:
reporter name, email, phone, signature; affected person's name;
child's name and date of birth; principal and named school
contacts; who the complaint is against, individuals involved,
witnesses; the complainant's address; uploaded attachments.

The coordinator detail page is built from an explicit whitelist
plus composed summaries, with an import-time check that the
whitelist and the identifier list never overlap — not a hide/show
toggle on the full record.

## What is logged

Every full-record detail view writes a `PIIAccessLog` row (who,
when, which report). Superusers can read the log in the admin;
nobody can edit or delete it from the admin.

## Consent recorded per record

Each report row carries `has_consented`, `opt_out_of_followup`,
and per-organization referral rows with their anonymous flags.

## Known pilot limits (next phase)

1. The opted-out rows still exist in the database; a true separate
   scrubbed table (the slides' "Anonymized Block Record") with the
   PII physically removed is the next step.
2. Quasi-identifiers (school, district, grade, role, city, named
   recourse) are still visible to coordinators; generalization
   rules need a team decision.
3. Open-text answers (description, remedy, responses) are shown
   unscrubbed and can contain names — the automated PII scrubber
   from the plan is not built yet.
4. Time-bound retention (deleting PII after a year, per the
   information sheet) is not automated yet.
5. Database-level access (Heroku dataclips, psql) bypasses all of
   this; limit DB credentials accordingly.
