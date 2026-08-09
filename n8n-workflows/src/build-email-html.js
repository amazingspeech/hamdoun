const PRIORITY_ORDER = { makkelijk: 0, gemiddeld: 1, lastig: 2 };

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildEmailHtml(items) {
  const briefs = items.filter((item) => item.output).map((item) => item.output);
  const missing = items.filter((item) => item.has_data === false).map((item) => item.keyword);

  briefs.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99));

  let html = '<h2>Waar begin je?</h2><ul>';
  for (const brief of briefs) {
    html += `<li><strong>${escapeHtml(brief.keyword)}</strong> (${escapeHtml(brief.priority)}) - ${escapeHtml(brief.priority_reason)}</li>`;
  }
  html += '</ul>';

  if (missing.length > 0) {
    html += `<h3>Nog geen data voor: ${escapeHtml(missing.join(', '))}</h3><p>Draai eerst de rankingtracker-workflow voor deze keywords.</p>`;
  }

  for (const brief of briefs) {
    html += `<h2>${escapeHtml(brief.title)}</h2>`;
    html += `<p><strong>Keyword:</strong> ${escapeHtml(brief.keyword)}</p>`;
    html += `<p><strong>Meta-beschrijving:</strong> ${escapeHtml(brief.meta_description)}</p>`;
    html += `<p><strong>Contenttype:</strong> ${escapeHtml(brief.content_type)}</p>`;
    html += '<ul>';
    for (const section of brief.outline) {
      html += `<li><strong>${escapeHtml(section.heading)}</strong>: ${escapeHtml(section.guidance)}</li>`;
    }
    html += '</ul>';
    html += `<p><strong>Invalshoek:</strong> ${escapeHtml(brief.differentiation)}</p>`;
    html += `<p><strong>Geschatte lengte:</strong> ${brief.estimated_word_count} woorden</p>`;
  }

  return html;
}

module.exports = { buildEmailHtml };
