# Ground Truth — Flask → FastAPI Migration of Microblog

Derived from `golden_patch.diff` (the reference solution) and confirmed empirically by running
both frameworks side by side.

- **Base repo:** `miguelgrinberg/microblog` @ `a975ef6`
- **Task:** port the application from Flask 3.0.0 to FastAPI, preserving observable behaviour
- **Reference solution:** `golden_patch.diff` — 48 file entries, 14 new / 1 deleted / 1 renamed / 32 modified, +1712 / −367 lines
- **Verification:** `verification/run_all.py` — three suites, one gate; current result `COMPLETE`

Obligations are written so a verifier can check a candidate migration without requiring it to be
textually identical to the golden patch. `MUST` items are load-bearing; `SHOULD` items the golden
patch satisfies but a different-but-correct solution may achieve another way.

---

## Definition of done

The task is complete only when **all three** test suites in §6 pass. They cover disjoint ground; no
one of them substitutes for another. All three are implemented in `verification/`; run them with
`python3 verification/run_all.py`, which exits non-zero unless every one passes.

| Suite | What it proves | Command | Reference result |
|---|---|---|---|
| **§6.1 Test cases** | The port imports, wires up, and the domain logic survived | `suite_cases.py` | **PASS** — 4/4 on both trees |
| **§6.2 Behaviour tests** | Wire-level parity with the Flask baseline | `suite_behaviour.py` | **PASS** — 97/98 functional, 99.2% similarity, 0 unexplained |
| **§6.3 Coverage tests** | The verification actually reaches the migrated code | `suite_coverage.py` | **PASS** — 27/27 gates |

`python -m unittest tests.py` alone is **not** a sufficient gate for this migration. The in-repo
suite issues **zero HTTP requests** — it constructs the app, then talks to the models directly. So
the fourteen shim modules that *are* the migration (request context, session, login, forms, CSRF,
`url_for`, i18n, moment, lenient params) pass it whether or not they work: measured on its own it
leaves them at **43.8%** line coverage, with `url_for`, `login_user`, `logout_user`, `flash`,
`validate_on_submit`, `hidden_tag`, `paginate`, `first_or_404`, `select_locale`, `gettext` and the
whole of `RequestContextMiddleware` never executed. §6.2 is what reaches them; §6.3 is what proves
it did.

**Current status of the golden patch: 3 of 3 suites pass — `RESULT: COMPLETE`.**

It did not, at first. §6.2 failed on the one difference the 98 HTTP cases could never see:
`app/moment.py` shipped a subresource-integrity hash that did not match the moment.js build its own
`src` pointed at, on a tag that `base.html` puts on every page. A browser enforcing SRI would have
refused to execute moment.js and every timestamp in the application would have stayed hidden. The
patch now carries the correct hash; §5.2 records the finding, because a verifier grading candidate
migrations needs to know it is a thing that happens.

---

## 0. Task framing

The base repo is a mature Flask application that leans on ten Flask extensions. A correct migration
cannot simply swap the web layer: each extension's contribution has to be re-provided, because the
models, routes and templates all depend on the abstractions those extensions install
(`current_user`, `url_for`, `g`, `db.session`, `_()`, `moment`, CSRF-protected forms).

The reference solution's strategy is **compatibility shims**: fourteen new modules under `app/`
re-implement the extension surface that the rest of the code already uses, so `app/models.py`,
`app/main/routes.py`, `app/auth/routes.py` and all 20 templates change only marginally.
A candidate is free to choose a different strategy, provided §3 (behavioural contract) holds.

---

## 1. Structural obligations

### 1.1 Files that MUST NOT survive

| Path | Reason |
|---|---|
| `.flaskenv` | Flask-CLI-only configuration; no Flask CLI after migration |
| `migrations/alembic.ini` | Moves to the project root (see 1.2) |

### 1.2 File that MUST move

| From | To | Reason |
|---|---|---|
| `migrations/alembic.ini` | `alembic.ini` | Alembic is invoked directly instead of through Flask-Migrate, so its config must sit where the `alembic` CLI looks for it |

### 1.3 Modules the reference solution adds

Fourteen new modules under `app/`. A candidate MUST provide the *capability* of each; the file
layout is advisory.

