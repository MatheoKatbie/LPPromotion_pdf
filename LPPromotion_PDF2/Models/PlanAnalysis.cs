using System.Text.Json.Serialization;

namespace LPPromotion_PDF2.Models;

public class PlanAnalysis
{
    // Propriété pour stocker le nom du fichier (non sérialisée en JSON)
    [JsonIgnore]
    public string? FileName { get; set; }

    [JsonPropertyName("type_bien")]
    public string? TypeBien { get; set; }

    [JsonPropertyName("surfaces")]
    public Surfaces Surfaces { get; set; } = new();

    [JsonPropertyName("caracteristiques")]
    public List<string> Caracteristiques { get; set; } = new();

    [JsonPropertyName("vision_analysis")]
    public string? VisionAnalysis { get; set; }

    public override string ToString()
    {
        var caracteristiques = string.Join(", ", Caracteristiques);
        return $"Type de bien: {TypeBien}\n" +
               $"{Surfaces}\n" +
               $"Caractéristiques: {caracteristiques}";
    }
}

public class Surfaces
{
    [JsonPropertyName("surface_totale")]
    public decimal SurfaceTotale { get; set; }

    [JsonPropertyName("pieces")]
    public List<Piece> Pieces { get; set; } = new();

    public override string ToString()
    {
        var pieces = string.Join("\n  ", Pieces.Select(p => p.ToString()));
        return $"Surface totale: {SurfaceTotale:F2}m²\n" +
               $"Pièces:\n  {pieces}";
    }
}

public class Piece
{
    [JsonPropertyName("nom")]
    public string Nom { get; set; } = string.Empty;

    [JsonPropertyName("surface")]
    public decimal Surface { get; set; }

    public override string ToString()
    {
        return $"{Nom}: {Surface:F2}m²";
    }
} 