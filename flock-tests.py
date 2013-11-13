import unittest
import flock

""" Override getRedditResponse() """
original_getRedditResponse = flock.getRedditResponse

def mock_getRedditResponse_no_response(subreddits):
	return None

def mock_getRedditResponse_no_youtube_links(subreddits):
	return {
		'data' : {
			'children' : [
				{
					'data' : {
						'url' : 'imgur.com'
					}
				}
			]
		}
	}

def mock_getRedditResponse_set_response(subreddits):
	return {
		'data' : {
			'children' : [
				{
					'data' : {
						'title' : 'Burial - Untrue (Full Album Mix)',
						'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
					}
				},
				{
					'data' : {
						'title' : 'Sage The Gemini - Gas Pedal (Motez Edit)',
						'url' : 'http://www.youtube.com/watch?v=cfLmW-dKtwg'
					}
				},
				{
					'data' : {
						'title' : 'Koreless & Jacques Greene - Untitled',
						'url' : 'http://www.youtube.com/watch?v=AY08MWIGYsk'
					}
				}
			]
		}
	}


class FrontpageTestCase(unittest.TestCase):
	def setUp(self):
		flock.app.testing = True
		self.app = flock.app.test_client()

	def tearDown(self):
		flock.getRedditResponse = original_getRedditResponse

	def test_frontpage(self):
		response = self.app.get('/', content_type='text/html')
		self.assertEqual(response.status_code, 200)

	def test_frontpage_subreddits_no_response(self):
		flock.getRedditResponse = mock_getRedditResponse_no_response
		response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
		self.assertEqual(response.status_code, 200)
		self.assertTrue('No Reddit response' in response.data)

	def test_frontpage_subreddits_no_youtube_links(self):
		flock.getRedditResponse = mock_getRedditResponse_no_youtube_links
		response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
		self.assertEqual(response.status_code, 200)
		self.assertTrue('No links found' in response.data)
	
	def test_frontpage_subreddits_all_links_present(self):
		flock.getRedditResponse = mock_getRedditResponse_set_response
		response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
		self.assertEqual(response.status_code, 200)
		self.assertTrue('http://www.youtube.com/watch?v=wRpHf4X7FNM' in response.data)
		self.assertTrue('http://www.youtube.com/watch?v=cfLmW-dKtwg' in response.data)
		self.assertTrue('http://www.youtube.com/watch?v=AY08MWIGYsk' in response.data)

class SanitiseURLCase(unittest.TestCase):
	def test_sanitise_short_youtube_url(self):
		url = 'http://youtu.be/wRpHf4X7FNM'
		new_url = flock.sanitiseShortYouTubeURL(url)
		self.assertTrue('http://www.youtube.com/watch?v=wRpHf4X7FNM' == new_url)

	def test_sanitise_short_youtube_url_fail_long(self):
		url = 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
		new_url = flock.sanitiseShortYouTubeURL(url)
		self.assertEquals(new_url, None)

	def test_sanitise_short_youtube_url_fail_wrong(self):
		url = 'http://i.imgur.com/2A2IS5z.jpg'
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

""" replace getYouTubeResponse """
original_getYouTubeResponse = flock.getYouTubeResponse

def mock_getYouTubeResponse_no_reponse(links):
	return None

def mock_getYouTubeResponse_fixed_response(links):
	response_object = {
		'items' : [
			{
				'snippet' : {
					'title' : 'Burial - Untrue (Full Album Mix)'
				}
			}
		]
	}
	return response_object

class GetLinkTitlesTestCase(unittest.TestCase):
	def tearDown(self):
		flock.getYouTubeResponse = original_getYouTubeResponse

	def test_get_link_titles_no_response(self):
		flock.getYouTubeResponse = mock_getYouTubeResponse_no_reponse
		links = [
			{
				'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM',
				'title' : 'Burial - Untrue (Full Album Mix) This is six years old today! (X-post r/dubstep)'
			}
		]
		new_links = flock.getLinkTitles(links)
		self.assertEquals(new_links[0]['video_title'], links[0]['title'])

	def test_get_link_titles_response(self):
		flock.getYouTubeResponse = mock_getYouTubeResponse_fixed_response
		links = [
			{
				'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
			}
		]
		new_links = flock.getLinkTitles(links)
		self.assertEquals(new_links[0]['video_title'], 'Burial - Untrue (Full Album Mix)')

if __name__ == '__main__':
	unittest.main()

