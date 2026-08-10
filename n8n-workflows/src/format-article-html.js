const FONT_SANS = "'IBM Plex Sans', -apple-system, 'Segoe UI', sans-serif";
const FONT_MONO = "'IBM Plex Mono', ui-monospace, SFMono-Regular, Menlo, monospace";
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

function escapeHtml(str) {
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Applies to text that has ALREADY been through escapeHtml.
function inlineMarkdown(escapedText) {
  return escapedText.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

function markdownToHtml(md) {
  const lines = escapeHtml(md).split('\n');
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === '') {
      i++;
      continue;
    }
    if (line.startsWith('# ')) {
      blocks.push({ type: 'h1', text: line.slice(2) });
      i++;
      continue;
    }
    if (line.startsWith('## ')) {
      blocks.push({ type: 'h2', text: line.slice(3) });
      i++;
      continue;
    }
    if (/^-\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^-\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^-\s+/, ''));
        i++;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }
    if (/^\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\d+\.\s+/, ''));
        i++;
      }
      blocks.push({ type: 'ol', items });
      continue;
    }

    // Plain paragraph: collect consecutive non-blank, non-special lines.
    const paraLines = [];
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !lines[i].startsWith('# ') &&
      !lines[i].startsWith('## ') &&
      !/^-\s+/.test(lines[i]) &&
      !/^\d+\.\s+/.test(lines[i])
    ) {
      paraLines.push(lines[i]);
      i++;
    }
    blocks.push({ type: 'p', text: paraLines.join('\n') });
  }

  return blocks
    .map((block) => {
      if (block.type === 'h1') {
        return `<h1 style="font-family:${FONT_SANS}; font-size:22px; color:${COLOR.text}; margin:20px 0 10px;">${inlineMarkdown(block.text)}</h1>`;
      }
      if (block.type === 'h2') {
        return `<h2 style="font-family:${FONT_SANS}; font-size:17px; color:${COLOR.accent}; margin:18px 0 8px;">${inlineMarkdown(block.text)}</h2>`;
      }
      if (block.type === 'ul') {
        const items = block.items.map((it) => `<li>${inlineMarkdown(it)}</li>`).join('');
        return `<ul style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px; padding-left:20px;">${items}</ul>`;
      }
      if (block.type === 'ol') {
        const items = block.items.map((it) => `<li>${inlineMarkdown(it)}</li>`).join('');
        return `<ol style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px; padding-left:20px;">${items}</ol>`;
      }
      return `<p style="font-family:${FONT_SANS}; font-size:14px; line-height:1.6; color:${COLOR.text}; margin:0 0 12px;">${inlineMarkdown(block.text).replace(/\n/g, '<br>')}</p>`;
    })
    .join('');
}

function buildDraftReviewEmailHtml(items) {
  let html = `<div style="font-family:${FONT_SANS}; max-width:680px; margin:0 auto; background-color:#FFFFFF;">`;
  html += `<div style="background-image:linear-gradient(135deg, ${COLOR.gradientStart}, ${COLOR.gradientEnd}); padding:28px 24px; border-radius:0 0 12px 12px;">`;
  html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:${COLOR.onGradient}; opacity:0.7; margin:0 0 6px;">Tessar &middot; Conceptartikelen</div>`;
  html += `<div style="font-family:${FONT_SANS}; font-size:20px; font-weight:600; color:${COLOR.onGradient};">${items.length} nieuw${items.length === 1 ? '' : 'e'} conceptartikel${items.length === 1 ? '' : 'en'} klaar voor review</div>`;
  html += `</div>`;

  for (const item of items) {
    html += `<div style="padding:20px 24px; border-bottom:1px solid ${COLOR.border};">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:11px; color:${COLOR.textDim}; text-transform:uppercase; margin-bottom:6px;">${escapeHtml(item.keyword)} &middot; ${escapeHtml(item.content_type)}</div>`;
    html += markdownToHtml(item.draft_markdown || '');
    html += `<div style="background-color:${COLOR.panel}; border:1px solid ${COLOR.border}; border-radius:8px; padding:12px 14px; margin-top:12px;">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:10px; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:${COLOR.textDim}; margin-bottom:6px;">Redactie-checklist</div>`;
    html += `<div style="font-family:${FONT_SANS}; font-size:13px; line-height:1.5; color:${COLOR.text};">${escapeHtml(item.editor_notes || '').replace(/\n/g, '<br>')}</div>`;
    html += `</div></div>`;
  }

  html += `</div>`;
  return html;
}

function buildFormattedArticleEmailHtml(items) {
  let html = `<div style="font-family:${FONT_SANS}; max-width:680px; margin:0 auto; background-color:#FFFFFF;">`;
  html += `<div style="background-image:linear-gradient(135deg, ${COLOR.gradientStart}, ${COLOR.gradientEnd}); padding:28px 24px; border-radius:0 0 12px 12px;">`;
  html += `<div style="font-family:${FONT_MONO}; font-size:11px; font-weight:600; letter-spacing:0.06em; text-transform:uppercase; color:${COLOR.onGradient}; opacity:0.7; margin:0 0 6px;">Tessar &middot; Geformatteerde artikelen</div>`;
  html += `<div style="font-family:${FONT_SANS}; font-size:20px; font-weight:600; color:${COLOR.onGradient};">${items.length} artikel${items.length === 1 ? '' : 'en'} klaar om te plakken</div>`;
  html += `</div>`;

  for (const item of items) {
    html += `<div style="padding:20px 24px; border-bottom:1px solid ${COLOR.border};">`;
    html += `<div style="font-family:${FONT_MONO}; font-size:11px; color:${COLOR.textDim}; text-transform:uppercase; margin-bottom:6px;">${escapeHtml(item.keyword)} &middot; ${escapeHtml(item.content_type)}</div>`;
    html += markdownToHtml(item.draft_markdown || '');
    html += `</div>`;
  }

  html += `</div>`;
  return html;
}

module.exports = { escapeHtml, markdownToHtml, buildDraftReviewEmailHtml, buildFormattedArticleEmailHtml };
