from urllib.parse import urlsplit
from fastapi import Request
import sqlalchemy as sa

from app import db
from app.auth import bp
from app.auth.email import send_password_reset_email
from app.auth.forms import LoginForm, RegistrationForm, \
    ResetPasswordRequestForm, ResetPasswordForm
from app.context import flash
from app.i18n import _
from app.login import current_user, login_user, logout_user
from app.models import User
from app.responses import redirect
from app.templating import render_template
from app.urls import url_for


@bp.api_route('/login', methods=['GET', 'POST'], name='auth.login')
async def login(request: Request):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = await LoginForm.from_formdata(request)
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == form.username.data))
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'))
            return redirect(url_for('auth.login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.query_params.get('next')
        if not next_page or urlsplit(next_page).netloc != '':
            next_page = url_for('main.index')
        return redirect(next_page)
    return render_template('auth/login.html', title=_('Sign In'), form=form)


@bp.get('/logout', name='auth.logout')
async def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.api_route('/register', methods=['GET', 'POST'], name='auth.register')
async def register(request: Request):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = await RegistrationForm.from_formdata(request)
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'))
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', title=_('Register'),
                           form=form)


@bp.api_route('/reset_password_request', methods=['GET', 'POST'],
              name='auth.reset_password_request')
async def reset_password_request(request: Request):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = await ResetPasswordRequestForm.from_formdata(request)
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.email == form.email.data))
        if user:
            send_password_reset_email(user)
        flash(
            _('Check your email for the instructions to reset your password'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title=_('Reset Password'), form=form)


@bp.api_route('/reset_password/{token}', methods=['GET', 'POST'],
              name='auth.reset_password')
async def reset_password(token: str, request: Request):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = await ResetPasswordForm.from_formdata(request)
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'))
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)