| Module | Replaces | Capability that MUST exist |
|---|---|---|
| `app/state.py` | `current_app` | A process-wide container for config, Elasticsearch client, Redis connection, task queue, logger |
| `app/db.py` | Flask-SQLAlchemy | Declarative base, per-request scoped session, `paginate()`, `first_or_404()`, `get_or_404()`, `create_all()`, `drop_all()` |
| `app/context.py` | `request`, `g`, `session`, `flash` | Per-request context variables plus flash storage and retrieval |
| `app/middleware.py` | Flask request context + `before_request` | Per-request setup/teardown of request, `g`, DB session scope, locale, current user; unhandled-error hook |
| `app/login.py` | Flask-Login | `current_user` proxy, `UserMixin`, `AnonymousUser`, `login_user()`, `logout_user()`, user loader, login-required guard |
| `app/session.py` | Flask's signed cookie session | Signed cookie session with per-session lifetime (required for "remember me") |
| `app/forms.py` | Flask-WTF | Base form with request-populated data, `validate_on_submit()`, `hidden_tag()`, session-backed CSRF |
| `app/i18n.py` | Flask-Babel | `Accept-Language` negotiation, `gettext`, `ngettext`, `lazy_gettext`, current-locale accessor |
| `app/templating.py` | `render_template` | Jinja environment carrying the globals in §2.3 |
| `app/urls.py` | `url_for` | Endpoint-name → URL builder supporting `_external` and `_anchor` |
| `app/responses.py` | `redirect` | Redirect response helper |
| `app/security.py` | `werkzeug.security` | `generate_password_hash` / `check_password_hash`, format-compatible with Werkzeug |
| `app/moment.py` | Flask-Moment | `include_moment()`, `locale()`/`lang()`, and the timestamp render helpers used by templates |
| `app/params.py` | `request.args.get(..., type=int)` | Lenient query-parameter coercion (see 3.4) |

### 1.4 Dependency swap

`requirements.txt` MUST drop every Flask-stack pin:

```
Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, flask-babel,
Flask-Mail, Flask-Migrate, Flask-Moment, Flask-HTTPAuth, Werkzeug
```

and MUST add an ASGI stack. The reference adds:

```
fastapi==0.128.8   starlette==0.49.3   uvicorn==0.39.0
pydantic==2.13.4   pydantic_core==2.46.4
python-multipart==0.0.20   itsdangerous==2.2.0
WTForms==3.2.1     Babel==2.18.0
```

`python-multipart` is **not optional** — form posts fail without it.
`itsdangerous` is **not optional** — it signs the session cookie.

### 1.5 Entrypoint and operational files

| File | Obligation |
|---|---|
| `microblog.py` | MUST expose an ASGI `app`. The Flask `shell_context_processor` has no FastAPI equivalent and MUST be relocated (reference: an `app.cli shell` command) |
| `app/cli.py` | MUST become a standalone Click app (`python -m app.cli`), since `@bp.cli` disappears with Flask. MUST keep `translate init/update/compile` |
| `boot.sh` | `flask db upgrade` → `alembic upgrade head`; gunicorn MUST run an ASGI worker |
| `Procfile` | same two substitutions |
| `Dockerfile` | MUST drop `ENV FLASK_APP`, copy `alembic.ini`, and compile translations without the Flask CLI |
| `deployment/supervisor/microblog.conf` | gunicorn MUST run an ASGI worker |
| `migrations/env.py` | MUST NOT import `flask`. Reads the URL from `config.Config` and the metadata from the declarative base; MUST preserve SQLite batch mode that Flask-Migrate configured automatically |

---

## 2. Preservation obligations

These are the things the migration MUST **not** change. They are what keeps the diff small.

### 2.1 Database schema — exact

The five models (`User`, `Post`, `Message`, `Notification`, `Task`) and the `followers`
association table MUST keep identical columns, types, nullability, indexes, unique constraints
and foreign keys. All nine Alembic revisions MUST remain unmodified and MUST apply forward and
backward.

**Verifier check:** `alembic upgrade head && alembic check` must report
`No new upgrade operations detected.`

### 2.2 Endpoint names — exact

`url_for` is called with `blueprint.view` names from templates and from `app/models.py`. Those
names MUST survive, or every template breaks. The 26 required names:

```
main.index          main.explore        main.user            main.user_popup
main.edit_profile   main.follow         main.unfollow        main.translate_text
main.search         main.send_message   main.messages        main.export_posts
main.notifications
auth.login          auth.logout         auth.register
auth.reset_password auth.reset_password_request
api.get_user        api.get_users       api.get_followers    api.get_following
api.create_user     api.update_user     api.get_token        api.revoke_token
static
```

URL paths MUST also be preserved, with Flask's `<converter:name>` rewritten to the target's
syntax (`/user/<username>` → `/user/{username}`, `/api/users/<int:id>` → `/api/users/{id}`).

### 2.3 Templates — near-frozen

