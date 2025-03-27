using LPPromotion_PDF2.Services;
using Microsoft.AspNetCore.Components;
using Microsoft.AspNetCore.Components.Forms;
using Microsoft.JSInterop;
using System.Text.Json;
using System.Text.Json.Serialization;
using LPPromotion_PDF2.Models;
using Microsoft.AspNetCore.Components.Web;
using System.Text;

namespace LPPromotion_PDF2.Pages
{
    public partial class PdfAnalyzer
    {
        private bool isLoading = false;
        private string errorMessage = string.Empty;
        private string result = string.Empty;
        private IReadOnlyList<IBrowserFile>? selectedFiles;
        private const long MaxFileSize = 10 * 1024 * 1024; // 10MB par fichier
        private const long MaxTotalSize = 50 * 1024 * 1024; // 50MB total
        private List<PlanAnalysis> analyses = new();
        private Dictionary<string, FileStatus> fileStatuses = new();
        private string? base64Pdf;

        [Inject]
        private IPythonApiService PythonApiService { get; set; } = default!;

        [Inject]
        private IJSRuntime JsRuntime { get; set; } = default!;

        private async Task OnDrop(DragEventArgs e)
        {
            try
            {
                var files = await JsRuntime.InvokeAsync<IReadOnlyList<IBrowserFile>>("getDroppedFiles");
                
                if (files == null || !files.Any())
                {
                    errorMessage = "Veuillez sélectionner au moins un fichier PDF.";
                    return;
                }

                // Vérifier le type de fichier
                if (files.Any(f => f.ContentType != "application/pdf"))
                {
                    errorMessage = "Tous les fichiers doivent être au format PDF.";
                    return;
                }

                // Vérifier la taille de chaque fichier
                if (files.Any(f => f.Size > MaxFileSize))
                {
                    errorMessage = $"Chaque fichier ne doit pas dépasser {MaxFileSize / (1024 * 1024)}MB.";
                    return;
                }

                // Vérifier la taille totale
                var totalSize = files.Sum(f => f.Size);
                if (totalSize > MaxTotalSize)
                {
                    errorMessage = $"La taille totale des fichiers ne doit pas dépasser {MaxTotalSize / (1024 * 1024)}MB.";
                    return;
                }

                selectedFiles = files;
                errorMessage = string.Empty;
                fileStatuses.Clear();
                analyses.Clear();
                result = string.Empty;
            }
            catch (Exception ex)
            {
                errorMessage = $"Erreur lors du dépôt des fichiers : {ex.Message}";
            }
        }

        private void OnFileSelected(InputFileChangeEventArgs e)
        {
            try
            {
                var files = e.GetMultipleFiles();
                if (files == null || !files.Any())
                {
                    errorMessage = "Veuillez sélectionner au moins un fichier PDF.";
                    return;
                }

                // Vérifier le type de fichier
                if (files.Any(f => f.ContentType != "application/pdf"))
                {
                    errorMessage = "Tous les fichiers doivent être au format PDF.";
                    return;
                }

                // Vérifier la taille de chaque fichier
                if (files.Any(f => f.Size > MaxFileSize))
                {
                    errorMessage = $"Chaque fichier ne doit pas dépasser {MaxFileSize / (1024 * 1024)}MB.";
                    return;
                }

                // Vérifier la taille totale
                var totalSize = files.Sum(f => f.Size);
                if (totalSize > MaxTotalSize)
                {
                    errorMessage = $"La taille totale des fichiers ne doit pas dépasser {MaxTotalSize / (1024 * 1024)}MB.";
                    return;
                }

                selectedFiles = files;
                errorMessage = string.Empty;
                fileStatuses.Clear();
                analyses.Clear();
                result = string.Empty;
            }
            catch (Exception ex)
            {
                errorMessage = $"Erreur lors de la sélection des fichiers : {ex.Message}";
            }
        }

