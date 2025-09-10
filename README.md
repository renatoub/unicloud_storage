# Unicloud Storage

`Unicloud Storage` is a Python library designed to simplify interaction with object storage services on commercial clouds like **AWS S3**, **Google Cloud Storage (GCS)**, and **Azure Blob Storage**. The library unifies the different APIs into a single, intuitive interface, allowing developers and data engineers to consistently manage files and folders regardless of the cloud provider.

[Leia em português](docs/README_pt.md)

## Features

*   **Multi-Cloud Connectivity**: Manage connections to AWS, GCP, and Azure from a single class.
*   **File Operations**: Download and upload files, with support for recursive operations and filtering by extension.
*   **DataFrame Integration**: Directly upload and download `pandas.DataFrame` objects to and from cloud storage.
*   **Folder Management**: Create, rename, and delete folders.
*   **Metadata Management**: Get and set file metadata.

## Installation

```bash
pip install unicloud-storage
```

## Authentication

Credentials can be provided through a dictionary. Here are examples for each provider:

**AWS**
```python
aws_auth = {
    "aws_access_key_id": "YOUR_ACCESS_KEY",
    "aws_secret_access_key": "YOUR_SECRET_KEY",
    "region_name": "us-east-1"
}
```

**GCP**
```python
gcp_auth = {
    "credentials_path": "/path/to/your/gcp-credentials.json"
}
```

**Azure**
```python
azure_auth = {
    "auth_method": "connection_string",
    "connection_string": "YOUR_CONNECTION_STRING"
}
# Or using other auth methods like sas_token or user_credentials
```

## Usage

### Getting a Client

```python
from unicloud_storage import get_client

# Get an AWS client
aws_client = get_client('aws', aws_auth)

# Get a GCP client
gcp_client = get_client('gcp', gcp_auth)

# Get an Azure client
azure_client = get_client('azure', azure_auth)
```

### Downloading Files

**Download a single file:**
```python
client.download_file(
    bucket_name="my-bucket",
    blob_name="data/my_file.txt",
    destination_path="local/my_file.txt"
)
```

**Download a list of files:**
```python
client.download_files(
    bucket_name="my-bucket",
    blob_names=["data/file1.txt", "data/file2.txt"],
    destination_folder="local/data"
)
```

**Download a folder:**
```python
client.download_folder(
    bucket_name="my-bucket",
    folder_name="data/",
    destination_folder="local/data"
)
```

**Download files by extension:**
```python
client.download_by_extension(
    bucket_name="my-bucket",
    destination_folder="local/images",
    extensions=[".jpg", ".png"],
    folder_name="images/"
)
```

### Uploading Files

**Upload a single file:**
```python
client.upload_file(
    bucket_name="my-bucket",
    source_path="local/new_file.txt",
    destination_blob_name="data/new_file.txt",
    overwrite=True # or False, or 'prompt'
)
```

**Upload a folder:**
```python
client.upload_folder(
    bucket_name="my-bucket",
    source_folder="local/data/",
    destination_folder="data/"
)
```

### Working with DataFrames

**Upload a DataFrame:**
```python
import pandas as pd

df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})

client.upload_dataframe(
    dataframe=df,
    bucket_name="my-bucket",
    destination_blob_name="data/my_df.parquet",
    file_format="parquet"
)
```

**Read a DataFrame:**
```python
df = client.read_dataframe(
    bucket_name="my-bucket",
    blob_name="data/my_df.parquet",
    file_format="parquet"
)
```

### Folder Management

**Create a folder:**
```python
client.create_folder(bucket_name="my-bucket", folder_name="new_folder/")
```

**Rename a folder:**
```python
client.rename_folder(
    bucket_name="my-bucket",
    old_folder_name="new_folder/",
    new_folder_name="renamed_folder/"
)
```

**Delete a folder:**
```python
client.delete_folder(bucket_name="my-bucket", folder_name="renamed_folder/")
```

### Metadata Management

**Set metadata:**
```python
client.set_metadata(
    bucket_name="my-bucket",
    blob_name="data/my_file.txt",
    metadata={"author": "John Doe", "version": "1.0"}
)
```

**Get metadata:**
```python
metadata = client.get_metadata(
    bucket_name="my-bucket",
    blob_name="data/my_file.txt"
)
print(metadata)
```
