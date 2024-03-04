# ctfcli-deploy-azure

A [ctfcli](https://github.com/CTFd/ctfcli) plugin for deploying CTF challenge containers to Azure. Currently supports web challenges via [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/).

## Installation

1. Install the plugin: `ctf plugins install https://github.com/pl4nty/ctfcli-deploy-azure.git`
2. Create an [Azure Container Apps environment](https://learn.microsoft.com/en-us/azure/container-apps/environment) and copy its [resource ID](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-get-info?tabs=portal#get-the-resource-id-for-a-storage-account)
3. (Optional) Add a [custom DNS suffix](https://learn.microsoft.com/en-us/azure/container-apps/environment-custom-dns-suffix)

## Usage

1. Login to Azure with a [method supported by DefaultAzureCredential](https://github.com/Azure/azure-sdk-for-python/blob/main/sdk/identity/azure-identity/README.md#defaultazurecredential) eg `az login`
2. Add container registry credentials to `.ctf/config`, or login to a container registry eg `az acr login --name example` and add `--skip-login` below
3. `ctf challenge deploy --host "azure://management.azure.com[env resource ID]?registry=ghcr.io/username"`
4. (Optional) If using a custom domain suffix, provide it in the suffix parameter eg "&suffix=.chals.example.com"

## Private container registries

Private container registries with password authentication are natively supported by `ctfcli`. To use Managed Identity authentication, [create a user-assigned managed identity](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/how-manage-user-assigned-managed-identities?pivots=identity-mi-methods-azp#create-a-user-assigned-managed-identity) and assign appropriate permissions eg `AcrPull` role for an Azure Container Registry. Copy its resource ID and provide it in an `identity` parameter with `--skip-login`:

`ctf challenge deploy --host "azure://management.azure.com[env resource ID]?registry=ghcr.io/username&identity=[identity resource ID] --skip-login`
