using System;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Identity;
using Microsoft.Extensions.Configuration;

namespace AzureAIContentUnderstandingCSharp
{
    class Program
    {
        static async Task Main(string[] args)
        {
            // Load environment variables (from .env or appsettings.json)
            var config = new ConfigurationBuilder()
                .AddEnvironmentVariables()
                .AddJsonFile("appsettings.json", optional: true)
                .Build();

            string endpoint = config["AZURE_AI_ENDPOINT"];
            string apiVersion = config["AZURE_AI_API_VERSION"] ?? "2024-12-01-preview";

            if (string.IsNullOrEmpty(endpoint))
            {
                Console.WriteLine("Please set AZURE_AI_ENDPOINT in your environment or appsettings.json.");
                return;
            }

            // Authenticate using DefaultAzureCredential
            var credential = new DefaultAzureCredential();

            // Create the client (implement HTTP logic in this class)
            var client = new AzureContentUnderstandingClient(
                endpoint,
                apiVersion,
                credential,
                userAgent: "azure-ai-content-understanding-csharp/analyzer_management"
            );

            // --- Create a simple analyzer ---
            string analyzerTemplatePath = "../analyzer_templates/call_recording_analytics.json";
            string analyzerId = "analyzer-management-sample-" + Guid.NewGuid().ToString();

            Console.WriteLine("Creating analyzer...");
            var createResponse = await client.BeginCreateAnalyzerAsync(analyzerId, analyzerTemplatePath);
            var createResult = await client.PollResultAsync(createResponse);

            Console.WriteLine(JsonSerializer.Serialize(createResult, new JsonSerializerOptions { WriteIndented = true }));

            // --- List all analyzers ---
            Console.WriteLine("\nListing all analyzers...");
            var allAnalyzers = await client.GetAllAnalyzersAsync();
            var analyzersArray = allAnalyzers.GetProperty("value").EnumerateArray();
            int count = 0;
            foreach (var _ in analyzersArray) count++;
            Console.WriteLine($"Number of analyzers in your resource: {count}");

            // Print first 3 analyzer details
            analyzersArray = allAnalyzers.GetProperty("value").EnumerateArray();
            int printed = 0;
            Console.WriteLine("First 3 analyzer details:");
            foreach (var analyzer in analyzersArray)
            {
                if (printed++ >= 3) break;
                Console.WriteLine(JsonSerializer.Serialize(analyzer, new JsonSerializerOptions { WriteIndented = true }));
            }

            // --- Get analyzer details by id ---
            Console.WriteLine($"\nGetting analyzer details for id: {analyzerId}");
            var analyzerDetail = await client.GetAnalyzerDetailByIdAsync(analyzerId);
            Console.WriteLine(JsonSerializer.Serialize(analyzerDetail, new JsonSerializerOptions { WriteIndented = true }));

            // --- Delete analyzer ---
            Console.WriteLine($"\nDeleting analyzer with id: {analyzerId}");
            await client.DeleteAnalyzerAsync(analyzerId);

            Console.WriteLine("Done.");
        }
    }

    // Implement this class to match your Python helper.
    public class AzureContentUnderstandingClient
    {
        private readonly string _endpoint;
        private readonly string _apiVersion;
        private readonly DefaultAzureCredential _credential;
        private readonly string _userAgent;

        public AzureContentUnderstandingClient(string endpoint, string apiVersion, DefaultAzureCredential credential, string userAgent = null)
        {
            _endpoint = endpoint;
            _apiVersion = apiVersion;
            _credential = credential;
            _userAgent = userAgent;
        }

        public async Task<string> BeginCreateAnalyzerAsync(string analyzerId, string analyzerTemplatePath)
        {
            // TODO: Implement HTTP POST to create analyzer using the template file
            // Return operation location or operation id for polling
            throw new NotImplementedException();
        }

        public async Task<JsonElement> PollResultAsync(string operationLocation)
        {
            // TODO: Implement polling logic to wait for operation completion
            throw new NotImplementedException();
        }

        public async Task<JsonElement> GetAllAnalyzersAsync()
        {
            // TODO: Implement HTTP GET to list all analyzers
            throw new NotImplementedException();
        }

        public async Task<JsonElement> GetAnalyzerDetailByIdAsync(string analyzerId)
        {
            // TODO: Implement HTTP GET to get analyzer details by id
            throw new NotImplementedException();
        }

        public async Task DeleteAnalyzerAsync(string analyzerId)
        {
            // TODO: Implement HTTP DELETE to delete analyzer by id
            throw new NotImplementedException();
        }
    }
}