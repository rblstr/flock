import unittest
import flock
import json

""" Override getRedditResponse() """
def mock_getRedditResponse_no_response(subreddits):
    return None


class FrontpageTestCase(unittest.TestCase):
    def setUp(self):
        flock.app.testing = True
        self.app = flock.app.test_client()

    def test_frontpage(self):
        response = self.app.get('/', content_type='text/html')
        self.assertEqual(response.status_code, 200)

    def test_frontpage_subreddits(self):
        flock.getRedditResponse = mock_getRedditResponse_no_response
        response = self.app.get('/?subreddits=futuregarage', content_type='text/html')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('No Reddit response' in response.data)

if __name__ == '__main__':
    unittest.main()
