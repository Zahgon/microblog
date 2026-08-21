"""Base form class.

Flask-WTF is replaced by WTForms itself. This base class adds the few
conveniences that were used from Flask-WTF: forms populated from the request,
``validate_on_submit()``, the ``hidden_tag()`` template helper, and CSRF
protection backed by the session.
"""
import os
from datetime import timedelta

import wtforms
from babel.support import Translations
from markupsafe import Markup
from wtforms import Form
from wtforms.csrf.session import SessionCSRF
from wtforms.meta import DefaultMeta
from wtforms.validators import ValidationError
from wtforms.widgets import HiddenInput

from app.context import get_request, get_session
from app.i18n import get_locale
from app.state import state

SUBMIT_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}

WTFORMS_TRANSLATION_DIRECTORY = os.path.join(
    os.path.dirname(os.path.abspath(wtforms.__file__)), 'locale')

_translations_cache = {}


def get_wtforms_translations():
    """Load the catalog that WTForms ships for the locale of the request.

    Flask-WTF used to connect the built in messages of WTForms, such as "This
    field is required.", to the translations of the application. Without this
    they would always be rendered in English.
    """
    locale = get_locale()
    key = str(locale)
    translations = _translations_cache.get(key)
    if translations is None:
        translations = Translations.load(WTFORMS_TRANSLATION_DIRECTORY,
                                         [locale], 'wtforms')
        _translations_cache[key] = translations
    return translations


class SessionCSRFTokens(SessionCSRF):
    """Session CSRF tokens that fail validation instead of raising."""

    def validate_csrf_token(self, form, field):
        if 'csrf' not in self.session:
            raise ValidationError(field.gettext('CSRF token missing.'))
        return super().validate_csrf_token(form, field)


class FormMeta(DefaultMeta):
    csrf = True
    csrf_class = SessionCSRFTokens
    csrf_time_limit = timedelta(minutes=30)

    @property
    def csrf_secret(self):
        secret_key = state.config.get('SECRET_KEY') or ''
        return secret_key.encode('utf-8') if isinstance(secret_key, str) \
            else secret_key

    @property
    def csrf_context(self):
        return get_session()

    def get_translations(self, form):
        return get_wtforms_translations()


class BaseForm(Form):
    """The base class of every form of the application."""

    Meta = FormMeta

    def __init__(self, *args, **kwargs):
        self._request = kwargs.pop('request', None) or get_request()
        super().__init__(*args, **kwargs)

    @classmethod
    async def from_formdata(cls, request=None, *args, **kwargs):
        """Create a form, filled with the data submitted with the request."""
        request = request or get_request()
        if 'formdata' not in kwargs and request is not None and \
                request.method in SUBMIT_METHODS:
            kwargs['formdata'] = await request.form()
        return cls(*args, request=request, **kwargs)

    def is_submitted(self):
        request = self._request
        return request is not None and request.method in SUBMIT_METHODS

    def validate_on_submit(self, extra_validators=None):
        return self.is_submitted() and self.validate(
            extra_validators=extra_validators)

    def hidden_tag(self, *fields):
        """Render the hidden fields of the form, the CSRF token included."""
        if not fields:
            fields = [field for field in self
                      if isinstance(field.widget, HiddenInput)]
        else:
            fields = [self[field] if isinstance(field, str) else field
                      for field in fields]
        return Markup('<div style="display:none;">{}</div>'.format(
            ''.join(str(field()) for field in fields)))
