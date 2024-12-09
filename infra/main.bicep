targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the the environment which is used to generate a short unique hash used in all resources.')
param environmentName string

@minLength(1)
@description('Location for the AI resource')
@allowed([
  'eastus'
  'eastus2'
  'northcentralus'
  'southcentralus'
  'spaincentral'
  'swedencentral'
  'westus'
  'westus3'
])
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Non-empty if the deployment is running on GitHub Actions')
param runningOnGitHub string = ''

var principalType = empty(runningOnGitHub) ? 'User' : 'ServicePrincipal'

var uniqueId = toLower(uniqueString(subscription().id, environmentName, location))
var resourcePrefix = '${environmentName}${uniqueId}'
var tags = { 
    'azd-env-name': environmentName
    owner: 'azure-ai-sample'
}

// Organize resources in a resource group
resource resourceGroup 'Microsoft.Resources/resourceGroups@2021-04-01' = {
    name: '${resourcePrefix}-rg'
    location: location
    tags: tags
}

var aiServiceName = '${resourcePrefix}-aiservice'
module aiService 'br/public:avm/res/cognitive-services/account:0.8.1' = {
  name: 'aiService'
  scope: resourceGroup
  params: {
    name: aiServiceName
    location: location
    tags: tags
    kind: 'AIServices'
    sku: 'S0'
    customSubDomainName: aiServiceName
    networkAcls: {
      defaultAction: 'Allow'
      bypass: 'AzureServices'
    }
    roleAssignments: [
        {
          principalId: principalId
          roleDefinitionIdOrName: 'Cognitive Services User'
          principalType: principalType
        }
      ]
  }
}

output AZURE_LOCATION string = location
output AZURE_TENANT_ID string = tenant().tenantId
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output AZURE_AI_ENDPOINT string = aiService.outputs.endpoint
