import datetime
import os
from typing import Dict, Any, Mapping, cast

import requests
from joserfc.jwk import import_key
from joserfc.jwt import encode

# --- Okta Configuration ---
# OKTA_ORG_URL = os.environ.get("OKTA_ORG_URL", "https://your-okta-domain.okta.com")
OKTA_TOKEN_ENDPOINT = "https://icanbwell.okta.com/oauth2/v1/token"

# --- Adam App Configuration (Initiator - gets the original tokens) ---
# This is mainly conceptual here, as the code starts with the already-obtained subject token.
ADAM_CLIENT_ID = os.environ.get("AUTH_CLIENT_ID")

# --- Bob App Configuration (Intermediary - performs the token exchange) ---
BOB_CLIENT_ID = os.environ.get("AUTH_TOKEN_EXCHANGE_CLIENT_ID")
# Bob's Private Key (PEM format, including BEGIN/END markers)
# IMPORTANT: Store this securely (e.g., in a secret manager or environment variable, NOT directly in code)
BOB_PRIVATE_KEY_PEM = os.environ.get("AUTH_TOKEN_EXCHANGE_PRIVATE_KEY")
BOB_KID = "RmGNhY3UD2_uGKL4k3hz6D086gRjTpx0L523fedkKB0"  # Key ID configured in Okta for Bob's app

# --- Charlie App Configuration (Target - whose token Bob wants to get) ---
CHARLIE_AUDIENCE = os.environ.get(
    "CHARLIE_AUDIENCE", "api://default"
)  # Audience for the new token

# --- Runtime Data ---
# The original token obtained by the Adam application for the user (ID Token or Access Token)
# This would be passed to Bob by Adam.
ADAM_SUBJECT_TOKEN = os.environ.get(
    "ADAM_SUBJECT_TOKEN", "your_adam_subject_token_here"
)


# --- Helper function for making POST requests ---
def make_post_request(
    url: str, headers: Dict[str, str], data: Mapping[str, str]
) -> Dict[str, Any] | None:
    content: str = ""
    try:
        response = requests.post(url, headers=headers, data=data, timeout=60)
        content = response.text
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        return cast(Dict[str, Any] | None, response.json())
    except requests.exceptions.HTTPError as err:
        print(f"HTTP Error: {err}")
        print(f"Response: {content}")
        return None
    except requests.exceptions.RequestException as err:
        print(f"Request Error: {err}")
        return None


# --- Generate Client Assertion JWT for Bob ---
def generate_bob_client_assertion_jwt(
    client_id: str, private_key_pem: str, token_endpoint_url: str
) -> str:
    # Load Bob's private key
    # private_key = serialization.load_pem_private_key(
    #     private_key_pem.encode('utf-8'),
    #     password=None,
    #     backend=default_backend()
    # )

    now = datetime.datetime.now(datetime.UTC)
    # JWT expiration should be short-lived, e.g., 5 minutes from now, according to Okta Developer https://developer.okta.com/docs/api/openapi/okta-oauth/guides/client-auth/
    # Okta may reject tokens with expiration too far in the future, according to Okta Developer Community https://devforum.okta.com/t/okta-python-sdk-client-assertion-expiration-woes/13348
    expiration_time = now + datetime.timedelta(minutes=5)

    # Required claims for the client assertion JWT, according to Okta Developer https://developer.okta.com/docs/guides/build-self-signed-jwt/js/main/
    payload = {
        "iss": client_id,  # Issuer: Bob's Client ID
        "sub": client_id,  # Subject: Bob's Client ID
        "aud": token_endpoint_url,  # Audience: Okta Token Endpoint
        "exp": int(
            expiration_time.timestamp()
        ),  # Expiration time (seconds since epoch)
        "iat": int(now.timestamp()),  # Issued at time
        "jti": os.urandom(16).hex(),  # Unique JWT ID
    }

    # JWT Header
    # headers = {
    #     "alg": "RS256",  # Algorithm (should match what you configured in Okta)
    #     "kid": kid,  # Key ID associated with Bob's public key in Okta
    # }

    # Encode and sign the JWT
    jwk = import_key(private_key_pem, "RSA")
    bob_client_assertion = encode({"alg": "RS256"}, payload, jwk)
    # bob_client_assertion: str = jwt.encode(claims=payload, key=import_key(private_key_pem,"RSA"), algorithms=["RS256"],
    #                                   header=headers)

    print(f"Generated client assertion JWT for Bob: {bob_client_assertion}")
    return bob_client_assertion


