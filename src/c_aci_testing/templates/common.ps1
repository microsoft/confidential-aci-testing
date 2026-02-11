Set-Alias -Name crictl -Value C:\ContainerPlat\crictl.exe
Set-Alias -Name shimdiag -Value C:\ContainerPlat\shimdiag.exe

function shimdiag_exec_pod {
  param(
    [string]$podName,
    [switch]$t,
    [parameter(ValueFromRemainingArguments=$true)]
    [string[]]$argv
  )
  $podId=(crictl pods --name $podName -q)
  if (!$podId) { throw "Pod $podName not found"; }
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
  $podId=(crictl pods --name $podName -q)
  if (!$podId) { throw "Pod $podName not found"; }
  $containerId=(crictl ps --pod $podId --name $containerName -q)
  if (!$containerId) { throw "Container $containerName not found in pod $podName"; }
  $opts = @()
  if ($it) { $opts += '-it' }
  crictl exec @opts $containerId $argv
}

cd (Split-Path -Parent ($MyInvocation.MyCommand.Path))