All 20 templates MUST work unmodified except for framework-specific identifiers. The golden patch
changes exactly **one** template, `app/templates/base.html`, in exactly **two** places:

1. `url_for('static', filename=...)` → `url_for('static', path=...)`
2. `flask_moment_render_all()` → the equivalent function in the moment replacement

This is only possible if the Jinja environment provides these globals:

```
url_for   get_flashed_messages   current_user   g   moment   config   get_locale
_   gettext   ngettext
```

`_post.html` interpolates HTML into translated strings, so the gettext callables MUST be installed
**newstyle** (returning `Markup` under autoescape) or that template renders escaped markup.

`base.html` calls `moment.include_moment()` with no arguments, so whatever that emits ships on
every page. If it carries a `integrity="..."` attribute, the hash MUST match the file the `src`
points at — a browser that enforces SRI silently refuses to execute a script whose hash is wrong,
and every timestamp in the application then stays hidden behind its `display: none`.

**Verifier check:** the `src` and `integrity` pair MUST equal Flask-Moment's for the same
moment.js version (BT-17).

### 2.4 Password hashes — binary compatible

Existing rows MUST keep working. The replacement MUST reproduce Werkzeug's
`method$salt$hash` format and its parsing, including:

- `method.split(':')` semantics, so a bare `pbkdf2` method falls back to `sha256` / 600000
- `scrypt` default parameters `32768:8:1`, `dklen=64`
- the argument-count rules: `pbkdf2` with more than two parameters MUST raise `ValueError`
- `salt_length=0` MUST raise `ValueError`; an unknown method MUST raise `ValueError`
- `check_password_hash` MUST return `False` on a hash with fewer than two `$` separators

Werkzeug additionally *raises* `ValueError` from `check_password_hash` when the separators are
present but the method is unparseable (`bogus$salt$hash`). Returning `False` there instead is a
tolerated deviation — see §4 row 10 — because the application only ever checks hashes it wrote.

**Verifier check:** a hash produced by `werkzeug.security.generate_password_hash` must validate
against the candidate's `check_password_hash`, and vice versa.

### 2.5 Search indexing hooks

`SearchableMixin` binds to SQLAlchemy `before_commit` / `after_commit` on the session. Flask-SQLAlchemy
exposed these via `db.event`; the migration MUST rebind them to plain `sqlalchemy.event` on the
new session and they MUST still fire on insert, update and delete.

### 2.6 Translations

`app/translations/es/LC_MESSAGES/messages.po` MUST be unchanged. Every message id used by the
application MUST still resolve, including WTForms' own built-in validator messages.

### 2.7 Test suite — same four tests

`tests.py` MUST keep the four tests of §6.1 with the same names and the same assertions. Only the
fixture may change: `create_app()` no longer pushes an application context, so `setUp` acquires a
DB session scope explicitly and `tearDown` releases it. Deleting, renaming, `@skip`-ing or
weakening any of the four is a failed migration, not a simplification.

A candidate MAY **add** tests, and §6.3 requires it to.

---

## 3. Behavioural contract

Established empirically: 98 test cases run against both the live Flask app and the live FastAPI app.

### 3.1 Hard invariants

| Dimension | Requirement | Reference result |
|---|---|---|
| HTTP status codes | Identical on every case | 98 / 98 |
| Flash message text | Identical, English and Spanish | 98 / 98 |
| Redirect `Location` | Identical up to the `/index` ≡ `/` alias | 98 / 98 |
| Form field errors | Identical | 97 / 98 |
| Response body | ≥ 98% similar after masking volatile values | 96 / 98 exact |

### 3.2 Authentication and session

- Anonymous access to a protected page MUST redirect to `auth.login` with a `next` query parameter and MUST flash the login-required message.
- "Remember me" MUST set a persistent cookie (`Max-Age`); without it the cookie MUST be a browser-session cookie.
- Session cookie MUST be signed, `HttpOnly` and `SameSite`.
- CSRF MUST be enforced on all form posts; a missing token MUST render the form with a field error, not raise.
- API token auth (`Bearer`) and basic auth MUST both work; a revoked token MUST yield `401`.

### 3.3 Error handling

| Condition | Required response |
|---|---|
| 404, client prefers HTML | `errors/404.html`, status 404 |
| 404, client prefers JSON, or path under `/api` | `{"error": "Not Found"}`, status 404 |
| Unhandled exception | DB session rolled back; `errors/500.html` or `{"error": "Internal Server Error"}`; the app MUST still serve the next request |
| API errors | MUST keep the `{"error": ..., "message": ...}` shape, not the framework's native error body |

