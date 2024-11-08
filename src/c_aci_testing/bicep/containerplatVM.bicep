param vmHostname string = 'atlas-vm'
param vmUsername string = 'atlas'
@secure()
param vmPassword string
param location string
param containerPorts array = ['80']
param useOfficialImages bool
param officialImageSku string = '2025-datacenter-g2'
param officialImageVersion string = 'latest'
@secure()
param vmImage string = ''

param managedIDName string
param vmSize string = 'Standard_DC4ads_cc_v5'
param vmZones array = []

var storageTokenUri = 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://storage.azure.com/&client_id=${managedIdentity.properties.clientId}'

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' existing = {
  name: managedIDName
}

resource publicIPAddress 'Microsoft.Network/publicIpAddresses@2020-08-01' = {
  name: '${deployment().name}-ip'
  location: location
  properties: {
    publicIPAllocationMethod: 'Static'
  }
  sku: {
    name: 'Standard'
  }
}

resource networkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2019-02-01' = {
  name: '${deployment().name}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'HTTPS'
        properties: {
          priority: 340
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '443'
        }
      }
      {
        name: 'HTTP'
        properties: {
          priority: 360
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '80'
        }
      }
      {
        name: 'Payload-HTTP'
        properties: {
          priority: 370
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRanges: containerPorts
        }
      }
    ]
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2021-01-01' = {
  name: '${deployment().name}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: '${deployment().name}-subnet'
        properties: {
          addressPrefix: '10.0.0.0/24'
        }
      }
    ]
  }
}

resource networkInterface 'Microsoft.Network/networkInterfaces@2021-08-01' = {
  name: '${deployment().name}-ni'
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          subnet: {
            id: '${resourceId(resourceGroup().name, 'Microsoft.Network/virtualNetworks', '${deployment().name}-vnet')}/subnets/${deployment().name}-subnet'
          }
          privateIPAllocationMethod: 'Dynamic'
          publicIPAddress: {
            id: resourceId(resourceGroup().name, 'Microsoft.Network/publicIpAddresses', '${deployment().name}-ip')
            properties: {
              deleteOption: 'Delete'
            }
          }
        }
      }
    ]
    networkSecurityGroup: {
      id: resourceId(resourceGroup().name, 'Microsoft.Network/networkSecurityGroups', '${deployment().name}-nsg')
    }
  }
  dependsOn: [
    networkSecurityGroup
    virtualNetwork
    publicIPAddress
  ]
}

resource virtualMachine 'Microsoft.Compute/virtualMachines@2022-03-01' = {
  name: '${deployment().name}-vm'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${managedIdentity.id}': {}
    }
  }
  properties: {
    hardwareProfile: {
      vmSize: vmSize
    }
    storageProfile: {
      osDisk: {
        createOption: 'fromImage'
        managedDisk: {
          storageAccountType: 'Premium_LRS'
        }
        deleteOption: 'Delete'
      }
      imageReference: useOfficialImages
        ? {
            publisher: 'MicrosoftWindowsServer'
            offer: 'WindowsServer'
            sku: officialImageSku
            version: officialImageVersion
          }
        : {
            id: vmImage
          }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: networkInterface.id
          properties: {
            deleteOption: 'Delete'
          }
        }
      ]
    }
    osProfile: {
      computerName: vmHostname
      adminUsername: vmUsername
      adminPassword: vmPassword
      windowsConfiguration: {
        enableAutomaticUpdates: false
        provisionVMAgent: true
        patchSettings: {
          enableHotpatching: false
          patchMode: 'Manual'
        }
      }
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
  zones: vmZones
}

resource vmRunCommand 'Microsoft.Compute/virtualMachines/runCommands@2022-03-01' = {
  name: 'RunPowerShellScript'
  location: location
  parent: virtualMachine
  properties: {
    source: {
      #disable-next-line prefer-interpolation
      script: concat(
        'try { ',
        join(
          [
            // Write utility scripts to download / upload stuff from / to the storage account into C:\, so that we:
            // 1. Do not have to repeat this every time we need this functionality
            // 2. Do not trigger Defender alerts when executing Invoke-WebRequest directly via runCommand

            'echo \'param([string]$uri, [string]$outFile)\' > C:\\storage_get.ps1'
            'echo \'# Script written in containerplatVM.bicep\' >> C:\\storage_get.ps1'
            'echo \'$ProgressPreference = "SilentlyContinue"\' >> C:\\storage_get.ps1'
            'echo \'$token = (Invoke-RestMethod -Uri "${storageTokenUri}" -Headers @{Metadata="true"} -Method GET -UseBasicParsing).access_token\' >> C:\\storage_get.ps1'
            'echo \'$headers = @{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12" }\' >> C:\\storage_get.ps1'
            'echo \'Invoke-RestMethod -Uri $uri -Method GET -Headers $headers -OutFile $outFile\' >> C:\\storage_get.ps1'

            'echo \'param([string]$uri, [string]$inFile)\' > C:\\storage_put.ps1'
            'echo \'# Script written in containerplatVM.bicep\' >> C:\\storage_put.ps1'
            'echo \'$ProgressPreference = "SilentlyContinue"\' >> C:\\storage_put.ps1'
            'echo \'$token = (Invoke-RestMethod -Uri "${storageTokenUri}" -Headers @{Metadata="true"} -Method GET -UseBasicParsing).access_token\' >> C:\\storage_put.ps1'
            'echo \'$dateStr = (Get-Date).ToUniversalTime().ToString("R")\' >> C:\\storage_put.ps1'
            'echo \'$headers = @{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12"; "x-ms-blob-type" = "BlockBlob"; "x-ms-date" = $dateStr }\' >> C:\\storage_put.ps1'
            'echo \'# -InFile requires file to not be open by ">>", but for some reason `Get-Content` works\' >> C:\\storage_put.ps1'
            'echo \'Invoke-RestMethod -Uri $uri -Method PUT -Headers $headers -Body (Get-Content -Raw $inFile)\' >> C:\\storage_put.ps1'
          ],
          '\r\n'
        ),
        ' } catch { Write-Output $_.Exception.ToString() >> C:\\bootstrap.log }'
      )
    }
  }
}

output ids array = [
  publicIPAddress.id
  networkSecurityGroup.id
  virtualNetwork.id
  networkInterface.id
  virtualMachine.id
  vmRunCommand.id
]
