from app.email import send_email
from app.i18n import _
from app.state import state
from app.templating import render_to_string


def send_password_reset_email(user):
    token = user.get_reset_password_token()
    send_email(_('[Microblog] Reset Your Password'),
               sender=state.config['ADMINS'][0],
               recipients=[user.email],
               text_body=render_to_string('email/reset_password.txt',
                                          user=user, token=token),
               html_body=render_to_string('email/reset_password.html',
                                          user=user, token=token))
