try {
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
