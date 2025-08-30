# 🛒 Kroger Public API 🛍️  --  with Examples in Python 🐍

A comprehensive Python client library for the Kroger Public API, featuring robust token management, comprehensive examples, and easy-to-use interfaces for all available endpoints.

## 📺 Demo

Adding an item to your cart via an interactive Python script, and checking that it appears in your account:

https://github.com/user-attachments/assets/0079cbc7-5af0-473b-909a-d43508fe43d5

You can also check out [kroger-mcp](https://github.com/CupOfOwls/kroger-mcp), which is an implementation of the Model Context Protocol leveraging this kroger-api package!

## 🚀 Quick Start

### Installation

#### From PyPI (Recommended)
```bash
pip install kroger-api
```

#### From Source
```bash
git clone https://github.com/CupOfOwls/kroger-api.git
cd kroger-api
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Basic Usage

```python
from kroger_api import KrogerAPI
from kroger_api.utils.env import load_and_validate_env, get_zip_code

# Env -- set in .env
load_and_validate_env(["KROGER_CLIENT_ID", "KROGER_CLIENT_SECRET"])
zip_code = get_zip_code(default="10001")

# Initialize the client
kroger = KrogerAPI()

# Get a client credentials token for public data
token_info = kroger.authorization.get_token_with_client_credentials("product.compact")

locations = kroger.location.search_locations(
                zip_code=zip_code,
                radius_in_miles=10,
                limit=1
            )

# Search for products
products = kroger.product.search_products(
        term="milk",
        location_id=locations["data"][0]["locationId"],
        limit=5
    )

print(f"Found {len(products['data'])} products!")
```

## 🔐 Getting Started with Credentials

### 1. Create a Kroger Developer Account
Visit the [Kroger Developer Portal](https://developer.kroger.com/manage/apps/register) to:
1. Create a developer account
2. Register your application
3. Get your `CLIENT_ID`, `CLIENT_SECRET`, and set your `REDIRECT_URI`

### 2. Set Up Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```bash
# Kroger API Credentials
KROGER_CLIENT_ID=your_client_id_here
KROGER_CLIENT_SECRET=your_client_secret_here
KROGER_REDIRECT_URI=http://localhost:8000/callback

# Optional (Recommended): Your zip code for location-based searches
KROGER_USER_ZIP_CODE=90210
```

**Important:** Set your `KROGER_REDIRECT_URI` during app registration. While marked as optional in the form, the OAuth flow requires it.

### 3. First Run Authorization
The first time you run a script requiring user authentication, you'll be prompted to authorize your app through your web browser. You're granting permission to **your own registered app**, not to any third party.

## 🔄 Token Management

This library implements robust, automatic token management:

### ✨ Features
- **Automatic token refresh** - No manual token handling required
- **Persistent storage** - Tokens saved securely to avoid repeated logins  
- **Proactive validation** - Tests tokens before use
- **Reactive recovery** - Automatically refreshes expired tokens during API calls
- **PKCE Support** - Enhanced OAuth security with Proof Key for Code Exchange

### 🔧 How it Works

**Proactive Approach:**
1. Loads saved tokens and tests them with a lightweight API request
2. Automatically refreshes if token is expired and refresh token is available

**Reactive Approach:**
1. Makes API requests with current token
2. On 401 Unauthorized errors, attempts token refresh
3. Retries original request with new token

Token files (automatically managed):
- `.kroger_token_client_product.compact.json` - Client credentials tokens
- `.kroger_token_user.json` - User authorization tokens

These tokens are stored in XDG_DATA_HOME/local/share/kroger-mcp/ on Unix-like machines or APPDATA/kroger-mcp/ on Windows machines.

### 🔒 Enhanced Security with PKCE

This library supports PKCE (Proof Key for Code Exchange) for enhanced security in the OAuth flow:

```python
from kroger_api import KrogerAPI
from kroger_api.utils import generate_pkce_parameters

# Generate PKCE parameters
pkce_params = generate_pkce_parameters()

# Initialize the client
kroger = KrogerAPI()

# Get authorization URL with PKCE
auth_url = kroger.authorization.get_authorization_url(
    scope="cart.basic:write profile.compact",
    state="random_state_value",
    code_challenge=pkce_params['code_challenge'],
    code_challenge_method=pkce_params['code_challenge_method']
)

# After user authorization and redirect, exchange code for token with verifier
token_info = kroger.authorization.get_token_with_authorization_code(
    code="authorization_code_from_redirect",
    code_verifier=pkce_params['code_verifier']
)
```

PKCE helps protect against authorization code interception attacks, particularly important for public clients or those using external tools to manage OAuth flows.

## 📚 Example Scripts

The `examples/` directory contains comprehensive demonstrations:

| Script | Description | Authentication Required |
|--------|-------------|------------------------|
| `location_api_examples.py` | Search stores, get details about locations, chains, and departments | Client credentials |
| `product_api_examples.py` | Search products, get details, filter by various criteria | Client credentials |
| `cart_api_examples.py` | Add items to user's cart, full shopping workflow | User authorization |
| `identity_api_examples.py` | Get user profile information | User authorization |
| `oauth_flow.py` | Complete OAuth2 authorization code flow example | User authorization |
| `token_refresh_example.py` | Demonstrates automatic token refresh functionality | Both |
| `authorization_api_examples.py` | All authorization endpoints and flows | Both |
| `clear_tokens.py` | Utility to delete all saved token files | None |

### 🏃‍♂️ Running Examples

```bash
# Make sure your .env file is configured first!

# Public API examples (no user login required)
python examples/location_api_examples.py
python examples/product_api_examples.py

# User-specific examples (requires browser login)
python examples/cart_api_examples.py
python examples/identity_api_examples.py
python examples/oauth_flow.py

# Utility scripts
python examples/clear_tokens.py  # Clear saved tokens
```

Here's a quick demo of browsing via the Product API with `examples/product_api_examples.py`:

<div align="center">
  <img src="assets/product_api_script.gif" alt="Kroger API Python Demo">
</div>

## 🏪 Kroger Public API Information

### API Versions & Rate Limits

| API | Version | Rate Limit | Notes |
|-----|---------|------------|-------|
| **Authorization** | 1.0.13 | No specific limit | Token management |
| **Products** | 1.2.4 | 10,000 calls/day | Search and product details |
| **Locations** | 1.2.2 | 1,600 calls/day per endpoint | Store locations and details |
| **Cart** | 1.2.3 | 5,000 calls/day | Add/manage cart items |
| **Identity** | 1.2.3 | 5,000 calls/day | User profile information |

**Note:** Rate limits are enforced per endpoint, not per operation. You can distribute calls across operations using the same endpoint as needed.

### 🔑 Available Scopes

When requesting user authorization, you can specify these scopes:

- `product.compact` - Read product information
- `cart.basic:write` - Add items to cart  
- `profile.compact` - Read user profile information

## 📖 API Documentation

For complete API documentation, visit:
- [Kroger Developer Portal](https://developer.kroger.com/)
- [API Documentation](https://developer.kroger.com/documentation/public/)
- [Acceptable Use Policy](https://developer.kroger.com/documentation/public/getting-started/acceptable-use)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This is an unofficial Python client for the Kroger Public API. It is not affiliated with, endorsed by, or sponsored by Kroger.
