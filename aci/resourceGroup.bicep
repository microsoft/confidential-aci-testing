param name string
param registryName string
param managedIdentityName string
param githubOrg string
param githubRepo string
param location string = deployment().location

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
    githubOrg: githubOrg
    githubRepo: githubRepo
  }
}
