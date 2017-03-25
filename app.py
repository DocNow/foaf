#!/usr/bin/env python

import time
import redis
import twarc
import datetime
import requests.exceptions

from flask_oauthlib.client import OAuth
from flask import jsonify, request, redirect, session, url_for, flash
from flask import Flask, render_template, send_file, send_from_directory

from rq import Queue
from foaf import foaf

app = Flask(__name__)
app.config.from_pyfile('app.cfg')

# Redis setup

R = redis.StrictRedis(
    host=app.config['REDIS_HOST'],
    port=app.config['REDIS_PORT'],
    charset='utf-8',
    decode_responses=True
)
Q = Queue(connection=R)

# Twitter auth

oauth = OAuth()
twitter = oauth.remote_app('twitter',
    base_url='https://api.twitter.com/1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authenticate',
    access_token_method='GET',
    consumer_key=app.config['TWITTER_CONSUMER_KEY'],
    consumer_secret=app.config['TWITTER_CONSUMER_SECRET']
)

# Authentication routes

@app.route('/login')
def login():
    next = request.args.get('next') or request.referrer or None
    callback_url = 'http://' + app.config['HOSTNAME'] + url_for('oauth_authorized', next=next)
    return twitter.authorize(callback=callback_url)

@app.route('/logout')
def logout():
    del session['twitter_token']
    del session['twitter_user']
    return redirect('/')

@app.route('/oauth-authorized')
def oauth_authorized():
    next_url = request.args.get('next') or url_for('index')
    resp = twitter.authorized_response()
    if resp is None:
        flash(u'You denied the request to sign in.')
        return redirect(next_url)
    session['twitter_token'] = (
        resp['oauth_token'],
        resp['oauth_token_secret']
    )
    session['twitter_user'] = resp['screen_name']
    return redirect(next_url)

@twitter.tokengetter
def get_twitter_token(token=None):
    return session.get('twitter_token')

@app.context_processor
def inject_user():
    return dict(twitter_user=get_username())

# App routes!

@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('/static', path)

@app.route('/', methods=['GET'])
def index():
    username = get_username()
    if username:
        job = get_job(username)
        finished_jobs = get_finished_jobs(username)
    else:
        job = None
        finished_jobs = []
    return render_template('index.html', job=job, finished_jobs=finished_jobs)

@app.route('/jobs', methods=['POST'])
def jobs():
    username = get_username()
    job = get_job(username)
    screen_name = request.form['screen_name']
    if not job:
        job = add_job(username, screen_name)
        if not job:
            flash("Sorry, I couldn't find a Twitter user %s!" % screen_name)
    return redirect('/')

@app.route('/job', methods=['GET'])
def job():
    username = get_username()
    if not username:
        job = {}
    else:
        job = get_job(username)
    return jsonify(job)

@app.route('/dataset/<user_id>')
def dataset(user_id):
    path = 'data/%s.csv.gz' % user_id
    return send_file(path, as_attachment=True, mimetype='application/gzip')

# Helper functions

def add_job(username, screen_name):
    twitter_user = get_twitter_user(screen_name)
    if twitter_user:
        token = session.get('twitter_token', None)
        job = {
            'screen_name': screen_name,
            'friends_checked': 0,
            'user_id': twitter_user['id_str'],
            'friends_count': twitter_user['friends_count'],
            'created': dtstr(datetime.datetime.utcnow())
        }
        R.hmset('job:%s' % username, job)
        Q.enqueue(foaf, timeout=60 * 60 * 24 * 7,
            args=(username, twitter_user['id_str'], token[0], token[1]))
        return job
    return None

def get_job(username):
    job = R.hgetall('job:%s' % username)
    if not job:
        return None

    job['created'] = dt(job['created'])

    # estimate when it should finish
    elapsed = (datetime.datetime.utcnow() - job['created']).total_seconds()
    friends_count = int(job['friends_count'])
    friends_checked = int(job['friends_checked']) or 1
    total = elapsed * (friends_count / friends_checked)
    finish = job['created'] + datetime.timedelta(seconds=total)
    job['estimated_finish'] = dt(dtstr(finish))

    return job

def get_finished_jobs(username):
    jobs = []
    for job_id in R.lrange("jobs:%s" % username, 0, -1):
        jobs.append(R.hgetall(job_id))
    return jobs

def get_username():
    return session.get('twitter_user', None)

def get_twarc():
    token = session.get('twitter_token', None)
    return twarc.Twarc(
        consumer_key=app.config['TWITTER_CONSUMER_KEY'],
        consumer_secret=app.config['TWITTER_CONSUMER_SECRET'],
        access_token=token[0],
        access_token_secret=token[1]
    )

def get_twitter_user(screen_name):
    try:
        t = get_twarc()
        return next(t.user_lookup(screen_names=[screen_name]))
    except requests.exceptions.HTTPError:
        return None


dt_format = '%Y-%m-%dT%H:%M:%SZ'

def dt(s):
    return datetime.datetime.strptime(s, dt_format)

def dtstr(t):
    return t.strftime(dt_format)