### 3.4 Query parameters MUST be lenient

Flask's `request.args.get(name, default, type=int)` silently returns the default when the value
will not parse. A naive port to typed FastAPI parameters changes this into a `422` JSON body
served to a browser. The migration MUST preserve the lenient behaviour for:

- `page` on `main.index`, `main.explore`, `main.user`, `main.messages`, `main.search`
- `page` and `per_page` on `api.get_users`, `api.get_followers`, `api.get_following`
- `since` on `main.notifications`

**Verifier check:** `GET /explore?page=abc` must return `200 text/html`, not `422`.
`per_page` must still be capped at 100 *after* the fallback.

### 3.5 Internationalisation

Locale is selected from `Accept-Language` against `config['LANGUAGES']`. Both the application's own
strings **and** WTForms' built-in validator messages MUST translate. The latter requires wiring
WTForms' shipped catalogues, which Flask-WTF did automatically and a plain WTForms port does not.

**Verifier check:** with `Accept-Language: es`, submitting an empty required field must yield
`Este campo es obligatorio.`, not `This field is required.`

### 3.6 Background jobs and mail

- `export_posts` MUST run under an RQ worker outside any request, report progress, write the notification, mark the task complete and send mail with `posts.json` attached.
- Password-reset mail MUST build an **external** URL with no request in scope (falls back to `SERVER_NAME`).
- Mail MUST still be sent on a background thread unless `sync=True`.

### 3.7 Request isolation

Flask's thread-local request context is gone. Whatever replaces it MUST NOT leak the current user,
`g`, the locale or the DB session between concurrent requests.

**Verifier check:** drive ≥ 100 overlapping requests across ≥ 4 distinct logged-in sessions and
assert every response renders its own user.

---

## 4. Accepted deviations

These differ from Flask and are **not** defects. A verifier MUST NOT penalise them.
Elsewhere in this document, `§4.n` refers to row `n` of this table.

| # | Deviation | Rationale |
|---|---|---|
| 1 | `url_for('main.index')` → `/` instead of `/index` | Both routes are registered and serve the same page; Werkzeug and Starlette just pick different rules |
| 2 | `hidden_tag()` wraps fields in `<div style="display:none;">` | Invisible; Flask-WTF's own markup varies by version |
| 3 | moment.js class `flask-moment` → `dynamic-moment`, vendored JS rewritten | Self-consistent with the replacement's own JS |
| 4 | `405` returns plain text instead of Werkzeug's HTML page | The app never templated 405 |
| 5 | CSRF wording *"The CSRF token is missing."* → *"CSRF token missing."* | WTForms' string rather than Flask-WTF's |
| 6 | Redirects carry no body; `204` content-type is `application/json` | Neither is part of the redirect/no-content contract |
| 7 | `/docs`, `/openapi.json` now exist; duplicate-operation-id warnings at startup | FastAPI default; routes deliberately share names |
| 8 | Password hashing falls back to pbkdf2 where `hashlib.scrypt` is unavailable | Werkzeug 3.0.1 raises instead; the fallback stays Werkzeug-readable |
| 9 | `?page=` with a value exceeding SQLite's integer range returns 500 | **Pre-existing.** The Flask original fails identically; it degrades to the styled 500 page |
| 10 | `check_password_hash('bogus$salt$hash', pw)` returns `False`; Werkzeug raises `ValueError` | Strictly more robust, and unreachable in this application, which only checks hashes it wrote |
| 11 | `generate_password_hash(pw, method='scrypt')` raises `NotImplementedError` where Werkzeug 3.0.1 lets an `AttributeError` escape | Only on an interpreter without `hashlib.scrypt`; the port guards, Werkzeug does not |

---

## 5. Known gaps in the golden patch

### 5.1 The compiled message catalogue is not carried

`app/translations/es/LC_MESSAGES/messages.mo` is **not** in `golden_patch.diff`.

It is a generated, git-ignored artifact, so its absence is defensible — but a tree built by applying
the patch alone renders English-only until `python -m app.cli translate compile` is run. The
`Dockerfile` and `Procfile` already perform that step, so deployed builds are unaffected.

A verifier scoring i18n MUST compile translations first, or it will wrongly fail every candidate
including the reference solution.

### 5.2 The moment.js subresource-integrity hash — found and fixed

`app/moment.py` originally declared:

```python
default_moment_version = '2.29.4'
default_moment_sri = ('sha512-qTXRIMyZIFb8iQcfjXWCO8+M5Tbc38Qi5WzdPOYZHIlZpz'
                      'BHG3L1LjigqOm4rd0Ns1PZlCyIB2N1XxKmqchIYQ==')
```

