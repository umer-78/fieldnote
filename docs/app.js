import { $, esc, fail, kpis, load, num, pct, select, table } from './kit.js';

try {
  const d = await load();
  const S = d.summary.systems, ocr = S['OCR run here (RapidOCR)'], hand = S['hand transcription (ceiling)'];
  kpis($('#kpis'), [
    { label: 'Right receipt first', value: pct(ocr.total.top1), note: `asking for a total; ${pct(ocr.date.top1)} asking for a date` },
    { label: 'Right answer read', value: pct(ocr.total.answer), note: `totals; ${pct(hand.total.answer)} on hand-typed text` },
    { label: 'Answers with a crop', value: pct((ocr.total.cited + ocr.date.cited) / 2, 0), note: 'the row the value came from, boxed' },
    { label: 'Query time', value: `${num(ocr.p95_ms, 1)} ms`, note: `p95; OCR costs ${num(d.summary.ocr_seconds_per_page, 1)} s a page, once` },
  ]);
  const labels = {};
  const label = async (id) => (labels[id] ??= fetch(`${d.base}/key/${id}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
  const img = (id) => `${d.base}/img/${id}.jpg`;
  async function show(i) {
    const e = d.examples[+i], g = await label(e.receipt), got = e.top[0];
    $('#question').innerHTML = g ? `“What is the ${e.asks} on the <b>${esc(g.company)}</b> receipt ${e.asks === 'total' ? `dated <b>${esc(g.date)}</b>` : `for <b>${esc(g.total)}</b>`}?”`
      : `Question ${esc(e.asks)} for receipt ${esc(e.receipt)} (the dataset could not be reached to show its wording).`;
    $('#result').innerHTML = `<div>Page retrieved<b>receipt ${esc(got)}</b><span class="pill ${e.right_page ? 'ok' : 'no'}">${e.right_page ? 'the right one' : `wanted ${esc(e.receipt)}`}</span></div>` +
      `<div>Next four<b class="mono" style="font-size:15px">${e.top.slice(1).map(esc).join(' · ')}</b><span class="muted small">ranked 2 to 5</span></div>` +
      `<div>Answer<b>${e.right_answer ? 'right' : 'wrong'}</b><span class="muted small">${g ? `the label says ${esc(g[e.asks])}` : ''}</span></div>`;
    const im = new Image();
    im.onload = () => {
      if (!e.box) { $('#crop').innerHTML = '<p class="muted">No row could be cited for this answer.</p>'; return; }
      const [x0, y0, x1, y1] = e.box, W = im.naturalWidth, H = im.naturalHeight, pad = 8;
      const cw = Math.min($('#crop').clientWidth || 600, 720), bw = x1 - x0 + 2 * pad, bh = y1 - y0 + 2 * pad, s = cw / bw;
      $('#crop').innerHTML = `<div role="img" aria-label="The cited row, cropped from receipt ${esc(got)}" style="width:${cw}px;height:${Math.round(bh * s)}px;background:url('${img(got)}') ${-(x0 - pad) * s}px ${-(y0 - pad) * s}px / ${W * s}px ${H * s}px no-repeat"></div>`;
      $('#pagelink').innerHTML = `Box (${e.box.join(', ')}) on <a href="${img(got)}">receipt ${esc(got)}, the whole scanned page</a>.`;
    };
    im.onerror = () => { $('#crop').innerHTML = '<p class="muted">The receipt image could not be loaded from the dataset.</p>'; $('#pagelink').textContent = ''; };
    im.src = img(got);
  }
  select($('#pick'), d.examples.map((e, i) => [i, `receipt ${e.receipt} · ${e.asks}${e.right_answer ? '' : ' (answered wrong)'}`]), Math.max(0, d.examples.findIndex((e) => e.right_answer)), show);
  table($('#table'), [
    { key: 'sys', label: 'Text from' }, { key: 'asks', label: 'Asking for' },
    { key: 'top1', label: 'Right page first', num: true, fmt: (v) => pct(v) }, { key: 'top5', label: 'In top 5', num: true, fmt: (v) => pct(v) },
    { key: 'answer', label: 'Right answer', num: true, fmt: (v) => pct(v) }, { key: 'cited', label: 'Cited', num: true, fmt: (v) => pct(v, 0) },
  ], Object.entries(S).flatMap(([sys, x]) => ['total', 'date'].map((asks) => ({ sys: sys.replace(' (RapidOCR)', '').replace(' (ceiling)', ', the ceiling'), asks, ...x[asks] }))));
} catch (err) {
  fail(err);
}
