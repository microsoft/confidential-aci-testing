# Confidential ACI Testing

This project provides utilities for testing workflows involving Confidential ACI.

For more help, see [Getting Started with C-ACI-Testing](https://youtu.be/C0Svgx8Tiiw)

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

```
latest=$(gh release list -R microsoft/confidential-aci-testing -L 1 --json tagName --jq '.[0].tagName')
gh release download $latest -R microsoft/confidential-aci-testing
pip install c_aci_testing*.tar.gz
rm c_aci_testing*.tar.gz
```

### Define your Azure Environment

All scripts can be given call-time parameters, but for parameters which will be consistent across runs, it's easier to define an environment file to use. You can create a blank env file with:

```
c-aci-testing env create > cacitesting.env
```

Then just fill in the values you wish to use for your deployments, and source it

```
source cacitesting.env
```

### Deploy infrastructure to Azure
```
c-aci-testing infra deploy
```

This will deploy/check the resources required to build images, generate security policies and deploy container instances.

This will only succeed if you're logged into an Azure account with subscription level permissions to assign roles.

### Create a Target
```
export TARGET_PATH=./my_new_target
export TARGET_NAME=my_new_target
```
```
c-aci-testing target create $TARGET_PATH -n $TARGET_NAME
```

This populates the directory with an example target, you can then modify the target for your specific workflow.

## Run the Target

```
c-aci-testing target run $TARGET_PATH -n <YOUR_DEPLOYMENT_NAME>
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
c-aci-testing images build $TARGET_PATH
```

```
c-aci-testing images push $TARGET_PATH
```

```
c-aci-testing policies gen $TARGET_PATH
```

```
DEPLOYMENT_NAME=my-deployment
```

```
# Deploy and monitor (Can be run separately)
c-aci-testing aci_deploy $TARGET_PATH \
    --deployment-name $DEPLOYMENT_NAME

c-aci-testing aci_monitor \
    --deployment-name $DEPLOYMENT_NAME

# Cleanup
c-aci-testing aci_remove \
    --deployment-name $DEPLOYMENT_NAME
```

### Integrate with VS Code
#### Add steps to Run and Debug

```
c-aci-testing vscode run_debug
```

This adds launch configurations for each script in the python package for easy use.

#### Add Targets to Testing

```
c-aci-testing vscode testing $TARGET_PATH
```

This creates a Python Unittest runner for a provided target, as well as populating a workspace level settings file which points unittest at the target. If there is already a workspace level target, it is left alone.

### Create a Github Actions workflow

```
c-aci-testing github workflow $TARGET_PATH
```

This adds a new workflow file to `.github/workflows` which runs the specified target.

## Contributing

To take administrator actions such as adding users as contributors, please refer to [engineering hub](https://eng.ms/docs/initiatives/open-source-at-microsoft/github/opensource/repos/jit)

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
