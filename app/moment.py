"""Rendering of timestamps with moment.js, a port of the Flask-Moment helper.

The ``moment`` object is exposed to the templates, where timestamps are
rendered inside a hidden span that the accompanying JavaScript formats on the
browser, in the local time zone of the visitor.
"""
from markupsafe import Markup

default_moment_version = '2.29.4'
default_moment_sri = ('sha512-42PE0rd+wZ2hNXftlM78BSehIGzezNeQuzihiBCvUEB3CVx'
                      'HvsShF86wBWwQORNxNINlBPuq7rG4WWhNiTVHFg==')


class moment:
    """Render a timestamp with moment.js."""

    @staticmethod
    def include_moment(version=default_moment_version, local_js=None,
                       no_js=None, sri=None):
        js = ''
        if not no_js:
            if local_js is not None:
                if not sri:
                    js = f'<script src="{local_js}"></script>\n'
                else:
                    js = (f'<script src="{local_js}" integrity="{sri}" '
                          'crossorigin="anonymous"></script>\n')
            elif version is not None:
                js_filename = 'moment-with-locales.min.js'
                if not sri and version == default_moment_version:
                    sri = default_moment_sri
                url = ('https://cdnjs.cloudflare.com/ajax/libs/moment.js/'
                       f'{version}/{js_filename}')
                if sri:
                    js = (f'<script src="{url}" integrity="{sri}" '
                          'crossorigin="anonymous"></script>\n')
                else:
                    js = f'<script src="{url}"></script>\n'
        return Markup(js + '''<script>
function moment_render(elem) {
  const timestamp = moment(elem.dataset.timestamp);
  const func = elem.dataset.function;
  const format = elem.dataset.format;
  const timestamp2 = elem.dataset.timestamp2;
  const no_suffix = elem.dataset.nosuffix;
  const units = elem.dataset.units;
  let args = [];
  if (format) args.push(format);
  if (timestamp2) args.push(moment(timestamp2));
  if (no_suffix) args.push(no_suffix);
  if (units) args.push(units);
  elem.textContent = timestamp[func].apply(timestamp, args);
  elem.style.display = "";
}
function moment_render_all() {
  const moments = document.querySelectorAll(".dynamic-moment");
  moments.forEach(function(moment) {
    moment_render(moment);
    const refresh = moment.dataset.refresh;
    if (refresh && refresh > 0) {
      (function(elem, interval) {
        setInterval(function() { moment_render(elem); }, interval);
      })(moment, refresh);
    }
  });
}
document.addEventListener("DOMContentLoaded", moment_render_all);
</script>''')

    @staticmethod
    def locale(language='en', auto_detect=False, customization=None):
        if auto_detect:
            return Markup('<script>\nvar locale = '
                          'window.navigator.userLanguage || '
                          'window.navigator.language;\n'
                          'moment.locale(locale);\nmoment_render_all();\n'
                          '</script>')
        if customization is not None:
            return Markup(f'<script>\nmoment.locale("{language}", '
                          f'{customization});\nmoment_render_all();\n'
                          '</script>')
        return Markup(f'<script>\nmoment.locale("{language}");\n'
                      'moment_render_all();\n</script>')

    lang = locale

    def __init__(self, timestamp=None, local=False):
        if timestamp is None:
            timestamp = self._timestamp_as_iso_8601(self._now())
        self.timestamp = timestamp
        self.local = local

    @staticmethod
    def _now():
        from datetime import datetime, timezone
        return datetime.now(timezone.utc)

    @staticmethod
    def _timestamp_as_iso_8601(timestamp):
        return timestamp.strftime('%Y-%m-%dT%H:%M:%SZ')

    def _render(self, func, format=None, timestamp2=None, no_suffix=None,
                units=None, refresh=False):
        timestamp = self.timestamp
        if not isinstance(timestamp, str):
            timestamp = self._timestamp_as_iso_8601(timestamp)
        attributes = f'data-function="{func}"'
        if format:
            attributes += f' data-format="{format}"'
        if timestamp2:
            attributes += f' data-timestamp2="{timestamp2}"'
        if no_suffix:
            attributes += f' data-nosuffix="{int(no_suffix)}"'
        if units:
            attributes += f' data-units="{units}"'
        return Markup(f'<span class="dynamic-moment" '
                      f'data-timestamp="{timestamp}" {attributes} '
                      f'data-refresh="{int(refresh) * 60000}" '
                      f'style="display: none">{timestamp}</span>')

    def format(self, fmt=None, refresh=False):
        return self._render('format', format=(fmt or ''), refresh=refresh)

    def fromNow(self, no_suffix=False, refresh=False):
        return self._render('fromNow', no_suffix=int(no_suffix),
                            refresh=refresh)

    def fromTime(self, timestamp, no_suffix=False, refresh=False):
        return self._render(
            'from', timestamp2=self._timestamp_as_iso_8601(timestamp),
            no_suffix=int(no_suffix), refresh=refresh)

    def calendar(self, refresh=False):
        return self._render('calendar', refresh=refresh)

    def valueOf(self, refresh=False):
        return self._render('valueOf', refresh=refresh)

    def unix(self, refresh=False):
        return self._render('unix', refresh=refresh)
