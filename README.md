# Confidential ACI Testing

This project provides utilities for testing workflows involving Confidential ACI.

## Contents

- [Dependencies](#dependencies)
- [Getting Started](#getting-started)
    - [Install the `c_aci_testing` package](#install-the-c_aci_testing-package)
    - [Define your Azure Environment](#define-your-azure-environment)
    - [Deploy infrastructure to Azure](#deploy-infrastructure-to-azure)
    - [Create a Target](#create-a-target)
    - [Run the Target](#run-the-target)
- [Extra Features](#extra-features)
    - [Run individual deployment steps](#run-individual-deployment-steps)
    - [Integrate with VS Code](#integrate-with-vs-code)
        - [Add steps to Run and Debug](#add-steps-to-run-and-debug)
        - [Add targets to Testing](#add-targets-to-testing)
    - [Create a Github Actions workflow](#create-a-github-actions-workflow)


## Dependencies

- [Python](https://www.python.org)
- [Docker](https://docs.docker.com/get-docker/) 
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)

## Getting Started

### Install the `c_aci_testing` package

While the repository is private, the easiest way to get the package is through the Github CLI

```
gh auth login
```
```
gh release download latest -R microsoft/confidential-aci-testing
pip install c-aci-testing*.tar.gz
```

### Define your Azure Environment

All scripts can be given call-time parameters, but for parameters which will be consistent across runs, it's easier to define an environment file to use. You can create a blank env file with:

```
python -m c_aci_testing.env_create > cacitesting.env
```

Then just fill in the values you wish to use for your deployments

### Deploy infrastructure to Azure
```
source cacitesting.env
python -m c_aci_testing.infra_deploy
```

This will deploy/check the resources required to build images, generate security policies and deploy container instances.

This will only succeed if you're logged into an Azure account with subscription level permissions to assign roles.

### Create a Target
```
export TARGET_PATH=./my_new_target
export TARGET_NAME=my_new_target
python -m c_aci_testing.target_create $TARGET_PATH -n $TARGET_NAME
```

This populates the directory with an example target, you can then modify the target for your specific workflow.

## Run the Target

```
source cacitesting.env
python -m c_aci_testing.target_run $TARGET_PATH -n <YOUR_DEPLOYMENT_NAME>
```
This will: 
- Build any images defined in your target directory
- Push them to your configured container registry
- Generate a security policy and update your .bicepparam file
- Deploy the container group to Confidential ACI
- Follow the logs of the deployed container and wait until process exits
- Remove the container group

## Extra Features

### Run individual deployment steps

As well as running a given target end to end, each individual stage of the process can be run separately

```
python -m c_aci_testing.images_build $TARGET_PATH
```

```
python -m c_aci_testing.images_push $TARGET_PATH
```

```
python -m c_aci_testing.policies_gen $TARGET_PATH
```

```
DEPLOYMENT_NAME=my-deployment

# Deploy and monitor (Can be run separately)
python -m c_aci_testing.aci_monitor --id \
    $(python -m c_aci_testing.aci_deploy $TARGET_PATH --name $DEPLOYMENT_NAME)

# Cleanup
python -m c_aci_testing.aci_remove --name $DEPLOYMENT_NAME
```

### Integrate with VS Code
#### Add steps to Run and Debug
Coming Soon
#### Add targets to Testing
Coming Soon
### Create a Github Actions workflow
Coming Soon

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
