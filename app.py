from flask import Flask, render_template, request
app = Flask(__name__)

@app.route('/', methods=['GET'])
def front():
	subreddits = request.args.get('subreddits')
	if not subreddits:
		return render_template('front.html')
	subreddit_list = subreddits.split('+')
	return ' '.join(subreddit_list)

if __name__ == '__main__':
	app.run(debug=True)
