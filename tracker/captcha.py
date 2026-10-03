"""
In-house hCaptcha integration.

Replaces the django-hcaptcha package, which silently fell back to
hCaptcha's public TEST keys when settings were missing (fail-open)
and let transport errors escape as server errors. This field is
fail-closed: when it is on a form, nothing validates without a
confirmed success from hCaptcha's verify API.

Settings (both read from the environment in settings/base.py):
  HCAPTCHA_KEY     the site key rendered into the widget
  HCAPTCHA_SECRET  the secret used for server-side verification
"""

import http.client
import json
import urllib.error
import urllib.parse
import urllib.request

from django import forms
from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

VERIFY_URL = "https://api.hcaptcha.com/siteverify"

# Transport, protocol, and parse failures during verification.
# URLError is an OSError; IncompleteRead is an HTTPException.
_TRANSPORT_ERRORS = (OSError, http.client.HTTPException, ValueError)


class HCaptchaWidget(forms.Widget):
    """
    Renders the hCaptcha container div and the api.js loader. The
    hCaptcha script posts the solve token under the fixed name
    "h-captcha-response", independent of the form prefix.
    """

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(
            '<div class="h-captcha" data-sitekey="{key}"></div>\n'
            '<script src="https://js.hcaptcha.com/1/api.js"'
            " async defer></script>".format(
                key=escape(settings.HCAPTCHA_KEY),
            )
        )

    def value_from_datadict(self, data, files, name):
        return data.get("h-captcha-response", "")


class HCaptchaField(forms.Field):
    widget = HCaptchaWidget

    def __init__(self, *, remote_ip=None, **kwargs):
        kwargs.setdefault("label", "Verify you are human")
        # required=False so Django's own empty-value check does not
        # run first; validate() owns the whole decision and raises
        # its specific message for an empty token.
        kwargs.setdefault("required", False)
        super().__init__(**kwargs)
        self.remote_ip = remote_ip

    def validate(self, value):
        if not value:
            raise forms.ValidationError(
                "Please prove you are a human.",
                code="required",
            )

        payload = {
            "secret": settings.HCAPTCHA_SECRET,
            "response": value,
        }

        if self.remote_ip:
            payload["remoteip"] = self.remote_ip

        request = urllib.request.Request(
            VERIFY_URL,
            data=urllib.parse.urlencode(payload).encode(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                result = json.load(response)

            if not isinstance(result, dict):
                raise ValueError("non-object verify response")

        except _TRANSPORT_ERRORS as exc:
            # The reporter's entries survive; they just retry.
            raise forms.ValidationError(
                "We could not reach the verification service. "
                "Your answers are still here — please try "
                "submitting again in a moment.",
                code="error_hcaptcha",
            ) from exc

        if not result.get("success"):
            raise forms.ValidationError(
                "hCaptcha could not be verified.",
                code="invalid_hcaptcha",
            )
