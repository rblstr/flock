# *flock*

Subreddit YouTube playlister

## Installation & Requirements

I recommend using [pip](http://www.pip-installer.org/en/latest/) and [virtualenv](http://www.virtualenv.org/en/latest/).

To clone and run flock for the first time, follow these steps:

1. git clone https://github.com/rblstr/flock.git && cd flock
2. virtualenv --no-site-packages .
3. . bin activate
4. pip install -r requirements.txt
5. python flock.py

## REST API

**"/"** - _GET_

Returns subreddit submission form

**Arguments:**

* **subreddits** - '+' seperated list of subreddits
