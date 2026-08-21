from datetime import datetime, timezone
from fastapi import Depends, Request
import sqlalchemy as sa
from langdetect import detect, LangDetectException

from app import db
from app.context import g, flash
from app.i18n import _, get_locale
from app.login import current_user, login_required
from app.main import bp
from app.main.forms import EditProfileForm, EmptyForm, PostForm, SearchForm, \
    MessageForm
from app.models import User, Post, Message, Notification
from app.params import Page, Since
from app.responses import redirect
from app.state import state
from app.templating import render_template
from app.translate import translate
from app.urls import url_for

authenticated = [Depends(login_required)]


def before_request():
    """Run before every request, from the request context middleware."""
    if current_user.is_authenticated:
        current_user.last_seen = datetime.now(timezone.utc)
        db.session.commit()
        g.search_form = SearchForm()
    g.locale = str(get_locale())


@bp.api_route('/index', methods=['GET', 'POST'], name='main.index',
              dependencies=authenticated)
@bp.api_route('/', methods=['GET', 'POST'], name='main.index',
              dependencies=authenticated)
async def index(request: Request, page: Page = 1):
    form = await PostForm.from_formdata(request)
    if form.validate_on_submit():
        try:
            language = detect(form.post.data)
        except LangDetectException:
            language = ''
        post = Post(body=form.post.data,
                    author=current_user._get_current_object(),
                    language=language)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'))
        return redirect(url_for('main.index'))
    posts = db.paginate(current_user.following_posts(), page=page,
                        per_page=state.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.get('/explore', name='main.explore', dependencies=authenticated)
async def explore(page: Page = 1):
    query = sa.select(Post).order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=state.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@bp.get('/user/{username}', name='main.user', dependencies=authenticated)
async def user(username: str, page: Page = 1):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    query = user.posts.select().order_by(Post.timestamp.desc())
    posts = db.paginate(query, page=page,
                        per_page=state.config['POSTS_PER_PAGE'],
                        error_out=False)
    next_url = url_for('main.user', username=user.username,
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=user.username,
                       page=posts.prev_num) if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@bp.get('/user/{username}/popup', name='main.user_popup',
        dependencies=authenticated)
async def user_popup(username: str):
    user = db.first_or_404(sa.select(User).where(User.username == username))
    form = EmptyForm()
    return render_template('user_popup.html', user=user, form=form)


@bp.api_route('/edit_profile', methods=['GET', 'POST'],
              name='main.edit_profile', dependencies=authenticated)
async def edit_profile(request: Request):
    form = await EditProfileForm.from_formdata(request,
                                               current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'))
        return redirect(url_for('main.edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@bp.post('/follow/{username}', name='main.follow', dependencies=authenticated)
async def follow(username: str, request: Request):
    form = await EmptyForm.from_formdata(request)
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.follow(user)
        db.session.commit()
        flash(_('You are following %(username)s!', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.post('/unfollow/{username}', name='main.unfollow',
         dependencies=authenticated)
async def unfollow(username: str, request: Request):
    form = await EmptyForm.from_formdata(request)
    if form.validate_on_submit():
        user = db.session.scalar(
            sa.select(User).where(User.username == username))
        if user is None:
            flash(_('User %(username)s not found.', username=username))
            return redirect(url_for('main.index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'))
            return redirect(url_for('main.user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username))
        return redirect(url_for('main.user', username=username))
    else:
        return redirect(url_for('main.index'))


@bp.post('/translate', name='main.translate_text',
         dependencies=authenticated)
async def translate_text(request: Request):
    data = await request.json()
    return {'text': translate(data['text'],
                              data['source_language'],
                              data['dest_language'])}


@bp.get('/search', name='main.search', dependencies=authenticated)
async def search(page: Page = 1):
    if not g.search_form.validate():
        return redirect(url_for('main.explore'))
    posts, total = Post.search(g.search_form.q.data, page,
                               state.config['POSTS_PER_PAGE'])
    next_url = url_for('main.search', q=g.search_form.q.data, page=page + 1) \
        if total > page * state.config['POSTS_PER_PAGE'] else None
    prev_url = url_for('main.search', q=g.search_form.q.data, page=page - 1) \
        if page > 1 else None
    return render_template('search.html', title=_('Search'), posts=posts,
                           next_url=next_url, prev_url=prev_url)


@bp.api_route('/send_message/{recipient}', methods=['GET', 'POST'],
              name='main.send_message', dependencies=authenticated)
async def send_message(recipient: str, request: Request):
    user = db.first_or_404(sa.select(User).where(User.username == recipient))
    form = await MessageForm.from_formdata(request)
    if form.validate_on_submit():
        msg = Message(author=current_user._get_current_object(),
                      recipient=user, body=form.message.data)
        db.session.add(msg)
        user.add_notification('unread_message_count',
                              user.unread_message_count())
        db.session.commit()
        flash(_('Your message has been sent.'))
        return redirect(url_for('main.user', username=recipient))
    return render_template('send_message.html', title=_('Send Message'),
                           form=form, recipient=recipient)


@bp.get('/messages', name='main.messages', dependencies=authenticated)
async def messages(page: Page = 1):
    current_user.last_message_read_time = datetime.now(timezone.utc)
    current_user.add_notification('unread_message_count', 0)
    db.session.commit()
    query = current_user.messages_received.select().order_by(
        Message.timestamp.desc())
    messages = db.paginate(query, page=page,
                           per_page=state.config['POSTS_PER_PAGE'],
                           error_out=False)
    next_url = url_for('main.messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('main.messages', page=messages.prev_num) \
        if messages.has_prev else None
    return render_template('messages.html', messages=messages.items,
                           next_url=next_url, prev_url=prev_url)


@bp.get('/export_posts', name='main.export_posts', dependencies=authenticated)
async def export_posts():
    if current_user.get_task_in_progress('export_posts'):
        flash(_('An export task is currently in progress'))
    else:
        current_user.launch_task('export_posts', _('Exporting posts...'))
        db.session.commit()
    return redirect(url_for('main.user', username=current_user.username))


@bp.get('/notifications', name='main.notifications',
        dependencies=authenticated)
async def notifications(since: Since = 0.0):
    query = current_user.notifications.select().where(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    notifications = db.session.scalars(query)
    return [{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications]
