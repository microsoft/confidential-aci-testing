param name string
param location string = resourceGroup().location
param githubRepo string

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
}

resource AcrPull 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid('AcrPull', resourceGroup().id, managedIdentity.name)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource AcrPush 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid('AcrPush', resourceGroup().id, managedIdentity.name)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8311e382-0749-4cb8-b61a-304f252e45ec')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

// Should ideally use this custom role, but our subscription doesn't allow role creation

// resource AciDeployerRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
//   name: guid('AciDeployerRole', resourceGroup().id, managedIdentity.name)
//   scope: resourceGroup()
//   properties: {
//     roleName: 'AciDeployer'
//     assignableScopes: [
//       resourceGroup().id
//     ]
//     description: 'Can deploy containers to Azure Container Instances'
//     type: 'CustomRole'
//     permissions: [
//       {
//         actions: [
//           'Microsoft.ContainerInstance/containerGroups/write'
//           'Microsoft.ContainerInstance/containerGroups/read'
//           'Microsoft.ContainerInstance/containerGroups/delete'
//           'Microsoft.ContainerInstance/containerGroups/containers/logs/read'
//         ]
//       }
//     ]
//   }
// }

resource AciCreate 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid('AciCreate', resourceGroup().id, managedIdentity.name)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c')
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource federatedCredentialPR 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  name: 'federatedCredentialPR'
  parent: managedIdentity
  properties: {
    audiences: [
      'api://AzureADTokenExchange'
    ]
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepo}:pull_request'
  }
}

resource federatedCredentialMain 'Microsoft.ManagedIdentity/userAssignedIdentities/federatedIdentityCredentials@2023-01-31' = {
  name: 'federatedCredentialMain'
  parent: managedIdentity
  dependsOn: [federatedCredentialPR]
  properties: {
    audiences: [
      'api://AzureADTokenExchange'
    ]
    issuer: 'https://token.actions.githubusercontent.com'
    subject: 'repo:${githubRepo}:ref:refs/heads/main'
  }
}
