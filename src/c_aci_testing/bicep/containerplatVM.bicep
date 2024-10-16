param vmUsername string = 'test-user'
@secure()
param vmPassword string
param location string
param containerPorts array
@secure()
param vmImage string
param managedIDName string
param containerplatUrl string
param vmCustomCommands array = []
param vmSize string = 'Standard_DC4ads_cc_v5'

var tokenUrl = 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://storage.azure.com/&client_id=${managedIdentity.properties.clientId}'

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
  zones: [
    '2'
  ]
}

resource networkSecurityGroup 'Microsoft.Network/networkSecurityGroups@2019-02-01' = {
  name: '${deployment().name}-nsg'
  location: location
  properties: {
    securityRules: [
      {
        name: 'RDP'
        properties: {
          priority: 300
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '3389'
        }
      }
      {
        name: 'SSH'
        properties: {
          priority: 320
          protocol: 'TCP'
          access: 'Allow'
          direction: 'Inbound'
          sourceAddressPrefix: '*'
          sourcePortRange: '*'
          destinationAddressPrefix: '*'
          destinationPortRange: '22'
        }
      }
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
      imageReference: {
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
      computerName: 'test-machine'
      adminUsername: vmUsername
      adminPassword: vmPassword
      windowsConfiguration: {
        enableAutomaticUpdates: true
        provisionVMAgent: true
        patchSettings: {
          enableHotpatching: false
          patchMode: 'AutomaticByOS'
        }
      }
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
  zones: [
    '2'
  ]
}

resource shutdownSchedule 'Microsoft.DevTestLab/schedules@2018-09-15' = {
  name: 'shutdown-computevm-${deployment().name}-vm'
  location: location
  properties: {
    status: 'Enabled'
    taskType: 'ComputeVmShutdownTask'
    dailyRecurrence: {
      time: '19:00'
    }
    timeZoneId: 'UTC'
    targetResourceId: virtualMachine.id
  }
}

resource vmRunCommand 'Microsoft.Compute/virtualMachines/runCommands@2022-03-01' = {
  name: '${deployment().name}-vm-RunPowerShellScript'
  location: location
  parent: virtualMachine
  properties: {
    source: {
      #disable-next-line prefer-interpolation
      script: concat(
        'try { ',
        join(
          union(
            [
              '$ProgressPreference = "SilentlyContinue"' // otherwise invoke-restmethod is very slow to download large files
              '$ErrorActionPreference = "Continue"'
              '$token = (Invoke-RestMethod -Uri "${tokenUrl}" -Headers @{Metadata="true"} -Method GET -UseBasicParsing).access_token'
              'Write-Output "Token acquired" >> C:/bootstrap.log'
              '$headers = @{ Authorization = "Bearer $token"; "x-ms-version" = "2019-12-12" }'
              'Invoke-RestMethod -Uri "${containerplatUrl}" -Method GET -Headers $headers -OutFile "C:/containerplat.tar"'
              'Write-Output "Containerplat download done" >> C:/bootstrap.log'
              'tar -xf C:/containerplat.tar -C C:/'
              'Write-Output "tar -xf C:/containerplat.tar -C C:/   result: $LASTEXITCODE" >> C:/bootstrap.log'
              'C:/containerplat_build/deploy.exe'
              'Write-Output "C:/containerplat_build/deploy.exe   result: $LASTEXITCODE" >> C:/bootstrap.log'
              'Write-Output "All done!" >> C:/bootstrap.log'
            ],
            vmCustomCommands
          ),
          '; '
        ),
        ' } catch { Write-Output $_.Exception.ToString() >> C:/bootstrap.log }'
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
  shutdownSchedule.id
  vmRunCommand.id
]
