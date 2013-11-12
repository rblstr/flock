from datetime import datetime, date
import time
import HTMLParser
import urllib
import urlparse
import logging
import json
import httplib
from flask import Flask, render_template, request

app = Flask(__name__)

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'www.reddit.com'
YOUTUBE_API_URL = 'https://www.googleapis.com'
YOUTUBE_API_TOKEN = 'AIzaSyAB7HWB9qehjXQPI-ZtBNGScdKXKqqsSgM'
assert YOUTUBE_API_TOKEN != 'PUT_PRIVATE_TOKEN_HERE', 'Please contact @rblstr regarding YouTube access token'
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
		v_id = urlparse.parse_qs(urlparse.urlparse(link_url).query).get("v")[0]
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


def renderError(error_string, subreddit_str=None):
    return render_template('front.html', subreddits=subreddit_str, error=error_string)


def generatePlaylist(subreddits):
	subreddit_str = " ".join(subreddits)

	# get reddit response
	response_object = getRedditResponse(subreddits)
	# no reddit response
	if not response_object:
		return renderError('No Reddit response', subreddit_str)

	# parse response
	links = parseRedditResponse(response_object)
	# no links detected
	if not links:
		return renderError('No links found', subreddit_str)

	# process links
	links = removeDuplicates(links)
	links = getLinkTitles(links)

	# generate YouTube embed code
	youtube_url = generateYouTubeURL(links)

	# return frontpage
	return render_template(	'front.html',
							subreddits = subreddit_str,
							youtube_url = youtube_url,
							links = links )


@app.route('/', methods=['GET'])
def front():
    subreddit_str = request.args.get('subreddits')
    if not subreddit_str:
            return render_template('front.html')
    subreddits = subreddit_str.split()
    return generatePlaylist(subreddits)


if __name__ == '__main__':
    app.run(debug=True)

