import os
import io
from typing import Any, Dict, List, Optional, Union
import polars as pl
from azure.core.exceptions import AzureError
from azure.identity import UsernamePasswordCredential
from azure.storage.blob import BlobServiceClient
from .base import BaseStorageClient, ConnectionError, DownloadError, UploadError, FileNotFoundError, DataFrame

class AzureStorageClient(BaseStorageClient):
    def __init__(self, auth_config: Dict[str, Any]):
        self.auth_config = auth_config
        self._client = self._connect()

    def _connect(self) -> BlobServiceClient:
        auth_method = self.auth_config.get("auth_method")
        try:
            if auth_method == "connection_string":
                return BlobServiceClient.from_connection_string(
                    self.auth_config["connection_string"]
                )
            elif auth_method == "sas_token":
                return BlobServiceClient(
                    account_url=self.auth_config["account_url"],
                    credential=self.auth_config["sas_token"],
                )
            elif auth_method == "user_credentials":
                credential = UsernamePasswordCredential(
                    client_id=self.auth_config.get("client_id"),
                    username=self.auth_config["user"],
                    password=self.auth_config["password"],
                )
                return BlobServiceClient(
                    account_url=self.auth_config["account_url"], credential=credential
                )
            else:
                raise ValueError(f"Unsupported Azure authentication method: {auth_method}")
        except KeyError as e:
            raise ValueError(f"Missing required auth config key: {e}") from e
        except AzureError as e:
            raise ConnectionError(f"Failed to connect to Azure: {e}") from e

    def download_file(
        self,
        bucket_name: str,
        blob_name: str,
        destination_path: str,
    ) -> None:
        try:
            blob_client = self._client.get_blob_client(
                container=bucket_name, blob=blob_name
            )
            if not blob_client.exists():
                raise FileNotFoundError(f"File not found on Azure: {blob_name}")
            with open(destination_path, "wb") as download_file:
                download_stream = blob_client.download_blob()
                download_file.write(download_stream.readall())
        except AzureError as e:
            raise DownloadError(f"Failed to download file from Azure: {e}") from e

    def download_files(
        self,
        bucket_name: str,
        blob_names: List[str],
        destination_folder: str,
    ) -> None:
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        for blob_name in blob_names:
            destination_path = os.path.join(destination_folder, os.path.basename(blob_name))
            self.download_file(bucket_name, blob_name, destination_path)

    def download_folder(
        self,
        bucket_name: str,
        folder_name: str,
        destination_folder: str,
        recursive: bool = True,
    ) -> None:
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        
        container_client = self._client.get_container_client(bucket_name)
        blob_list = container_client.list_blobs(name_starts_with=folder_name, delimiter="/" if not recursive else None)

        for blob in blob_list:
            if "/" in blob.name and not recursive:
                continue

            relative_path = os.path.relpath(blob.name, folder_name)
            destination_path = os.path.join(destination_folder, relative_path)
            destination_dir = os.path.dirname(destination_path)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            self.download_file(bucket_name, blob.name, destination_path)

    def download_by_extension(
        self,
        bucket_name: str,
        destination_folder: str,
        extensions: Union[str, List[str]],
        folder_name: Optional[str] = None,
        recursive: bool = True,
    ) -> None:
        if isinstance(extensions, str):
            extensions = [extensions]
        
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)

        container_client = self._client.get_container_client(bucket_name)
        blob_list = container_client.list_blobs(name_starts_with=folder_name)

        for blob in blob_list:
            if not any(blob.name.endswith(ext) for ext in extensions):
                continue
            
            if not recursive and folder_name and "/" in blob.name[len(folder_name):].strip("/"):
                continue

            relative_path = os.path.relpath(blob.name, folder_name) if folder_name else blob.name
            destination_path = os.path.join(destination_folder, relative_path)
            destination_dir = os.path.dirname(destination_path)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)

            self.download_file(bucket_name, blob.name, destination_path)

    def list_files(
        self,
        bucket_name: str,
        folder_name: Optional[str] = None,
        recursive: bool = False,
    ) -> List[str]:
        container_client = self._client.get_container_client(bucket_name)
        blob_list = container_client.list_blobs(name_starts_with=folder_name, delimiter="/" if not recursive else None)
        files = []
        for blob in blob_list:
            files.append(blob.name)
        if not recursive:
            for prefix in blob_list.by_page():
                files.extend(list(prefix.prefixes))
        return files

    def upload_file(
        self,
        bucket_name: str,
        source_path: str,
        destination_blob_name: str,
        overwrite: Union[bool, str] = False,
        create_folder: bool = True,
    ) -> None:
        try:
            blob_client = self._client.get_blob_client(
                container=bucket_name, blob=destination_blob_name
            )
            exists = blob_client.exists()
            if exists:
                if overwrite == 'prompt':
                    response = input(f"File {destination_blob_name} already exists. Overwrite? (y/n): ")
                    if response.lower() != 'y':
                        print("Skipping upload.")
                        return
                elif not overwrite:
                    print(f"File {destination_blob_name} already exists. Skipping upload.")
                    return

            with open(source_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True if overwrite or overwrite == 'prompt' else False)
        except AzureError as e:
            raise UploadError(f"Failed to upload file to Azure: {e}") from e

    def upload_files(
        self,
        bucket_name: str,
        source_paths: List[str],
        destination_folder: str,
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        for source_path in source_paths:
            destination_blob_name = os.path.join(destination_folder, os.path.basename(source_path)).replace("\\", "/")
            self.upload_file(bucket_name, source_path, destination_blob_name, overwrite, create_folder)

    def upload_folder(
        self,
        bucket_name: str,
        source_folder: str,
        destination_folder: str,
        recursive: bool = True,
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        for root, dirs, files in os.walk(source_folder):
            if not recursive and root != source_folder:
                continue
            for file in files:
                source_path = os.path.join(root, file)
                relative_path = os.path.relpath(source_path, source_folder)
                destination_blob_name = os.path.join(destination_folder, relative_path).replace("\\", "/")
                self.upload_file(bucket_name, source_path, destination_blob_name, overwrite, create_folder)

    def upload_dataframe(
        self,
        dataframe: DataFrame,
        bucket_name: str,
        destination_blob_name: str,
        file_format: str = "parquet",
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        blob_client = self._client.get_blob_client(
            container=bucket_name, blob=destination_blob_name
        )
        if not overwrite and blob_client.exists():
            print(f"File {destination_blob_name} already exists. Skipping upload.")
            return

        buffer = io.BytesIO()
        if file_format == "parquet":
            dataframe.write_parquet(buffer)
        elif file_format == "csv":
            dataframe.write_csv(buffer)
        elif file_format == "json":
            dataframe.write_json(buffer, row_oriented=True)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        buffer.seek(0)
        blob_client.upload_blob(buffer, overwrite=overwrite)

    def read_dataframe(
        self,
        bucket_name: str,
        blob_name: str,
        file_format: str = "parquet",
    ) -> DataFrame:
        try:
            blob_client = self._client.get_blob_client(container=bucket_name, blob=blob_name)
            if not blob_client.exists():
                raise FileNotFoundError(f"File not found on Azure: {blob_name}")
            downloader = blob_client.download_blob()
            buffer = io.BytesIO(downloader.readall())
            buffer.seek(0)
        except AzureError as e:
            raise DownloadError(f"Failed to read file from Azure: {e}") from e

        if file_format == "parquet":
            return pl.read_parquet(buffer)
        elif file_format == "csv":
            return pl.read_csv(buffer)
        elif file_format == "json":
            return pl.read_json(buffer)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def create_folder(self, bucket_name: str, folder_name: str) -> None:
        blob_name = f"{folder_name.strip('/')}/"
        try:
            blob_client = self._client.get_blob_client(container=bucket_name, blob=blob_name)
            if not blob_client.exists():
                blob_client.upload_blob(b"")
        except AzureError as e:
            raise UploadError(f"Failed to create folder in Azure: {e}") from e

    def rename_folder(self, bucket_name: str, old_folder_name: str, new_folder_name: str) -> None:
        old_folder_name = old_folder_name.strip('/') + '/'
        new_folder_name = new_folder_name.strip('/') + '/'

        container_client = self._client.get_container_client(bucket_name)
        blob_list = container_client.list_blobs(name_starts_with=old_folder_name)
        blobs_to_delete = []

        for blob in blob_list:
            new_blob_name = blob.name.replace(old_folder_name, new_folder_name, 1)
            new_blob_client = container_client.get_blob_client(new_blob_name)
            source_blob_client = container_client.get_blob_client(blob.name)
            new_blob_client.start_copy_from_url(source_blob_client.url)
            blobs_to_delete.append(blob.name)
        
        for blob_name in blobs_to_delete:
            container_client.delete_blob(blob_name)

    def delete_folder(self, bucket_name: str, folder_name: str) -> None:
        container_client = self._client.get_container_client(bucket_name)
        blob_list = container_client.list_blobs(name_starts_with=folder_name)
        for blob in blob_list:
            container_client.delete_blob(blob.name)

    def get_metadata(self, bucket_name: str, blob_name: str) -> dict:
        try:
            blob_client = self._client.get_blob_client(container=bucket_name, blob=blob_name)
            if not blob_client.exists():
                raise FileNotFoundError(f"File not found on Azure: {blob_name}")
            properties = blob_client.get_blob_properties()
            return properties.metadata
        except AzureError as e:
            raise DownloadError(f"Failed to get metadata from Azure: {e}") from e

    def set_metadata(self, bucket_name: str, blob_name: str, metadata: dict) -> None:
        try:
            blob_client = self._client.get_blob_client(container=bucket_name, blob=blob_name)
            if not blob_client.exists():
                raise FileNotFoundError(f"File not found on Azure: {blob_name}")
            blob_client.set_blob_metadata(metadata)
        except AzureError as e:
            raise UploadError(f"Failed to set metadata in Azure: {e}") from e
