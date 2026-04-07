"""
Script to insert the language_model_gateway function directly into the OpenWebUI database.
This bypasses the need for API key authentication.
"""

from __future__ import annotations

import json
import sys
from typing import Any

import psycopg2


def main() -> None:
    """Insert the language_model_gateway function into the database."""
    # Read the JSON config
    try:
        with open("language_model_gateway_pipe.json", "r") as f:
            config: dict[str, Any] = json.load(f)[0]
    except FileNotFoundError:
        print("Error: language_model_gateway_pipe.json not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(
            f"Error: Invalid JSON in language_model_gateway_pipe.json: {e}",
            file=sys.stderr,
        )
        sys.exit(1)
    except IndexError as e:
        print(
            f"Error: Invalid configuration structure in language_model_gateway_pipe.json: {e}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read the Python code
    try:
        with open("language_model_gateway_pipe.py", "r") as f:
            content: str = f.read()
    except FileNotFoundError:
        print("Error: language_model_gateway_pipe.py not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading language_model_gateway_pipe.py: {e}", file=sys.stderr)
        sys.exit(1)

    # Update content in config
    config["content"] = content

    # Connect to database
    try:
        conn = psycopg2.connect(
            host="baileyai-open-webui-db-1",
            port=5431,
            database="myapp_db",
            user="myapp_user",
            password="myapp_pass",  # pragma: allowlist secret
        )
        cur = conn.cursor()

        # Insert function with ON CONFLICT to update if exists
        cur.execute(
            """INSERT INTO public.function (id, user_id, name, type, content, meta, created_at, updated_at, is_active, is_global)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                meta = EXCLUDED.meta,
                updated_at = EXCLUDED.updated_at,
                is_active = EXCLUDED.is_active,
                is_global = EXCLUDED.is_global""",
            (
                config["id"],
                config["user_id"],
                config["name"],
                config["type"],
                config["content"],
                json.dumps(config["meta"]),
                config["created_at"],
                config["updated_at"],
                config["is_active"],
                config["is_global"],
            ),
        )

        conn.commit()
        cur.close()
        conn.close()
        print("Successfully inserted language_model_gateway function")
    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing required configuration key: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