        private async Task AnalyzePdf()
        {
            if (selectedFiles == null || !selectedFiles.Any()) return;

            try
            {
                isLoading = true;
                errorMessage = string.Empty;
                result = string.Empty;
                analyses.Clear();
                fileStatuses.Clear();

                var results = new List<string>();
                foreach (var file in selectedFiles)
                {
                    // Initialiser le statut du fichier
                    fileStatuses[file.Name] = new FileStatus { IsAnalyzing = true };
                    StateHasChanged();

                    try
                    {
                        using var stream = file.OpenReadStream(maxAllowedSize: MaxFileSize);
                        
                        // Envoyer le fichier à l'API Python
                        var analysis = await PythonApiService.AnalyzePdfAsync(stream, file.Name);

                        // Créer une copie de l'analyse avec le nom du fichier
                        var analysisWithFileName = new PlanAnalysis
                        {
                            FileName = file.Name,
                            TypeBien = analysis.TypeBien,
                            Surfaces = analysis.Surfaces,
                            Caracteristiques = analysis.Caracteristiques
                        };
                        
                        // Stocker le nom du fichier dans une propriété temporaire
                        results.Add($"=== Analyse de {file.Name} ===\n{analysisWithFileName}\n");
                        analyses.Add(analysisWithFileName);
                        
                        // Mettre à jour le statut du fichier
                        fileStatuses[file.Name] = new FileStatus { IsCompleted = true };
                    }
                    catch (Exception ex)
                    {
                        // En cas d'erreur, mettre à jour le statut du fichier
                        fileStatuses[file.Name] = new FileStatus 
                        { 
                            HasError = true, 
                            ErrorMessage = $"Erreur : {ex.Message}" 
                        };
                    }

                    StateHasChanged();
                }

                result = string.Join("\n", results);
            }
            catch (Exception ex)
            {
                errorMessage = $"Erreur lors de l'analyse des PDFs : {ex.Message}";
            }
            finally
            {
                isLoading = false;
            }
        }

        private string GenerateCsv()
        {
            if (!analyses.Any()) return string.Empty;

            var csv = new System.Text.StringBuilder();
            
            // Ajouter le BOM UTF-8 pour Excel
            csv.Append("\uFEFF");
            
            // En-têtes
            csv.AppendLine("Nom du fichier;Type de bien;Surface totale;Pièces;Caractéristiques");

            // Données
            foreach (var analysis in analyses)
            {
                // Formater les pièces avec leurs surfaces dans une seule cellule
                var pieces = analysis.Surfaces.Pieces
                    .OrderBy(p => p.Nom) // Trier les pièces par nom
                    .Select(p => $"{p.Nom}: {p.Surface:0.00}m²");

                // Joindre les pièces avec des retours à la ligne
                var piecesFormatted = string.Join("\r\n", pieces);

                // Formater les caractéristiques dans une seule cellule
                var caracteristiques = string.Join("\r\n", analysis.Caracteristiques.OrderBy(c => c));

                // Nettoyer les valeurs pour éviter les problèmes de formatage CSV
                var fileName = analysis.FileName?.Replace(";", ",");
                var typeBien = analysis.TypeBien?.Replace(";", ",");
                
                // Entourer les cellules contenant des sauts de ligne avec des guillemets doubles
                // et échapper les guillemets existants
                piecesFormatted = $"\"{piecesFormatted.Replace("\"", "\"\"")}\"";
                caracteristiques = $"\"{caracteristiques.Replace("\"", "\"\"")}\"";
                
                // Ajouter la ligne au CSV en utilisant le point-virgule comme séparateur
                csv.AppendLine($"{fileName};" +
                              $"{typeBien};" +
                              $"{analysis.Surfaces.SurfaceTotale:0.00}m²;" +
                              $"{piecesFormatted};" +
                              $"{caracteristiques}");
            }

            return csv.ToString();
        }

        private async Task DownloadCsv()
        {
            try
            {
                var csv = GenerateCsv();
                if (string.IsNullOrEmpty(csv)) return;

                var fileName = $"analyse_plans_{DateTime.Now:yyyyMMdd_HHmmss}.csv";
                await JsRuntime.InvokeVoidAsync("downloadCsv", fileName, csv);
            }
            catch (Exception ex)
            {
                errorMessage = $"Erreur lors de l'export CSV : {ex.Message}";
            }
        }

        private async Task ConvertToBase64(IBrowserFile file)
        {
            try
            {
                using var stream = file.OpenReadStream(maxAllowedSize: MaxFileSize);
                using var memoryStream = new MemoryStream();
                await stream.CopyToAsync(memoryStream);
                
                base64Pdf = Convert.ToBase64String(memoryStream.ToArray());
                StateHasChanged();
            }
            catch (Exception ex)
            {
                errorMessage = $"Erreur lors de la conversion en base64 : {ex.Message}";
            }
        }
    }

    public class FileStatus
    {
        public bool IsAnalyzing { get; set; }
        public bool IsCompleted { get; set; }
        public bool HasError { get; set; }
        public string? ErrorMessage { get; set; }
    }

    public class ChatResponse
    {
        public List<Choice>? Choices { get; set; }
    }

    public class Choice
    {
        public Message? Message { get; set; }
    }

    public class Message
    {
        public string? Content { get; set; }
    }
}
