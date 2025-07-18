using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Threading.Tasks;
using Azure.Core;
using Azure.Identity;
using Microsoft.Extensions.Configuration;

namespace AzureAIContentUnderstanding
{
    class Program
    {
        // Mapping of analyzer templates to their template and sample file paths
        static readonly Dictionary<string, (string TemplatePath, string SampleFilePath)> ExtractionTemplates =
            new Dictionary<string, (string, string)>
            {
                { "invoice", ("../analyzer_templates/invoice.json", "../data/invoice.pdf") },
                { "chart", ("../analyzer_templates/image_chart.json", "../data/pieChart.jpg") },
                { "call_recording", ("../analyzer_templates/call_recording_analytics.json", "../data/callCenterRecording.mp3") },
                { "conversation_audio", ("../analyzer_templates/conversational_audio_analytics.json", "../data/callCenterRecording.mp3") },
                { "marketing_video", ("../analyzer_templates/marketing_video.json", "../data/FlightSimulator.mp4") }
            };

        static async Task Main(string[] args)
        {
            // Load environment variables
            var config = new ConfigurationBuilder()
                .AddEnvironmentVariables()
                .AddJsonFile("appsettings.json", optional: true)
                .Build();

            string azureAiEndpoint = config["AZURE_AI_ENDPOINT"];
            string azureAiApiVersion = config["AZURE_AI_API_VERSION"] ?? "2024-12-01-preview";

            if (string.IsNullOrEmpty(azureAiEndpoint))
            {
                Console.WriteLine("Please set the AZURE_AI_ENDPOINT environment variable.");
                return;
            }

            // Select analyzer template and generate analyzer ID
            string analyzerTemplate = "invoice";
            string analyzerId = "field-extraction-sample-" + Guid.NewGuid().ToString();
            var (analyzerTemplatePath, analyzerSampleFilePath) = ExtractionTemplates[analyzerTemplate];

            // Create AzureContentUnderstandingClient (implement REST logic in this class)
            var credential = new DefaultAzureCredential();
            var client = new AzureContentUnderstandingClient(
                endpoint: azureAiEndpoint,
                apiVersion: azureAiApiVersion,
                credential: credential
            );

            // Create analyzer from template
            Console.WriteLine("Creating analyzer...");
            var createResponse = await client.BeginCreateAnalyzerAsync(analyzerId, analyzerTemplatePath);
            var createResult = await client.PollResultAsync(createResponse);

            Console.WriteLine("Analyzer creation result:");
            Console.WriteLine(JsonSerializer.Serialize(createResult, new JsonSerializerOptions { WriteIndented = true }));

            // Analyze sample file
            Console.WriteLine("Analyzing sample file...");
            var analyzeResponse = await client.BeginAnalyzeAsync(analyzerId, analyzerSampleFilePath);
            var analyzeResult = await client.PollResultAsync(analyzeResponse);

            Console.WriteLine("Analysis result:");
            Console.WriteLine(JsonSerializer.Serialize(analyzeResult, new JsonSerializerOptions { WriteIndented = true }));

            // Clean up: delete analyzer
            Console.WriteLine("Deleting analyzer...");
            await client.DeleteAnalyzerAsync(analyzerId);

            Console.WriteLine("Done.");
        }
    }

    /// <summary>
    /// Utility class to interact with the Azure Content Understanding API.
    /// You must implement the REST API logic for each method.
    /// </summary>
    public class AzureContentUnderstandingClient
    {
        private readonly string _endpoint;
        private readonly string _apiVersion;
        private readonly TokenCredential _credential;

        public AzureContentUnderstandingClient(string endpoint, string apiVersion, TokenCredential credential)
        {
            _endpoint = endpoint;
            _apiVersion = apiVersion;
            _credential = credential;
        }

        public async Task<object> BeginCreateAnalyzerAsync(string analyzerId, string analyzerTemplatePath)
        {
            // TODO: Implement REST API call to create analyzer using analyzerTemplatePath
            // Return operation handle or result
            throw new NotImplementedException();
        }

        public async Task<object> PollResultAsync(object operationHandle)
        {
            // TODO: Implement polling logic for long-running operation
            throw new NotImplementedException();
        }

        public async Task<object> BeginAnalyzeAsync(string analyzerId, string sampleFilePath)
        {
            // TODO: Implement REST API call to analyze file
            throw new NotImplementedException();
        }

        public async Task DeleteAnalyzerAsync(string analyzerId)
        {
            // TODO: Implement REST API call to delete analyzer
            throw new NotImplementedException();
        }
    }
}