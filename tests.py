import mock
import datetime
import HTMLParser
import httplib
import io
import json
import logging
import pickle
import os
import time
import unittest
import urllib2

os.environ['FLOCK_SETTINGS'] = 'debug_config.py'

import flock


flock.app.testing = True
logging.disable(logging.CRITICAL)

urllib2.urlopen = mock.MagicMock()


class DuplicateSubredditTestCase(unittest.TestCase):
    def setUp(self):
        global mock_cache
        self.app = flock.app.test_client()
        self.mock_cache = {}

        f = open('tests/futuregarage_hot_week_100.json', 'r')
        reddit_response = json.load(f)
        f.close()

        self.reddit_response_dump = reddit_response

        f = open('tests/subreddit_list_dump.json', 'r')
        self.subreddit_list = json.load(f)
        f.close()

        self.getSubredditList = flock.getSubredditList
        flock.getSubredditList = mock.MagicMock()

        self.getRedditResponse = flock.getRedditResponse
        flock.getRedditResponse = mock.MagicMock()

        self.render_template = flock.render_template
        flock.render_template = mock.MagicMock()
        flock.render_template.side_effect = self.render_template

        self.get = flock.cache.get
        flock.cache.get = mock.MagicMock()
        flock.cache.get.return_value = None

    def tearDown(self):
        flock.getSubredditList = self.getSubredditList
        flock.getRedditResponse = self.getRedditResponse
        flock.render_template = self.render_template
        flock.cache.get = self.get

    def test_subreddit_list_contains_no_duplicates(self):
        flock.getSubredditList.return_value = self.subreddit_list[:]
        flock.getRedditResponse.return_value = self.reddit_response_dump
        response = self.app.get('/?subreddits=futuregarage+futurebeats')
        self.assertEqual(response.status_code, 200)
        args,kwargs = flock.render_template.call_args
        self.assertItemsEqual(kwargs.get('subreddit_list'), self.subreddit_list)

    def test_subreddit_list_contains_non_music_subreddits_when_requested(self):
        flock.getSubredditList.return_value = self.subreddit_list[:]
        flock.getRedditResponse.return_value = self.reddit_response_dump
        response = self.app.get('/?subreddits=youtubehaiku')
        self.assertEqual(response.status_code, 200)
        args,kwargs = flock.render_template.call_args
        subreddit_list = self.subreddit_list[:]
        subreddit_list.append('youtubehaiku')
        self.assertItemsEqual(kwargs.get('subreddit_list'), subreddit_list)


class FlockBaseTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flock.app.test_client()
        
        test_json_handle = open('tests/futuregarage_top_week_100.json')
        self.futuregarage_top = json.load(test_json_handle)
        test_json_handle.close()

        test_json_handle = open('tests/futuregarage_hot_week_100.json')
        self.futuregarage_hot = json.load(test_json_handle)
        test_json_handle.close()

        test_json_handle = open('tests/kimono.json')
        self.kimono_data = test_json_handle.read().decode('unicode-escape')
        test_json_handle.close()

        test_json_handle = open('tests/subreddit_list_dump.json')
        self.subreddit_list = json.load(test_json_handle)
        test_json_handle.close()

        self.original_getSubredditList = flock.getSubredditList

        flock.getSubredditList = mock.MagicMock(return_value=[])

        self.original_getRedditResponse = flock.getRedditResponse
        self.original_cache_get = flock.cache.get
        self.original_cache_set = flock.cache.set
        self.original_urlopen = flock.urllib2.urlopen

        """ We never want to make an actual HTTP request """
        flock.urllib2.urlopen = mock.MagicMock()
        """ Ensure we don't hit the cache by default """
        flock.cache.get = mock.MagicMock(name='get', return_value=None)
    
    def tearDown(self):
        flock.getRedditResponse = self.original_getRedditResponse
        flock.cache.get = self.original_cache_get
        flock.cache.set = self.original_cache_set
        flock.urllib2.urlopen = self.original_urlopen
        flock.getSubredditList = self.original_getSubredditList

        flock.rate_limited_requests = {}


