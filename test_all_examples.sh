# /usr/bin/bash

# This script runs all the examples in the examples directory.
# It assumes that the examples are in a directory called "examples" in the current directory.

source venv/bin/activate

python examples/cart_api_examples.py
python examples/identity_api_examples.py
python examples/location_api_examples.py
python examples/product_api_examples.py
python examples/authorization_api_examples.py
python examples/oauth_flow.py
python examples/oauth_pkce_flow.py
python examples/token_refresh_example.py