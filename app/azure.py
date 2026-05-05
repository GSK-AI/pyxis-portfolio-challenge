import logging
import os
from functools import lru_cache

import upath
from azure.core.exceptions import ResourceExistsError
from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobProperties, BlobServiceClient, ContainerClient

from app.settings import settings
from app.utils import use_local_storage

logger = logging.getLogger(__name__)


def _parse_azure_uri(uri: upath.UPath) -> tuple[str, str]:
    """
    Parse an Azure Blob Storage URI into container and blob path.

    Args:
        uri (upath.UPath): The Azure Blob Storage URI (e.g., az://
            container/blob/path.csv).

    Returns:
        tuple[str, str]: A tuple containing the container name and blob path.

    Raises:
        ValueError: If the URI is not a valid Azure Blob Storage URI.

    """
    str_uri = str(uri)
    # Example: az://container/blob/path.csv
    if not str_uri.startswith("az://"):
        raise ValueError("Not an Azure Blob URI")
    without_scheme = str_uri[len("az://") :]
    parts = without_scheme.split("/", 1)
    if len(parts) != 2:
        raise ValueError("Azure URI must be az://container/blobpath")
    container, blob_path = parts
    return container, blob_path


def _get_credential():
    """Authenticate with Azure Key Vault and retrieve secrets."""
    if settings.managed_identity_enabled:
        credential = ManagedIdentityCredential()
    else:
        credential = DefaultAzureCredential()

    key_vault_client = SecretClient(
        vault_url=settings.azure_key_vault_url, credential=credential
    )
    # Retrieve secrets from Key Vault and set environment variables
    secret_value = key_vault_client.get_secret("adls-client-secret").value
    if not secret_value:
        raise ValueError("You need to add the azure client secret in your key vault.")
    os.environ["AZURE_CLIENT_SECRET"] = secret_value

    return credential


@lru_cache(maxsize=1)
def get_blob_service_client():
    """Get Azure Blob Service Client."""
    if use_local_storage():
        raise ValueError("Local storage is being used, cannot connect to blob storage.")
    logger.info("Connecting to Azure Blob Storage...")
    credential = _get_credential()
    client = BlobServiceClient(
        account_url=settings.azure_storage_account_url, credential=credential
    )
    logger.info("Connected to Azure Blob Storage.")
    return client


def _get_blobs(container_client: ContainerClient) -> dict[str, BlobProperties]:
    """Get blobs from a container."""
    return {blob.name: blob for blob in container_client.list_blobs()}


def _load_bytes_azure(
    uri: upath.UPath,
) -> bytes:
    """
    Read blob file from a container.

    Args:
        uri (upath.UPath): The Azure Blob Storage URI (e.g., az://
            container/blob/path.csv).

    Returns:
        bytes: The content of the blob as bytes.

    """
    blob_service_client = get_blob_service_client()
    container_name, filename = _parse_azure_uri(uri)
    container_client = blob_service_client.get_container_client(container_name)
    blobs = _get_blobs(container_client)
    blob_names = [blob.name for blob in container_client.list_blobs()]

    if filename not in blob_names:
        raise ValueError(f"File {filename} not found in container {container_name}")

    blob_client = container_client.get_blob_client(blobs[filename])  # type: ignore
    return blob_client.download_blob().readall()


def _list_files_azure(uri: upath.UPath) -> list[str]:
    """Get a list of files in a directory in Azure Blob Storage."""
    blob_service_client = get_blob_service_client()
    container_name, dir_name = _parse_azure_uri(uri)
    container_client = blob_service_client.get_container_client(container_name)
    return [
        f"az://{container_name}/{blob.name}"
        for blob in container_client.list_blobs(name_starts_with=dir_name)
    ]


def upload_bytes(
    content: bytes,
    uri: upath.UPath,
    overwrite: bool = False,
):
    """
    Uploads raw bytes content to Azure Blob Storage.

    Args:
        content (bytes): The file contents (already serialized).
        filename (str): The full path within the container.
        uri (upath.UPath): az://container/path or similar.
        overwrite (bool): Whether to overwrite existing blobs.

    """
    blob_service_client = get_blob_service_client()
    container_name, blob_path = _parse_azure_uri(uri)
    container_client = blob_service_client.get_container_client(container_name)

    blob_client = container_client.get_blob_client(blob_path)

    try:
        blob_client.upload_blob(content, overwrite=overwrite)
    except ResourceExistsError:
        logger.info(
            f"File {blob_path} already exists in container"
            f" {container_name}, so skipping upload to blob."
        )
