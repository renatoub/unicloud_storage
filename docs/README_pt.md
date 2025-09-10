# Unicloud Storage

`Unicloud Storage` é uma biblioteca Python projetada para simplificar a interação com serviços de armazenamento de objetos em nuvens comerciais como **AWS S3**, **Google Cloud Storage (GCS)** e **Azure Blob Storage**. A biblioteca unifica as diferentes APIs em uma interface única e intuitiva, permitindo que desenvolvedores e engenheiros de dados gerenciem arquivos e pastas de forma consistente, independentemente do provedor de nuvem.

[Read in English](../README.md)

## Funcionalidades

*   **Conectividade Multi-Cloud**: Gerencie conexões com AWS, GCP e Azure a partir de uma única classe.
*   **Operações de Arquivo**: Baixe e envie arquivos, com suporte para operações recursivas e filtragem por extensão.
*   **Integração com DataFrame**: Envie e baixe objetos `pandas.DataFrame` diretamente para e do armazenamento em nuvem.
*   **Gerenciamento de Pastas**: Crie, renomeie e exclua pastas.
*   **Gerenciamento de Metadados**: Obtenha e defina metadados de arquivos.

## Instalação

```bash
pip install unicloud-storage
```

## Autenticação

As credenciais podem ser fornecidas através de um dicionário. Aqui estão exemplos para cada provedor:

**AWS**
```python
aws_auth = {
    "aws_access_key_id": "SUA_CHAVE_DE_ACESSO",
    "aws_secret_access_key": "SUA_CHAVE_SECRETA",
    "region_name": "us-east-1"
}
```

**GCP**
```python
gcp_auth = {
    "credentials_path": "/caminho/para/suas/credenciais-gcp.json"
}
```

**Azure**
```python
azure_auth = {
    "auth_method": "connection_string",
    "connection_string": "SUA_CONNECTION_STRING"
}
# Ou usando outros métodos de autenticação como sas_token ou user_credentials
```

## Uso

### Obtendo um Cliente

```python
from unicloud_storage import get_client

# Obtenha um cliente AWS
aws_client = get_client('aws', aws_auth)

# Obtenha um cliente GCP
gcp_client = get_client('gcp', gcp_auth)

# Obtenha um cliente Azure
azure_client = get_client('azure', azure_auth)
```

### Baixando Arquivos

**Baixar um único arquivo:**
```python
client.download_file(
    bucket_name="meu-bucket",
    blob_name="dados/meu_arquivo.txt",
    destination_path="local/meu_arquivo.txt"
)
```

**Baixar uma lista de arquivos:**
```python
client.download_files(
    bucket_name="meu-bucket",
    blob_names=["dados/arquivo1.txt", "dados/arquivo2.txt"],
    destination_folder="local/dados"
)
```

**Baixar uma pasta:**
```python
client.download_folder(
    bucket_name="meu-bucket",
    folder_name="dados/",
    destination_folder="local/dados"
)
```

**Baixar arquivos por extensão:**
```python
client.download_by_extension(
    bucket_name="meu-bucket",
    destination_folder="local/imagens",
    extensions=[".jpg", ".png"],
    folder_name="imagens/"
)
```

### Enviando Arquivos

**Enviar um único arquivo:**
```python
client.upload_file(
    bucket_name="meu-bucket",
    source_path="local/novo_arquivo.txt",
    destination_blob_name="dados/novo_arquivo.txt",
    overwrite=True # ou False, ou 'prompt'
)
```

**Enviar uma pasta:**
```python
client.upload_folder(
    bucket_name="meu-bucket",
    source_folder="local/dados/",
    destination_folder="dados/"
)
```

### Trabalhando com DataFrames

**Enviar um DataFrame:**
```python
import pandas as pd

df = pd.DataFrame({'col1': [1, 2], 'col2': [3, 4]})

client.upload_dataframe(
    dataframe=df,
    bucket_name="meu-bucket",
    destination_blob_name="dados/meu_df.parquet",
    file_format="parquet"
)
```

**Ler um DataFrame:**
```python
df = client.read_dataframe(
    bucket_name="meu-bucket",
    blob_name="dados/meu_df.parquet",
    file_format="parquet"
)
```

### Gerenciamento de Pastas

**Criar uma pasta:**
```python
client.create_folder(bucket_name="meu-bucket", folder_name="nova_pasta/")
```

**Renomear uma pasta:**
```python
client.rename_folder(
    bucket_name="meu-bucket",
    old_folder_name="nova_pasta/",
    new_folder_name="pasta_renomeada/"
)
```

**Excluir uma pasta:**
```python
client.delete_folder(bucket_name="meu-bucket", folder_name="pasta_renomeada/")
```

### Gerenciamento de Metadados

**Definir metadados:**
```python
client.set_metadata(
    bucket_name="meu-bucket",
    blob_name="dados/meu_arquivo.txt",
    metadata={"autor": "Joao Silva", "versao": "1.0"}
)
```

**Obter metadados:**
```python
metadata = client.get_metadata(
    bucket_name="meu-bucket",
    blob_name="dados/meu_arquivo.txt"
)
print(metadata)
```
