param name string
param registryName string
param managedIdentityName string
param githubRepo string
param location string = deployment().location
param storageAccountName string = ''

targetScope = 'subscription'

resource resourceGroup 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: name
  location: location
}

module containerRegistry './containerRegistry.bicep' = {
  name: 'containerRegistryModule'
  scope: resourceGroup
  params: {
    name: registryName
    location: location
  }
}

module managedIdentity './managedIdentity.bicep' = {
  name: 'managedIdentityModule'
  scope: resourceGroup
  params: {
    name: managedIdentityName
    location: location
    githubRepo: githubRepo
  }
}

module storageAccount './blobStorage.bicep' = if (storageAccountName != '') {
  name: 'storageAccountModule'
  scope: resourceGroup
  dependsOn: [
    managedIdentity
  ]
  params: {
    name: storageAccountName
    location: location
    managedIdName: managedIdentityName
  }
}
