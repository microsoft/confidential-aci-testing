using './example-non-terminating.bicep'

// Image info
param registry=''
param repository=''
param tag=''

// Deployment info
param location=''
param ccePolicies={}
param managedIDName=''
