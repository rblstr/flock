import HTMLParser
import httplib
import json
import pickle
import time
import unittest
import mock
import flock


class MockHTTPResponseWithJSON(object):
	def __init__(self, status, response):
		self.status = status
		self.response = response
	
	def read(self):
		return self.response

class MockHTTPResponseWithError(object):
	def __init__(self, status):
		self.status = status
	
	def read(self):
		return '{ "error" : "" }'

class MockHTTPResponseWithInvalidJSON(object):
	def __init__(self, status):
		self.status = status
	
	def read(self):
		return '<html></html>'


class FlockBaseTestCase(unittest.TestCase):
	def setUp(self):
		flock.app.testing = True
		self.app = flock.app.test_client()
		test_json_handle = open('tests/futuregarage_top_week_100.json')
		self.futuregarage_top = json.load(test_json_handle)
		test_json_handle.close()
		test_json_handle = open('tests/futuregarage_hot_week_100.json')
		self.futuregarage_hot = json.load(test_json_handle)
		test_json_handle.close()
		self.original_getRedditResponse = flock.getRedditResponse
		self.original_cache_get = flock.cache.get
		self.original_cache_set = flock.cache.set
		self.original_request = flock.httplib.HTTPConnection.request
		flock.httplib.HTTPConnection.request = mock.MagicMock(name='request')
		self.original_response = flock.httplib.HTTPConnection.getresponse
	
	def tearDown(self):
		flock.getRedditResponse = self.original_getRedditResponse
		flock.cache.get = self.original_cache_get
		flock.cache.set = self.original_cache_set
		flock.httplib.HTTPConnection.request = self.original_request
		flock.httplib.HTTPConnection.getresponse = self.original_response


