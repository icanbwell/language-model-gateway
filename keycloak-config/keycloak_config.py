import json
import os
import time
from typing import Any, Dict, List, cast

import requests

from keycloak import KeycloakAdmin, KeycloakOpenIDConnection


def wait_for_keycloak(max_attempts: int = 30, delay: int = 2) -> None:
    keycloak_url = f"http://{os.getenv('KEYCLOAK_HOST', 'localhost')}:{os.getenv('KEYCLOAK_HEALTH_CHECK_PORT', '8080')}/health"

    keycloak_admin_user = os.getenv("KC_BOOTSTRAP_ADMIN_USERNAME", "admin")
    keycloak_admin_password = os.getenv("KC_BOOTSTRAP_ADMIN_PASSWORD", "password")

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
        f"Could not connect to Keycloak server at {keycloak_url} after {max_attempts} attempts with username '{keycloak_admin_user}'. Please check if Keycloak is running and accessible."
    )


def configure_keycloak() -> None:
    # Wait for Keycloak to be ready
    wait_for_keycloak()

    # https://www.keycloak.org/docs-api/latest/rest-api/index.html
    # https://python-keycloak.readthedocs.io/en/latest/modules/admin.html

    keycloak_server_url = f"http://{os.getenv('KEYCLOAK_HOST', 'localhost')}:{os.getenv('KEYCLOAK_PORT', '8080')}/"
    print(f"Connecting to Keycloak server at {keycloak_server_url}")
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=keycloak_server_url,
        username=os.getenv("KC_BOOTSTRAP_ADMIN_USERNAME", "admin"),
        password=os.getenv("KC_BOOTSTRAP_ADMIN_PASSWORD", "password"),
        realm_name="master",
    )
    print("Keycloak connection established with realm 'master'")
    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)

    # Realm Configuration
    realm_name = os.getenv("MY_REALM_NAME", "bwell-realm")
    realm_config = {
        "realm": realm_name,
        "enabled": True,
        "sslRequired": "none",  # keep if you want to override default (default is 'external')
        # "defaultSignatureAlgorithm": "RS256",  # default is RS256
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

        # Get current profile
        profile_url = f"{keycloak_server_url}/admin/realms/{realm_name}/users/profile"
        profiles = keycloak_connection.raw_get(profile_url)  # type: ignore[arg-type]
        attributes = profiles.json()["attributes"]

        # Add unmanaged Attribute
        attributes.append(
            {
                "name": "custom",
                "displayName": "${custom}",
                "validations": {"length": {"max": 255}},
                "annotations": {},
                "permissions": {"view": ["admin"], "edit": ["admin", "user"]},
                "multivalued": False,
            }
        )

        # new profile's payload
        new_profiles = {
            "attributes": attributes,
            "groups": profiles.json()["groups"],
            "unmanagedAttributePolicy": "ENABLED",  # 'ADMIN_VIEW', 'ADMIN_EDIT'
        }

        # Update profile
        result = keycloak_connection.raw_put(profile_url, json.dumps(new_profiles))  # type: ignore[arg-type]
        print(result)

        # Define protocol mappers for use in client scopes
        email_protocol_mapper = {
            "name": "email",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "aggregate.attrs": "false",
                "claim.name": "email",
                "id.token.claim": "true",
                "introspection.token.claim": "true",
                "jsonType.label": "String",
                "lightweight.claim": "false",
                "multivalued": "false",
                "user.attribute": "email",
                "userinfo.token.claim": "true",
            },
        }
        user_attribute_protocol_mapper = {
            "name": "user-attribute-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "user-attribute",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "user-attribute",
                "userinfo.token.claim": "true",
            },
        }
        access_attribute_protocol_mapper = {
            "name": "access-attribute-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "access-attribute",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "access-attribute",
                "userinfo.token.claim": "true",
            },
        }
        aud_hardcoded_client1_mapper = {
            "name": "aud-hardcoded-client1",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-hardcoded-claim-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "id.token.claim": "true",
                "claim.value": os.getenv("CLIENT_AUDIENCE", "bwell-client-id"),
                "claim.name": "aud",
                "jsonType.label": "String",
            },
        }
        cognito_groups_mapper = {
            "name": "cognito-groups-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "user.attribute": "cognito:groups",
                "claim.name": "cognito:groups",
                "jsonType.label": "String",
                "id.token.claim": "true",
                "access.token.claim": "true",
                "userinfo.token.claim": "true",
                "multivalued": "true",
            },
        }
        client_person_mapper = {
            "name": "client-person-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "clientFhirPersonId",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "clientFhirPersonId",
                "userinfo.token.claim": "true",
            },
        }
        client_patient_mapper = {
            "name": "client-patient-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "clientFhirPatientId",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "clientFhirPatientId",
                "userinfo.token.claim": "true",
            },
        }
        bwell_person_mapper = {
            "name": "bwell-person-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "bwellFhirPersonId",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "bwellFhirPersonId",
                "userinfo.token.claim": "true",
            },
        }
        bwell_patient_mapper = {
            "name": "bwell-patient-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "bwellFhirPatientId",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "bwellFhirPatientId",
                "userinfo.token.claim": "true",
            },
        }
        bwell_token_use_mapper = {
            "name": "bwell-token-use-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "token_use",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "token_use",
                "userinfo.token.claim": "true",
            },
        }
        bwell_username_mapper = {
            "name": "bwell-username-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "username",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "username",
                "userinfo.token.claim": "true",
            },
        }
        custom_scope_mapper = {
            "name": "custom-scope-mapper",
            "protocol": "openid-connect",
            "protocolMapper": "oidc-usermodel-attribute-mapper",
            "consentRequired": False,
            "config": {
                "access.token.claim": "true",
                "claim.name": "custom:scope",
                "id.token.claim": "true",
                "jsonType.label": "String",
                "user.attribute": "custom:scope",
                "userinfo.token.claim": "true",
            },
        }
        # Define client scopes with protocol mappers
        client_scopes: List[Dict[str, Any]] = [
            {
                "name": "offline_access",
                "protocol": "openid-connect",
                "attributes": {
                    "consent.screen.text": "${offlineAccessScopeConsentText}",
                    "display.on.consent.screen": "true",
                },
                "description": "OpenID Connect built-in scope: offline_access",
            },
            {
                "name": "openid",
                "protocol": "openid-connect",
                "attributes": {
                    "consent.screen.text": "",
                    "display.on.consent.screen": "true",
                    "gui.order": "",
                    "include.in.token.scope": "false",
                },
                "description": "OpenID Connect built-in scope: openid",
            },
            {
                "name": "email",
                "protocol": "openid-connect",
                "attributes": {
                    "consent.screen.text": "",
                    "display.on.consent.screen": "true",
                    "gui.order": "",
                    "include.in.token.scope": "false",
                },
                "description": "OpenID Connect built-in scope: email",
                "protocolMappers": [email_protocol_mapper],
            },
            {
                "name": "user/*.*",
                "protocol": "openid-connect",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "description": "FHIR User scope",
                "protocolMappers": [user_attribute_protocol_mapper],
            },
            {
                "name": "access/*.*",
                "protocol": "openid-connect",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "description": "FHIR Access scope",
                "protocolMappers": [access_attribute_protocol_mapper],
            },
            {
                "name": "audience",
                "protocol": "openid-connect",
                "description": "Hardcoded audience claim for client1",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [aud_hardcoded_client1_mapper],
            },
            {
                "name": "cognito-groups",
                "protocol": "openid-connect",
                "description": "Cognito groups claim mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [cognito_groups_mapper],
            },
            {
                "name": "client-person-mapper",
                "protocol": "openid-connect",
                "description": "Client FHIR Person ID mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [client_person_mapper],
            },
            {
                "name": "client-patient-mapper",
                "protocol": "openid-connect",
                "description": "Client FHIR Patient ID mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [client_patient_mapper],
            },
            {
                "name": "bwell-person-mapper",
                "protocol": "openid-connect",
                "description": "Bwell FHIR Person ID mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [bwell_person_mapper],
            },
            {
                "name": "bwell-patient-mapper",
                "protocol": "openid-connect",
                "description": "Bwell FHIR Patient ID mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [bwell_patient_mapper],
            },
            {
                "name": "bwell-token-use-mapper",
                "protocol": "openid-connect",
                "description": "Bwell token use mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [bwell_token_use_mapper],
            },
            {
                "name": "bwell-username-mapper",
                "protocol": "openid-connect",
                "description": "Bwell username mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [bwell_username_mapper],
            },
            {
                "name": "custom-scope-mapper",
                "protocol": "openid-connect",
                "description": "Custom scope mapper",
                "attributes": {
                    "display.on.consent.screen": "true",
                    "include.in.token.scope": "false",
                },
                "protocolMappers": [custom_scope_mapper],
            },
        ]

        # Add or update client scopes in Keycloak
        for scope in client_scopes:
            try:
                existing_scopes = keycloak_admin.get_client_scopes()
                existing_scope = next(
                    (s for s in existing_scopes if s["name"] == scope["name"]), None
                )
                if not existing_scope:
                    print(f"Creating new client scope: {scope['name']}")
                    keycloak_admin.create_client_scope(scope)
            except Exception as e:
                print(f"Error creating/updating client scope {scope['name']}: {e}")

        # Client Configuration
        # https://www.keycloak.org/docs-api/latest/rest-api/index.html#ClientRepresentation
        client1 = {
            "clientId": os.getenv("CLIENT_ID", "bwell-client-id"),
            "name": os.getenv("CLIENT_ID", "bwell-client-id"),
            "enabled": True,  # default is True
            "protocol": "openid-connect",  # default is openid-connect
            # "publicClient": False,  # default is False
            "secret": os.getenv("CLIENT_SECRET", "bwell-secret"),
            "redirectUris": ["*"],
            "webOrigins": ["*"],
            "attributes": {
                "access.token.lifespan": int(
                    os.getenv("CLIENT_ACCESS_TOKEN_LIFE_SPAN", "3600")
                ),
                "id.token.lifespan": int(
                    os.getenv("CLIENT_ID_TOKEN_LIFE_SPAN", "3600")
                ),
                "refresh.token.lifespan": int(
                    os.getenv("CLIENT_REFRESH_TOKEN_LIFE_SPAN", "3600")
                ),
                "post.logout.redirect.uris": "https://open-webui.localhost",
            },
            "defaultClientScopes": [
                "web-origins",
                "roles",
                "profile",
                "email",
                "openid",
                "audience",
                "cognito-groups",
                "client-person-mapper",
                "client-patient-mapper",
                "bwell-person-mapper",
                "bwell-patient-mapper",
                "bwell-token-use-mapper",
                "bwell-username-mapper",
                "custom-scope-mapper",
            ],
            "optionalClientScopes": [
                "user/*.*",
                "access/*.*",
            ],
        }
        client2 = {
            "clientId": os.getenv("CLIENT_ID_2", "bwell-client-id-2"),
            "name": os.getenv("CLIENT_ID_2", "bwell-client-id-2"),
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": os.getenv("CLIENT_SECRET_2", "bwell-secret-2"),
            "serviceAccountsEnabled": True,  # Enable client credentials flow
            "redirectUris": ["*"],
            "webOrigins": ["*"],
        }
        client3 = {
            "clientId": os.getenv("CLIENT_ID_3", "bwell-client-id-3"),
            "name": os.getenv("CLIENT_ID_3", "bwell-client-id-3"),
            "enabled": True,
            "protocol": "openid-connect",
            "publicClient": False,
            "secret": os.getenv("CLIENT_SECRET_3", "bwell-secret-3"),
            "redirectUris": ["*"],
            "webOrigins": ["*"],
            "attributes": {
                "access.token.lifespan": int(
                    os.getenv("CLIENT_ACCESS_TOKEN_LIFE_SPAN_3", "3600")
                ),
                "id.token.lifespan": int(
                    os.getenv("CLIENT_ID_TOKEN_LIFE_SPAN_3", "3600")
                ),
                "refresh.token.lifespan": int(
                    os.getenv("CLIENT_REFRESH_TOKEN_LIFE_SPAN_3", "3600")
                ),
                "post.logout.redirect.uris": "https://open-webui.localhost",
            },
            "defaultClientScopes": [
                "web-origins",
                "roles",
                "profile",
                "email",
                "openid",
            ],
            "optionalClientScopes": [
                "user/*.*",
                "access/*.*",
                "audience",
                "cognito-groups",
                "client-person-mapper",
                "client-patient-mapper",
                "bwell-person-mapper",
                "bwell-patient-mapper",
                "bwell-token-use-mapper",
                "bwell-username-mapper",
                "custom-scope-mapper",
            ],
        }
        clients = [client1, client2, client3]
        for client_config in clients:
            create_client(client_config=client_config, keycloak_admin=keycloak_admin)

        # User Creation Example
        # https://www.keycloak.org/docs-api/latest/rest-api/index.html#UserRepresentation
        admin_user = {
            "username": os.getenv("MY_ADMIN_USER_NAME", "admin"),
            "enabled": True,
            # Default demographics
            "firstName": os.getenv("MY_ADMIN_USER_FIRST_NAME", "Admin"),
            "lastName": os.getenv("MY_ADMIN_USER_LAST_NAME", "User"),
            "email": os.getenv("MY_ADMIN_USER_EMAIL", "admin@tester.com"),
            "emailVerified": True,
            "credentials": [
                {
                    "type": "password",
                    "value": os.getenv("MY_ADMIN_USER_PASSWORD", "password"),
                    "temporary": False,
                }
            ],
            "attributes": {
                "custom:scope": os.getenv("MY_ADMIN_USER_SCOPE", ""),
                "cognito:groups": os.getenv("MY_ADMIN_USER_GROUPS", "").split(","),
                "username": os.getenv("MY_ADMIN_USER_TOKEN_USERNAME", "admin"),
            },
        }
        test_user = {
            "username": os.getenv("MY_USER_NAME", "tester"),
            "enabled": True,
            "firstName": os.getenv("MY_USER_FIRST_NAME", "Test"),
            "lastName": os.getenv("MY_USER_LAST_NAME", "User"),
            "email": os.getenv("MY_USER_EMAIL", "testuser@tester.com"),
            "emailVerified": True,
            "credentials": [
                {
                    "type": "password",
                    "value": os.getenv("MY_USER_PASSWORD", "password"),
                    "temporary": False,
                }
            ],
            "attributes": {
                "custom:scope": os.getenv("MY_USER_SCOPE", ""),
                "cognito:groups": os.getenv("MY_USER_GROUPS", "").split(","),
                "clientFhirPersonId": os.getenv("MY_USER_CLIENT_PERSON_ID", ""),
                "clientFhirPatientId": os.getenv("MY_USER_CLIENT_PATIENT_ID", ""),
                "bwellFhirPersonId": os.getenv("MY_USER_BWELL_PERSON_ID", ""),
                "bwellFhirPatientId": os.getenv("MY_USER_BWELL_PATIENT_ID", ""),
                "username": os.getenv("MY_USER_TOKEN_USERNAME", "tester"),
            },
        }
        users_to_create = [
            admin_user,
            test_user,
        ]

        for user_config in users_to_create:
            user_id = create_user(
                keycloak_admin=keycloak_admin, user_config=user_config
            )
            group_env = None
            if user_config["username"] == os.getenv("MY_ADMIN_USER_NAME", "admin"):
                group_env = os.getenv("MY_ADMIN_USER_GROUPS", "")
            elif user_config["username"] == os.getenv("MY_USER_NAME", "tester"):
                group_env = os.getenv("MY_USER_GROUPS", "")
            if group_env:
                group_names = [g.strip() for g in group_env.split(",") if g.strip()]
                for group_name in group_names:
                    # Find group by name
                    groups = keycloak_admin.get_groups()
                    group = next((g for g in groups if g["name"] == group_name), None)
                    if not group:
                        print(
                            f"Group {group_name} not found for user {user_config['username']}, creating group."
                        )
                        keycloak_admin.create_group({"name": group_name})
                        # Fetch group again after creation
                        groups = keycloak_admin.get_groups()
                        group = next(
                            (g for g in groups if g["name"] == group_name), None
                        )
                    if group:
                        keycloak_admin.group_user_add(user_id, group["id"])
                    else:
                        print(
                            f"Failed to create or find group {group_name} for user {user_config['username']}"
                        )

        print("Keycloak configuration completed successfully!")

    except Exception as e:
        print(f"Error configuring Keycloak: {e}")
        raise


