"""Command line interface.

The commands that used to be registered on the Flask CLI are now a standalone
click application, which is run with ``python -m app.cli``. The ``shell``
command takes the place of the shell context processor of the Flask version.
"""
import os
import click


@click.group()
def cli():
    """Microblog command line interface."""
    pass


@cli.group()
def translate():
    """Translation and localization commands."""
    pass


@translate.command()
@click.argument('lang')
def init(lang):
    """Initialize a new language."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system(
            'pybabel init -i messages.pot -d app/translations -l ' + lang):
        raise RuntimeError('init command failed')
    os.remove('messages.pot')


@translate.command()
def update():
    """Update all languages."""
    if os.system('pybabel extract -F babel.cfg -k _l -o messages.pot .'):
        raise RuntimeError('extract command failed')
    if os.system('pybabel update -i messages.pot -d app/translations'):
        raise RuntimeError('update command failed')
    os.remove('messages.pot')


@translate.command()
def compile():
    """Compile all languages."""
    if os.system('pybabel compile -d app/translations'):
        raise RuntimeError('compile command failed')


@cli.command()
def shell():
    """Run a Python shell with the application objects preloaded."""
    import code
    import sqlalchemy as sa
    import sqlalchemy.orm as so
    from app import create_app, db
    from app.models import User, Post, Message, Notification, Task

    create_app()
    context = {'sa': sa, 'so': so, 'db': db, 'User': User, 'Post': Post,
               'Message': Message, 'Notification': Notification, 'Task': Task}
    code.interact(local=context)


if __name__ == '__main__':
    cli()
