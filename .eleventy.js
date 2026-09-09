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