class FrontpageTestCase(FlockBaseTestCase):
	def test_frontpage(self):
		response = self.app.get('/', content_type='text/html', follow_redirects=True)
		self.assertEqual(response.status_code, 200)

	def test_frontpage_subreddits_no_response(self):
		flock.cache.get = mock.MagicMock(name='get', return_value=None)
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(name='getresponse',
																  return_value=None)

		response = self.app.get('/?subreddits=futuregarage',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('No Reddit response', response.data)

	def test_frontpage_subreddits_no_response_404(self):
		flock.cache.get = mock.MagicMock(name='get', return_value=None)
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(name='getresponse',
												return_value=MockHTTPResponseWithJSON(404, ''))

		response = self.app.get('/?subreddits=futuregarage',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('No Reddit response', response.data)

	def test_frontpage_subreddits_reddit_error(self):
		flock.cache.get = mock.MagicMock(name='get', return_value=None)
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(name='getresponse',
													return_value=MockHTTPResponseWithError(200))

		response = self.app.get('/?subreddits=futuregarage',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('No Reddit response', response.data)

	def test_frontpage_subreddits_invalid_json(self):
		flock.cache.get = mock.MagicMock(name='get', return_value=None)
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(name='getresponse',
											return_value=MockHTTPResponseWithInvalidJSON(200))

		response = self.app.get('/?subreddits=futuregarage',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('No Reddit response', response.data)

	def test_frontpage_subreddits_no_youtube_links(self):
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(
							name='getresponse ',
							return_value=MockHTTPResponseWithJSON(200, json.dumps(self.futuregarage_top)))
		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		response = self.app.get('/?subreddits=futuregarage',
				                content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertNotIn('RA News: New Burial EP set for December', response.data)

	def test_frontpage_subreddits_all_links_present(self):
		h = HTMLParser.HTMLParser()
		futuregarage_links = flock.parseRedditResponse(self.futuregarage_top)

		flock.httplib.HTTPConnection.request = mock.MagicMock(name='request')
		flock.httplib.HTTPConnection.getresponse = mock.MagicMock(
							name='getresponse ',
							return_value=MockHTTPResponseWithJSON(200, json.dumps(self.futuregarage_top)))
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
		expected = 'http://www.youtube.com/embed/wRpHf4X7FNM?modestbranding=1&playlist=&showinfo=1&autohide=0&rel=0'
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
		expected = 'http://www.youtube.com/embed/wRpHf4X7FNM?modestbranding=1&playlist=wRpHf4X7FNM&showinfo=1&autohide=0&rel=0'
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
		expected = 'http://www.youtube.com/embed/wRpHf4X7FNM?modestbranding=1&playlist=wRpHf4X7FNM%2CwRpHf4X7FNM&showinfo=1&autohide=0&rel=0'
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
		expected = 'http://www.youtube.com/embed/wRpHf4X7FNM?modestbranding=1&playlist=wRpHf4X7FNM&showinfo=1&autohide=0&rel=0'
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
		flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)
		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=50',
								content_type='text/html',
								follow_redirects=True)

		flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
		self.assertEqual(response.status_code, 200)

	def test_limit_argument_operates_on_reddit_results_post_parsing(self):
		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
												 return_value=self.futuregarage_top)
		flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)
		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=2',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
		self.assertEqual(response.data.count('"track"'), 2)

	def test_unsupported_sort_argument(self):
		response = self.app.get('/?subreddits=futuregarage&sort=error',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('Invalid sort type: error', response.data)

	def test_unsupported_time_argument(self):
		response = self.app.get('/?subreddits=futuregarage&t=never',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('Invalid time type: never', response.data)

	def test_unsupported_limit_argument(self):
		response = self.app.get('/?subreddits=futuregarage&limit=1000',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertIn('Invalid limit: 1000', response.data)

	def test_unsupported_limit_string_argument(self):
		response = self.app.get('/?subreddits=futuregarage&limit=never',
								content_type='text/html',
								follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertTrue('Invalid limit: never', response.data)


class CacheTestCase(FlockBaseTestCase):
	def test_frontpage_hits_memcached(self):
		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',				
												 return_value=self.futuregarage_top)

		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		response = self.app.get('/?subreddits=futuregarage', follow_redirects=True)

		self.assertEquals(response.status_code, 200)
		flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'top', 'week', 100)
		flock.cache.get.assert_called_once_with('futuregarage')

	def test_frontpage_hits_memcached_same_number_of_times_as_subreddits(self):
		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
												 return_value=self.futuregarage_top)

		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		response = self.app.get('/?subreddits=1+2+3+4+5', follow_redirects=True)

		self.assertEquals(response.status_code, 200)
		flock.getRedditResponse.assert_called_once_with(['1', '2', '3', '4', '5'], 'top', 'week', 100)
		self.assertEquals(flock.cache.get.call_count, 5)


	def test_frontpage_hits_memcached_same_number_of_times_as_subreddits_with_names(self):
		return_value = flock.parseRedditResponse(self.futuregarage_top)

		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=None)

		flock.cache.get = mock.MagicMock(name='get', return_value=pickle.dumps(return_value))

		response = self.app.get('/?subreddits=1+2+3+4+5', follow_redirects=True)

		self.assertEquals(response.status_code, 200)
		self.assertFalse(flock.getRedditResponse.called)
		calls = [ mock.call('1'), 
				mock.call('2'),
				mock.call('3'),
				mock.call('4'),
				mock.call('5') ]
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
			if args[0] == 'futuregarage':
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

		response = self.app.get('/?subreddits=futuregarage+futurebeats', follow_redirects=True)

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
			if args[0] == 'futuregarage':
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

		flock.cache.set.assert_called_with('futuregarage', pickle.dumps(cache_value))

	def test_cache_is_hit_after_cache_is_warmed(self):
		cache_value = flock.parseRedditResponse(self.futuregarage_top)

		flock.cache.set = mock.MagicMock(name='set')
		flock.cache.get = mock.MagicMock(name='get', return_value=None)

		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse',
												 return_value=self.futuregarage_top)

		self.app.get('/?subreddits=futuregarage', follow_redirects=True)

		flock.getRedditResponse.assert_called_with(['futuregarage'], 'top', 'week', 100)
		flock.cache.set.assert_called_with('futuregarage', pickle.dumps(cache_value))

		flock.cache.get = mock.MagicMock(name='get', return_value=pickle.dumps(cache_value))
		flock.cache.set = mock.MagicMock(name='set')
		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse')

		self.app.get('/?subreddits=futuregarage', follow_redirects=True)

		flock.cache.get.assert_called_with('futuregarage')
		self.assertEqual(flock.getRedditResponse.call_count, 0)
		self.assertEqual(flock.cache.set.call_count, 0)


if __name__ == '__main__':
	unittest.main()

