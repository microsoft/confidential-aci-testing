function Get-AcrToken {
  param(
    [Parameter(
      Mandatory = $true,
      HelpMessage = "ACR registry name including .azurecr.io"
    )][string]$registry
  )
  try {
    if (-not $registry.EndsWith(".azurecr.io")) {
        throw "Registry $registry is not an ACR registry"
    }

    if ($env:ACR_CREDENTIALS) {
      return $env:ACR_CREDENTIALS
    }

    $maybeClientID = ""
    if (Test-Path -Path "C:\managed_identity_client_id.txt") {
      $maybeClientID = "&client_id=$(Get-Content -Path "C:\managed_identity_client_id.txt")"
    }

    # Get the access token from the managed identity endpoint
    $resource = "https://management.azure.com/"
    $apiVersion = "2018-02-01"
    $tokenAuthUri = "http://169.254.169.254/metadata/identity/oauth2/token"
    $headers = @{"Metadata" = "true"}
    $uri = "${tokenAuthUri}?api-version=${apiVersion}&resource=${resource}${maybeClientID}"

    $tokenResponse = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers
    $accessToken = $tokenResponse.access_token

    # Decode the access token to get tenant ID
    $tokenParts = $accessToken -split '\.'
    $tokenPayload = $tokenParts[1]

    # Add padding to base64 string if necessary
    $mod4 = $tokenPayload.Length % 4
    if ($mod4 -gt 0) {
        $tokenPayload += '=' * (4 - $mod4)
    }

    $decodedPayload = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($tokenPayload))
    $payloadJson = $decodedPayload | ConvertFrom-Json
    $tenantId = $payloadJson.tid

    # Exchange the AAD access token for an ACR refresh token
    $exchangeUri = "https://$registry/oauth2/exchange"
    $exchangeBody = @{
        grant_type   = "access_token"
        service      = $registry
        tenant       = $tenantId
        access_token = $accessToken
    }

    $exchangeResponse = Invoke-RestMethod -Method Post -Uri $exchangeUri -Body $exchangeBody -ContentType "application/x-www-form-urlencoded" -TimeoutSec 10
    $acrRefreshToken = $exchangeResponse.refresh_token
    $acrCreds = "00000000-0000-0000-0000-000000000000:$acrRefreshToken"
    return $acrCreds
  } catch {
    Write-Host "Failed to get ACR token: $_"
    Write-Host "You can set a manually acquired token as an environment variable in order to use this script."
    Write-Host "Run first on your own machine:"
    Write-Host "az acr login -n $registry -t | jq -r '`"00000000-0000-0000-0000-000000000000:\(.accessToken)`"'"
    Write-Host "Then in here do:"
    Write-Host "`$env:ACR_CREDENTIALS = `"...`""
    throw $_
  }
}

function Pull-Image {
  param (
    [Parameter(
      Mandatory = $true,
      HelpMessage = "Pull config JSON"
    )][string]$pullJson,
    [Parameter(
      Mandatory = $true,
      HelpMessage = "Image reference"
    )][string]$imageName
  )

  $registry = ($imageName -split '/')[0]
  $maybeCreds = @()
  $maybeWithCredentialsMsg = ""
  if ($registry.EndsWith(".azurecr.io")) {
    try {
      $acrCreds = Get-AcrToken -registry $registry
    } catch {
      Write-Host "ERROR: Failed to acquire ACR token, pulling without credentials"
      $acrCreds = $null
    }
    if ($acrCreds) {
      $maybeCreds = @("--creds", $acrCreds)
      $maybeWithCredentialsMsg = " (with ACR credentials)"
    }
  }

  Write-Host "Pulling image: $imageName$maybeWithCredentialsMsg"
  C:\ContainerPlat\crictl.exe pull @maybeCreds --pod-config $pullJson $imageName
}
