import logging

from flask import session, redirect, url_for, request, Blueprint, render_template
from flask import make_response, g, flash

from fair3r_custom_overlay.lib import config
from fair3r_custom_overlay.models import User

auth = Blueprint('auth', __name__)
log = logging.getLogger(__name__)


@auth.route('/', methods=['GET', 'POST'])
@auth.route('/login', methods=['GET', 'POST'])
def login():

    session.pop('user_id', None)

    if request.method == 'POST':
        try:
            user = User.authenticate(request.form['USR'], request.form['PWD'])
            g.user = user
        except Exception as e:
            if config.CONTEXT == 'dev':
                flash(str(e), 'error')
            else:
                flash('mauvais utilisateur ou mot de passe', 'error')
            return render_template('login.html')

        session['user_id'] = g.user.id
        response = make_response(redirect(url_for("dashboard.home")))
        response.set_cookie('ics_signature', value='signed !!')
        return response

    return render_template('login.html')


@auth.route('/logout')
def logout():

    session.pop('user_id', None)
    g.user = None
    flash('veuillez vous signer a nouveau')
    response = make_response(redirect(url_for('.login')))
    response.delete_cookie('ics_signature')
    return response
