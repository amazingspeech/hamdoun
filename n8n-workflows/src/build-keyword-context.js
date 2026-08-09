// n8n-workflows/src/build-keyword-context.js
function buildKeywordContext(rows, trackedKeywords) {
  const byKeyword = {};
  for (const row of rows) {
    if (!byKeyword[row.keyword]) byKeyword[row.keyword] = [];
    byKeyword[row.keyword].push(row);
  }

  return trackedKeywords.map((keyword) => {
    const rowsForKeyword = byKeyword[keyword] || [];
    if (rowsForKeyword.length === 0) {
      return { keyword, has_data: false, top_competitors: [] };
    }
    const latestDate = rowsForKeyword
      .map((r) => r.checked_at)
      .sort()
      .slice(-1)[0];
    const latestRows = rowsForKeyword.filter((r) => r.checked_at === latestDate);
    const topCompetitors = latestRows
      .filter((r) => !r.is_target_domain)
      .sort((a, b) => Number(a.rank) - Number(b.rank))
      .slice(0, 3)
      .map((r) => ({
        domain: r.domain,
        title: r.title,
        description: r.description,
        rank: Number(r.rank),
      }));
    return { keyword, has_data: true, top_competitors: topCompetitors };
  });
}

module.exports = { buildKeywordContext };
