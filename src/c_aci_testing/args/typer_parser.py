#   ---------------------------------------------------------------------------------
#   Copyright (c) Microsoft Corporation. All rights reserved.
#   Licensed under the MIT License. See LICENSE in project root for information.
#   ---------------------------------------------------------------------------------

"""Typer-based CLI parser for c-aci-testing commands."""

from __future__ import annotations

import os
import subprocess
from typing import Optional, Dict, Any, List
import re

import typer
from typing_extensions import Annotated

# Create the main CLI app
app = typer.Typer(
    name="c-aci-testing",
    help="Utilities for testing workflows involving Confidential ACI.",
    no_args_is_help=True,
)

# Create sub-apps for each command category
env_app = typer.Typer(help="Environment management commands", no_args_is_help=True)
target_app = typer.Typer(help="Target management commands", no_args_is_help=True)
aci_app = typer.Typer(help="Azure Container Instance commands", no_args_is_help=True)
infra_app = typer.Typer(help="Infrastructure management commands", no_args_is_help=True)
images_app = typer.Typer(help="Container image management commands", no_args_is_help=True)
policies_app = typer.Typer(help="Policy management commands", no_args_is_help=True)
vm_app = typer.Typer(help="Virtual machine management commands", no_args_is_help=True)
vscode_app = typer.Typer(help="VSCode integration commands", no_args_is_help=True)
github_app = typer.Typer(help="GitHub integration commands", no_args_is_help=True)
vn2_app = typer.Typer(help="VN2 management commands", no_args_is_help=True)

# Add sub-apps to main app
app.add_typer(env_app, name="env")
app.add_typer(target_app, name="target")
app.add_typer(aci_app, name="aci")
app.add_typer(infra_app, name="infra")
app.add_typer(images_app, name="images")
app.add_typer(policies_app, name="policies")
app.add_typer(vm_app, name="vm")
app.add_typer(vscode_app, name="vscode")
app.add_typer(github_app, name="github")
app.add_typer(vn2_app, name="vn2")


# Helper functions for common argument patterns
def get_env_or_prompt(env_var: str, prompt: str, default: Optional[str] = None) -> str:
    """Get value from environment variable, or prompt user if not set."""
    value = os.getenv(env_var, default)
    if not value:
        value = typer.prompt(prompt)
    return value


