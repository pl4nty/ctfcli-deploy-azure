# based on https://github.com/CTFd/ctfcli/blob/0.1.1/ctfcli/core/deployment/registry.py

import logging
from urllib.parse import urlparse, parse_qs

import click
from slugify import slugify
from azure.identity import DefaultAzureCredential
from azure.mgmt.core.tools import parse_resource_id
from azure.mgmt.appcontainers import ContainerAppsAPIClient, types

from ctfcli.core.deployment import register_deployment_handler
from ctfcli.core.deployment.base import DeploymentHandler, DeploymentResult
from ctfcli.core.deployment.registry import RegistryDeploymentHandler

log = logging.getLogger("ctfcli.core.deployment.azure")
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARN) # defaults to INFO

class AzureDeploymentHandler(DeploymentHandler):
    def __init__(self, *args, **kwargs):
        super(AzureDeploymentHandler, self).__init__(*args, **kwargs)

        # default to tcp for pwn challenges and https for web
        if not self.protocol:
            self.protocol = {"pwn": "tcp", "web": "https"}.get(self.challenge.get("category"))

    def deploy(self, skip_login=False, *args, **kwargs) -> DeploymentResult:
        # Check whether challenge defines image
        # Unnecessary, but ensures compatibility with other deployment handlers
        if not self.challenge.get("image"):
            click.secho("Challenge does not define an image to deploy", fg="red")
            return DeploymentResult(False)

        if not self.host:
            click.secho(
                "No host provided for the deployment. Use --host, or define host in the challenge.yml file",
                fg="red",
            )
            return DeploymentResult(False)

        # azure://management.azure.com/subscriptions/<id>/resourceGroups/<rg>/providers/Microsoft.App/managedEnvironments/cae?registry=example.azurecr.io&suffix=chals.example.com&identity=<ARM ID>
        host_url = urlparse(self.host)
        query = parse_qs(host_url.query)
        registry = query.get("registry", None)
        if not registry:
            click.secho(
                "No registry provided for the deployment. Ensure the host contains a registry query parameter like ?registry=example.azurecr.io",
                fg="red",
            )
            return DeploymentResult(False)
        registry = registry[0]

        id = parse_resource_id(host_url.path)
        client = ContainerAppsAPIClient(DefaultAzureCredential(), id.get("subscription"), f"https://{host_url.hostname}", logging_enable=False)
        environment = client.managed_environments.get(id.get("resource_group"), id.get("name"))

        result = RegistryDeploymentHandler(self.challenge, f"registry://{registry}").deploy(skip_login)
        if not result.success:
            return result

        # after the registry push, which builds the image
        port = self.challenge.image.get_exposed_port()
        if not port:
            click.secho("Challenge image does not expose a port", fg="red")
            return DeploymentResult(False)
        port = int(port)

        identities = query.get("identity", [])
        ingress: types.Ingress = {
            "external": True,
            "transport": "tcp" if self.protocol == "tcp" else "auto", # auto is http-only
            "targetPort": port,
            "stickySessions": {"affinity": "sticky"},
        }
        if self.protocol == "tcp":
            ingress["exposedPort"] = port

        # v5 accepts plain ARM JSON dicts, typed by azure.mgmt.appcontainers.types
        name = slugify(self.challenge.get("name"))
        container_app: types.ContainerApp = {
            "location": environment.location,
            "identity": {
                "type": "UserAssigned",
                "userAssignedIdentities": {identity: {} for identity in identities},
            } if identities else {"type": "None"},
            "properties": {
                "environmentId": environment.id,
                "configuration": {
                    "ingress": ingress,
                    "registries": [{"server": registry.split("/")[0], "identity": identity} for identity in identities],
                },
                "template": {
                    "containers": [{"name": "main", "image": f"{registry.rstrip('/')}/{self.challenge.image.basename}"}],
                },
            },
        }
        result = client.container_apps.begin_create_or_update(id.get("resource_group"), name, container_app).result()

        if query.get("suffix", None):
            connection_info = f"{name}.{query.get('suffix')[0]}"
        else:
            connection_info = result.properties.latest_revision_fqdn

        match self.protocol:
            case "tcp":
                connection_info = f"nc {connection_info} {port}"
            case "https":
                connection_info = f"https://{connection_info}"

        return DeploymentResult(True, connection_info=connection_info)

def load(commands):
    register_deployment_handler("azure", AzureDeploymentHandler)
