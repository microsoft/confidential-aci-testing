using './.bicep'

// Image info
param registry=''
param repository='example'
param tag='latest'

// Deployment info
param location = ''
param ccePolicy=''
param managedIDName=''
param managedIDGroup=''