def get_subscription_default() -> str:
    """Get default subscription from Azure CLI."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "--output", "tsv"],
            stdout=subprocess.PIPE,
            check=True,
            text=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def parse_key_value_pairs(values: List[str]) -> Dict[str, str]:
    """Parse key=value pairs from command line arguments."""
    kv_pairs = {}
    for value in values:
        if "=" not in value:
            raise typer.BadParameter(f"Invalid format for key-value pair: {value}. Expected format is key=value.")
        key, val = value.split("=", 1)
        kv_pairs[key.strip()] = val.strip()
    return kv_pairs


# Common option types with environment variable support
SubscriptionOption = Annotated[
    str,
    typer.Option(
        "--subscription",
        help="The Azure subscription ID to use",
        envvar="SUBSCRIPTION",
    ),
]

ResourceGroupOption = Annotated[
    str,
    typer.Option(
        "--resource-group",
        help="The Azure resource group to use",
        envvar="RESOURCE_GROUP",
    ),
]

LocationOption = Annotated[
    str,
    typer.Option(
        "--location",
        help="The Azure location to use",
        envvar="LOCATION",
    ),
]

RegistryOption = Annotated[
    str,
    typer.Option(
        "--registry",
        help="The container registry to use",
        envvar="REGISTRY",
    ),
]

ManagedIdentityOption = Annotated[
    str,
    typer.Option(
        "--managed-identity",
        help="The managed identity resource ID to use",
        envvar="MANAGED_IDENTITY",
    ),
]

DeploymentNameOption = Annotated[
    str,
    typer.Option(
        "--deployment-name",
        help="The name of the Azure deployment",
        envvar="DEPLOYMENT_NAME",
    ),
]

RepositoryOption = Annotated[
    Optional[str],
    typer.Option(
        "--repository",
        help="The container repository name",
        envvar="REPOSITORY",
    ),
]

TagOption = Annotated[
    Optional[str],
    typer.Option(
        "--tag",
        help="The container image tag",
        envvar="TAG",
    ),
]


# Environment commands
@env_app.command("create")
def env_create():
    """Create environment variables template."""
    from ..tools.env_create import env_create
    env_create()


# ACI commands  
aci_get_app = typer.Typer(help="Get ACI information", no_args_is_help=True)
aci_app.add_typer(aci_get_app, name="get")

@aci_app.command("deploy")
def aci_deploy(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
    location: Annotated[
        Optional[str],
        typer.Option(
            "--location",
            help="The Azure location to use",
            envvar="LOCATION",
        ),
    ] = None,
    managed_identity: Annotated[
        Optional[str],
        typer.Option(
            "--managed-identity",
            help="The managed identity resource ID to use",
            envvar="MANAGED_IDENTITY",
        ),
    ] = None,
):
    """Deploy ACI resources."""
    # Prompt for missing required arguments
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    if not location:
        location = typer.prompt("Location")
    if not managed_identity:
        managed_identity = typer.prompt("Managed identity resource ID")
    
    from ..tools.aci_deploy import aci_deploy
    aci_deploy(
        target_path=os.path.abspath(target_path),
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        location=location,
        managed_identity=managed_identity,
    )


@aci_get_app.command("ids")
def aci_get_ids(
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
):
    """Get ACI container IDs."""
    # Prompt for missing required arguments
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    
    from ..tools.aci_get_ids import aci_get_ids
    result = aci_get_ids(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )
    print(result)


# Images commands
@images_app.command("build")
def images_build(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    registry: Annotated[
        Optional[str],
        typer.Option(
            "--registry",
            help="The container registry to use",
            envvar="REGISTRY",
        ),
    ] = None,
    repository: RepositoryOption = None,
    tag: TagOption = None,
):
    """Build container images."""
    # Prompt for missing required arguments
    if not registry:
        registry = typer.prompt("Container registry")
    
    from ..tools.images_build import images_build
    images_build(
        target_path=os.path.abspath(target_path),
        registry=registry,
        repository=repository,
        tag=tag,
    )


# Policies commands
@policies_app.command("gen")
def policies_gen(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    policy_type: Annotated[
        Optional[str],
        typer.Option(
            "--policy-type",
            help="The policy type to use",
            envvar="POLICY_TYPE",
        ),
    ] = None,
):
    """Generate policies."""
    # Prompt for missing required arguments
    if not policy_type:
        policy_type = typer.prompt("Policy type")
    
    from ..tools.policies_gen import policies_gen
    policies_gen(
        target_path=os.path.abspath(target_path),
        policy_type=policy_type,
    )


@aci_app.command("monitor")
def aci_monitor(
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
    follow: Annotated[
        bool,
        typer.Option(
            "--follow/--no-follow",
            help="Follow logs after deployment",
        ),
    ] = False,
):
    """Monitor ACI deployment."""
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    
    from ..tools.aci_monitor import aci_monitor
    aci_monitor(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        follow=follow,
    )


@aci_app.command("remove")
def aci_remove(
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
):
    """Remove ACI deployment."""
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    
    from ..tools.aci_remove import aci_remove
    aci_remove(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )


@aci_app.command("param_set")
def aci_param_set(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    parameters: Annotated[
        Optional[List[str]],
        typer.Option(
            "--parameters",
            help="The parameter key value pair to add in the format key=value",
        ),
    ] = None,
    add: Annotated[
        bool,
        typer.Option(
            "--add/--no-add",
            help="Add the parameter to the list if it isn't already present",
        ),
    ] = True,
):
    """Set parameters in ACI deployment."""
    parameters_dict = {}
    if parameters:
        parameters_dict = parse_key_value_pairs(parameters)
    
    from ..tools.aci_param_set import aci_param_set
    aci_param_set(
        target_path=os.path.abspath(target_path),
        parameters=parameters_dict,
        add=add,
    )


@aci_get_app.command("ips")
def aci_get_ips(
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
):
    """Get ACI container IPs."""
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    
    from ..tools.aci_get_ips import aci_get_ips
    result = aci_get_ips(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )
    print(result)


@aci_get_app.command("is_live")
def aci_get_is_live(
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
):
    """Check if ACI deployment is live."""
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    
    from ..tools.aci_get_is_live import aci_get_is_live
    result = aci_get_is_live(
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
    )
    print(result)


@images_app.command("push")
def images_push(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    registry: Annotated[
        Optional[str],
        typer.Option(
            "--registry",
            help="The container registry to use",
            envvar="REGISTRY",
        ),
    ] = None,
    repository: RepositoryOption = None,
    tag: TagOption = None,
):
    """Push container images."""
    if not registry:
        registry = typer.prompt("Container registry")
    
    from ..tools.images_push import images_push
    images_push(
        target_path=os.path.abspath(target_path),
        registry=registry,
        repository=repository,
        tag=tag,
    )


@images_app.command("pull")
def images_pull(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    registry: Annotated[
        Optional[str],
        typer.Option(
            "--registry",
            help="The container registry to use",
            envvar="REGISTRY",
        ),
    ] = None,
    repository: RepositoryOption = None,
    tag: TagOption = None,
):
    """Pull container images."""
    if not registry:
        registry = typer.prompt("Container registry")
    
    from ..tools.images_pull import images_pull
    images_pull(
        target_path=os.path.abspath(target_path),
        registry=registry,
        repository=repository,
        tag=tag,
    )


# GitHub commands
@github_app.command("workflow")
def github_workflow(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
):
    """GitHub workflow operations."""
    from ..tools.github_workflow import github_workflow
    github_workflow(target_path=os.path.abspath(target_path))


# VSCode commands
@vscode_app.command("run_debug")
def vscode_run_debug(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
):
    """Run debug configuration in VSCode."""
    from ..tools.vscode_run_debug import vscode_run_debug
    vscode_run_debug(target_path=os.path.abspath(target_path))


# Target commands
@target_app.command("create")
def target_create(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    name: Annotated[
        str,
        typer.Option(
            "-n", "--name",
            help="The name of the new target",
        ),
    ] = "example",
):
    """Create a new target."""
    from ..tools.target_create import target_create
    target_create(target_path=os.path.abspath(target_path), name=name)


@target_app.command("add_test")
def target_add_test(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
):
    """Add a test to the target."""
    from ..tools.target_add_test import target_add_test
    target_add_test(target_path=os.path.abspath(target_path))


@target_app.command("run")
def target_run(
    target_path: Annotated[
        str,
        typer.Argument(
            help="The relative path to the c-aci-testing target directory",
        ),
    ] = os.getcwd(),
    deployment_name: Annotated[
        Optional[str],
        typer.Option(
            "--deployment-name",
            help="The name of the Azure deployment",
            envvar="DEPLOYMENT_NAME",
        ),
    ] = None,
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option(
            "--registry",
            help="The container registry to use",
            envvar="REGISTRY",
        ),
    ] = None,
    repository: RepositoryOption = None,
    tag: TagOption = None,
    location: Annotated[
        Optional[str],
        typer.Option(
            "--location",
            help="The Azure location to use",
            envvar="LOCATION",
        ),
    ] = None,
    managed_identity: Annotated[
        Optional[str],
        typer.Option(
            "--managed-identity",
            help="The managed identity resource ID to use",
            envvar="MANAGED_IDENTITY",
        ),
    ] = None,
    policy_type: Annotated[
        Optional[str],
        typer.Option(
            "--policy-type",
            help="The policy type to use",
            envvar="POLICY_TYPE",
        ),
    ] = None,
    follow: Annotated[
        bool,
        typer.Option(
            "--follow/--no-follow",
            help="Follow logs after deployment",
        ),
    ] = False,
    cleanup: Annotated[
        bool,
        typer.Option(
            "--cleanup/--no-cleanup",
            help="Cleanup the target resources after completion",
        ),
    ] = True,
    prefer_pull: Annotated[
        bool,
        typer.Option(
            "--prefer-pull",
            help="Attempt to pull images before building them",
        ),
    ] = False,
):
    """Run a target."""
    # Prompt for missing required arguments
    if not deployment_name:
        deployment_name = typer.prompt("Deployment name")
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    if not registry:
        registry = typer.prompt("Container registry")
    if not location:
        location = typer.prompt("Location")
    if not managed_identity:
        managed_identity = typer.prompt("Managed identity resource ID")
    if not policy_type:
        policy_type = typer.prompt("Policy type")
    
    from ..tools.target_run import target_run
    target_run(
        target_path=os.path.abspath(target_path),
        deployment_name=deployment_name,
        subscription=subscription,
        resource_group=resource_group,
        registry=registry,
        repository=repository,
        tag=tag,
        location=location,
        managed_identity=managed_identity,
        policy_type=policy_type,
        follow=follow,
        cleanup=cleanup,
        prefer_pull=prefer_pull,
    )


# Infrastructure commands
@infra_app.command("deploy")
def infra_deploy(
    subscription: Annotated[
        Optional[str],
        typer.Option(
            "--subscription",
            help="The Azure subscription ID to use",
            envvar="SUBSCRIPTION",
        ),
    ] = None,
    resource_group: Annotated[
        Optional[str],
        typer.Option(
            "--resource-group",
            help="The Azure resource group to use",
            envvar="RESOURCE_GROUP",
        ),
    ] = None,
    registry: Annotated[
        Optional[str],
        typer.Option(
            "--registry",
            help="The container registry to use",
            envvar="REGISTRY",
        ),
    ] = None,
    managed_identity: Annotated[
        Optional[str],
        typer.Option(
            "--managed-identity",
            help="The managed identity resource ID to use",
            envvar="MANAGED_IDENTITY",
        ),
    ] = None,
    location: Annotated[
        Optional[str],
        typer.Option(
            "--location",
            help="The Azure location to use",
            envvar="LOCATION",
        ),
    ] = None,
    storage_account: Annotated[
        Optional[str],
        typer.Option(
            "--storage-account",
            help="The storage account to use",
            envvar="STORAGE_ACCOUNT",
        ),
    ] = None,
    github_repo: Annotated[
        Optional[str],
        typer.Option(
            "--github-repo",
            help="The Github repository to give credentials for",
            envvar="GITHUB_REPO",
        ),
    ] = None,
):
    """Deploy infrastructure."""
    # Prompt for missing required arguments
    if not subscription:
        subscription = get_subscription_default() or typer.prompt("Subscription ID")
    if not resource_group:
        resource_group = typer.prompt("Resource group")
    if not registry:
        registry = typer.prompt("Container registry")
    if not managed_identity:
        managed_identity = typer.prompt("Managed identity resource ID")
    if not location:
        location = typer.prompt("Location")
    if not github_repo:
        github_repo = typer.prompt("GitHub repository")
    
    from ..tools.infra_deploy import infra_deploy
    infra_deploy(
        subscription=subscription,
        resource_group=resource_group,
        registry=registry,
        managed_identity=managed_identity,
        location=location,
        storage_account=storage_account,
        github_repo=github_repo,
    )


if __name__ == "__main__":
    app()