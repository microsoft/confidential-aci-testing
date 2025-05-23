try {
    if (Get-ScheduledTask -TaskName InitializeL1 -ErrorAction Ignore) {
        echo "Unregistering InitializeL1 job" >> C:\bootstrap.log
        Unregister-ScheduledTask -TaskName InitializeL1 -Confirm:$False
    }

    $needRestart = $false

    $hyperVEnabled = (Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V | Select-Object -ExpandProperty State) -eq "Enabled"
    if (-not $hyperVEnabled) {
        echo "Enabling Hyper-V" >> C:\bootstrap.log
        Enable-WindowsOptionalFeature -Online -All -FeatureName Microsoft-Hyper-V -NoRestart 2>&1 >> C:\bootstrap.log
        $needRestart = $true
    }
    $containersEnabled = (Get-WindowsOptionalFeature -Online -FeatureName Containers | Select-Object -ExpandProperty State) -eq "Enabled"
    if (-not $containersEnabled) {
        echo "Enabling Containers" >> C:\bootstrap.log
        Enable-WindowsOptionalFeature -Online -All -FeatureName Containers -NoRestart 2>&1 >> C:\bootstrap.log
        $needRestart = $true
    }

    # debug vsock ports
    echo "Adding debug vsock ports reg entries" >> C:\bootstrap.log
    $portnumber = 0x808
    $keyName = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Virtualization\GuestCommunicationServices\"
    $vsockTemplate = "{0:x8}-facb-11e6-bd58-64006a7986d3"
    $newKey = New-Item -Path $keyName -Name ($vsockTemplate -f $PortNumber) -Force
    New-ItemProperty -Path $newKey.PSPAth -Name "ElementName" -Value "Vsock port $PortNumber" -PropertyType "String" 2>&1 >> C:\bootstrap.log
    $portnumber2 = 0x800
    $newKey2 = New-Item -Path $keyName -Name ($vsockTemplate -f $PortNumber2) -Force
    New-ItemProperty -Path $newKey2.PSPAth -Name "ElementName" -Value "Vsock port $PortNumber2" -PropertyType "String" 2>&1 >> C:\bootstrap.log

    $sevSnpFlagExists = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Hypervisor" -Name EnableSevSnp -ErrorAction Ignore)
    $hardwareIsolationFlagExists = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\Hypervisor" -Name EnableHardwareIsolation -ErrorAction Ignore)
    $virtualisationBasedSecurityFlagExists = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\DeviceGuard" -Name EnableVirtualizationBasedSecurity -ErrorAction Ignore)

    # "reg add" will create top-level key if it doesn't exist instead of erroring out

    if (-not $sevSnpFlagExists -and -not $hardwareIsolationFlagExists) {
        echo "Adding required reg flags for sev-snp" >> C:\bootstrap.log
        # Before 22600
        reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Hypervisor" /v EnableSevSnp /t REG_DWORD /d 1 /f 2>&1 >> C:\bootstrap.log
        # After 22600 (WS2025)
        reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Hypervisor" /v EnableHardwareIsolation /t REG_DWORD /d 1 /f 2>&1 >> C:\bootstrap.log

        $needRestart = $true
    } else {
        echo "SevSnp or HardwareIsolation flag already exists" >> C:\bootstrap.log
    }
    if (-not $virtualisationBasedSecurityFlagExists) {
        reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\DeviceGuard" /v EnableVirtualizationBasedSecurity /t REG_DWORD /d 1 /f 2>&1 >> C:\bootstrap.log
        $needRestart = $true
    }

    if ($needRestart) {
        $scriptPath = $MyInvocation.MyCommand.Path
        echo "Registering InitializeL1 task and restarting" >> C:\bootstrap.log
        Register-ScheduledTask -TaskName InitializeL1 `
            -Action (New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-File $scriptPath") `
            -Trigger (New-ScheduledTaskTrigger -AtStartup) `
            -User SYSTEM 2>&1 >> C:\bootstrap.log
        if (Test-Path C:\bootstrap_restarted) {
            echo "Aborting: already restarted last time" >> C:\bootstrap.log
            echo "DEPLOY-ERROR" >> C:\bootstrap.log
            exit
        }
        echo "1" >> C:\bootstrap_restarted
        Restart-Computer -Confirm:$False 2>&1 >> C:\bootstrap.log
        exit
    }

    C:\containerplat_build\deploy.exe 2>&1 >> C:\bootstrap.log

    $success = $LASTEXITCODE -eq 0
    if ($success) {
        echo "DEPLOY-SUCCESS" >> C:\bootstrap.log
    } else {
        echo "DEPLOY-ERROR cplat deploy.exe returned $LASTEXITCODE" >> C:\bootstrap.log
    }
} catch {
    echo $_.Exception.ToString() >> C:\bootstrap.log
    echo "DEPLOY-ERROR" >> C:\bootstrap.log
}
