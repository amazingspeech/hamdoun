// .eleventy.js
// Eleventy-config voor de 13 statische tessar.nl-pagina's (alles behalve
// de homepage — index.html/index.src.html draaien nog op de bestaande
// dc-runtime/prerender-pijplijn, zie scripts/prerender-index.mjs, en
// worden hieronder als kant-en-klaar bestand meegekopieerd, niet
// getemplate). Output blijft plat op domeinniveau (geen /pagina/-mappen),
// exact zoals de huidige, live URL-structuur.
module.exports = function (eleventyConfig) {
  // Statische bestanden die niet als Nunjucks-template verwerkt mogen
  // worden: gewoon 1-op-1 meekopieren naar _site/.
  eleventyConfig.addPassthroughCopy("assets");
  eleventyConfig.addPassthroughCopy("tessar-concierge-widget.js");
  eleventyConfig.addPassthroughCopy("sitemap.xml");
  eleventyConfig.addPassthroughCopy("robots.txt");
  eleventyConfig.addPassthroughCopy("llms.txt");
  eleventyConfig.addPassthroughCopy("googleb2c866753bf6b639.html");
  // De homepage is al kant-en-klaar gebakken door scripts/prerender-index.mjs
  // (npm run build) — hier alleen meekopieren, nooit als template verwerken.
  eleventyConfig.addPassthroughCopy("index.html");
  // og-image.jpg: live op productie, gerefereerd door og:image/twitter:image
  // op 6 van de 13 gemigreerde pagina's (privacy, services, chatbots,
  // prijzen, contact, blog) en de homepage (de 6 artikelpagina's gebruiken
  // hun eigen blog-thumbnail als og:image, 404.html heeft geen og:image).
  // Zonder deze regel bakt Eleventy hem niet mee naar _site/, en verwijdert
  // de eerstvolgende rsync --delete-deploy hem stilletjes van de server
  // (final-review-report, bevinding C1).
  eleventyConfig.addPassthroughCopy("og-image.jpg");
  // Tessar-logo-symbol.png/.webp: ook live op productie, maar nergens in
  // deze repo (HTML/CSS/JS) gerefereerd. Bewuste keuze om ze toch te blijven
  // uitleveren in plaats van te laten vervallen: een niet-in-de-repo
  // referentie (e-mailhandtekening, extern systeem, bewaarde link) kan nog
  // steeds bestaan, en het risico van een stille 404 daar weegt zwaarder dan
  // de kosten van ~730KB blijven meekopiëren (final-review-report, I2).
  eleventyConfig.addPassthroughCopy("Tessar-logo-symbol.png");
  eleventyConfig.addPassthroughCopy("Tessar-logo-symbol.webp");
  // support.js NIET toevoegen: dode dc-runtime-code, bevestigd ongebruikt
  // door de gebakken index.html en door geen enkele gemigreerde pagina
  // gerefereerd (final-review-report, I2); hier weglaten is de bedoelde
  // uitkomst.

  return {
    dir: {
      input: ".",
      output: "_site",
      includes: "_includes",
    },
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: false,
    templateFormats: ["html", "njk"],
  };
};
