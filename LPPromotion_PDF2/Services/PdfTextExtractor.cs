using System.Text;
using iText.Kernel.Pdf;
using iText.Kernel.Pdf.Canvas.Parser;
using iText.Kernel.Pdf.Canvas.Parser.Listener;

namespace LPPromotion_PDF2.Services;

public interface IPdfTextExtractor
{
    Task<string> ExtractTextAsync(Stream pdfStream);
}

public class PdfTextExtractor : IPdfTextExtractor
{
    public async Task<string> ExtractTextAsync(Stream pdfStream)
    {
        try
        {
            // Créer un MemoryStream pour stocker le contenu du PDF
            using var memoryStream = new MemoryStream();
            await pdfStream.CopyToAsync(memoryStream);
            memoryStream.Position = 0;

            using var pdfReader = new PdfReader(memoryStream);
            using var pdfDocument = new PdfDocument(pdfReader);
            var text = new StringBuilder();

            for (int i = 1; i <= pdfDocument.GetNumberOfPages(); i++)
            {
                var page = pdfDocument.GetPage(i);
                var strategy = new SimpleTextExtractionStrategy();
                var currentText = iText.Kernel.Pdf.Canvas.Parser.PdfTextExtractor.GetTextFromPage(page, strategy);
                text.AppendLine(currentText);
            }

            return text.ToString();
        }
        catch (Exception ex)
        {
            throw new Exception($"Erreur lors de l'extraction du texte du PDF : {ex.Message}", ex);
        }
    }
} 