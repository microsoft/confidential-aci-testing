Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe
Set-Alias -Name shimdiag -Value C:\ContainerPlat\shimdiag.exe

function get_pod_id {
  param(
    [string]$podName,
    [switch]$NoError
  )
  $podId = (crictl pods --name $podName -q)
  if (!$podId) {
    if ($NoError) { return "" }
    throw "Pod $podName not found"
  }
  return $podId
}

function get_container_id {
  param(
    [string]$podName,
    [string]$containerName,
    [switch]$NoError
  )
  $podId = get_pod_id -NoError:$NoError $podName
  if (!$podId) { return "" }
  $containerId = (crictl ps --pod $podId --name $containerName -a -q)
  if (!$containerId) {
    if ($NoError) { return "" }
    throw "Container $containerName not found in pod $podName"
  }
  return $containerId
}

function shimdiag_exec_pod {
  param(
    [string]$podName,
    [switch]$t,
    [parameter(ValueFromRemainingArguments=$true)]
    [string[]]$argv
  )
  $podId = get_pod_id $podName
  $opts = @()
  if ($t) { $opts += '-t' }
  shimdiag exec @opts ("k8s.io-"+$podId) $argv
}

function container_exec {
  param(
    [string]$podName,
    [string]$containerName,
    [switch]$it,
    [parameter(ValueFromRemainingArguments=$true)]
    [string[]]$argv
  )
  $containerId = get_container_id $podName $containerName
  $opts = @()
  if ($it) { $opts += '-it' }
  crictl exec @opts $containerId $argv
}

cd (Split-Path -Parent ($MyInvocation.MyCommand.Path))