# --- Step 1: Obtain the actor_token (Access Token for Bob) using Client Credentials Grant ---
def get_bob_actor_token() -> str | None:
    token_url: str = OKTA_TOKEN_ENDPOINT

    assert BOB_CLIENT_ID, "BOB_CLIENT_ID environment variable must be set."
    assert BOB_PRIVATE_KEY_PEM, "BOB_PRIVATE_KEY_PEM environment variable must be set."

    # Generate the client_assertion JWT using Bob's credentials
    bob_client_assertion: str = generate_bob_client_assertion_jwt(
        client_id=BOB_CLIENT_ID,
        private_key_pem=BOB_PRIVATE_KEY_PEM,
        token_endpoint_url=token_url,
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "client_credentials",
        "client_id": BOB_CLIENT_ID,
        # "scope": "openid profile",  # Default scopes as custom scopes are not available without API Access Management
        "scope": "okta.apps.read",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": bob_client_assertion,
    }

    print("\n--- Getting Bob's Actor Token (Access Token for Bob) ---")
    response_json = make_post_request(token_url, headers, data)

    if response_json and "access_token" in response_json:
        print("Bob's Actor Token obtained successfully.")
        return cast(str, response_json["access_token"])
    else:
        print("Failed to obtain Bob's Actor Token.")
        return None


# --- Step 2: Perform Token Exchange ---
def perform_token_exchange(
    adam_subject_token: str, bob_actor_token1: str
) -> Dict[str, Any] | None:
    token_exchange_url = OKTA_TOKEN_ENDPOINT  # Using the default authorization server

    assert BOB_CLIENT_ID, "BOB_CLIENT_ID environment variable must be set."
    assert BOB_PRIVATE_KEY_PEM, "BOB_PRIVATE_KEY_PEM environment variable must be set."

    # Generate a new client_assertion JWT for Bob for this request
    bob_client_assertion: str = generate_bob_client_assertion_jwt(
        client_id=BOB_CLIENT_ID,
        private_key_pem=BOB_PRIVATE_KEY_PEM,
        token_endpoint_url=token_exchange_url,  # Use the token endpoint for audience
    )

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": BOB_CLIENT_ID,  # Bob is the client making the exchange request
        "subject_token": adam_subject_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:id_token",
        "actor_token": bob_actor_token1,
        "actor_token_type": "urn:ietf:params:oauth:token-type:access_token",
        # Indicating the actor token is an access token
        "scope": "openid profile email",  # Requesting default scopes for the new token
        "audience": CHARLIE_AUDIENCE,  # The identifier for Charlie's API/Resource Server
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": bob_client_assertion,
    }

    print(
        "\n--- Performing Token Exchange (Bob acting on behalf of Adam for Charlie) ---"
    )
    response_json = make_post_request(token_exchange_url, headers, data)

    if response_json and "access_token" in response_json:
        print("Token exchange successful! New token for Charlie obtained.")
        return response_json
    else:
        print("Token exchange failed.")
        return None


# --- Main execution flow ---
def test_token_exchange() -> None:
    # Ensure Bob's private key is properly loaded
    if not BOB_PRIVATE_KEY_PEM or BOB_PRIVATE_KEY_PEM == "...":
        print(
            "Error: BOB_PRIVATE_KEY_PEM environment variable is not set or is incorrect."
        )
        exit(1)

    # 1. Get Bob's actor_token (API1's access token)
    bob_actor_token = get_bob_actor_token()

    if bob_actor_token:
        # 2. Perform the token exchange
        exchanged_tokens_for_charlie = perform_token_exchange(
            ADAM_SUBJECT_TOKEN, bob_actor_token
        )

        if exchanged_tokens_for_charlie:
            print("\nExchanged Tokens for Charlie:")
            print(exchanged_tokens_for_charlie)
            # Bob can now use the 'access_token' from 'exchanged_tokens_for_charlie'
            # to access Charlie's resources on behalf of the original user (Adam_SUBJECT_TOKEN's owner).
            # The 'act' claim in the new token will reflect Bob as the actor.
    else:
        print("Cannot proceed with token exchange without Bob's actor token.")
