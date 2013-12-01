import HTMLParser
import urllib
import urlparse
import logging
import json
import httplib
from flask import Flask, render_template, request, redirect, flash

app = Flask(__name__, static_folder='static', static_url_path='')

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'www.reddit.com'
YOUTUBE_API_URL = 'https://www.googleapis.com'
YOUTUBE_API_TOKEN = 'AIzaSyDPBTRqfIAJM5zRP9fDauMYcAkJip3UaMQ'
USER_AGENT = 'flock/0.1 by /u/rblstr'
SECRET_KEY = 'skeleton_key'

app.config['SECRET_KEY'] = SECRET_KEY


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
    response_object = json.loads(body)
    if response_object.get('error'):
        return None
    
    return response_object


def getYouTubeResponse(links):
    video_ids = []
    for link in links:
        link_url = link.get('url')
        video_id = urlparse.parse_qs(urlparse.urlparse(link_url).query).get("v")[0]
        video_ids.append(video_id)
        
    playlist = ",".join(video_ids)
    playlist = unicode(playlist).encode('utf-8')
    
    query = {
        'part' : 'snippet',
        'id' : playlist,
        'key' : YOUTUBE_API_TOKEN
    }
    query_string = urllib.urlencode(query)
    
    request_url = '%s/youtube/v3/videos?%s' % (YOUTUBE_API_URL, query_string)
    
    response = urllib.urlopen(request_url)
    if not response:
        return None
    
    body = response.read()
    response_object = json.loads(body)
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
    html_parser = HTMLParser.HTMLParser()
    
    children = response_object['data']['children']
    children = [child.get('data') for child in children]
    
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


def getLinkTitles(links):
    response_object = getYouTubeResponse(links)
    if not response_object:
        for link in links:
            link['video_title'] = link.get('title')
        return links # No YouTube response, but no matter
        
    for i,item in enumerate(response_object.get('items')):
        snippet = item.get('snippet')
        link = links[i]
        link['video_title'] = snippet['title']
    
    return links


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


supported_sorts = [
    'top',
    'hot'
]

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
    if not sort in supported_sorts:
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
    
    reddit_response = getRedditResponse(subreddits, sort, t, 100)
    if not reddit_response:
        flash('No Reddit response', 'error')
        return redirect('/')

    links = parseRedditResponse(reddit_response)
    if not links:
        flash('No links found', 'error')
        return redirect('/')

    links = removeDuplicates(links)
    links = getLinkTitles(links)

    links = links[0:limit]

    youtube_url = generateYouTubeURL(links)

    return render_template( 'front.html',
                            subreddits=subreddits_str,
                            youtube_url=youtube_url,
                            links=links)


if __name__ == '__main__':
    app.run(debug=True)

