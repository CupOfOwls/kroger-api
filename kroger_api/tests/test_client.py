import unittest
from unittest.mock import patch, MagicMock
from urllib.parse import parse_qs, urlsplit
from kroger_api.client import KrogerClient

class TestKrogerClient(unittest.TestCase):

    def setUp(self):
        self.client = KrogerClient(client_id="fake_id", client_secret="fake_secret", redirect_uri="http://redirect.uri")

    def test_get_authorization_url_basic(self):
        url = self.client.get_authorization_url(scope="openid profile")
        self.assertIn("scope=openid%20profile", url)
        self.assertIn("client_id=fake_id", url)
        self.assertIn("redirect_uri=http%3A%2F%2Fredirect.uri", url)

    def test_get_authorization_url_encodes_every_value(self):
        client = KrogerClient(client_id="fake_id", client_secret="fake_secret",
                              redirect_uri="http://localhost:8000/callback?app=a&b=c")
        url = client.get_authorization_url(scope="cart.basic:write profile.compact", state="a&b=c d",
                                           code_challenge="abc-_", code_challenge_method="S256")
        self.assertTrue(url.startswith("https://api.kroger.com/v1/connect/oauth2/authorize?"))
        self.assertEqual(parse_qs(urlsplit(url).query), {
            "scope": ["cart.basic:write profile.compact"],
            "client_id": ["fake_id"],
            "redirect_uri": ["http://localhost:8000/callback?app=a&b=c"],
            "response_type": ["code"],
            "state": ["a&b=c d"],
            "code_challenge": ["abc-_"],
            "code_challenge_method": ["S256"],
        })

    @patch('kroger_api.client.load_token')
    @patch('kroger_api.client.save_token')
    @patch('kroger_api.client.requests.request')
    
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