The actual SHA-512 of
`https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment-with-locales.min.js` — the file the
same function builds a `src` for — is

```
sha512-42PE0rd+wZ2hNXftlM78BSehIGzezNeQuzihiBCvUEB3CVxHvsShF86wBWwQORNxNINlBPuq7rG4WWhNiTVHFg==
```

which is what Flask-Moment 1.0.6 ships. The original value matched neither that file nor
`moment.min.js`, for any 2.24–2.29 release.

`base.html` calls `moment.include_moment()` with defaults, so the tag is on **every page**. A
browser enforcing subresource integrity refuses to execute the script, `moment_render_all()` never
runs, and every `<span class="dynamic-moment" … style="display: none">` stays hidden — the
"last seen" line, every post timestamp, every message timestamp.

Server-side testing cannot see this. The markup is byte-identical apart from the hash, the page
returns 200, and no request is made to the CDN. It surfaced only in the differential against
Flask-Moment's own constant (BT-17).

**Status: fixed.** `golden_patch.diff` now carries the correct hash. The patch is otherwise
byte-identical to the version that failed — two lines changed.

**Verifier check:** `BT-17 cdn src+sri` MUST agree with the source tree. Keep this gate: a
hand-ported constant that no server-side assertion can reach is exactly the kind of thing that
survives a migration unnoticed.

## 6. Verification — three test suites

The task is **not complete** until **all three** of the suites below pass. They are not
interchangeable, and no two of them cover the same ground:

- **§6.1 Test cases** — the in-repo suite. Proves the application object still builds under the new
  framework and that the model layer survived. Blind to every HTTP-level concern (§6.3).
- **§6.2 Behaviour tests** — differential parity against the Flask baseline on a *running* app. The
  only suite that can observe status codes, redirects, flashes, CSRF, cookies, locale negotiation
  and rendered markup.
- **§6.3 Coverage tests** — proves the verification actually reaches the code the migration added.
  Without this, §6.1 passing means almost nothing for the fourteen new modules.

All three are implemented under `verification/`:

```
verification/
  run_all.py            all three, one gate, non-zero exit unless every one passes
  suite_cases.py        6.1
  suite_behaviour.py    6.2 -- scoring and gates
  suite_coverage.py     6.3
  battery.py            the 98 request-level cases, framework-agnostic
  _drive_source.py      Flask test client adapter
  _drive_target.py      Starlette TestClient adapter
  extras.py             BT-13 .. BT-17, the checks with no HTTP surface
  _drive_*_extra.py     their two adapters
  _scrypt_pin/          injected into the source interpreter only (section 8)
```

Neither repository is written to: the source tree is copied to `.work/source` and its catalogue
compiled there (§5.1), and `coverage` is installed side-by-side rather than into either virtualenv.

### 6.0 Preconditions

```bash
# patch integrity
git checkout a975ef6
git apply --check golden_patch.diff && git apply golden_patch.diff

# no residual Flask references  (§1.1, §1.4, §1.5)
grep -rniE '\bflask' . --include='*.py' --include='*.txt' --include='*.sh' \
     --include='Procfile' --include='Dockerfile' --include='*.conf' \
     --exclude-dir=venv --exclude-dir=.git      # expect: no matches

# schema fidelity  (§2.1)
alembic upgrade head
alembic check                                   # expect: No new upgrade operations detected.
alembic downgrade base

# translations — see §5, or every i18n case fails for the wrong reason
python -m app.cli translate compile

# baseline for §6.2, built once
git worktree add ../baseline a975ef6 && pip install -r ../baseline/requirements.txt
```

**Gate:** clean apply, zero `flask` matches outside `venv/`, `alembic check` clean, nine revisions
up and nine down, `messages.mo` present.

---

### 6.1 Test cases

The four tests in `tests.py`, unchanged in name and assertion. The golden patch rewrites their
*setup* (`create_app` no longer pushes an app context; `db.new_session_scope()` replaces it) but
MUST NOT weaken what they assert.

```bash
python3 verification/suite_cases.py        # runs `python -m unittest tests.py` on both trees
```

| ID | Test | Asserts |
|---|---|---|
| TC-1 | `test_password_hashing` | `set_password` / `check_password` round-trip; wrong password rejected |
| TC-2 | `test_avatar` | Gravatar URL built from the MD5 of the email, size honoured |
| TC-3 | `test_follow` | `follow` / `unfollow`, `is_following`, `following_count`, `followers_count`, association-table wiring |
| TC-4 | `test_follow_posts` | The `following_posts()` union query — ordering and membership across four users |