def create_user(*, keycloak_admin: KeycloakAdmin, user_config: Dict[str, Any]) -> str:
    existing_users = keycloak_admin.get_users()
    existing_user = next(
        (u for u in existing_users if u["username"] == user_config["username"]),
        None,
    )
    if existing_user:
        print(f"Updating existing user: {user_config['username']}")
        keycloak_admin.update_user(existing_user["id"], user_config)
        return cast(str, existing_user["id"])  # Return user ID if needed
    else:
        print(f"Creating new user: {user_config['username']}")
        new_user_id = keycloak_admin.create_user(user_config)
        return new_user_id


def create_client(
    *, client_config: Dict[str, Any], keycloak_admin: KeycloakAdmin
) -> str:
    # Create or Update Client
    clients = keycloak_admin.get_clients()
    existing_client = next(
        (c for c in clients if c["clientId"] == client_config["clientId"]), None
    )
    if existing_client:
        print(f"Updating existing client: {client_config['clientId']}")
        keycloak_admin.update_client(existing_client["id"], client_config)
        return cast(str, existing_client["id"])
    else:
        print(f"Creating new client: {client_config['clientId']}")
        new_client_id = keycloak_admin.create_client(client_config)
        return new_client_id


def add_mapper_to_client_scope(
    scope_id: str, mapper: Dict[str, Any], keycloak_admin: KeycloakAdmin
) -> None:
    """Add a protocol mapper to a client scope via KeycloakAdmin."""
    try:
        keycloak_admin.add_mapper_to_client_scope(scope_id, mapper)
        print(f"Added protocol mapper '{mapper['name']}' to client scope {scope_id}")
    except Exception as e:
        print(
            f"Error adding protocol mapper '{mapper['name']}' to client scope {scope_id}: {e}"
        )


if __name__ == "__main__":
    print("Starting Keycloak configuration...")
    configure_keycloak()
