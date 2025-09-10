import pytest
from unittest.mock import MagicMock, patch, mock_open, call
from unicloud_storage_lib import StorageConnector

# The module where the code under test lives
MODULE_PATH = "unicloud_storage_lib"

# Path to the classes as they are used in the module under test
BLOB_SERVICE_CLIENT_PATH = f"{MODULE_PATH}.BlobServiceClient"
USERNAME_PASSWORD_CREDENTIAL_PATH = f"{MODULE_PATH}.UsernamePasswordCredential"

# A valid dummy URL for Azure Storage
AZURE_DUMMY_URL = "https://testaccount.blob.core.windows.net"

@pytest.fixture
def mock_connector(mocker):
    """Provides a StorageConnector instance with a mocked _connect method."""
    mock_service_client = MagicMock()
    mocker.patch(f"{MODULE_PATH}.StorageConnector._connect", return_value=mock_service_client)
    connector = StorageConnector(provider="azure", auth_config={}) # Auth is mocked
    connector._client = mock_service_client # Explicitly set the client
    return connector

# --- Connection Tests ---

def test_connect_azure_with_connection_string(mocker):
    mock_from_conn_str = mocker.patch(f"{BLOB_SERVICE_CLIENT_PATH}.from_connection_string")
    StorageConnector(provider="azure", auth_config={"auth_method": "connection_string", "connection_string": "test_conn_str"})
    mock_from_conn_str.assert_called_once_with("test_conn_str")

def test_connect_azure_with_sas_token(mocker):
    mock_service_client_constructor = mocker.patch(BLOB_SERVICE_CLIENT_PATH)
    StorageConnector(provider="azure", auth_config={"auth_method": "sas_token", "account_url": AZURE_DUMMY_URL, "sas_token": "test_token"})
    mock_service_client_constructor.assert_called_once_with(account_url=AZURE_DUMMY_URL, credential="test_token")

# --- Single File Operation Tests ---

@patch("builtins.open", new_callable=mock_open)
def test_upload_file(mock_open_file, mock_connector):
    mock_connector.upload_file("test-bucket", "/path/to/source.txt", "dest/blob.txt")
    mock_open_file.assert_called_once_with("/path/to/source.txt", "rb")
    mock_connector._client.get_blob_client().upload_blob.assert_called_once()

@patch("builtins.open", new_callable=mock_open)
def test_download_file(mock_open_file, mock_connector):
    mock_blob_client = mock_connector._client.get_blob_client()
    mock_download_stream = mock_blob_client.download_blob()
    mock_download_stream.readall.return_value = b"file data"
    mock_connector.download_file("test-bucket", "source/blob.txt", "/path/to/dest.txt")
    mock_open_file.assert_called_once_with("/path/to/dest.txt", "wb")
    mock_open_file().write.assert_called_once_with(b"file data")

# --- Multi-File Upload Tests ---

@patch("os.path.isdir", return_value=False)
@patch("os.path.isfile", return_value=True)
def test_upload_mult_files_single_file(mock_isfile, mock_isdir, mock_connector):
    mock_connector.upload_file = MagicMock()
    mock_connector.upload_mult_files("/local/file.txt", "test-bucket", "cloud/folder")
    mock_connector.upload_file.assert_called_once_with("test-bucket", "/local/file.txt", "cloud/folder/file.txt")

@patch("os.walk")
@patch("os.path.isdir", return_value=True)
@patch("os.path.isfile", return_value=False)
def test_upload_mult_files_directory(mock_isfile, mock_isdir, mock_walk, mock_connector):
    mock_walk.return_value = [
        ("/local/dir", ["subdir"], ["file1.txt", "file2.log"]),
        ("/local/dir/subdir", [], ["file3.txt"]),
    ]
    mock_connector.upload_file = MagicMock()
    mock_connector.upload_mult_files("/local/dir", "test-bucket", "cloud/dest")
    expected_calls = [
        call("test-bucket", "/local/dir/file1.txt", "cloud/dest/file1.txt"),
        call("test-bucket", "/local/dir/file2.log", "cloud/dest/file2.log"),
        call("test-bucket", "/local/dir/subdir/file3.txt", "cloud/dest/subdir/file3.txt"),
    ]
    mock_connector.upload_file.assert_has_calls(expected_calls, any_order=True)

@patch("os.walk")
@patch("os.path.isdir", return_value=True)
@patch("os.path.isfile", return_value=False)
def test_upload_mult_files_directory_with_filter(mock_isfile, mock_isdir, mock_walk, mock_connector):
    mock_walk.return_value = [("/local/dir", [], ["file1.txt", "image.jpg", "file2.txt"])]
    mock_connector.upload_file = MagicMock()
    mock_connector.upload_mult_files("/local/dir", "test-bucket", "cloud/dest", extension=".txt")
    expected_calls = [
        call("test-bucket", "/local/dir/file1.txt", "cloud/dest/file1.txt"),
        call("test-bucket", "/local/dir/file2.txt", "cloud/dest/file2.txt"),
    ]
    mock_connector.upload_file.assert_has_calls(expected_calls, any_order=True)

# --- Multi-File Download Tests ---

@patch("os.makedirs")
@patch("os.path.isdir", return_value=True) # Assume dest dir exists for simplicity in some tests
def test_download_mult_files_directory(mock_isdir, mock_makedirs, mock_connector):
    mock_blob1 = MagicMock(); mock_blob1.name = "cloud/folder/file1.txt"
    mock_blob2 = MagicMock(); mock_blob2.name = "cloud/folder/subdir/file2.log"
    mock_container_client = mock_connector._client.get_container_client()
    mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]
    mock_connector.download_file = MagicMock()
    mock_connector.download_mult_files("cloud/folder", "test-bucket", "/local/dest")
    mock_container_client.list_blobs.assert_called_once_with(name_starts_with="cloud/folder")
    expected_calls = [
        call("test-bucket", "cloud/folder/file1.txt", "/local/dest/file1.txt"),
        call("test-bucket", "cloud/folder/subdir/file2.log", "/local/dest/subdir/file2.log"),
    ]
    mock_connector.download_file.assert_has_calls(expected_calls, any_order=True)

@patch("os.makedirs")
@patch("os.path.isdir", return_value=True)
def test_download_mult_files_with_filter(mock_isdir, mock_makedirs, mock_connector):
    mock_blob1 = MagicMock(); mock_blob1.name = "cloud/folder/file1.txt"
    mock_blob2 = MagicMock(); mock_blob2.name = "cloud/folder/image.jpg"
    mock_container_client = mock_connector._client.get_container_client()
    mock_container_client.list_blobs.return_value = [mock_blob1, mock_blob2]
    mock_connector.download_file = MagicMock()
    mock_connector.download_mult_files("cloud/folder", "test-bucket", "/local/dest", extension=".txt")
    mock_connector.download_file.assert_called_once_with("test-bucket", "cloud/folder/file1.txt", "/local/dest/file1.txt")
