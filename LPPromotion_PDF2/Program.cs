using LPPromotion_PDF2.Services;
using LPPromotion_PDF2;
using Microsoft.AspNetCore.Components.Web;
using Microsoft.AspNetCore.Components.WebAssembly.Hosting;
using LPPromotion_PDF2.Models;
using Microsoft.Extensions.Options;

var builder = WebAssemblyHostBuilder.CreateDefault(args);
builder.RootComponents.Add<App>("#app");
builder.RootComponents.Add<HeadOutlet>("head::after");

// Configuration des services
builder.Services.AddScoped(sp => new HttpClient { BaseAddress = new Uri(builder.HostEnvironment.BaseAddress) });
builder.Services.AddScoped<IPdfTextExtractor, PdfTextExtractor>();

// Configuration de l'API Python
var pythonSettings = builder.Configuration.GetSection("PythonApi").Get<PythonApiSettings>();
builder.Services.AddScoped<IPythonApiService>(sp => 
    new PythonApiService(sp.GetRequiredService<HttpClient>(), Options.Create(pythonSettings)));

await builder.Build().RunAsync();
