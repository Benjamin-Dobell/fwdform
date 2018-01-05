import os
import requests
from uuid import uuid4

from flask.ext.cors import CORS
from flask.ext.sqlalchemy import SQLAlchemy
from flask import Flask, request, redirect, abort

app = Flask(__name__)
cors = CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)

api_domain = os.environ['MAILGUN_DOMAIN']
api_key = os.environ['MAILGUN_API_KEY']
mailgun_send_url = 'https://api.mailgun.net/v3/%s/messages' % api_domain

registration_disabled=os.environ.get('REGISTRATION_DISABLED')
fallback_from=os.environ.get('FALLBACK_FROM')

class User(db.Model):

    def __init__(self, email):
        self.email = email
        self.uuid = str(uuid4())

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), unique=True)
    uuid = db.Column(db.String(36), unique=True)

@app.route('/')
def index():
    return redirect('http://github.com/Benjamin-Dobell/fwdform')

@app.route('/register', methods=['POST'])
def register():
    if registration_disabled:
        abort(500)
    user = User.query.filter_by(email=request.form['email']).first()
    if user:
        return ('Email already registered', 403)
    user = User(request.form['email'])
    db.session.add(user)
    db.session.commit()
    return "Token: {}".format(user.uuid)

@app.route('/user/<uuid>', methods=['POST'])
def forward(uuid):
    user = User.query.filter_by(uuid=uuid).first()
    if not user:
        return ('User not found', 406)
    message = {
               'to': [user.email],
               'from': request.form.get('email') or fallback_from,
               'subject': 'Message from {}'.format(request.form.get('name') or request.form.get('email') or 'Anonymous'),
               'text': request.form['message'],
              }
    result = requests.post(
        mailgun_send_url,
        auth=("api", api_key),
        data=message
    )
    if result.status_code != requests.codes.ok:
        abort(500)
    if 'redirect' in request.form:
        return redirect(request.form['redirect'])
    return 'Your message was sent successfully'

@app.errorhandler(400)
def bad_parameters(e):
    return ('<p>Missing information. Press the back button to complete '
            'the empty fields.</p><p><i>Developers: we were expecting '
            'the parameters "name", "email" and "message". You might '
            'also consider using JS validation.</i>', 400)

@app.errorhandler(500)
def error(e):
    return ('Sorry, something went wrong!', 500)

