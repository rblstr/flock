import HTMLParser
import urllib
import urlparse
import logging
import json
import httplib
from flask import Flask, render_template, request

app = Flask(__name__, static_folder='static', static_url_path='')

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'www.reddit.com'
USER_AGENT = 'flock/0.1 by /u/rblstr'

def getYouTubeURL(links):
	youtube_ids = []
	for entry in links:
		v_id = urlparse.parse_qs(urlparse.urlparse(entry.get('url')).query).get("v")
		if not v_id:
			continue
		v_id = v_id[0]
		youtube_ids.append(v_id)

	first_id = youtube_ids[0]
	youtube_ids = youtube_ids[1:]
	playlist = ",".join(youtube_ids)
	playlist = unicode(playlist).encode('utf-8')

	query = {
		'autohide'			: 0,
		'showinfo'			: 1,
		'modestbranding'	: 1,
		'rel'				: 0,
		'playlist'			: playlist
	}
	query_string = urllib.urlencode(query)

	youtube_url = "http://www.youtube.com/embed/%s?%s" % (first_id, query_string)
	return youtube_url

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

def parseChildren(children):
	links = []
	html_parser = HTMLParser.HTMLParser()
	for child in children:
		child['url'] = sanitiseURL(child.get('url'))
		if child.get('url'):
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

def getChildren(subreddits):
	connection = httplib.HTTPConnection(REDDIT_URL)
	request_url = '/r/%s/top.json?t=week&limit=100' % '+'.join(subreddits)
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
	children = response_object['data']['children']
	children = [child.get('data') for child in children]
	return children

def getLinks(children):
	links = parseChildren(children)
	links = removeDuplicates(links)
	return links

def renderError(error_string, subreddit_str=None):
	return render_template('front.html', subreddits=subreddit_str, error=error_string)

def generatePlaylist(subreddits):
	if not subreddits:
		return render_template('front.html')
	subreddit_str = " ".join(subreddits)
	children = getChildren(subreddits)
	if not children:
		return renderError('Invalid subreddits', subreddit_str)
	links = getLinks(children)
	if not links:
		return renderError('No links returned', subreddit_str)
	youtube_url = getYouTubeURL(links)
	return render_template('front.html', subreddits=subreddit_str, youtube_url=youtube_url, links=links)

@app.route('/', methods=['GET'])
def front():
	subreddit_str = request.args.get('subreddits')
	if not subreddit_str:
		return render_template('front.html')
	subreddits = subreddit_str.split()
	return generatePlaylist(subreddits)

if __name__ == '__main__':
	app.run(debug=True)
