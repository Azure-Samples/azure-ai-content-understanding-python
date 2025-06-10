using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Drawing;
using System.Drawing.Imaging;

namespace AzureAIContentUnderstanding
{
    class Program
    {
        static void Main(string[] args)
        {
            // --- Prerequisites ---
            string AZURE_AI_ENDPOINT = Environment.GetEnvironmentVariable("AZURE_AI_ENDPOINT");
            string AZURE_AI_API_VERSION = Environment.GetEnvironmentVariable("AZURE_AI_API_VERSION") ?? "2024-12-01-preview";

            // Create Azure AI Content Understanding Client
            var client = new AzureContentUnderstandingClient(
                endpoint: AZURE_AI_ENDPOINT,
                apiVersion: AZURE_AI_API_VERSION
                // Add authentication as needed
            );

            // Utility function to save images
            void SaveImage(string imageId, object analyzeResponse)
            {
                byte[] rawImage = client.GetImageFromAnalyzeOperation(analyzeResponse, imageId);
                using (var ms = new MemoryStream(rawImage))
                using (var image = Image.FromStream(ms))
                {
                    Directory.CreateDirectory(".cache");
                    image.Save($".cache/{imageId}.jpg", ImageFormat.Jpeg);
                }
            }

            // --- Document Content ---
            string ANALYZER_ID = "content-doc-sample-" + Guid.NewGuid();
            string ANALYZER_TEMPLATE_FILE = "../analyzer_templates/content_document.json";
            string ANALYZER_SAMPLE_FILE = "../data/invoice.pdf";

            var response = client.BeginCreateAnalyzer(ANALYZER_ID, ANALYZER_TEMPLATE_FILE);
            var result = client.PollResult(response);

            response = client.BeginAnalyze(ANALYZER_ID, ANALYZER_SAMPLE_FILE);
            result = client.PollResult(response);

            Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
            client.DeleteAnalyzer(ANALYZER_ID);

            // --- Audio Content ---
            ANALYZER_ID = "content-audio-sample-" + Guid.NewGuid();
            ANALYZER_TEMPLATE_FILE = "../analyzer_templates/audio_transcription.json";
            ANALYZER_SAMPLE_FILE = "../data/audio.wav";

            response = client.BeginCreateAnalyzer(ANALYZER_ID, ANALYZER_TEMPLATE_FILE);
            result = client.PollResult(response);

            response = client.BeginAnalyze(ANALYZER_ID, ANALYZER_SAMPLE_FILE);
            result = client.PollResult(response);

            Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
            client.DeleteAnalyzer(ANALYZER_ID);

            // --- Video Content ---
            ANALYZER_ID = "content-video-sample-" + Guid.NewGuid();
            ANALYZER_TEMPLATE_FILE = "../analyzer_templates/content_video.json";
            ANALYZER_SAMPLE_FILE = "../data/FlightSimulator.mp4";

            response = client.BeginCreateAnalyzer(ANALYZER_ID, ANALYZER_TEMPLATE_FILE);
            result = client.PollResult(response);

            response = client.BeginAnalyze(ANALYZER_ID, ANALYZER_SAMPLE_FILE);
            result = client.PollResult(response);

            Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));

            // Save keyframes (optional)
            var keyframeIds = new HashSet<string>();
            var resultDict = result as Dictionary<string, object>;
            if (resultDict != null && resultDict.ContainsKey("result"))
            {
                var resultData = resultDict["result"] as Dictionary<string, object>;
                if (resultData != null && resultData.ContainsKey("contents"))
                {
                    var contents = resultData["contents"] as List<Dictionary<string, object>>;
                    if (contents != null)
                    {
                        foreach (var content in contents)
                        {
                            if (content.TryGetValue("markdown", out var markdownObj) && markdownObj is string markdown)
                            {
                                foreach (Match match in Regex.Matches(markdown, @"(keyFrame\.\d+)\.jpg"))
                                {
                                    keyframeIds.Add(match.Groups[1].Value);
                                }
                            }
                        }
                    }
                }
            }
            Console.WriteLine("Unique Keyframe IDs: " + string.Join(", ", keyframeIds));
            foreach (var keyframeId in keyframeIds)
            {
                SaveImage(keyframeId, response);
            }
            client.DeleteAnalyzer(ANALYZER_ID);

            // --- Video Content with Face ---
            ANALYZER_ID = "content-video-face-sample-" + Guid.NewGuid();
            ANALYZER_TEMPLATE_FILE = "../analyzer_templates/face_aware_in_video.json";
            ANALYZER_SAMPLE_FILE = "../data/FlightSimulator.mp4";

            response = client.BeginCreateAnalyzer(ANALYZER_ID, ANALYZER_TEMPLATE_FILE);
            result = client.PollResult(response);

            response = client.BeginAnalyze(ANALYZER_ID, ANALYZER_SAMPLE_FILE);
            result = client.PollResult(response);

            Console.WriteLine(JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));

            // Get and Save Key Frames and Face Thumbnails
            var faceIds = new HashSet<string>();
            keyframeIds = new HashSet<string>();
            resultDict = result as Dictionary<string, object>;
            if (resultDict != null && resultDict.ContainsKey("result"))
            {
                var resultData = resultDict["result"] as Dictionary<string, object>;
                if (resultData != null && resultData.ContainsKey("contents"))
                {
                    var contents = resultData["contents"] as List<Dictionary<string, object>>;
                    if (contents != null)
                    {
                        foreach (var content in contents)
                        {
                            if (content.TryGetValue("faces", out var facesObj) && facesObj is List<Dictionary<string, object>> faces)
                            {
                                foreach (var face in faces)
                                {
                                    if (face.TryGetValue("faceId", out var faceIdObj) && faceIdObj is string faceId)
                                    {
                                        faceIds.Add($"face.{faceId}");
                                    }
                                }
                            }
                            if (content.TryGetValue("markdown", out var markdownObj) && markdownObj is string markdown)
                            {
                                foreach (Match match in Regex.Matches(markdown, @"(keyFrame\.\d+)\.jpg"))
                                {
                                    keyframeIds.Add(match.Groups[1].Value);
                                }
                            }
                        }
                    }
                }
            }
            Console.WriteLine("Unique Face IDs: " + string.Join(", ", faceIds));
            Console.WriteLine("Unique Keyframe IDs: " + string.Join(", ", keyframeIds));
            foreach (var faceId in faceIds)
            {
                SaveImage(faceId, response);
            }
            foreach (var keyframeId in keyframeIds)
            {
                SaveImage(keyframeId, response);
            }
            client.DeleteAnalyzer(ANALYZER_ID);
        }
    }

    // Stub for the client class, replace with your actual implementation
    public class AzureContentUnderstandingClient
    {
        public AzureContentUnderstandingClient(string endpoint, string apiVersion) { /* ... */ }
        public object BeginCreateAnalyzer(string analyzerId, string analyzerTemplatePath) => null;
        public object PollResult(object response) => null;
        public object BeginAnalyze(string analyzerId, string fileLocation) => null;
        public void DeleteAnalyzer(string analyzerId) { }
        public byte[] GetImageFromAnalyzeOperation(object analyzeResponse, string imageId) => new byte[0];
    }
}