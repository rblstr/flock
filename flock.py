import copy
import pickle
import math
from datetime import datetime
import os
import HTMLParser
import urllib
import urlparse
import logging
import json
import httplib
from werkzeug.contrib.cache import MemcachedCache
from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__, static_folder='static', static_url_path='')
cache = MemcachedCache(['127.0.0.1:11211'])

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'www.reddit.com'
USER_AGENT = 'flock/0.1 by /u/rblstr'

def getRedditResponse(subreddits, sort='top', t='week', limit=100):
    connection = httplib.HTTPConnection(REDDIT_URL)

    query = {
        't' : t,
        'limit' : limit
    }
    query_string = urllib.urlencode(query)
    
    request_url = '/r/%s/%s.json?%s' % ('+'.join(subreddits), sort, query_string)
    
    headers = {
        'User-Agent' : USER_AGENT
    }
    
    connection.request('GET', request_url, headers=headers)
    response = connection.getresponse()

    if not response or response.status != 200:
        return None
    
    body = response.read()
    try:
        response_object = json.loads(body)
    except ValueError:
        return None
    if response_object.get('error') != None:
        return None
    
    return response_object


def sanitiseShortYouTubeURL(url):
    if not 'youtu.be' in url:
        return None
    # parse URL
    parsed = urlparse.urlparse(url)
    # get video id
    video_id = parsed.path[1:]
    if not video_id:
        return None
    # create new url
    new_url = 'http://www.youtube.com/watch?v=%s' % video_id
    return new_url


def sanitiseYouTubeURL(url):
    # parse query string
    query_dict = urlparse.parse_qs(urlparse.urlparse(url).query)
    # get "v" value
    v = query_dict.get('v', None)
    if not v:
        return None
    # create new url
    new_url = 'http://www.youtube.com/watch?v=%s' % v[0]
    return new_url


def sanitiseURL(url):
    if 'youtube' in url.lower():
        return sanitiseYouTubeURL(url)
    elif 'youtu.be' in url.lower():
        return sanitiseShortYouTubeURL(url)
    else:
        return None


def parseChild(child):
    accepted_keys = [
        'id',
        'title',
        'url',
        'permalink',
        'num_comments',
        'ups',
        'downs',
        'author',
        'subreddits',
        'created_utc',
    ]

    for key in child.keys():
        if key not in accepted_keys:
            del child[key]

    return child


def parseRedditResponse(response_object):
    response_copy = copy.deepcopy(response_object)
    html_parser = HTMLParser.HTMLParser()
    
    children = response_copy['data']['children']
    children = [child['data'] for child in children]
    
    links = []
    for child in children:
        url = sanitiseURL(child.get('url'))
        if not url:
            continue
        child['url'] = url
        child['title'] = html_parser.unescape(child.get('title'))
        child['permalink'] = 'http://%s%s' % (REDDIT_URL, child.get('permalink'))
        child = parseChild(child)
        links.append(child)
        
    return links


def removeDuplicates(links):
    urls = []
    new_links = []
    for link in links:
        if link.get('url') not in urls:
            new_links.append(link)
            urls.append(link.get('url'))
    return new_links


def generateYouTubeURL(links):
    youtube_ids = []
    for entry in links:
        link_url = entry.get('url')
        v_id = urlparse.parse_qs(urlparse.urlparse(link_url).query).get("v")
        if not v_id:
            continue
        v_id = v_id[0]
        youtube_ids.append(v_id)
        
    first_id = youtube_ids[0]
    youtube_ids = youtube_ids[1:]
    playlist = ",".join(youtube_ids)
    playlist = unicode(playlist).encode('utf-8')

    query = {
        'autohide' : 0,
        'showinfo' : 1,
        'modestbranding' : 1,
        'rel' : 0,
        'playlist' : playlist
    }
    query_string = urllib.urlencode(query)
    
    youtube_url = "http://www.youtube.com/embed/%s?%s" % (first_id, query_string)
    return youtube_url


def getLinks(subreddits, sort, t):
    subreddits_to_get = []
    links = []
    for subreddit in subreddits:
        key = "%s+%s+%s" % (subreddit, sort, t)
        subreddit_links = cache.get(key)
        if not subreddit_links:
            subreddits_to_get.append(subreddit)
        else:
            links.extend(pickle.loads(subreddit_links))

    if subreddits_to_get:
        reddit_response = getRedditResponse(subreddits_to_get, sort, t, 100)
        if not reddit_response:
            flash('No Reddit response', 'error')
            return links

        response_links = parseRedditResponse(reddit_response)

        for subreddit in subreddits_to_get:
            subreddit_links = filter(lambda link: link.get('subreddits') != subreddit,
                                        response_links)
            if subreddit_links:
                key = "%s+%s+%s" % (subreddit, sort, t)
                cache.set(key, pickle.dumps(subreddit_links))

        links.extend(response_links)

    return links


def hot(entry):
    ups = entry.get('ups')
    downs = entry.get('downs')
    date = entry.get("created_utc")
    s = ups - downs
    order = math.log10(max(abs(s), 1))
    if s > 0:
        sign = 1
    elif s < 0:
        sign = -1
    else:
        sign = 0
    seconds = date - 1134028003
    return round(order + sign * seconds / 45000, 7)


def top(entry):
    return entry.get('ups') - entry.get('downs')


supported_sorts = {
    'top' : top,
    'hot' : hot
}

supported_times = [
    'day',
    'week',
    'month',
    'year',
    'all'
]


@app.route('/', methods=['GET'])
def playlist():
    subreddits_str = request.args.get('subreddits')
    if not subreddits_str:
        return render_template('front.html')

    sort = request.args.get('sort', 'top')
    if not sort in supported_sorts.keys():
        flash('Invalid sort type: %s' % sort, 'error')
        return redirect('/')

    t = request.args.get('t', 'week')
    if not t in supported_times:
        flash('Invalid time type: %s' % t, 'error')
        return redirect('/')

    limit = request.args.get('limit', '100')
    try:
        limit = int(limit)
    except ValueError:
        flash('Invalid limit: %s' % limit, 'error')
        return redirect('/')
    if not (limit > 0 and limit <= 100):
        flash('Invalid limit: %d' % limit, 'error')
        return redirect('/')

    subreddits = subreddits_str.split()
    
    links = getLinks(subreddits, sort, t)

    if not links:
        flash('No links found', 'error')
        return redirect('/')

    links = removeDuplicates(links)

    sort_func = supported_sorts[sort]
    links = sorted(links, reverse=True, key=lambda l: l['created_utc'])
    links = sorted(links, reverse=True, key=lambda l: sort_func(l))

    links = links[0:limit]

    youtube_url = generateYouTubeURL(links)

    return render_template( 'front.html',
                            subreddits=subreddits_str,
                            youtube_url=youtube_url,
                            links=links)


app.config.from_object('debug_config')
if os.getenv('FLOCK_SETTINGS', None):
    app.config.from_envvar('FLOCK_SETTINGS')


if __name__ == '__main__':
    app.run(debug=True)

