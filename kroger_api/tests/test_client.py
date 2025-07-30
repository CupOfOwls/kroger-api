import unittest
from unittest.mock import patch, MagicMock
from kroger_api.client import KrogerClient

class TestKrogerClient(unittest.TestCase):

    def setUp(self):
        self.client = KrogerClient(client_id="fake_id", client_secret="fake_secret", redirect_uri="http://redirect.uri")

    def test_get_authorization_url_basic(self):
        url = self.client.get_authorization_url(scope="openid profile")
        self.assertIn("scope=openid profile", url)
        self.assertIn("client_id=fake_id", url)
        self.assertIn("redirect_uri=http://redirect.uri", url)

    @patch('kroger_api.client.load_token')
    @patch('kroger_api.client.save_token')
    @patch('kroger_api.client.requests.post')
    
    def test_get_token_with_client_credentials(self, mock_post, mock_save_token, mock_load_token):
        #mock load_token to return None
        mock_load_token.return_value = None
        
        #mock response from requests.post
        mock_response = MagicMock()
        mock_response.json.return_value = {"access_token": "abc123", "expires_in": 3600}
        mock_response.raise_for_status = lambda: None
        mock_post.return_value = mock_response
        
        token_info = self.client.get_token_with_client_credentials("scope1")
        
        self.assertEqual(token_info["access_token"], "abc123")
        mock_save_token.assert_called_once()

if __name__ == '__main__':
    unittest.main()