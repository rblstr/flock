import urllib
import urlparse
import logging
import json
import httplib
from flask import Flask, render_template, request

app = Flask(__name__)

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
	for child in children:
		child['url'] = sanitiseURL(child.get('url'))
		if child.get('url'):
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

def getLinks(subreddits):
	connection = httplib.HTTPConnection(REDDIT_URL)
	request_url = '/r/%s/top.json?t=week&limit=100' % '+'.join(subreddits)
	headers = {
		'User-Agent' : USER_AGENT
	}
	connection.request('GET', request_url, headers=headers)
	response = connection.getresponse()
	body = response.read()
	response_object = json.loads(body)
	children = response_object['data']['children']
	children = [child.get('data') for child in children]
	links = parseChildren(children)
	links = removeDuplicates(links)
	return links

@app.route('/', methods=['GET'])
def front():
	subreddits = request.args.get('subreddits')
	if not subreddits:
		return render_template('front.html')
	subreddits = subreddits.split()
	links = getLinks(subreddits)
	youtube_url = getYouTubeURL(links)
	subreddit_str = " ".join(subreddits)
	return render_template('front.html', subreddits=subreddit_str, youtube_url=youtube_url, links=links)

if __name__ == '__main__':
	app.run(debug=True)
