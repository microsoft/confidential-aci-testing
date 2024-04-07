# Confidential ACI Testing

This project provides utilities for testing workflows involving Confidential ACI.

## Prerequisites

### [Docker](https://docs.docker.com/get-docker/) 

Any operations which require docker, require the following flag:
```
-v /var/run/docker.sock:/var/run/docker.sock
```
This enables docker-in-docker inside the testing container.

### [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)

After installing, log into your azure account with:
```
az login
```

Any operation which requires the Azure CLI, requires the following command:
```
-v ~/.azure:/root/.azure
```

This passes your Azure Identity down into the container.

## Setup

### Define your environment
```
docker run \
    cacitesting.azurecr.io/releases:latest \
    c_aci_testing.env_create > cacitesting.env
```
This creates an environment file with the core variables that need to be defined, such as the URL of the registry to use for image pushing.

### Deploy infrastructure to Azure
```
docker run \
    -v ~/.azure:/root/.azure \
    --env-file cacitesting.env \
    cacitesting.azurecr.io/releases:latest \
    c_aci_testing.infra_deploy
```
This will deploy/check the resources required to build images, generate security policies and deploy container instances.

This will only succeed if you're logged into an Azure account with subscription level permissions.

### Create Target
```
mkdir my_caci_example

docker run \
    -v ./my_caci_example:/target \
    --env-file cacitesting.env \
    cacitesting.azurecr.io/releases:latest \
    c_aci_testing.target_create -n my_caci_example
```

All operations carried out by the container are directed at whatever directory is mounted at `/target`. 

This populates the directory with an example target, you can then modify the target for your specific workflow.

## Running a target

```
docker run \
    -v ./my_caci_example:/target \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v ~/.azure:/root/.azure \
    --env-file cacitesting.env \
    cacitesting.azurecr.io/releases:latest \
    c_aci_testing.target_run \
        -n <YOUR_DEPLOYMENT_NAME>
```
This will: 
- Build any images defined in your target directory
- Push them to your configured container registry
- Generate a security policy and update your .bicepparam file
- Deploy the container group to Confidential ACI
- Follow the logs of the deployed container and wait until process exits
- Remove the container group

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
