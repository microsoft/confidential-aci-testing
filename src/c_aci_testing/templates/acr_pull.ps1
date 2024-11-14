param (
    [Parameter(
      Mandatory = $true,
      HelpMessage = "ACR Registry name"
    )][string]$acrName,
    [Parameter(
      Mandatory = $true,
      HelpMessage = "Pull config JSON"
    )][string]$pullJson,
    [Parameter(
      Mandatory = $true,
      HelpMessage = "Managed identity client ID"
    )][string]$clientID,
    [Parameter(
      Mandatory = $true,
      HelpMessage = "Full image name"
    )][string]$imageName
)

try {
  if ($acrName.EndsWith(".azurecr.io")) {
      $acrName = $acrName.Substring(0, $acrName.Length - ".azurecr.io".Length)
  }

  $acrLoginServer = "$acrName.azurecr.io"

  # Get the access token from the managed identity endpoint
  $resource = "https://management.azure.com/"
  $apiVersion = "2018-02-01"
  $tokenAuthUri = "http://169.254.169.254/metadata/identity/oauth2/token"
  $headers = @{"Metadata" = "true"}
  $uri = "${tokenAuthUri}?api-version=${apiVersion}&resource=${resource}&client_id=${clientID}"

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
  $exchangeUri = "https://$acrLoginServer/oauth2/exchange"
  $exchangeBody = @{
      grant_type   = "access_token"
      service      = $acrLoginServer
      tenant       = $tenantId
      access_token = $accessToken
  }

  $exchangeResponse = Invoke-RestMethod -Method Post -Uri $exchangeUri -Body $exchangeBody -ContentType "application/x-www-form-urlencoded"
  $acrRefreshToken = $exchangeResponse.refresh_token

  Write-Host "Pulling image: $imageName"

  C:\ContainerPlat\crictl.exe pull --creds "00000000-0000-0000-0000-000000000000:$acrRefreshToken" --pod-config $pullJson $imageName
} catch {
  Write-Host "Failed to get ACR token: $_"
  Write-Host "Pulling image: $imageName without credentials"
  C:\ContainerPlat\crictl.exe pull --pod-config $pullJson $imageName
  exit 1
}
