using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Identity;
using Microsoft.Extensions.Configuration;

namespace AzureAIContentUnderstanding
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // ---------------------------
            // Prerequisites & Setup
            // ---------------------------
            var config = new ConfigurationBuilder()
                .AddEnvironmentVariables()
                .AddJsonFile("appsettings.json", optional: true)
                .Build();

            string endpoint = config["AZURE_AI_ENDPOINT"];
            string apiVersion = config["AZURE_AI_API_VERSION"] ?? "2024-12-01-preview";
            string trainingDataSasUrl = config["TRAINING_DATA_SAS_URL"];
            string trainingDataPath = config["TRAINING_DATA_PATH"];

            if (string.IsNullOrEmpty(endpoint) || string.IsNullOrEmpty(trainingDataSasUrl) || string.IsNullOrEmpty(trainingDataPath))
            {
                Console.WriteLine("Please set AZURE_AI_ENDPOINT, TRAINING_DATA_SAS_URL, and TRAINING_DATA_PATH in your environment or appsettings.json.");
                return;
            }

            // ---------------------------
            // Analyzer template
            // ---------------------------
            string analyzerTemplatePath = "../analyzer_templates/receipt.json";

            // ---------------------------
            // Create Azure Content Understanding Client
            // ---------------------------
            var credential = new DefaultAzureCredential();
            var client = new AzureContentUnderstandingClient(
                endpoint: endpoint,
                apiVersion: apiVersion,
                credential: credential,
                userAgent: "azure-ai-content-understanding-csharp/analyzer_training"
            );

            // ---------------------------
            // Create analyzer with defined schema
            // ---------------------------
            string analyzerId = "train-sample-" + Guid.NewGuid().ToString();

            Console.WriteLine("Creating analyzer...");
            var createResponse = await client.BeginCreateAnalyzerAsync(
                analyzerId,
                analyzerTemplatePath,
                trainingDataSasUrl,
                trainingDataPath
            );
            var createResult = await client.PollResultAsync(createResponse);

            if (createResult.TryGetProperty("status", out var statusProp) && statusProp.GetString() == "Succeeded")
            {
                Console.WriteLine($"Here is the analyzer detail for {analyzerId}:");
                Console.WriteLine(JsonSerializer.Serialize(createResult, new JsonSerializerOptions { WriteIndented = true }));
            }
            else
            {
                Console.WriteLine("Check your service please, there may be some issues in configuration and deployment.");
                return;
            }

            // ---------------------------
            // Use created analyzer to extract document content
            // ---------------------------
            Console.WriteLine("Analyzing document...");
            var analyzeResponse = await client.BeginAnalyzeAsync(analyzerId, "../data/receipt.png");
            var analyzeResult = await client.PollResultAsync(analyzeResponse);

            Console.WriteLine(JsonSerializer.Serialize(analyzeResult, new JsonSerializerOptions { WriteIndented = true }));

            // ---------------------------
            // Delete analyzer (optional cleanup)
            // ---------------------------
            Console.WriteLine("Deleting analyzer...");
            await client.DeleteAnalyzerAsync(analyzerId);

            Console.WriteLine("Done.");
        }
    }

    // Stub for the client class, replace with your actual implementation
    public class AzureContentUnderstandingClient
    {
        public AzureContentUnderstandingClient(string endpoint, string apiVersion, DefaultAzureCredential credential, string userAgent = null) { /* ... */ }

        public Task<string> BeginCreateAnalyzerAsync(string analyzerId, string analyzerTemplatePath, string trainingDataSasUrl, string trainingDataPath)
        {
            // TODO: Implement HTTP POST to create analyzer with training data
            throw new NotImplementedException();
        }

        public Task<JsonElement> PollResultAsync(string operationLocation)
        {
            // TODO: Implement polling logic for long-running operation
            throw new NotImplementedException();
        }

        public Task<string> BeginAnalyzeAsync(string analyzerId, string fileLocation)
        {
            // TODO: Implement HTTP POST to analyze file
            throw new NotImplementedException();
        }

        public Task DeleteAnalyzerAsync(string analyzerId)
        {
            // TODO: Implement HTTP DELETE to delete analyzer
            throw new NotImplementedException();
        }
    }
}