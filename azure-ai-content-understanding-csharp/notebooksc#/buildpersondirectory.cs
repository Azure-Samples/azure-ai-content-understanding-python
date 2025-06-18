using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace AzureAIContentUnderstanding
{
    class BuildPersonDirectory
    {
        static async Task Main(string[] args)
        {
            // Setup configuration and logging
            var config = new ConfigurationBuilder()
                .AddJsonFile("appsettings.json", optional: true)
                .AddEnvironmentVariables()
                .Build();

            var loggerFactory = LoggerFactory.Create(builder => builder.AddConsole());
            var logger = loggerFactory.CreateLogger<BuildPersonDirectory>();

            var endpoint = config["AZURE_AI_ENDPOINT"];
            var apiKey = config["AZURE_AI_API_KEY"];
            var apiVersion = config["AZURE_AI_API_VERSION"] ?? "2025-05-01-preview";

            var client = new AzureContentUnderstandingFaceClient(endpoint, apiKey, apiVersion);

            // --- Build a Person Directory ---
            string folderPath = "../data/face/enrollment_data"; // Update as needed
            string personDirectoryId = $"person_directory_id_{Guid.NewGuid().ToString("N").Substring(0, 8)}";
            await client.CreatePersonDirectoryAsync(personDirectoryId);
            logger.LogInformation($"Created person directory with ID: {personDirectoryId}");

            foreach (var subfolderPath in Directory.GetDirectories(folderPath))
            {
                var personName = Path.GetFileName(subfolderPath);
                var person = await client.AddPersonAsync(personDirectoryId, new Dictionary<string, string> { { "name", personName } });
                logger.LogInformation($"Created person {personName} with person_id: {person["personId"]}");

                foreach (var imagePath in Directory.GetFiles(subfolderPath))
                {
                    if (imagePath.EndsWith(".png", StringComparison.OrdinalIgnoreCase) ||
                        imagePath.EndsWith(".jpg", StringComparison.OrdinalIgnoreCase) ||
                        imagePath.EndsWith(".jpeg", StringComparison.OrdinalIgnoreCase))
                    {
                        var imageData = AzureContentUnderstandingFaceClient.ReadFileToBase64(imagePath);
                        var face = await client.AddFaceAsync(personDirectoryId, imageData, person["personId"]);
                        if (face != null)
                            logger.LogInformation($"Added face from {Path.GetFileName(imagePath)} with face_id: {face["faceId"]} to person_id: {person["personId"]}");
                        else
                            logger.LogWarning($"Failed to add face from {Path.GetFileName(imagePath)} to person_id: {person["personId"]}");
                    }
                }
            }
            logger.LogInformation("Done");

            // --- Identifying person ---
            string testImagePath = "../data/face/family.jpg";
            var testImageData = AzureContentUnderstandingFaceClient.ReadFileToBase64(testImagePath);
            var detectedFaces = await client.DetectFacesAsync(testImageData);
            foreach (var face in detectedFaces["detectedFaces"])
            {
                var identifiedPersons = await client.IdentifyPersonAsync(personDirectoryId, testImageData, face["boundingBox"]);
                if (identifiedPersons.ContainsKey("personCandidates"))
                {
                    var person = identifiedPersons["personCandidates"][0];
                    var name = person.ContainsKey("tags") && person["tags"].ContainsKey("name") ? person["tags"]["name"] : "Unknown";
                    logger.LogInformation($"Detected person: {name} with confidence: {person.GetValueOrDefault("confidence", 0)} at bounding box: {face["boundingBox"]}");
                }
            }
            logger.LogInformation("Done");

            // --- Adding and associating a new face ---
            string newFaceImagePath = "new_face_image_path"; // Replace with actual path
            string existingPersonId = "existing_person_id"; // Replace with actual person ID
            var newFaceImageData = AzureContentUnderstandingFaceClient.ReadFileToBase64(newFaceImagePath);
            var newFace = await client.AddFaceAsync(personDirectoryId, newFaceImageData, existingPersonId);
            if (newFace != null)
                logger.LogInformation($"Added face from {newFaceImagePath} with face_id: {newFace["faceId"]} to person_id: {existingPersonId}");
            else
                logger.LogWarning($"Failed to add face from {newFaceImagePath} to person_id: {existingPersonId}");

            // --- Associating a list of already enrolled faces ---
            var existingFaceIdList = new List<string> { "existing_face_id_1", "existing_face_id_2" }; // Replace with actual face IDs
            await client.UpdatePersonAsync(personDirectoryId, existingPersonId, faceIds: existingFaceIdList);

            // --- Associating and disassociating a face from a person ---
            string existingFaceId = "existing_face_id"; // Replace with actual face ID
            // Disassociate
            await client.UpdateFaceAsync(personDirectoryId, existingFaceId, personId: "");
            logger.LogInformation($"Removed association of face_id: {existingFaceId} from the existing person_id");
            logger.LogInformation((await client.GetFaceAsync(personDirectoryId, existingFaceId)).ToString());
            // Associate
            await client.UpdateFaceAsync(personDirectoryId, existingFaceId, personId: existingPersonId);
            logger.LogInformation($"Associated face_id: {existingFaceId} with person_id: {existingPersonId}");
            logger.LogInformation((await client.GetFaceAsync(personDirectoryId, existingFaceId)).ToString());

            // --- Updating metadata (tags and descriptions) ---
            string personDirectoryDescription = "This is a sample person directory for managing faces.";
            var personDirectoryTags = new Dictionary<string, string> { { "project", "face_management" }, { "version", "1.0" } };
            await client.UpdatePersonDirectoryAsync(personDirectoryId, description: personDirectoryDescription, tags: personDirectoryTags);
            logger.LogInformation($"Updated Person Directory with description: '{personDirectoryDescription}' and tags: {personDirectoryTags}");
            logger.LogInformation((await client.GetPersonDirectoryAsync(personDirectoryId)).ToString());

            // Update tags for an individual person
            var personTags = new Dictionary<string, string> { { "role", "tester" }, { "department", "engineering" }, { "name", "" } };
            await client.UpdatePersonAsync(personDirectoryId, existingPersonId, tags: personTags);
            logger.LogInformation($"Updated person with person_id: {existingPersonId} with tags: {personTags}");
            logger.LogInformation((await client.GetPersonAsync(personDirectoryId, existingPersonId)).ToString());

            // --- Deleting a face ---
            await client.DeleteFaceAsync(personDirectoryId, existingFaceId);
            logger.LogInformation($"Deleted face with face_id: {existingFaceId}");

            // --- Deleting a person ---
            await client.DeletePersonAsync(personDirectoryId, existingPersonId);
            logger.LogInformation($"Deleted person with person_id: {existingPersonId}");

            // --- Deleting a person and their associated faces ---
            var response = await client.GetPersonAsync(personDirectoryId, existingPersonId);
            var faceIds = response.ContainsKey("faceIds") ? (List<string>)response["faceIds"] : new List<string>();
            foreach (var faceId in faceIds)
            {
                logger.LogInformation($"Deleting face with face_id: {faceId} from person_id: {existingPersonId}");
                await client.DeleteFaceAsync(personDirectoryId, faceId);
            }
            await client.DeletePersonAsync(personDirectoryId, existingPersonId);
            logger.LogInformation($"Deleted person with person_id: {existingPersonId} and all associated faces.");
        }
    }

    // Utility methods for base64 encoding
    public static class AzureContentUnderstandingFaceClient
    {
        public static string ReadFileToBase64(string filePath)
        {
            return Convert.ToBase64String(File.ReadAllBytes(filePath));
        }
    }
}