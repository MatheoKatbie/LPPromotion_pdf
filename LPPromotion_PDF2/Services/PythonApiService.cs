using System.Net.Http.Json;
using LPPromotion_PDF2.Models;
using Microsoft.Extensions.Options;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace LPPromotion_PDF2.Services;

public interface IPythonApiService
{
    Task<PlanAnalysis> AnalyzePdfAsync(Stream pdfStream, string fileName);
}

public class PythonApiService : IPythonApiService
{
    private readonly HttpClient _httpClient;
    private readonly PythonApiSettings _settings;
    private readonly JsonSerializerOptions _jsonOptions;

    public PythonApiService(HttpClient httpClient, IOptions<PythonApiSettings> settings)
    {
        _httpClient = httpClient;
        _settings = settings.Value;
        
        _httpClient.BaseAddress = new Uri(_settings.BaseUrl);

        _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true,
            NumberHandling = JsonNumberHandling.AllowReadingFromString
        };
    }

    public async Task<PlanAnalysis> AnalyzePdfAsync(Stream pdfStream, string fileName)
    {
        try
        {
            using var content = new MultipartFormDataContent();
            
            // Créer un MemoryStream pour stocker le contenu du PDF
            using var memoryStream = new MemoryStream();
            await pdfStream.CopyToAsync(memoryStream);
            memoryStream.Position = 0;
            
            // Créer le StreamContent avec le bon type de contenu
            var streamContent = new StreamContent(memoryStream);
            streamContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("application/pdf");
            
            // Ajouter le fichier au contenu multipart
            content.Add(streamContent, "file", fileName);

            var response = await _httpClient.PostAsync("/extract", content);
            response.EnsureSuccessStatusCode();

            var result = await response.Content.ReadFromJsonAsync<PlanAnalysis>(_jsonOptions);
            return result ?? new PlanAnalysis();
        }
        catch (Exception ex)
        {
            if (_settings.DebugMode)
            {
                throw new Exception($"Erreur lors de l'analyse du PDF: {ex.Message}", ex);
            }
            return new PlanAnalysis();
        }
    }
}

public class PythonApiSettings
{
    public string BaseUrl { get; set; } = string.Empty;
    public bool DebugMode { get; set; }
} 