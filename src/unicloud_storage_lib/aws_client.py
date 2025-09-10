import os
import io
import boto3
from typing import Any, Dict, List, Optional, Union
import polars as pl
from botocore.exceptions import ClientError
from .base import BaseStorageClient, ConnectionError, DownloadError, UploadError, FileNotFoundError, DataFrame

class AwsStorageClient(BaseStorageClient):
    def __init__(self, auth_config: Dict[str, Any]):
        self.auth_config = auth_config
        self._client = self._connect()

    def _connect(self) -> boto3.client:
        try:
            return boto3.client(
                "s3",
                aws_access_key_id=self.auth_config.get("aws_access_key_id"),
                aws_secret_access_key=self.auth_config.get("aws_secret_access_key"),
                region_name=self.auth_config.get("region_name"),
            )
        except Exception as e:
            raise ConnectionError(f"Failed to connect to AWS: {e}") from e

    def download_file(
        self,
        bucket_name: str,
        blob_name: str,
        destination_path: str
    ) -> None:
        try:
            self._client.download_file(bucket_name, blob_name, destination_path)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found on AWS: {blob_name}") from e
            raise DownloadError(f"Failed to download file from AWS: {e}") from e

    def download_files(
        self,
        bucket_name: str,
        blob_names: List[str],
        destination_folder: str
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
        recursive: bool = True
    ) -> None:
        files = self.list_files(bucket_name, folder_name, recursive=recursive)
        self.download_files(bucket_name, files, destination_folder)

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
        
        files = self.list_files(bucket_name, folder_name, recursive=recursive)
        files_to_download = [
            f for f in files if any(f.endswith(ext) for ext in extensions)
        ]
        self.download_files(bucket_name, files_to_download, destination_folder)

    def list_files(
        self,
        bucket_name: str,
        folder_name: Optional[str] = None,
        recursive: bool = False
    ) -> List[str]:
        paginator = self._client.get_paginator("list_objects_v2")
        kwargs = {"Bucket": bucket_name}
        if folder_name:
            kwargs["Prefix"] = folder_name
        if not recursive:
            kwargs["Delimiter"] = "/"
        
        files = []
        for page in paginator.paginate(**kwargs):
            if "Contents" in page:
                for obj in page["Contents"]:
                    files.append(obj["Key"])
            if "CommonPrefixes" in page and not recursive:
                for prefix in page["CommonPrefixes"]:
                    files.append(prefix["Prefix"])
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
            exists = False
            try:
                self._client.head_object(Bucket=bucket_name, Key=destination_blob_name)
                exists = True
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise UploadError(f"Failed to check for file existence: {e}") from e

            if exists:
                if overwrite == 'prompt':
                    response = input(f"File {destination_blob_name} already exists. Overwrite? (y/n): ")
                    if response.lower() != 'y':
                        print("Skipping upload.")
                        return
                elif not overwrite:
                    print(f"File {destination_blob_name} already exists. Skipping upload.")
                    return
            
            self._client.upload_file(source_path, bucket_name, destination_blob_name)
        except ClientError as e:
            raise UploadError(f"Failed to upload file to AWS: {e}") from e

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
        if not overwrite:
            try:
                self._client.head_object(Bucket=bucket_name, Key=destination_blob_name)
                print(f"File {destination_blob_name} already exists. Skipping upload.")
                return
            except ClientError as e:
                if e.response["Error"]["Code"] != "404":
                    raise UploadError(f"Failed to check for file existence: {e}") from e

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
        self._client.upload_fileobj(buffer, bucket_name, destination_blob_name)

    def read_dataframe(
        self,
        bucket_name: str,
        blob_name: str,
        file_format: str = "parquet"
    ) -> DataFrame:
        buffer = io.BytesIO()
        try:
            self._client.download_fileobj(bucket_name, blob_name, buffer)
            buffer.seek(0)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found on AWS: {blob_name}") from e
            raise DownloadError(f"Failed to download file from AWS: {e}") from e

        if file_format == "parquet":
            return pl.read_parquet(buffer)
        elif file_format == "csv":
            return pl.read_csv(buffer)
        elif file_format == "json":
            return pl.read_json(buffer)
        else:
            raise ValueError(f"Unsupported file format: {file_format}")

    def create_folder(self, bucket_name: str, folder_name: str) -> None:
        self._client.put_object(Bucket=bucket_name, Key=f"{folder_name.strip('/')}/")

    def rename_folder(self, bucket_name: str, old_folder_name: str, new_folder_name: str) -> None:
        old_folder_name = old_folder_name.strip('/') + '/'
        new_folder_name = new_folder_name.strip('/') + '/'

        paginator = self._client.get_paginator("list_objects_v2")
        blobs_to_delete = []
        for page in paginator.paginate(Bucket=bucket_name, Prefix=old_folder_name):
            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                old_key = obj["Key"]
                new_key = new_folder_name + old_key[len(old_folder_name):]
                
                copy_source = {'Bucket': bucket_name, 'Key': old_key}
                self._client.copy_object(Bucket=bucket_name, CopySource=copy_source, Key=new_key)
                blobs_to_delete.append({'Key': old_key})
        
        if blobs_to_delete:
            self._client.delete_objects(Bucket=bucket_name, Delete={'Objects': blobs_to_delete})

    def delete_folder(self, bucket_name: str, folder_name: str) -> None:
        paginator = self._client.get_paginator("list_objects_v2")
        delete_keys = []
        for page in paginator.paginate(Bucket=bucket_name, Prefix=folder_name):
            if "Contents" in page:
                delete_keys.extend([{'Key': obj['Key']} for obj in page['Contents']])
        if delete_keys:
            self._client.delete_objects(Bucket=bucket_name, Delete={'Objects': delete_keys})

    def get_metadata(self, bucket_name: str, blob_name: str) -> dict:
        try:
            head_object = self._client.head_object(Bucket=bucket_name, Key=blob_name)
            return head_object.get("Metadata", {})
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found on AWS: {blob_name}") from e
            raise DownloadError(f"Failed to get metadata from AWS: {e}") from e

    def set_metadata(self, bucket_name: str, blob_name: str, metadata: dict) -> None:
        try:
            copy_source = {"Bucket": bucket_name, "Key": blob_name}
            self._client.copy_object(
                Bucket=bucket_name,
                Key=blob_name,
                CopySource=copy_source,
                Metadata=metadata,
                MetadataDirective="REPLACE",
            )
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise FileNotFoundError(f"File not found on AWS: {blob_name}") from e
            raise UploadError(f"Failed to set metadata in AWS: {e}") from e