**Gate:** `Ran 4 tests … OK`. A candidate MUST NOT delete, rename, `@skip`, or weaken any of the
four. Reference result: **4/4 on both trees, ~0.7 s.**

What this suite does **not** touch: no HTTP request is ever issued, so routing, middleware,
session, login, CSRF, forms, `url_for`, templating, i18n, error handlers and pagination are all
outside it. That is the subject of §6.2 and the reason for §6.3.

---

### 6.2 Behaviour tests

Run the candidate and the Flask baseline side by side and diff the responses. Everything below was
executed against the golden patch; the "Reference" column is the observed result.

Harness: 98 request-level cases driven through each framework's own in-process transport, replaying
one shared script against both. Each case records `status`, `Content-Type`, `Location`, the flash
messages, the form field errors, and the response body normalised for volatile values (CSRF
tokens, timestamps, `<script>` blocks). Two tiers are scored — **strict** (byte-level after
normalisation) and **functional** (additionally masking the four cosmetic deviations of §4:
`/index` ≡ `/`, the `hidden_tag()` wrapper div, the moment CSS class, the moment `<script>` block).

| ID | Group | Cases | Assertion | Strict | Functional | Similarity |
|---|---|---:|---|---:|---:|---:|
| BT-1 | Anonymous pages | 6 | home / login / register / reset-request / explore render; `/static` served | 3/6 | **6/6** | 100.0% |
| BT-2 | Registration | 6 | success, duplicate username, duplicate email, invalid fields, missing CSRF | 2/6 | **6/6** | 100.0% |
| BT-3 | Login | 4 | wrong password, unknown user, success, flash text | 2/4 | **4/4** | 100.0% |
| BT-4 | Authenticated pages | 15 | index, `/index` alias, post create / empty / oversize, explore, profile, popup, 404 user, edit-profile incl. taken username, flash consumed once | 3/15 | **15/15** | 100.0% |
| BT-5 | Follow / unfollow | 10 | follow, unfollow, self-follow, unknown user, missing CSRF, and each flash | 4/10 | **10/10** | 100.0% |
| BT-6 | Messages & notifications | 5 | send-message form + post, message list, notification poll, unknown recipient | 2/5 | **5/5** | 100.0% |
| BT-7 | Search & translate | 3 | empty query redirect, result page, translate endpoint | 2/3 | **3/3** | 100.0% |
| BT-8 | Query-param handling (§3.4) | 11 | `page=abc`, `page=`, `page=1.9`, `page=0`, `page=-3` on five routes plus `since=abc` — all MUST stay `200 text/html` | 1/11 | **11/11** | 100.0% |
| BT-9 | Error handling (§3.3) | 4 | 404 under `*/*`, `text/html`, `application/json`; wrong method | 2/4 | 3/4 | 80.3% |
| BT-10 | Internationalisation (§3.5) | 8 | `Accept-Language: es` on login, register flash, rendered flash, **WTForms validator messages**, login-required flash, home; `en` control | 2/8 | **8/8** | 100.0% |
| BT-11 | REST API (§3.3) | 23 | create/read/update user, pagination, basic-auth token issue, bearer auth, revoke, 401/403/404 error bodies, lenient + capped `per_page` | **23/23** | **23/23** | 100.0% |
| BT-12 | Logout | 3 | logout, anonymous home, login page | 1/3 | **3/3** | 100.0% |
| | **TOTAL** | **98** | | **47/98** (48.0%) | **97/98** (99.0%) | **99.2%** |

Cross-cutting results on the same 98 cases:

| Dimension | Result |
|---|---|
| HTTP status codes identical | **98 / 98** |
| Flash text identical (EN + ES) | **98 / 98** |
| Redirect `Location` identical | 93 / 98 raw → **98 / 98** with `/index` ≡ `/` (§4.1) |
| Form field errors identical | **97 / 98** (the one delta is §4.5, CSRF wording) |
| Body byte-identical after masking | **96 / 98** |

Five further groups sit outside the 98, because they have no HTTP surface. They are run the same
way — both trees, same code path, diffed — except BT-13 and BT-15, which assert on the target
alone. 47 named checks in total.

