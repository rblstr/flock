import logging
import json
import httplib
from flask import Flask, render_template, request

app = Flask(__name__)

logging.getLogger().setLevel(logging.DEBUG)

REDDIT_URL = 'www.reddit.com'
USER_AGENT = 'flock/0.1 by /u/rblstr'

def parseChildren(children):
	links = []
	for child in children:
		if 'youtube' in child.get('url').lower() or 'youtu.be' in child.get('url').lower():
			links.append(child)
	return links

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
	return links

@app.route('/', methods=['GET'])
def front():
	subreddits = request.args.get('subreddits')
	if not subreddits:
		return render_template('front.html')
	subreddits = subreddits.split()
	links = getLinks(subreddits)
	return '<br>'.join([link.get("title") for link in links])

if __name__ == '__main__':
	app.run(debug=True)
