from typing import Dict, Any
from .base import BaseStorageClient

def get_client(provider: str, auth_config: Dict[str, Any]) -> BaseStorageClient:
    """
    Factory function to get a storage client for a specific provider.

    :param provider: The cloud provider (e.g., 'aws', 'gcp', 'azure').
    :param auth_config: A dictionary with authentication credentials.
    :return: An instance of a storage client.
    """
    if provider.lower() == 'aws':
        from .aws_client import AwsStorageClient
        return AwsStorageClient(auth_config)
    elif provider.lower() == 'gcp':
        from .gcp_client import GcpStorageClient
        return GcpStorageClient(auth_config)
    elif provider.lower() == 'azure':
        from .azure_client import AzureStorageClient
        return AzureStorageClient(auth_config)
    else:
        raise ValueError(f"Unsupported provider: {provider}")

__all__ = ["get_client", "BaseStorageClient"]