| ID | Requirement | Reference |
|---|---|---|
| BT-13 | **Request isolation (§3.7)** — 200 overlapping requests across 8 concurrently logged-in sessions; every response must render its own user | **pass**, 0 leaks in 200 |
| BT-14 | **Hash compatibility (§2.4)** — 4 method strings recorded by shape and verdict, cross-validated in both directions against real `werkzeug.security`, plus a legacy `pbkdf2:sha256:600000$…` row, 6 malformed inputs, `salt_length=0`, an unknown method, `pbkdf2` with 3 parameters, and `scrypt` | **pass** — 20 agree, 4 differ (§4 rows 10 and 11) |
| BT-15 | **Background job (§3.6)** — `export_posts` with no request in scope: progress reported, notification written, task marked complete, `posts.json` attached | **pass** — progress `[0, 100, 100]`, complete, attached |
| BT-16 | **Off-request URL building (§3.6)** — `_external` with only `SERVER_NAME` to go on, plus the relative, `_anchor` and query forms, and an unknown endpoint | **pass** — 5/5 agree |
| BT-17 | **moment shim API (§2.3)** — `format`, `fromNow` (± `no_suffix`, ± `refresh`), `calendar`, `unix`, `valueOf`, the `cdn src+sri` pair, and the four `include_moment` variants, compared against Flask-Moment | **pass** — `src`+`integrity` agree; 4 differ by §4.3 |

**Gate:** functional pass ≥ 97/98 and output similarity ≥ 99%, with every difference accounted for
by §4; status codes and flash text at 98/98 with **no** exceptions; BT-13 … BT-17 with no
unexplained difference.

Reference result: **PASS.** The single functional failure among the 98 is `I04 GET on POST-only
route` — Werkzeug's templated 405 page versus Starlette's plain-text `Method Not Allowed` — which
is deviation §4.4 and accepted. Among the 47 extra checks, 40 agree and 7 differ by §4 (rows 3, 10
and 11); **0 unexplained**. This suite is what caught §5.2, and it is the only one that could
have.

**BT-1 … BT-17 have no coverage in §6.1 and cannot be substituted by it.**

---

### 6.3 Coverage tests

Proves the verification reaches the code the migration introduced. Coverage is measured across the
**whole** verification run — the four test cases of §6.1 plus the 98 behaviour cases and the 47
extra checks of §6.2 — and gated per module, plus a non-regression gate against the source tree
measured exactly the same way.

```bash
python3 verification/suite_coverage.py
```

| | Statements | Covered | Line coverage |
|---|---:|---:|---:|
| Flask baseline `a975ef6`, same three phases | 856 | 688 | **80.4%** |
| Golden patch | 1593 | 1337 | **83.9%** |
| — of which, the 14 new modules | 663 | 592 | **89.3%** |

For contrast, `tests.py` measured alone: 1593 statements, **45.3%**, and the new modules at
**43.8%**. That gap is the entire argument for this suite existing.

| ID | Requirement | Threshold | Reference | |
|---|---|---:|---:|---|
| CV-1 | The 14 new modules of §1.3, in aggregate | ≥ 80% | 89.3% | pass |
| CV-2 | Overall coverage MUST NOT regress against the source tree | ≥ 80.4% | 83.9% | pass |
| CV-3 | `app/state.py` | ≥ 80% | 100.0% | pass |
| CV-4 | `app/db.py` | ≥ 80% | 87.7% | pass |
| CV-5 | `app/context.py` | ≥ 80% | 86.8% | pass |
| CV-6 | `app/middleware.py` | ≥ 80% | 80.0% | pass |
| CV-7 | `app/login.py` | ≥ 80% | 86.5% | pass |
| CV-8 | `app/session.py` | ≥ 80% | 82.4% | pass |
| CV-9 | `app/forms.py` | ≥ 80% | 96.8% | pass |
| CV-10 | `app/i18n.py` | ≥ 80% | 89.6% | pass |
| CV-11 | `app/templating.py` | ≥ 80% | 100.0% | pass |
| CV-12 | `app/urls.py` | ≥ 80% | 91.9% | pass |
| CV-13 | `app/responses.py` | ≥ 80% | 100.0% | pass |
| CV-14 | `app/security.py` — hand-written crypto, held higher | ≥ 90% | 100.0% | pass |
| CV-15 | `app/moment.py` | ≥ 80% | 86.6% | pass |
| CV-16 | `app/params.py` | ≥ 80% | 92.9% | pass |
| CV-17 | `urls.url_for` executes | yes | yes | pass |
| CV-18 | `middleware.RequestContextMiddleware.__call__` executes | yes | yes | pass |
| CV-19 | `session.SessionMiddleware.__call__` executes | yes | yes | pass |
| CV-20 | `login_user`, `logout_user`, `load_user`, `login_required` execute | 4/4 | 4/4 | pass |
| CV-21 | `context.flash`, `context.get_flashed_messages` execute | 2/2 | 2/2 | pass |
| CV-22 | `validate_on_submit`, `hidden_tag`, `validate_csrf_token`, `get_translations` execute | 4/4 | 4/4 | pass |
| CV-23 | `i18n.select_locale`, `i18n.gettext` execute | 2/2 | 2/2 | pass |
| CV-24 | `params.convert` — the §3.4 fallback — executes | yes | yes | pass |
| CV-25 | `db.paginate`, `db.first_or_404`, `db.get_or_404` execute | 3/3 | 3/3 | pass |
| CV-26 | `security.generate_password_hash`, `security.check_password_hash` execute | 2/2 | 2/2 | pass |
| CV-27 | `moment.include_moment` executes | yes | yes | pass |

