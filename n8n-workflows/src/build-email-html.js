const PRIORITY_ORDER = { makkelijk: 0, gemiddeld: 1, lastig: 2 };

// Hex equivalents of Tessar's design tokens (preview/assets/tessar-tokens.css),
// converted from OKLCH because no mail client understands oklch(). Email
// clients also strip <style> blocks unreliably, so every rule below is
// inlined rather than declared once and referenced.
const COLOR = {
  text: '#0C121A',
  textDim: '#555A53',
  border: '#E3E1DD',
  panel: '#F9F8F5',
  accent: '#006894',
  onGradient: '#001A2E',
  gradientStart: '#00BCD8',
  gradientEnd: '#0091CE',
};

const PRIORITY_STYLE = {
  makkelijk: { bg: '#EDFDF5', border: '#B0D9C6', text: '#006C41' },
  gemiddeld: { bg: '#EBF3F7', border: '#9DC4D8', text: '#006894' },
  lastig: { bg: '#FFF6F5', border: '#EBD1CC', text: '#AF3E30' },
};

const FONT_SANS = "'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif";
const FONT_MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function priorityBadge(priority) {
  const style = PRIORITY_STYLE[priority] || PRIORITY_STYLE.gemiddeld;
  return `<span style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; padding:3px 8px; border-radius:6px; background-color:${style.bg}; border:1px solid ${style.border}; color:${style.text};">${escapeHtml(priority)}</span>`;
}

function buildEmailHtml(items) {
  const briefs = items.filter((item) => item.output).map((item) => item.output);
  const missing = items.filter((item) => item.has_data === false).map((item) => item.keyword);

  briefs.sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99));

  let html = `<div style="font-family:${FONT_SANS}; max-width:640px; margin:0 auto; background-color:#FFFFFF;">`;

  // Header: the Tessar gradient banner
  html += `<div style="background-color:${COLOR.gradientEnd}; background-image:linear-gradient(135deg, ${COLOR.gradientStart}, ${COLOR.gradientEnd}); padding:28px 24px; border-radius:0 0 12px 12px;">`;
  html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:${COLOR.onGradient}; opacity:0.7; margin:0 0 6px;">Tessar &middot; SEO Content Briefs</div>`;
  html += `<div style="font-size:24px; font-weight:700; color:${COLOR.onGradient}; letter-spacing:-0.02em; line-height:1.3;">Waar begin je deze week?</div>`;
  html += '</div>';

  html += '<div style="padding:24px;">';

  // "Waar begin je?" summary list
  html += `<h2 style="font-size:19px; font-weight:700; color:${COLOR.text}; margin:0 0 12px;">Waar begin je?</h2>`;
  for (const brief of briefs) {
    html += `<div style="border:1px solid ${COLOR.border}; border-radius:10px; padding:12px 16px; margin-bottom:8px; background-color:${COLOR.panel};">`;
    html += `<strong style="color:${COLOR.text}; font-size:15px;">${escapeHtml(brief.keyword)}</strong> ${priorityBadge(brief.priority)}`;
    html += `<div style="color:${COLOR.textDim}; font-size:14px; margin-top:4px;">${escapeHtml(brief.priority_reason)}</div>`;
    html += '</div>';
  }

  if (missing.length > 0) {
    const style = PRIORITY_STYLE.lastig;
    html += `<div style="border:1px solid ${style.border}; background-color:${style.bg}; border-radius:10px; padding:12px 16px; margin:16px 0;">`;
    html += `<strong style="color:${style.text}; font-size:14px;">Nog geen data voor: ${escapeHtml(missing.join(', '))}</strong>`;
    html += `<div style="color:${COLOR.textDim}; font-size:13px; margin-top:4px;">Draai eerst de rankingtracker-workflow voor deze keywords.</div>`;
    html += '</div>';
  }

  // Full briefs, one card per keyword
  for (const brief of briefs) {
    html += `<div style="border:1px solid ${COLOR.border}; border-radius:12px; padding:20px; margin:24px 0 0; box-shadow:0 1px 2px rgba(0,0,0,0.06);">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.05em; text-transform:uppercase; color:${COLOR.accent}; margin:0 0 8px;">${escapeHtml(brief.keyword)} &middot; ${escapeHtml(brief.search_intent)}</div>`;
    html += `<h2 style="font-size:19px; font-weight:700; color:${COLOR.text}; letter-spacing:-0.01em; margin:0 0 12px;">${escapeHtml(brief.suggested_title)}</h2>`;
    html += `<p style="color:${COLOR.text}; font-size:14px; line-height:1.6; margin:0 0 12px;">${escapeHtml(brief.meta_description)}</p>`;
    html += `<p style="font-size:14px; margin:0 0 8px;"><strong style="color:${COLOR.text};">Contenttype:</strong> <span style="color:${COLOR.textDim};">${escapeHtml(brief.content_type)} &mdash; ${escapeHtml(brief.content_type_reason)}</span></p>`;
    html += `<p style="font-size:14px; margin:0 0 16px;"><strong style="color:${COLOR.text};">Doelgroep:</strong> <span style="color:${COLOR.textDim};">${escapeHtml(brief.target_audience_pain_point)}</span></p>`;
    html += `<div style="border-top:1px solid ${COLOR.border}; margin:0 0 16px;"></div>`;

    html += '<ul style="margin:0 0 16px; padding-left:20px;">';
    for (const section of brief.suggested_h2s) {
      html += `<li style="color:${COLOR.text}; font-size:14px; line-height:1.6; margin-bottom:8px;"><strong>${escapeHtml(section.heading)}</strong>: <span style="color:${COLOR.textDim};">${escapeHtml(section.guidance)}</span></li>`;
    }
    html += '</ul>';

    html += `<p style="font-size:14px; margin:0 0 8px;"><strong style="color:${COLOR.text};">Invalshoek:</strong> <span style="color:${COLOR.textDim};">${escapeHtml(brief.differentiation_angle)}</span></p>`;

    if (brief.competitor_analysis && brief.competitor_analysis.length > 0) {
      html += `<p style="font-size:14px; margin:12px 0 4px;"><strong style="color:${COLOR.text};">Concurrentie:</strong></p>`;
      html += '<ul style="margin:0 0 16px; padding-left:20px;">';
      for (const c of brief.competitor_analysis) {
        html += `<li style="color:${COLOR.textDim}; font-size:13px; line-height:1.6; margin-bottom:6px;"><strong style="color:${COLOR.text};">${escapeHtml(c.name)}</strong> dekt: ${escapeHtml(c.covers)} &mdash; gat: ${escapeHtml(c.gap)}</li>`;
      }
      html += '</ul>';
    }

    html += `<p style="font-size:14px; margin:0 0 8px;"><strong style="color:${COLOR.text};">CTA:</strong> <span style="color:${COLOR.textDim};">${escapeHtml(brief.cta_direction)}</span></p>`;
    html += `<p style="font-family:${FONT_MONO}; font-size:12px; color:${COLOR.textDim}; margin:0;">${brief.target_word_count} woorden geschat</p>`;
    html += '</div>';
  }

  html += '</div>';

  // Footer
  html += `<div style="padding:16px 24px; text-align:center; border-top:1px solid ${COLOR.border}; margin-top:8px;">`;
  html += `<div style="color:${COLOR.textDim}; font-size:12px;">Automatisch gegenereerd door de Tessar content-brief-generator</div>`;
  html += '</div>';

  html += '</div>';

  return html;
}

module.exports = { buildEmailHtml };
