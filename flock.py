import copy
import HTMLParser
import httplib
import json
import logging
import math
import os
import pickle
import time
import urllib
import urllib2
import urlparse
from datetime import datetime
from werkzeug.contrib.cache import MemcachedCache, SimpleCache
from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__, static_folder='static', static_url_path='')
app.config.from_object('debug_config')
if os.getenv('FLOCK_SETTINGS', None):
    app.config.from_envvar('FLOCK_SETTINGS')

if app.debug:
    cache = SimpleCache()
else:
    cache = MemcachedCache(['127.0.0.1:11211'])

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'http://www.reddit.com'
KIMONO_URL = 'http://www.kimonolabs.com/api/6bl1t44o'
YOUTUBE_EMBED_URL = 'https://www.youtube.com/embed/'
USER_AGENT = 'flock/0.1 by /u/rblstr'


def getSubredditList():
    subreddit_list = cache.get('subreddits')

    if subreddit_list:
        subreddit_list = pickle.loads(subreddit_list)
    else:
        query = {
            'apikey': app.config['KIMONO_KEY']
        }
        query_string = urllib.urlencode(query)

        try:
            response = makeRequest('%s?%s' % (KIMONO_URL, query_string))

            response_obj = json.load(response)

            response.close()
        except:
            return []

        if response_obj.get('results', None) is None:
            return []

        results = response_obj['results']
        subreddit_list = results['collection1'] + results['collection2']

        parsed_subreddit_list = []
        for entry in subreddit_list:
            entry = entry['subreddit']
            if entry['text'].startswith('/r/'):
                entry = entry['text'][3:]
                parsed_subreddit_list.append(entry)

        subreddit_list = sorted(parsed_subreddit_list, key=lambda s: s.lower())
        subreddit_list = sorted(subreddit_list, key=len)

        timeout = 60 * 60 * 24 * 7
        cache.set('subreddits', pickle.dumps(subreddit_list), timeout=timeout)

    return subreddit_list


def makeRequest(url):
    headers = {
        'User-Agent': USER_AGENT
    }
    request = urllib2.Request(url, headers=headers)
    result = urllib2.urlopen(request)
    return result


rate_limited_requests = {}


def rateLimitedRequest(url, timeout):
    global rate_limited_requests
    domain = urlparse.urlparse(url).netloc
    last_request_time = rate_limited_requests.get(domain, datetime(1979, 1, 1, 1))
    request_time = datetime.now()
    delta = request_time - last_request_time
    if delta.seconds < timeout:
        time.sleep(timeout-delta.seconds)
    response = makeRequest(url)
    request_time = datetime.now()
    rate_limited_requests[domain] = request_time
    return response


def getRedditResponse(subreddits, sort='top', t='week', limit=100):
    query = {
        't': t,
        'limit': limit
    }
    query_string = urllib.urlencode(query)

    request_url = '%s/r/%s/%s.json?%s' % (REDDIT_URL,
                                          '+'.join(subreddits),
                                          sort,
                                          query_string)

    try:
        response = rateLimitedRequest(request_url, 2.0)
    except urllib2.HTTPError:
        return None

    if not response:
        return None

    body = response.read()
    response.close()
    try:
        response_object = json.loads(body)
    except ValueError:
        return None
    if response_object.get('error') is not None:
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
        child['permalink'] = '%s%s' % (REDDIT_URL,
                                       child.get('permalink'))
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
        'autohide': 0,
        'showinfo': 1,
        'modestbranding': 1,
        'rel': 0,
        'version': 3,
        'enablejsapi': 1,
        'playlist': playlist
    }
    query_string = urllib.urlencode(query)

    youtube_url = "https://www.youtube.com/embed/%s?%s" % (first_id,
                                                           query_string)
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
            subreddit_links = filter(lambda link:
                                     link.get('subreddits') != subreddit,
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
    return round(sign * order + seconds / 45000, 7)


def top(entry):
    return entry.get('ups') - entry.get('downs')


supported_sorts = {
    'top': top,
    'hot': hot
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
    subreddit_list = getSubredditList()

    subreddits_str = request.args.get('subreddits')
    if not subreddits_str:
        return render_template('front.html', subreddit_list=subreddit_list)

    sort = request.args.get('sort', 'hot')
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

    selected_subreddits = subreddits_str.split()
    lower_subreddit_list = [sub.lower() for sub in subreddit_list]
    for subreddit in selected_subreddits:
        if not subreddit.lower() in lower_subreddit_list:
            subreddit_list.append(subreddit)

    links = getLinks(selected_subreddits, sort, t)

    if not links:
        flash('No links found', 'error')
        return redirect('/')

    links = removeDuplicates(links)

    sort_func = supported_sorts[sort]
    links = sorted(links, reverse=True, key=lambda l: l['created_utc'])
    links = sorted(links, reverse=True, key=lambda l: sort_func(l))

    links = links[0:limit]

    youtube_url = generateYouTubeURL(links)

    return render_template('front.html',
                           selected_subreddits=selected_subreddits,
                           youtube_url=youtube_url,
                           links=links,
                           sort=sort,
                           time=t,
                           subreddit_list=subreddit_list)


if __name__ == '__main__':
    app.run()
