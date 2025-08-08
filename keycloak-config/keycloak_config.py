import os
import time
import requests

from keycloak import KeycloakAdmin


def wait_for_keycloak(max_attempts: int = 30, delay: int = 2) -> None:
    keycloak_url = f"http://{os.getenv('KEYCLOAK_HOST', 'localhost')}:{os.getenv('KEYCLOAK_HEALTH_CHECK_PORT', '8080')}/health"

    keycloak_admin_user = os.getenv("KEYCLOAK_ADMIN", "admin")
    keycloak_admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD", "password")

    for attempt in range(max_attempts):
        try:
            response = requests.get(
                keycloak_url,
                auth=(keycloak_admin_user, keycloak_admin_password),
                timeout=5,
            )
            if response.status_code == 200:
                print(f"Keycloak is ready at {keycloak_url}")
                return
            print(
                f"Keycloak not ready at {keycloak_url}, status code: {response.status_code}"
            )
        except requests.RequestException as e:
            print(
                f"Waiting for Keycloak at {keycloak_url} (Attempt {attempt + 1}/{max_attempts}): {e}"
            )

        time.sleep(delay)

    raise RuntimeError(
        f"Could not connect to Keycloak server at {keycloak_url} after {max_attempts} attempts with {keycloak_admin_user}:{keycloak_admin_password}. Please check if Keycloak is running and accessible."
    )


def configure_keycloak() -> None:
    # Wait for Keycloak to be ready
    wait_for_keycloak()

    # Keycloak Admin Configuration
    keycloak_admin = KeycloakAdmin(
        server_url=f"http://{os.getenv('KEYCLOAK_HOST', 'localhost')}:{os.getenv('KEYCLOAK_PORT', '8080')}/",
        username=os.getenv("KEYCLOAK_ADMIN", "admin"),
        password=os.getenv("KEYCLOAK_ADMIN_PASSWORD", "password"),
        realm_name="master",
    )

    # Realm Configuration
    realm_name = os.getenv("MY_REALM_NAME", "bwell-realm")
    realm_config = {
        "realm": realm_name,
        "enabled": True,
        "sslRequired": "none",
        "defaultSignatureAlgorithm": "RS256",
    }

    try:
        # Check if realm exists
        realms = keycloak_admin.get_realms()
        existing_realm = next((r for r in realms if r["realm"] == realm_name), None)

        if existing_realm:
            print(f"Updating existing realm: {realm_name}")
            keycloak_admin.update_realm(realm_name, realm_config)
        else:
            print(f"Creating new realm: {realm_name}")
            keycloak_admin.create_realm(realm_config)

        # Set current realm
        keycloak_admin.change_current_realm(realm_name)

        # Client Configuration
        client_config = {
            "clientId": os.getenv("CLIENT_ID", "bwell-client-id"),
            "name": os.getenv("CLIENT_ID", "bwell-client-id"),
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": os.getenv("CLIENT_SECRET", "bwell-secret"),
        }

        # Create or Update Client
        clients = keycloak_admin.get_clients()
        existing_client = next(
            (c for c in clients if c["clientId"] == client_config["clientId"]), None
        )

        if existing_client:
            print(f"Updating existing client: {client_config['clientId']}")
            keycloak_admin.update_client(existing_client["id"], client_config)
        else:
            print(f"Creating new client: {client_config['clientId']}")
            keycloak_admin.create_client(client_config)

        # User Creation Example
        users_to_create = [
            {
                "username": os.getenv("MY_ADMIN_USER_NAME", "admin"),
                "enabled": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": os.getenv("MY_ADMIN_USER_PASSWORD", "password"),
                        "temporary": False,
                    }
                ],
                "attributes": {
                    "custom:scope": os.getenv("MY_ADMIN_USER_SCOPE", ""),
                    "cognito:groups": os.getenv("MY_ADMIN_USER_GROUPS", ""),
                },
            },
            {
                "username": os.getenv("MY_USER_NAME", "tester"),
                "enabled": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": os.getenv("MY_USER_PASSWORD", "password"),
                        "temporary": False,
                    }
                ],
                "attributes": {
                    "custom:scope": os.getenv("MY_USER_SCOPE", ""),
                    "cognito:groups": os.getenv("MY_USER_GROUPS", ""),
                },
            },
        ]

        for user_config in users_to_create:
            existing_users = keycloak_admin.get_users()
            existing_user = next(
                (u for u in existing_users if u["username"] == user_config["username"]),
                None,
            )

            if existing_user:
                print(f"Updating existing user: {user_config['username']}")
                keycloak_admin.update_user(existing_user["id"], user_config)
            else:
                print(f"Creating new user: {user_config['username']}")
                keycloak_admin.create_user(user_config)

        print("Keycloak configuration completed successfully!")

    except Exception as e:
        print(f"Error configuring Keycloak: {e}")
        raise


if __name__ == "__main__":
    print("Starting Keycloak configuration...")
    configure_keycloak()
