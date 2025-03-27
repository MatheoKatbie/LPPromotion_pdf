namespace LPPromotion_PDF2.Models;

public class GrokApiSettings
{
    public string BaseUrl { get; set; } = string.Empty;
    public string ApiKey { get; set; } = string.Empty;
    public int MaxFileSize { get; set; }
    public string[] SupportedFileTypes { get; set; } = Array.Empty<string>();
    public bool DebugMode { get; set; }
} 