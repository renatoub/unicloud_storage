import os
import io
from typing import Any, Dict, List, Optional, Union
import pandas as pd
from google.cloud import storage
from google.api_core.exceptions import GoogleAPICallError
from .base import BaseStorageClient, ConnectionError, DownloadError, UploadError, FileNotFoundError

class GcpStorageClient(BaseStorageClient):
    def __init__(self, auth_config: Dict[str, Any]):
        self.auth_config = auth_config
        self._client = self._connect()

    def _connect(self) -> storage.Client:
        try:
            if "credentials_path" in self.auth_config:
                return storage.Client.from_service_account_json(
                    self.auth_config["credentials_path"]
                )
            else:
                return storage.Client()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to GCP: {e}") from e

    def download_file(
        self,
        bucket_name: str,
        blob_name: str,
        destination_path: str,
    ) -> None:
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            if not blob.exists():
                raise FileNotFoundError(f"File not found on GCP: {blob_name}")
            blob.download_to_filename(destination_path)
        except GoogleAPICallError as e:
            raise DownloadError(f"Failed to download file from GCP: {e}") from e

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
        blobs = self.list_files(bucket_name, folder_name, recursive=recursive)
        for blob_name in blobs:
            relative_path = os.path.relpath(blob_name, folder_name)
            destination_path = os.path.join(destination_folder, relative_path)
            destination_dir = os.path.dirname(destination_path)
            if not os.path.exists(destination_dir):
                os.makedirs(destination_dir)
            self.download_file(bucket_name, blob_name, destination_path)

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
        
        blobs = self.list_files(bucket_name, folder_name, recursive=recursive)
        files_to_download = [
            blob for blob in blobs if any(blob.endswith(ext) for ext in extensions)
        ]
        self.download_files(bucket_name, files_to_download, destination_folder)

    def list_files(
        self,
        bucket_name: str,
        folder_name: Optional[str] = None,
        recursive: bool = False,
    ) -> List[str]:
        blobs = self._client.bucket(bucket_name).list_blobs(prefix=folder_name, delimiter="/" if not recursive else None)
        files = []
        for blob in blobs:
            files.append(blob.name)
        if not recursive:
            for prefix in blobs.prefixes:
                files.append(prefix)
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
            bucket = self._client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)

            if blob.exists():
                if overwrite == 'prompt':
                    response = input(f"File {destination_blob_name} already exists. Overwrite? (y/n): ")
                    if response.lower() != 'y':
                        print("Skipping upload.")
                        return
                elif not overwrite:
                    print(f"File {destination_blob_name} already exists. Skipping upload.")
                    return

            blob.upload_from_filename(source_path)
        except GoogleAPICallError as e:
            raise UploadError(f"Failed to upload file to GCP: {e}") from e

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
        dataframe: pd.DataFrame,
        bucket_name: str,
        destination_blob_name: str,
        file_format: str = "parquet",
        overwrite: bool = False,
        create_folder: bool = True,
    ) -> None:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)

        if not overwrite and blob.exists():
            print(f"File {destination_blob_name} already exists. Skipping upload.")
            return

        buffer = io.BytesIO()
        if file_format == "parquet":
            dataframe.to_parquet(buffer, index=False)
        elif file_format == "csv":
            dataframe.to_csv(buffer, index=False)
        elif file_format == "json":
            dataframe.to_json(buffer, orient="records", lines=True)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

        buffer.seek(0)
        blob.upload_from_file(buffer)

    def read_dataframe(
        self, bucket_name: str, blob_name: str, file_format: str = "parquet"
    ) -> pd.DataFrame:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        
        if not blob.exists():
            raise FileNotFoundError(f"File not found on GCP: {blob_name}")

        buffer = io.BytesIO()
        blob.download_to_file(buffer)
        buffer.seek(0)

        if file_format == "parquet":
            return pd.read_parquet(buffer)
        elif file_format == "csv":
            return pd.read_csv(buffer)
        elif file_format == "json":
            return pd.read_json(buffer, orient="records", lines=True)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def create_folder(self, bucket_name: str, folder_name: str) -> None:
        bucket = self._client.bucket(bucket_name)
        blob = bucket.blob(f"{folder_name.strip('/')}/")
        blob.upload_from_string("")

    def rename_folder(self, bucket_name: str, old_folder_name: str, new_folder_name: str) -> None:
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=old_folder_name)
        blobs_to_delete = []
        for blob in blobs:
            new_blob_name = blob.name.replace(old_folder_name, new_folder_name, 1)
            bucket.copy_blob(blob, bucket, new_blob_name)
            blobs_to_delete.append(blob)
        
        for blob in blobs_to_delete:
            blob.delete()

    def delete_folder(self, bucket_name: str, folder_name: str) -> None:
        bucket = self._client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=folder_name)
        for blob in blobs:
            blob.delete()

    def get_metadata(self, bucket_name: str, blob_name: str) -> dict:
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.get_blob(blob_name)
            if not blob:
                raise FileNotFoundError(f"File not found on GCP: {blob_name}")
            return blob.metadata
        except GoogleAPICallError as e:
            raise DownloadError(f"Failed to get metadata from GCP: {e}") from e

    def set_metadata(self, bucket_name: str, blob_name: str, metadata: dict) -> None:
        try:
            bucket = self._client.bucket(bucket_name)
            blob = bucket.get_blob(blob_name)
            if not blob:
                raise FileNotFoundError(f"File not found on GCP: {blob_name}")
            blob.metadata = metadata
            blob.patch()
        except GoogleAPICallError as e:
            raise UploadError(f"Failed to set metadata in GCP: {e}") from e
