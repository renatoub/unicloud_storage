from abc import ABC, abstractmethod
from typing import Any, List, Optional, Union
import pandas as pd

class StorageClientError(Exception):
    """Base exception for storage client errors."""
    pass

class ConnectionError(StorageClientError):
    """Exception raised for connection failures."""
    pass

class DownloadError(StorageClientError):
    """Exception raised for download failures."""
    pass

class UploadError(StorageClientError):
    """Exception raised for upload failures."""
    pass

class FileNotFoundError(StorageClientError):
    """Exception raised when a file is not found."""
    pass

class BaseStorageClient(ABC):
    """
    Abstract base class for a cloud storage client.
    """

    @abstractmethod
    def download_file(
        self, bucket_name: str, blob_name: str, destination_path: str
    ) -> None:
        """Downloads a single file."""
        pass

    @abstractmethod
    def download_files(
        self, bucket_name: str, blob_names: List[str], destination_folder: str
    ) -> None:
        """Downloads a list of files."""
        pass

    @abstractmethod
    def download_folder(
        self, bucket_name: str, folder_name: str, destination_folder: str, recursive: bool = True
    ) -> None:
        """Downloads a folder."""
        pass

    @abstractmethod
    def download_by_extension(
        self,
        bucket_name: str,
        destination_folder: str,
        extensions: Union[str, List[str]],
        folder_name: Optional[str] = None,
        recursive: bool = True,
    ) -> None:
        """Downloads files by extension."""
        pass

    @abstractmethod
    def list_files(
        self, bucket_name: str, folder_name: Optional[str] = None, recursive: bool = False
    ) -> List[str]:
        """Lists files in a folder."""
        pass

    @abstractmethod
    def upload_file(
        self,
        bucket_name: str,
        source_path: str,
        destination_blob_name: str,
        overwrite: Union[bool, str] = False,
        create_folder: bool = True,
    ) -> None:
        """Uploads a single file."""
        pass

    @abstractmethod
    def upload_files(
        self,
        bucket_name: str,
        source_paths: List[str],
        destination_folder: str,
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        """Uploads a list of files."""
        pass

    @abstractmethod
    def upload_folder(
        self,
        bucket_name: str,
        source_folder: str,
        destination_folder: str,
        recursive: bool = True,
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        """Uploads a folder."""
        pass

    @abstractmethod
    def upload_dataframe(
        self,
        dataframe: pd.DataFrame,
        bucket_name: str,
        destination_blob_name: str,
        file_format: str = "parquet",
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        """Uploads a pandas DataFrame."""
        pass

    @abstractmethod
    def read_dataframe(
        self, bucket_name: str, blob_name: str, file_format: str = "parquet"
    ) -> pd.DataFrame:
        """Reads a file from storage into a pandas DataFrame."""
        pass

    @abstractmethod
    def create_folder(self, bucket_name: str, folder_name: str) -> None:
        """Creates a folder."""
        pass

    @abstractmethod
    def rename_folder(self, bucket_name: str, old_folder_name: str, new_folder_name: str) -> None:
        """Renames a folder."""
        pass

    @abstractmethod
    def delete_folder(self, bucket_name: str, folder_name: str) -> None:
        """Deletes a folder."""
        pass

    @abstractmethod
    def get_metadata(self, bucket_name: str, blob_name: str) -> dict:
        """Gets metadata of a file."""
        pass

    @abstractmethod
    def set_metadata(self, bucket_name: str, blob_name: str, metadata: dict) -> None:
        """Sets metadata of a file."""
        pass
