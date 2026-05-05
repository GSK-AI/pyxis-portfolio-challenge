import logging
import os
import sqlite3
from typing import Any, Tuple

import psycopg2
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from psycopg2.extras import DictCursor

logger = logging.getLogger(__name__)

# Define constants for Key Vault and secret names
KEY_VAULT_NAME = os.environ.get("keyvault", "codvmtrdfpus6kvdevtest01")
SECRET_NAMES = {
    "database_server": "postgres-server-name",
    "database_name": "postgres-dbname",
    "database_user": "postgres-username",
    "database_password": "postgres-pwd",
    "database_port": "postgres-port-number",
}


def get_secret(client, secret_name):
    """Retrieve a secret from Azure Key Vault."""
    try:
        return client.get_secret(secret_name).value
    except Exception as e:
        print(f"Error retrieving secret : {e}")
        return None


def get_database_credentials():
    """Retrieve database credentials from Azure Key Vault."""
    kv_uri = f"https://{KEY_VAULT_NAME}.vault.azure.net"
    if bool(int(os.environ.get("MANAGED_IDENTITY", "0"))):
        credential = ManagedIdentityCredential()
    else:
        credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)

    credentials = {}
    for key, secret_name in SECRET_NAMES.items():
        credentials[key] = get_secret(client, secret_name)

    return credentials


def connect_to_sqlite():
    """Establish a connection to the SQLite database."""
    db_path = os.environ.get("PORTFOLIO_DB_PATH", None)
    if db_path is None:
        logger.info(
            "PORTFOLIO_DB_PATH environment variable not set, required for running "
            "locally with sqlite."
        )
        return None
    try:
        logger.info(f"Attempting to connnect to SQLite database at {db_path}")
        connection = sqlite3.connect(db_path, check_same_thread=False)
        logger.info("Connection to SQLite database established successfully.")
        return connection
    except sqlite3.Error as e:
        logger.info(f"Error connecting to SQLite database: {e}")
        return None


def connect_to_postgresql(credentials):
    """Establish a connection to the PostgreSQL database."""
    try:
        connection = psycopg2.connect(
            host=credentials["database_server"],
            database=credentials["database_name"],
            user=credentials["database_user"],
            password=credentials["database_password"],
            port=credentials["database_port"],
            cursor_factory=DictCursor,
            connect_timeout=30,
        )
        logger.info("Connection to PostgreSQL database established successfully.")
        return connection
    except Exception as e:
        logger.info(f"Error connecting to PostgreSQL database: {e}")
        return None


def get_db_cursor() -> Tuple[Any, Any]:
    """Get database cursor based on environment."""
    if os.environ.get("TESTING") == "1":
        connection = connect_to_sqlite()
        if connection is None:
            raise ConnectionError("Failed to establish sqlite database connection.")
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()
        return cursor, connection
    else:
        credentials = get_database_credentials()
        if not all(credentials.values()):
            raise ValueError("Failed to retrieve all necessary database credentials.")

        connection = connect_to_postgresql(credentials)
        if connection is None:
            raise ConnectionError("Failed to establish a database connection.")
        cursor = connection.cursor()
        return cursor, connection


def main():
    """Test the connection."""
    # Retrieve database credentials
    if os.environ.get("TESTING") == "1":
        # Use local SQLite database for testing
        connection = connect_to_sqlite()

    else:
        credentials = get_database_credentials()

        if not all(credentials.values()):
            print("Failed to retrieve all necessary database credentials.")
            return
        # Connect to the PostgreSQL database
        connection = connect_to_postgresql(credentials)

    # Perform database operations here

    # Close the connection
    if connection:
        connection.close()
        print("connection closed.")


if __name__ == "__main__":
    main()