**Gate:** CV-1 … CV-27 all pass. Reference result: **27/27, PASS.**

**Exempted lines.** `app/security.py`'s scrypt parameter block (10 statements) cannot execute on an
interpreter without `hashlib.scrypt` (§8), so CV-14 is scored over the remaining 45. The suite
detects this at runtime rather than taking it on trust: if the interpreter *does* have
`hashlib.scrypt`, nothing is exempted and the block must be covered. No other exemption exists.

**Note on the thresholds.** CV-2 is objective — non-regression against a baseline measured the same
way. The 80% / 90% floors in CV-1 and CV-3 … CV-16 are proposed, not derived; adjust them if your
grading scale differs. CV-17 … CV-27 are binary and should not be relaxed: each maps onto a named
obligation in §2 or §3, and CV-24 in particular guards the defect that §3.4 exists to prevent.

---

## 7. Scoring rubric

Weights apply **after** the §6 gate. A candidate that fails any of the three suites is incomplete
regardless of score; the rubric ranks completed migrations, it does not excuse an unmet gate.

| Weight | Obligation | Suite | Fail condition |
|---:|---|---|---|
| 20% | §2.1 schema exact | 6.0 | `alembic check` reports drift, or any revision fails to apply |
| 20% | §3.1 status + flash parity | 6.2 (BT-1…12) | any status code or flash string differs |
| 15% | §2.2 endpoint names + URL paths preserved | 6.2 | any template raises on `url_for`, or a path changed |
| 10% | §3.7 request isolation | 6.2 (BT-13) | any cross-request identity, `g`, locale or session leak |
| 10% | §2.4 hash compatibility | 6.2 (BT-14) | a Werkzeug hash fails to validate, or `check_password_hash` raises |
| 10% | §3.4 lenient query params | 6.2 (BT-8) | `?page=abc` returns 4xx, or `per_page` is uncapped after fallback |
| 5% | §3.5 i18n incl. WTForms messages | 6.2 (BT-10) | validator messages stay English under `Accept-Language: es` |
| 5% | §2.7 test suite and its reach | 6.1 + 6.3 | fewer than 4 tests, any renamed or weakened, or any CV gate unmet |
| 5% | §1.5 operational files | 6.0 | `boot.sh` / `Procfile` / `Dockerfile` still invoke the Flask CLI |

Applying this to the reference solution: every row above passes, and all three suites of §6 pass.
The migration scores full marks and is **complete**.

Worth keeping in view: the one defect this exercise actually found (§5.2) is weighted by **no row
in this table**, because it is not a framework-migration concern — it is a hand-copied constant
that happened to travel in the same patch. The rubric ranks; the gate decides. A candidate that
scores 100% here and fails §6.2 is still incomplete.

---

## 8. Reference environment


Every number in this document was measured on:

Python 3.9.6 · Flask 3.0.0 / Werkzeug 3.0.1 (source) · FastAPI 0.128.8 / Starlette 0.49.3 (target)
SQLAlchemy 2.0.52 · WTForms 3.2.1 · Babel 2.18.0 · uvicorn 0.39.0 · coverage 7.10.7 · darwin 25.4.0

Two environment caveats affect reproduction, neither of them a property of the code:

- This interpreter is linked against LibreSSL 2.8.3 and has no `hashlib.scrypt`. Werkzeug 3.0.1
  defaults to scrypt, so the **Flask baseline** must be run with `generate_password_hash` pinned to
  `pbkdf2:sha256` or TC-1 errors out. The port already falls back to pbkdf2 on its own (§4.8), so
  only the baseline needs the pin. The §6.3 baseline figure of 51.0% is measured with it applied.
- Redis and Elasticsearch were not running. BT-15 was exercised with `get_current_job` and the
  progress channel stubbed; live search was not driven end to end. §2.5 was verified by binding a
  fake Elasticsearch client and asserting the session events fire on insert, update and delete.