class FrontpageTestCase(FlockBaseTestCase):
    def test_frontpage(self):
        response = self.app.get('/', content_type='text/html', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_frontpage_subreddits_no_response(self):
        flock.cache.get = mock.MagicMock(name='get', return_value=None)
        flock.urllib2.urlopen = mock.MagicMock(return_value=None)

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No Reddit response', response.data)

    def test_frontpage_subreddits_no_response_404(self):
        flock.cache.get = mock.MagicMock(name='get', return_value=None)
        def throw_404(url):
            raise urllib2.HTTPError(url, 404, 'Not found', None, None)
        flock.urllib2.urlopen = mock.MagicMock(side_effect=throw_404)

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No Reddit response', response.data)

    def test_frontpage_subreddits_reddit_error(self):
        response_string = u'{ "error" : {} }'
        flock.cache.get = mock.MagicMock(name='get', return_value=None)
        flock.urllib2.urlopen = mock.MagicMock(return_value=io.StringIO(response_string))

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No Reddit response', response.data)

    def test_frontpage_subreddits_invalid_json(self):
        return_value = io.StringIO(u'<html></html>')
        flock.cache.get = mock.MagicMock(name='get', return_value=None)
        flock.urllib2.urlopen = mock.MagicMock(return_value=return_value)

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('No Reddit response', response.data)

    def test_frontpage_subreddits_no_youtube_links(self):
        return_value = io.StringIO(json.dumps(self.futuregarage_top, ensure_ascii=False))
        flock.urllib2.urlopen = mock.MagicMock(return_value=return_value)

        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        for child in self.futuregarage_top['data']['children']:
            child = child['data']
            if not 'youtube' in child['domain'] and not 'youtu.be' in child['domain']:
                self.assertNotIn(child['title'], response.data)

    def test_parse_reddit_response(self):
        futuregarage_links = flock.parseRedditResponse(self.futuregarage_top)
        futuregarage_links = [ child['title'] for child in futuregarage_links ]
        for child in self.futuregarage_top['data']['children']:
            child = child['data']
            if not 'youtube' in child['domain'] and not 'youtu.be' in child['domain']:
                self.assertNotIn(child['title'], futuregarage_links)

    def test_frontpage_subreddits_all_links_present(self):
        h = HTMLParser.HTMLParser()
        futuregarage_links = flock.parseRedditResponse(self.futuregarage_top)

        return_value = io.StringIO(json.dumps(self.futuregarage_top, ensure_ascii=False))
        flock.urllib2.urlopen = mock.MagicMock(return_value=return_value)
    
        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        response = self.app.get('/?subreddits=futuregarage',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)

        unescaped_response = h.unescape(response.data)
        for child in futuregarage_links:
            self.assertIn(child['title'], unescaped_response)
            self.assertIn(child['url'], unescaped_response)
            self.assertIn(child['permalink'], unescaped_response)

class SanitiseURLCase(unittest.TestCase):
    def test_sanitise_short_youtube_url(self):
        url = 'http://youtu.be/wRpHf4X7FNM'
        new_url = flock.sanitiseShortYouTubeURL(url)
        self.assertEquals(new_url, 'http://www.youtube.com/watch?v=wRpHf4X7FNM')

    def test_sanitise_short_youtube_url_fail_long(self):
        url = 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
        new_url = flock.sanitiseShortYouTubeURL(url)
        self.assertEquals(new_url, None)

    def test_sanitise_short_youtube_url_fail_wrong(self):
        url = 'http://i.imgur.com/2A2IS5z.jpg'
        new_url = flock.sanitiseShortYouTubeURL(url)
        self.assertEquals(new_url, None)

    def test_sanitise_short_youtube_url_fail_no_videoid(self):
        url = 'http://youtu.be/'
        new_url = flock.sanitiseShortYouTubeURL(url)
        self.assertEquals(new_url, None)

    def test_sanitise_long_youtube_url(self):
        url = 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
        new_url = flock.sanitiseYouTubeURL(url)
        self.assertEquals(new_url, 'http://www.youtube.com/watch?v=wRpHf4X7FNM')

    def test_sanitise_long_youtube_url_fail_short(self):
        url = 'http://youtu.be/wRpHf4X7FNM'
        new_url = flock.sanitiseYouTubeURL(url)
        self.assertEquals(new_url, None)

    def test_sanitise_long_youtube_url_fail_wrong(self):
        url = 'http://i.imgur.com/2A2IS5z.jpg'
        new_url = flock.sanitiseYouTubeURL(url)
        self.assertEquals(new_url, None)

    def test_sanitise_youtube_url_short_input(self):
        url = 'http://youtu.be/wRpHf4X7FNM'
        new_url = flock.sanitiseURL(url)
        self.assertEquals(new_url, 'http://www.youtube.com/watch?v=wRpHf4X7FNM')

    def test_sanitise_youtube_url_long_input(self):
        url = 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
        new_url = flock.sanitiseURL(url)
        self.assertEquals(new_url, 'http://www.youtube.com/watch?v=wRpHf4X7FNM')

    def test_sanitise_youtube_url_fail(self):
        url = 'http://i.imgur.com/2A2IS5z.jpg'
        new_url = flock.sanitiseURL(url)
        self.assertEquals(new_url, None)

class YouTubeEmbedURLTestCase(unittest.TestCase):
    def test_generate_youtube_embed_url_one_link(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        youtube_url = flock.generateYouTubeURL(links)
        expected = 'https://www.youtube.com/embed/wRpHf4X7FNM?playlist=&showinfo=1&modestbranding=1&enablejsapi=1&version=3&autohide=0&rel=0'
        self.assertEquals(youtube_url, expected)

    def test_generate_youtube_embed_url_two_links(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        youtube_url = flock.generateYouTubeURL(links)
        expected = 'https://www.youtube.com/embed/wRpHf4X7FNM?playlist=wRpHf4X7FNM&showinfo=1&modestbranding=1&enablejsapi=1&version=3&autohide=0&rel=0'
        self.assertEquals(youtube_url, expected)

    def test_generate_youtube_embed_url_multiple_links(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        youtube_url = flock.generateYouTubeURL(links)
        expected = 'https://www.youtube.com/embed/wRpHf4X7FNM?playlist=wRpHf4X7FNM%2CwRpHf4X7FNM&showinfo=1&modestbranding=1&enablejsapi=1&version=3&autohide=0&rel=0'
        self.assertEquals(youtube_url, expected)

    def test_generate_youtube_embed_url_missing_videoid(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/v/wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        youtube_url = flock.generateYouTubeURL(links)
        expected = 'https://www.youtube.com/embed/wRpHf4X7FNM?playlist=wRpHf4X7FNM&showinfo=1&modestbranding=1&enablejsapi=1&version=3&autohide=0&rel=0'
        self.assertEquals(youtube_url, expected)


class DuplicatesTestCase(unittest.TestCase):
    def test_remove_duplicates_one_link(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        new_links = flock.removeDuplicates(links)
        self.assertEquals(new_links, links)

    def test_remove_duplicates_duplicate_links(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    }
                ]
        new_links = flock.removeDuplicates(links)
        del links[1]
        self.assertEquals(new_links, links)

    def test_remove_duplicates_non_duplicate_links(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=eAUaOTLvBIM'
                    }
                ]
        new_links = flock.removeDuplicates(links)
        self.assertEquals(new_links, links)

    def test_remove_duplicates_duplicate_links_order_preserved(self):
        links = [
                {
                    'url' : 'http://www.youtube.com/watch?v=AY08MWIGYsk'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
                    },
                {
                    'url' : 'http://www.youtube.com/watch?v=cfLmW-dKtwg'
                    }
                ]
        new_links = flock.removeDuplicates(links)
        del links[2]
        self.assertEquals(new_links, links)


class OptionalPlaylistOptionsTestCase(FlockBaseTestCase):
    def test_accepts_valid_optional_arguments(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=50',
                                content_type='text/html',
                                follow_redirects=True)

        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
        self.assertEqual(response.status_code, 200)

    def test_limit_argument_operates_on_reddit_results_post_parsing(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=2',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
        self.assertEqual(response.data.count('"track"'), 2)

    def test_unsupported_sort_argument(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&sort=error',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(flock.getRedditResponse.called)
        self.assertIn('Invalid sort type: error', response.data)

    def test_unsupported_time_argument(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&t=never',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(flock.getRedditResponse.called)
        self.assertIn('Invalid time type: never', response.data)

    def test_unsupported_limit_argument(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&limit=1000',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(flock.getRedditResponse.called)
        self.assertIn('Invalid limit: 1000', response.data)

    def test_unsupported_limit_string_argument(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        response = self.app.get('/?subreddits=futuregarage&limit=never',
                                content_type='text/html',
                                follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(flock.getRedditResponse.called)
        self.assertTrue('Invalid limit: never', response.data)


class CacheTestCase(FlockBaseTestCase):
    def test_frontpage_hits_memcached(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',              
                                                 return_value=self.futuregarage_top)

        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        response = self.app.get('/?subreddits=futuregarage', follow_redirects=True)

        self.assertEquals(response.status_code, 200)
        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'week', 100)
        flock.cache.get.assert_called_once_with('futuregarage+hot+week')

    def test_frontpage_hits_memcached_same_number_of_times_as_subreddits(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        response = self.app.get('/?subreddits=1+2+3+4+5', follow_redirects=True)

        self.assertEquals(response.status_code, 200)
        flock.getRedditResponse.assert_called_once_with(['1', '2', '3', '4', '5'], 'hot', 'week', 100)
        self.assertEquals(flock.cache.get.call_count, 5)


    def test_frontpage_hits_memcached_same_number_of_times_as_subreddits_with_names(self):
        return_value = flock.parseRedditResponse(self.futuregarage_top)

        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=None)

        flock.cache.get = mock.MagicMock(name='get', return_value=pickle.dumps(return_value))

        response = self.app.get('/?subreddits=1+2+3+4+5', follow_redirects=True)

        self.assertEquals(response.status_code, 200)
        self.assertFalse(flock.getRedditResponse.called)
        calls = [ mock.call('1+hot+week'), 
                mock.call('2+hot+week'),
                mock.call('3+hot+week'),
                mock.call('4+hot+week'),
                mock.call('5+hot+week') ]
        flock.cache.get.assert_has_calls(calls)
    
    def test_link_sort_order_is_maintained_top(self):
        h = HTMLParser.HTMLParser()
        futuregarage_links = flock.parseRedditResponse(self.futuregarage_top)
        futuregarage_links = sorted(futuregarage_links,
                                    reverse=True,
                                    key=lambda l: l['created_utc'])
        futuregarage_links = sorted(futuregarage_links,
                                    reverse=True,
                                    key=lambda l: flock.top(l))

        cache_value = {}
        cache_value['data'] = {}
        cache_value['data']['children'] = {}
        cache_value['data']['children'] = self.futuregarage_top['data']['children'][::2]
        cache_value = flock.parseRedditResponse(cache_value)

        def cache_side_effect(*args, **kwargs):
            if args[0] == 'futuregarage+top+week':
                return pickle.dumps(cache_value)
            return None

        flock.cache.get = mock.MagicMock(name='get')
        flock.cache.get.side_effect = cache_side_effect
        
        reddit_value = {}
        reddit_value['data'] = {}
        reddit_value['data']['children'] = {}
        reddit_value['data']['children'] = self.futuregarage_top['data']['children'][1::2]
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=reddit_value)

        response = self.app.get('/?subreddits=futuregarage+futurebeats&sort=top', follow_redirects=True)

        unescaped_response = h.unescape(response.data)
        for child in futuregarage_links:
            self.assertIn(child['title'], unescaped_response)
            self.assertIn(child['url'], unescaped_response)
            self.assertIn(child['permalink'], unescaped_response)

        j = 1
        for i,child in enumerate(futuregarage_links):
            first_child = futuregarage_links[i]
            second_child = futuregarage_links[j]
            first_pos = unescaped_response.find(first_child['title'])
            second_pos = unescaped_response.find(second_child['title'])
            self.assertLess(first_pos, second_pos,
                '%s:%d, %s:%d' % (first_child['title'], flock.top(first_child),
                                  second_child['title'], flock.top(second_child)))
            j = j + 1
            if j >= len(futuregarage_links):
                break

    def test_link_sort_order_is_maintained_hot(self):
        h = HTMLParser.HTMLParser()
        futuregarage_links = flock.parseRedditResponse(self.futuregarage_top)
        futuregarage_links = sorted(futuregarage_links,
                                    reverse=True,
                                    key=lambda l: l['created_utc'])
        futuregarage_links = sorted(futuregarage_links,
                                    reverse=True,
                                    key=lambda l: flock.hot(l))

        cache_value = {}
        cache_value['data'] = {}
        cache_value['data']['children'] = {}
        cache_value['data']['children'] = self.futuregarage_top['data']['children'][::2]
        cache_value = flock.parseRedditResponse(cache_value)

        def cache_side_effect(*args, **kwargs):
            if args[0] == 'futuregarage+hot+week':
                return pickle.dumps(cache_value)
            return None

        flock.cache.get = mock.MagicMock(name='get')
        flock.cache.get.side_effect = cache_side_effect
        
        reddit_value = {}
        reddit_value['data'] = {}
        reddit_value['data']['children'] = {}
        reddit_value['data']['children'] = self.futuregarage_top['data']['children'][1::2]
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=reddit_value)

        response = self.app.get('/?subreddits=futuregarage+futurebeats&sort=hot', follow_redirects=True)

        unescaped_response = h.unescape(response.data)
        for child in futuregarage_links:
            self.assertIn(child['title'], unescaped_response)
            self.assertIn(child['url'], unescaped_response)
            self.assertIn(child['permalink'], unescaped_response)

        j = 1
        for i,child in enumerate(futuregarage_links):
            first_child = futuregarage_links[i]
            second_child = futuregarage_links[j]
            first_pos = unescaped_response.find(first_child['title'])
            second_pos = unescaped_response.find(second_child['title'])
            self.assertLess(first_pos, second_pos,
                '%s:%d, %s:%d' % (first_child['title'], flock.top(first_child),
                                  second_child['title'], flock.top(second_child)))
            j = j + 1
            if j >= len(futuregarage_links):
                break

    def test_cache_is_heated_with_parsed_links(self):
        cache_value = flock.parseRedditResponse(self.futuregarage_top)
        
        flock.cache.set = mock.MagicMock(name='set')
        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        self.app.get('/?subreddits=futuregarage', follow_redirects=True)

        flock.cache.set.assert_called_with('futuregarage+hot+week', pickle.dumps(cache_value))

    def test_cache_is_hit_after_cache_is_warmed(self):
        cache_value = flock.parseRedditResponse(self.futuregarage_top)

        flock.cache.set = mock.MagicMock(name='set')
        flock.cache.get = mock.MagicMock(name='get', return_value=None)

        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
                                                 return_value=self.futuregarage_top)

        self.app.get('/?subreddits=futuregarage', follow_redirects=True)

        flock.getRedditResponse.assert_called_with(['futuregarage'], 'hot', 'week', 100)
        flock.cache.set.assert_called_with('futuregarage+hot+week', pickle.dumps(cache_value))

        flock.cache.get = mock.MagicMock(name='get', return_value=pickle.dumps(cache_value))
        flock.cache.set = mock.MagicMock(name='set')
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse')

        self.app.get('/?subreddits=futuregarage', follow_redirects=True)

        flock.cache.get.assert_called_with('futuregarage+hot+week')
        self.assertEqual(flock.getRedditResponse.call_count, 0)
        self.assertEqual(flock.cache.set.call_count, 0)


class SubredditListTestCase(FlockBaseTestCase):
    def setUp(self):
        FlockBaseTestCase.setUp(self)

        flock.getSubredditList = self.original_getSubredditList
        flock.urllib2.urlopen = mock.MagicMock(return_value=io.StringIO(self.kimono_data))

    def tearDown(self):
        FlockBaseTestCase.tearDown(self)
        flock.urllib2.urlopen = self.original_urlopen

    def test_subreddits_are_parsed(self):
        subreddit_list = flock.getSubredditList()
        self.assertItemsEqual(subreddit_list, self.subreddit_list)

    def test_cache_is_warmed_when_cold(self):
        flock.cache.get = mock.MagicMock(return_value=None)
        flock.cache.set = mock.MagicMock()

        subreddit_list = flock.getSubredditList()

        self.assertTrue(flock.urllib2.urlopen.called)
        flock.cache.set.assert_called_with('subreddits',
                                           pickle.dumps(subreddit_list),
                                           timeout=60*60*24*7)

    def test_no_urlopen_when_cache_is_hot(self):
        flock.cache.get = mock.MagicMock(return_value=pickle.dumps(self.subreddit_list))
        subreddit_list = flock.getSubredditList()

        self.assertFalse(flock.urllib2.urlopen.called)

        self.assertItemsEqual(subreddit_list, self.subreddit_list)

    def test_no_kimono_response(self):
        flock.urllib2.urlopen = mock.MagicMock(side_effect=IOError)
        subreddit_list = flock.getSubredditList()
        self.assertEqual(subreddit_list, [])

    def test_no_kimono_result(self):
        flock.urllib2.urlopen = mock.MagicMock(return_value=io.StringIO(u'{}'))
        subreddit_list = flock.getSubredditList()
        self.assertEqual(subreddit_list, [])

    def test_invalid_kimono_result(self):
        flock.urllib2.urlopen = mock.MagicMock(return_value=io.StringIO(u'<xml/>'))
        subreddit_list = flock.getSubredditList()
        self.assertEqual(subreddit_list, [])


class RateLimitTestCase(FlockBaseTestCase):
    def setUp(self):
        FlockBaseTestCase.setUp(self)

    def tearDown(self):
        FlockBaseTestCase.tearDown(self)

    def test_rate_limit_call_waits_set_seconds_before_second_attempt(self):
        before_call = datetime.datetime.now()
        response = flock.rateLimitedRequest('http://url.com', 1.0)
        response = flock.rateLimitedRequest('http://url.com', 1.0)
        after_call = datetime.datetime.now()
        delta = after_call - before_call
        self.assertGreaterEqual(delta.seconds, 1.0)

    def test_rate_limit_call_waits_no_longer_than_timeout_for_second_request(self):
        before_call = datetime.datetime.now()
        response = flock.rateLimitedRequest('http://url.com', 1.0)
        response = flock.rateLimitedRequest('http://url.com', 1.0)
        after_call = datetime.datetime.now()
        delta = after_call - before_call
        self.assertLess(delta.seconds, 2.0)

    def test_rate_limit_calls_urlopen_when_timeout_has_passed(self):
        response = flock.rateLimitedRequest('url', 1.0)
        self.assertEqual(flock.urllib2.urlopen.call_count, 1)

    def test_rate_limit_returns_urlopen_reponse(self):
        urlopen_response = io.StringIO(u'{}')
        flock.urllib2.urlopen = mock.MagicMock(return_value=urlopen_response)
        response = flock.rateLimitedRequest('url', 1.0)
        self.assertEquals(response, urlopen_response)

    def test_rate_limit_only_applies_to_same_url(self):
        before_call = datetime.datetime.now()
        response1 = flock.rateLimitedRequest('http://url1.com', 5.0)
        response2 = flock.rateLimitedRequest('http://url2.com', 5.0)
        after_call = datetime.datetime.now()
        delta = after_call - before_call
        self.assertLess(delta.seconds, 5.0)


if __name__ == '__main__':
    unittest.main()
