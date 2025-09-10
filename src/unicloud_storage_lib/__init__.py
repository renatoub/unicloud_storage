from typing import Dict, Any
from .base import BaseStorageClient
from .aws_client import AwsStorageClient
from .gcp_client import GcpStorageClient
from .azure_client import AzureStorageClient

def get_client(provider: str, auth_config: Dict[str, Any]) -> BaseStorageClient:
    """
    Factory function to get a storage client for a specific provider.

    :param provider: The cloud provider (e.g., 'aws', 'gcp', 'azure').
    :param auth_config: A dictionary with authentication credentials.
    :return: An instance of a storage client.
    """
    if provider.lower() == 'aws':
        return AwsStorageClient(auth_config)
    elif provider.lower() == 'gcp':
        return GcpStorageClient(auth_config)
    elif provider.lower() == 'azure':
        return AzureStorageClient(auth_config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

__all__ = ["get_client", "BaseStorageClient"]