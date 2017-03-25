#!/usr/bin/env python3

import re
import sys
import gzip
import redis
import twarc
import logging
import requests

from os.path import dirname, abspath, join

from flask.config import Config
config = Config('.')
config.from_pyfile('app.cfg')

R = redis.StrictRedis(
    host=config['REDIS_HOST'],
    port=config['REDIS_PORT'],
    charset='utf-8',
    decode_responses=True
)

def friendships(t, user_id, level=2):
    logging.info("getting friends for user %s", user_id)
    level -= 1
    try:
        for friend_id in t.friend_ids(user_id):
            yield (user_id, friend_id)
            if level > 0:
                for friendship in friendships(t, friend_id, level):
                    yield friendship
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            logging.error("can't get friends for protected user %s", user_id)
        else:
            raise(e)

def write_data(username, user_id):
    data_dir = join(dirname(abspath(__file__)), 'data')
    data_file = join(data_dir, "%s.csv.gz" % user_id)
    data = gzip.open(data_file, "w")
    for friend_id in R.smembers('userid:%s' % user_id):
        data.write("%s,%s\n" % (user_id, friend_id))
        for foaf_id in R.smembers('userid:%s' % friend_id):
            data.write("%s,%s\n" % (user_id, friend_id))
    data.close()

def foaf(username, twitter_user_id, access_token, access_token_secret):
    t = twarc.Twarc(
        consumer_key=config["TWITTER_CONSUMER_KEY"],
        consumer_secret=config["TWITTER_CONSUMER_SECRET"],
        access_token=access_token,
        access_token_secret=access_token_secret
    )

    for user_id, friend_user_id in friendships(t, twitter_user_id, 2):
        if user_id == twitter_user_id:
            R.hincrby("job:%s" % username, "friends_checked", 1)
        R.sadd("userid:%s" % user_id, friend_user_id)

    write_data(username, twitter_user_id)

    job = R.hgetall("job:%s" % username)
    job_id = 'job:%s' % R.incr("jobid")
    R.hmset(job_id, job)
    R.lpush("jobs:%s" % username, job_id)
    R.delete("job:%s" % username)
