import unittest
import mock
import flock


class FrontpageTestCase(unittest.TestCase):
    def setUp(self):
        flock.app.testing = True
        self.app = flock.app.test_client()

    def test_frontpage(self):
        response = self.app.get('/', content_type='text/html', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

    def test_frontpage_subreddits_no_response(self):
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=None)

        response = self.app.get('/?subreddits=futuregarage', content_type='text/html', follow_redirects=True)

        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'top', 'week', 100)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('No Reddit response' in response.data)

    def test_frontpage_subreddits_no_youtube_links(self):
        return_value = {
            'data' : {
                'children' : [
                    {
                        'data' : 
						{
                            'url' : 'imgur.com'
                        }
                    }
                ]
            }
        }

        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=return_value)

        response = self.app.get('/?subreddits=futuregarage', content_type='text/html', follow_redirects=True)

        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'top', 'week', 100)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('No links found' in response.data)
        
    def test_frontpage_subreddits_all_links_present(self):
        return_value = {
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
                            'url' : 'http://www.youtube.com/watch?v=AY08MWIGYsk',
                            'media' : 'adding a field to be pruned'
                        }
                    }
                ]
            }
        }
                
        flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=return_value)
        flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)

        response = self.app.get('/?subreddits=futuregarage', content_type='text/html', follow_redirects=True)

        flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'top', 'week', 100)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('http://www.youtube.com/watch?v=wRpHf4X7FNM' in response.data)
        self.assertTrue('Burial - Untrue (Full Album Mix)' in response.data)
        self.assertTrue('http://www.youtube.com/watch?v=cfLmW-dKtwg' in response.data)
        self.assertTrue('Sage The Gemini - Gas Pedal (Motez Edit)' in response.data)
        self.assertTrue('http://www.youtube.com/watch?v=AY08MWIGYsk' in response.data)
        self.assertTrue('Koreless &amp; Jacques Greene - Untitled' in response.data)

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


class GetLinkTitlesTestCase(unittest.TestCase):
    def test_get_link_titles_no_response(self):
        flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)

        links = [
            {
                'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM',
                'title' : 'Burial - Untrue (Full Album Mix) This is six years old today! (X-post r/dubstep)'
            }
        ]
        new_links = flock.getLinkTitles(links)

        flock.getYouTubeResponse.assert_called_once_with(links)
        self.assertEquals(new_links[0]['video_title'], links[0]['title'])

    def test_get_link_titles_response(self):
        return_value = {
            'items' : [
                {
                    'snippet' : {
                        'title' : 'Burial - Untrue (Full Album Mix)'
                    }
                }
            ]
        }
        flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=return_value)

        links = [
            {
                'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
            }
        ]
        new_links = flock.getLinkTitles(links)

        flock.getYouTubeResponse.assert_called_once_with(links)
        self.assertEquals(new_links[0]['video_title'], 'Burial - Untrue (Full Album Mix)')


class OptionalPlaylistOptionsTestCase(unittest.TestCase):
	def setUp(self):
		flock.app.testing = True
		self.app = flock.app.test_client()

	def test_accepts_valid_optional_arguments(self):
		return_value = {
			'data' : {
				'children' : [
					{
						'data' : {
							'title' : 'Burial - Untrue (Full Album Mix)',
							'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
						}
					}
				]
			}
		}
				
		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=return_value)
		flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)

		response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=50',
									content_type='text/html',
									follow_redirects=True)

		flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
		self.assertEqual(response.status_code, 200)

	def test_limit_argument_operates_on_reddit_results_post_parsing(self):
		return_value = {
			'data' : {
				'children' : [
					{
						'data' : {
							'title' : 'Burial - Untrue (Full Album Mix)',
							'url' : 'http://www.youtube.com/watch?v=wRpHf4X7FNM'
						}
					},
                    {
                        'data' : 
						{
                            'url' : 'imgur.com'
                        }
                    },
                    {
                        'data' : 
						{
                            'url' : 'imgur.com'
                        }
                    },
                    {
                        'data' : 
						{
                            'url' : 'imgur.com'
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
                            'url' : 'http://www.youtube.com/watch?v=AY08MWIGYsk',
                            'media' : 'adding a field to be pruned'
                        }
                    }
				]
			}
		}

		flock.getRedditResponse = mock.MagicMock(name='getRedditResponse', return_value=return_value)
		flock.getYouTubeResponse = mock.MagicMock(name='getYouTubeResponse', return_value=None)

		response = self.app.get('/?subreddits=futuregarage&sort=hot&t=month&limit=2',
									content_type='text/html',
									follow_redirects=True)

		flock.getRedditResponse.assert_called_once_with(['futuregarage'], 'hot', 'month', 100)
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data.count('"track"'), 2)
	
	def test_unsupported_sort_argument(self):
		response = self.app.get('/?subreddits=futuregarage&sort=error',
									content_type='text/html',
									follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertTrue('Invalid sort type: error' in response.data)

	def test_unsupported_time_argument(self):
		response = self.app.get('/?subreddits=futuregarage&t=never',
									content_type='text/html',
									follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertTrue('Invalid time type: never' in response.data)

	def test_unsupported_limit_argument(self):
		response = self.app.get('/?subreddits=futuregarage&limit=1000',
									content_type='text/html',
									follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertTrue('Invalid limit: 1000' in response.data)

	def test_unsupported_limit_string_argument(self):
		response = self.app.get('/?subreddits=futuregarage&limit=never',
									content_type='text/html',
									follow_redirects=True)

		self.assertEqual(response.status_code, 200)
		self.assertTrue('Invalid limit: never' in response.data)


if __name__ == '__main__':
        unittest.main()

