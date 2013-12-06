# _flock_
[![Build Status](https://travis-ci.org/rblstr/flock.png?branch=dev)](https://travis-ci.org/rblstr/flock) [![Coverage Status](https://coveralls.io/repos/rblstr/flock/badge.png?branch=dev)](https://coveralls.io/r/rblstr/flock?branch=dev)

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

Returns subreddit submission form and YouTube playlist if subreddits have been given.

**Arguments:**

* **subreddits** - **_REQUIRED_** - '+' seperated list of subreddits
* **sort** - **_OPTIONAL_** - What Reddit sort function to use.
    * **Default:** _top_
    * **Supported:** _top_, _hot_
* **t** - **_OPTIONAL_** - Select time range for items.
    * **Default:** _week_
    * **Supported:** _day_, _week_, _month_, _year_, _all_
* **limit** - **_OPTIONAL_** - Set a limit on the maximum number of items in the playlist.
    * **Default:** _100_
    * **Supported:** Any number in the range 0 < t <= 100
