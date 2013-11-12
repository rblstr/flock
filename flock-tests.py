import unittest
import flock
import json

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


class FrontpageTestCase(unittest.TestCase):
    def setUp(self):
        flock.app.testing = True
        self.app = flock.app.test_client()

    def tearDown(self):
        flock.getRedditResponse = original_getRedditResponse

    def test_frontpage(self):
        response = self.app.get('/', content_type='text/html')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_subreddits(self):
        flock.getRedditResponse = mock_getRedditResponse_no_response
        response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('No Reddit response' in response.data)
    
    def test_frontpage_no_youtube_links(self):
        flock.getRedditResponse = mock_getRedditResponse_no_youtube_links
        response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('No links found' in response.data)

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

if __name__ == '__main__':
    unittest.main()
