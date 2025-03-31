using './example.bicep'

// Image info
param registry=''
param repository=''
param tag=''

// Deployment info
param location=''
param ccePolicies={
  example: ''
}
param managedIDName=''
