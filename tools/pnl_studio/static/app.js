'use strict';

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return node;
};

const state = { platform: 'meesho', month: null, months: [], result: null, config: null, currency: 'Rs' };

/* ---------------------------------------------------------------- formatting */
const money = (v) => (v < 0 ? '-' : '') + '₹' + Math.abs(Number(v) || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const money0 = (v) => (v < 0 ? '-' : '') + '₹' + Math.abs(Number(v) || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
const num = (v) => Number(v || 0).toLocaleString('en-IN');
const pct = (v) => (Number(v) || 0).toFixed(2) + '%';
const pct1 = (v) => (Number(v) || 0).toFixed(1) + '%';
const sign = (v) => (v > 0 ? 'pos' : v < 0 ? 'neg' : '');

function banner(msg, kind = 'warn') {
  const b = $('#banner');
  if (!msg) { b.classList.add('hidden'); return; }
  b.className = 'banner ' + kind;
  b.textContent = msg;
}

async function api(path, options) {
  const res = await fetch(path, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

/* ---------------------------------------------------------------- table build */
function table(columns, rows, opts = {}) {
  const head = el('tr', {}, columns.map((c) => el('th', {}, c.label)));
  const body = rows.map((row) => {
    if (row._divider) return el('tr', { class: 'divider' }, el('td', { colspan: columns.length }));
    const tr = el('tr', { class: [row._emphasis ? 'emphasis' : '', row._current ? 'current' : ''].join(' ').trim() });
    for (const c of columns) {
      const raw = row[c.key];
      let text = raw;
      if (c.fmt) text = c.fmt(raw, row);
      const td = el('td', { class: c.signed ? sign(Number(raw)) : '' }, text);
      tr.append(td);
    }
    return tr;
  });
  return el('div', { class: 'scroll' },
    el('table', {}, el('thead', {}, head), el('tbody', {}, body)),
    opts.note ? el('div', { class: 'note' }, opts.note) : null);
}

function card(title, ...children) {
  return el('section', { class: 'card' }, title ? el('h2', {}, title) : null, ...children);
}

function kpi(label, value, hint, colour) {
  return el('div', { class: 'kpi' },
    el('div', { class: 'label' }, label),
    el('div', { class: 'value ' + (colour || '') }, value),
    hint ? el('div', { class: 'hint' }, hint) : null);
}

/* ---------------------------------------------------------------- renderers */
function renderOverview(r) {
  const root = $('#tab-overview');
  root.replaceChildren();
  if (!r.has_data) {
    root.append(card(null, el('p', {}, 'No order lines found for ' + r.month_label + '.')));
    return;
  }
  const k = r.kpis, f = r.funnel_summary, ads = r.ads, cash = r.cash;

  root.append(card(r.month_label + ' — headline',
    el('div', { class: 'kpis' },
      kpi('Net profit', money0(k.net_profit), pct(k.net_margin_on_gross) + ' of gross sale', sign(k.net_profit)),
      kpi('Gross profit', money0(k.gross_profit), 'before ads'),
      kpi('Gross sale', money0(k.gross_sale), num(k.orders) + ' orders'),
      kpi('Settlement', money0(k.settlement), money0(cash.receivable) + ' still receivable'),
      kpi('Units sold', num(k.units_sold), 'delivered + in transit + exchange'),
      kpi('Net profit / unit', money(k.np_per_unit)),
      kpi('ASP / order', money(k.asp_per_order), money(k.asp_per_unit) + ' per unit'),
      kpi('Avg COGS / unit', money(k.avg_cogs_per_unit), 'blended COGS ' + pct(k.blended_cogs_pct)),
      kpi('Ad spend', money0(k.ad_spend), 'ACOS ' + pct(k.acos) + ' · ROAS ' + k.roas.toFixed(2) + 'x'),
      kpi('Return % (closed)', pct(k.return_pct_closed), 'RTO ' + pct(k.rto_pct_closed), k.return_pct_closed > 10 ? 'neg' : ''),
      kpi('Gross margin', pct(k.gross_margin), 'TACOS ' + pct(k.tacos)))));

  root.append(card('Order funnel',
    table([
      { key: 'status', label: 'Status' },
      { key: 'orders', label: 'Orders', fmt: num },
      { key: 'pct', label: '% of orders', fmt: pct },
      { key: 'units', label: 'Units', fmt: num },
      { key: 'gross_sale', label: 'Gross sale', fmt: money },
      { key: 'settlement', label: 'Settlement', fmt: money, signed: true },
      { key: 'bar', label: '', fmt: (_, row) => el('span', { class: 'bar', style: 'width:' + Math.max(2, row.pct) + '%' }) },
    ], r.funnel),
    el('p', { class: 'muted' },
      'Closed orders: ' + num(f.closed) + ' · return ' + pct(f.return_pct_closed) +
      ' · RTO ' + pct(f.rto_pct_closed) + ' · leakage on all orders ' + pct(f.leakage_pct) +
      ' · ' + num(f.in_transit) + ' still in transit.')));

  root.append(card('Ad spend',
    el('p', { class: 'muted' },
      'Base ' + money(ads.base) + ' · GST ' + money(ads.gst) + ' · credits ' + money(ads.credits) +
      ' · total ' + money(ads.total) + ' across ' + ads.days_active + ' of ' + ads.days_in_month + ' days.'),
    ads.campaigns.length ? table([
      { key: 'campaign', label: 'Campaign' },
      { key: 'days', label: 'Days', fmt: num },
      { key: 'spend', label: 'Spend', fmt: money },
      { key: 'share_pct', label: 'Share', fmt: pct1 },
    ], ads.campaigns) : el('p', { class: 'muted' }, 'No ad rows for this month.')));

  root.append(card('Cash position',
    el('div', { class: 'kpis' },
      kpi('Banked', money0(cash.settled), cash.settled_lines + ' settled lines'),
      kpi('Receivable', money0(cash.receivable), cash.receivable_lines + ' unsettled lines', cash.receivable > 0 ? 'neg' : ''),
      kpi('Total earned', money0(cash.total)),
      kpi('Ads deducted', money0(cash.ads_deducted)),
      kpi('Manufacturing outlay', money0(cash.manufacturing_outlay), 'timing differs from settlement'))));
}

function renderBooks(r) {
  const root = $('#tab-books');
  root.replaceChildren();
  if (!r.has_data) return;
  const maxProfit = Math.max(...r.books.map((b) => Math.abs(b.net_profit)), 1);

  root.append(card('Book-level P&L — ' + r.month_label,
    table([
      { key: 'book', label: 'Book' },
      { key: 'units_sold', label: 'Units', fmt: num },
      { key: 'asp', label: 'ASP', fmt: money },
      { key: 'gross_sale', label: 'Gross sale', fmt: money },
      { key: 'settlement', label: 'Settlement', fmt: money },
      { key: 'cogs', label: 'COGS', fmt: money, signed: true },
      { key: 'writeoff', label: 'Write-off', fmt: money, signed: true },
      { key: 'gross_profit', label: 'Gross profit', fmt: money, signed: true },
      { key: 'ad_alloc', label: 'Ad alloc.', fmt: money, signed: true },
      { key: 'net_profit', label: 'Net profit', fmt: money, signed: true },
      { key: 'np_per_unit', label: 'NP/unit', fmt: money, signed: true },
      { key: 'np_pct', label: 'NP %', fmt: pct1 },
      { key: 'bar', label: '', fmt: (_, row) => el('span', {
        class: 'bar' + (row.net_profit < 0 ? ' neg' : ''),
        style: 'width:' + Math.max(2, Math.abs(row.net_profit) / maxProfit * 100) + '%',
      }) },
    ], r.books, { note: r.ad_allocation_note })));

  root.append(card('Returns & failure cost by book',
    table([
      { key: 'book', label: 'Book' },
      { key: 'returns', label: 'Returns', fmt: num },
      { key: 'rto', label: 'RTO', fmt: num },
      { key: 'return_shipping', label: 'Return shipping', fmt: money, signed: true },
      { key: 'writeoff', label: 'Stock write-off', fmt: money, signed: true },
      { key: 'total_cost', label: 'Total return cost', fmt: money, signed: true },
      { key: 'pct_of_book_gp', label: '% of book GP', fmt: pct1 },
      { key: 'cost_per_return', label: 'Cost per failure', fmt: money, signed: true },
    ], r.return_costs),
    el('p', { class: 'muted' },
      'Total return cost ' + money(r.return_cost_summary.total) + ' = ' +
      pct(r.return_cost_summary.pct_of_net_profit) + ' of net profit.')));

  root.append(card('Share of business',
    table([
      { key: 'book', label: 'Book' },
      { key: 'unit_share_pct', label: 'Unit share', fmt: pct1 },
      { key: 'rev_share_pct', label: 'Revenue share', fmt: pct1 },
      { key: 'profit_share_pct', label: 'Profit share', fmt: pct1 },
      { key: 'return_pct', label: 'Return %', fmt: pct },
      { key: 'rto_pct', label: 'RTO %', fmt: pct },
      { key: 'gp_pct', label: 'GP %', fmt: pct1 },
    ], r.books)));
}

function renderSkus(r) {
  const root = $('#tab-skus');
  root.replaceChildren();
  if (!r.has_data) return;

  root.append(card('SKU-level P&L — ' + r.month_label,
    table([
      { key: 'sku', label: 'SKU' },
      { key: 'book', label: 'Book' },
      { key: 'cost', label: 'Cost/unit', fmt: money },
      { key: 'orders', label: 'Orders', fmt: num },
      { key: 'units_sold', label: 'Units', fmt: num },
      { key: 'returns', label: 'Ret', fmt: num },
      { key: 'rto', label: 'RTO', fmt: num },
      { key: 'return_pct', label: 'Return %', fmt: pct },
      { key: 'asp', label: 'ASP', fmt: money },
      { key: 'settle_per_unit', label: 'Settle/unit', fmt: money },
      { key: 'contrib_per_unit', label: 'Contribution/unit', fmt: money, signed: true },
      { key: 'gross_profit', label: 'Gross profit', fmt: money, signed: true },
    ], r.skus)));

  const payback = r.skus
    .filter((s) => s.contrib_per_unit > 0)
    .map((s) => ({ sku: s.sku, contrib: s.contrib_per_unit, units: Math.ceil(r.kpis.ad_spend / s.contrib_per_unit) }))
    .sort((a, b) => a.units - b.units);
  if (payback.length) {
    root.append(card('Ad payback — units needed to cover ' + money0(r.kpis.ad_spend) + ' of ads',
      table([
        { key: 'sku', label: 'SKU' },
        { key: 'contrib', label: 'Contribution/unit', fmt: money },
        { key: 'units', label: 'Units to break even', fmt: num },
      ], payback)));
  }
}

function renderStatement(r) {
  const root = $('#tab-statement');
  root.replaceChildren();
  if (!r.has_data) return;
  const rows = r.statement.map((line) => line.divider
    ? { _divider: true }
    : { label: line.label, value: line.value, pct_of_gross: line.pct_of_gross, _emphasis: line.emphasis });

  root.append(card('Profit & loss statement — ' + r.month_label,
    table([
      { key: 'label', label: 'Line' },
      { key: 'value', label: 'Amount', fmt: money, signed: true },
      { key: 'pct_of_gross', label: '% of gross sale', fmt: pct },
    ], rows),
    el('p', { class: 'muted' },
      'Assumptions: ' + Math.round(r.resell_rate * 100) + '% of returned/RTO stock resellable (' +
      r.writeoff_pct + '% written off) · return shipping ' + money(r.return_shipping_per_order) +
      ' per failed order · units sold = delivered + in transit + exchange.')));

  root.append(card('Cohort build',
    table([
      { key: 'step', label: 'Step' },
      { key: 'rows', label: 'Rows', fmt: num },
    ], [
      { step: 'Rows across all de-duplicated payment files', rows: r.cohort.rows_in_scope },
      { step: 'Excluded (placed outside ' + r.month_label + ')', rows: r.cohort.rows_excluded },
      { step: 'Kept (placed in ' + r.month_label + ')', rows: r.cohort.rows_kept, _emphasis: true },
      { step: '— real order lines', rows: r.cohort.order_lines },
      { step: '— fee-adjustment lines', rows: r.cohort.fee_lines },
      { step: 'Unique orders', rows: r.cohort.unique_orders },
    ])));
}

function renderRisk(r) {
  const root = $('#tab-risk');
  root.replaceChildren();
  if (!r.has_data) return;
  const be = r.breakeven, s = r.sensitivity, c = r.conservative;

  root.append(card('Break-even',
    el('div', { class: 'kpis' },
      kpi('Ad headroom', money0(be.ad_headroom), 'spent ' + money0(be.ad_spent) + ' (' + pct1(be.ad_used_pct) + ')'),
      kpi('Break-even COGS/unit', money(be.breakeven_cogs_per_unit), 'actual ' + money(be.actual_cogs_per_unit)),
      kpi('Headroom per unit', money(be.headroom_per_unit), null, sign(be.headroom_per_unit)))));

  root.append(card('Return-rate sensitivity',
    el('p', { class: 'muted' },
      'Each failed order costs ' + money(s.cost_per_failure) + ' = return shipping ' +
      money(r.return_shipping_per_order) + ' + ' + r.writeoff_pct + '% write-off on a ' +
      money(s.avg_cost_per_unit) + ' average unit.'),
    table([
      { key: 'return_rate', label: 'Return rate', fmt: (v, row) => pct(v) + (row.is_current ? ' (current)' : '') },
      { key: 'return_cost', label: 'Return cost', fmt: money },
      { key: 'net_profit', label: 'Net profit', fmt: money, signed: true },
    ], s.rows.map((row) => ({ ...row, _current: row.is_current })))));

  root.append(card('Conservative view — haircut the in-transit orders',
    el('p', { class: 'muted' },
      'Applying the observed ' + pct(c.fail_rate) + ' failure rate to ' + num(c.transit_orders) +
      ' orders still in transit (' + num(c.transit_units) + ' units, ' + money(c.transit_settlement) + ' booked).'),
    table([
      { key: 'item', label: 'Item' },
      { key: 'value', label: 'Amount', fmt: money, signed: true },
    ], [
      { item: 'Settlement at risk', value: -c.settlement_at_risk },
      { item: 'Stock recovered (' + Math.round(r.resell_rate * 100) + '% resellable)', value: c.stock_recovered },
      { item: 'Extra return shipping', value: -c.extra_return_shipping },
      { item: 'Reported net profit', value: c.reported_net_profit, _emphasis: true },
      { item: 'Conservative net profit', value: c.conservative_net_profit, _emphasis: true },
      { item: 'Downside risk (' + pct1(c.downside_pct) + ')', value: -c.downside },
      { item: 'Worst case — every in-transit order fails', value: c.worst_case_net_profit },
    ])));
}

/* ---------------------------------------------------------------- compare */
function renderCompareChips() {
  const box = $('#compareMonths');
  box.replaceChildren();
  for (const m of state.months) {
    const chip = el('label', { class: 'chip' },
      el('input', { type: 'checkbox', value: m.month, checked: true }), m.label);
    chip.querySelector('input').addEventListener('change', (e) => chip.classList.toggle('on', e.target.checked));
    chip.classList.add('on');
    box.append(chip);
  }
}

async function runCompare() {
  const months = [...$('#compareMonths').querySelectorAll('input:checked')].map((i) => i.value);
  const out = $('#compareOut');
  out.replaceChildren();
  if (months.length < 2) { banner('Pick at least two months to compare.', 'warn'); return; }
  banner('');
  const data = await api('/api/compare?platform=' + state.platform + '&months=' + months.join(','));
  const fmt = { money, int: num, pct, x: (v) => Number(v).toFixed(2) + 'x' };

  const columns = [{ key: 'label', label: 'Metric' }];
  data.months.forEach((m, i) => {
    columns.push({ key: 'v' + i, label: m.label, fmt: (v, row) => fmt[row.kind](v) });
    if (i > 0) columns.push({ key: 'd' + i, label: 'Δ', fmt: (v) => v === null ? '—' : (v > 0 ? '+' : '') + pct1(v), signed: true });
  });
  const rows = data.rows.map((r) => {
    const row = { label: r.label, kind: r.kind };
    r.values.forEach((v, i) => { row['v' + i] = v; });
    r.deltas.forEach((d, i) => { row['d' + i] = d; });
    return row;
  });
  out.append(card('KPI trend', table(columns, rows)));

  const bookCols = [{ key: 'book', label: 'Book' }];
  data.months.forEach((m, i) => {
    bookCols.push({ key: 'u' + i, label: m.label + ' units', fmt: num });
    bookCols.push({ key: 'p' + i, label: m.label + ' net profit', fmt: money, signed: true });
  });
  const bookRows = data.books.rows.map((r) => {
    const row = { book: r.book };
    r.units.forEach((v, i) => { row['u' + i] = v; });
    r.net_profit.forEach((v, i) => { row['p' + i] = v; });
    return row;
  });
  out.append(card('Book trend', table(bookCols, bookRows)));
}

/* ---------------------------------------------------------------- data tab */
function renderData(r) {
  const root = $('#dataOut');
  root.replaceChildren();
  const src = r.sources;
  const rows = src.files.map((f) => ({
    name: f.name,
    rel: f.rel,
    kind: f.settled ? 'Settled' : 'Outstanding',
    order_rows: f.order_rows,
    ad_rows: f.ad_rows,
    dupes: f.duplicates.length ? f.duplicates.join(', ') : '—',
  }));
  root.append(card('Discovered files (' + rows.length + ')',
    el('p', { class: 'muted' },
      num(src.rows_before_dedupe) + ' raw order rows → ' + num(src.rows_after_dedupe) +
      ' after de-duplication. Identical file copies are collapsed by content hash.'),
    table([
      { key: 'name', label: 'File' },
      { key: 'kind', label: 'Type' },
      { key: 'order_rows', label: 'Order rows', fmt: num },
      { key: 'ad_rows', label: 'Ad rows', fmt: num },
      { key: 'rel', label: 'Path' },
      { key: 'dupes', label: 'Duplicate copies ignored' },
    ], rows)));
  if (src.errors.length) {
    root.append(card('Parse errors',
      table([{ key: 'file', label: 'File' }, { key: 'error', label: 'Error' }], src.errors)));
  }
}

/* ---------------------------------------------------------------- config tab */
function renderConfig() {
  const cfg = state.config;
  const root = $('#configOut');
  root.replaceChildren();

  const body = el('tbody');
  const addRow = (sku, meta) => {
    const tr = el('tr', {},
      el('td', {}, el('input', { type: 'text', value: sku, 'data-field': 'sku' })),
      el('td', {}, el('input', { type: 'text', value: meta.book, 'data-field': 'book' })),
      el('td', {}, el('input', { type: 'number', step: '0.01', min: '0', value: meta.cost, 'data-field': 'cost' })),
      el('td', {}, el('input', { type: 'text', value: meta.note || '', 'data-field': 'note' })),
      el('td', {}, el('button', { onclick: (e) => e.target.closest('tr').remove() }, 'Remove')));
    body.append(tr);
  };
  Object.entries(cfg.skus).forEach(([sku, meta]) => addRow(sku, meta));
  root._addRow = () => addRow('', { book: '', cost: 0 });

  root.append(el('div', { class: 'scroll' },
    el('table', { class: 'cfgtable' },
      el('thead', {}, el('tr', {},
        el('th', {}, 'SKU'), el('th', {}, 'Book'), el('th', {}, 'Cost/unit'),
        el('th', {}, 'Note'), el('th', {}, ''))),
      body)));

  for (const [key, pf] of Object.entries(cfg.platforms)) {
    const monthBody = el('tbody');
    const months = new Set([...Object.keys(pf.months || {}), ...state.months.map((m) => m.month)]);
    for (const m of [...months].sort()) {
      const override = (pf.months || {})[m] || {};
      monthBody.append(el('tr', {},
        el('td', {}, m),
        el('td', {}, el('input', {
          type: 'number', min: '0', max: '100', step: '1',
          value: override.resell_rate !== undefined ? Math.round(override.resell_rate * 100) : '',
          placeholder: Math.round(pf.default_resell_rate * 100),
          'data-month': m, 'data-platform': key, 'data-field': 'resell',
        })),
        el('td', {}, el('input', {
          type: 'text', value: override.note || '',
          'data-month': m, 'data-platform': key, 'data-field': 'mnote',
        }))));
    }
    root.append(el('h3', {}, key + ' assumptions'),
      el('div', { class: 'row' },
        el('label', {}, 'Default resell rate %',
          el('input', { type: 'number', min: '0', max: '100', step: '1', class: 'num',
            value: Math.round(pf.default_resell_rate * 100), 'data-platform': key, 'data-field': 'defresell' })),
        el('label', {}, 'Return shipping / failed order ₹',
          el('input', { type: 'number', min: '0', step: '1', class: 'num',
            value: pf.return_shipping_per_order, 'data-platform': key, 'data-field': 'retship' }))),
      el('div', { class: 'scroll' },
        el('table', { class: 'cfgtable' },
          el('thead', {}, el('tr', {},
            el('th', {}, 'Month'), el('th', {}, 'Resell rate % (blank = default)'), el('th', {}, 'Note'))),
          monthBody)));
  }
}

function collectConfig() {
  const cfg = JSON.parse(JSON.stringify(state.config));
  const skus = {};
  for (const tr of $('#configOut').querySelectorAll('table.cfgtable')[0].querySelectorAll('tbody tr')) {
    const get = (f) => tr.querySelector('[data-field="' + f + '"]').value.trim();
    const sku = get('sku');
    if (!sku) continue;
    const entry = { book: get('book'), cost: Number(get('cost') || 0) };
    const note = get('note');
    if (note) entry.note = note;
    skus[sku] = entry;
  }
  cfg.skus = skus;

  for (const [key, pf] of Object.entries(cfg.platforms)) {
    const def = $('#configOut').querySelector('[data-platform="' + key + '"][data-field="defresell"]');
    const ship = $('#configOut').querySelector('[data-platform="' + key + '"][data-field="retship"]');
    if (def) pf.default_resell_rate = Number(def.value || 0) / 100;
    if (ship) pf.return_shipping_per_order = Number(ship.value || 0);
    const months = {};
    for (const input of $('#configOut').querySelectorAll('[data-platform="' + key + '"][data-field="resell"]')) {
      const m = input.getAttribute('data-month');
      const noteInput = $('#configOut').querySelector('[data-platform="' + key + '"][data-field="mnote"][data-month="' + m + '"]');
      const entry = {};
      if (input.value !== '') entry.resell_rate = Number(input.value) / 100;
      if (noteInput && noteInput.value.trim()) entry.note = noteInput.value.trim();
      if (Object.keys(entry).length) months[m] = entry;
    }
    pf.months = months;
  }
  return cfg;
}

/* ---------------------------------------------------------------- flow */
function renderAll(r) {
  state.result = r;
  renderOverview(r);
  renderBooks(r);
  renderSkus(r);
  renderStatement(r);
  renderRisk(r);
  renderData(r);
  const warnings = [];
  if (r.cohort.unmapped_skus.length) warnings.push('Unmapped SKUs (no book/cost): ' + r.cohort.unmapped_skus.join(', '));
  if (r.cohort.zero_cost_skus.length) warnings.push('SKUs with zero cost: ' + r.cohort.zero_cost_skus.join(', '));
  if (r.sources.errors.length) warnings.push(r.sources.errors.length + ' file(s) failed to parse — see Data Sources.');
  banner(warnings.join(' · '), warnings.length ? 'warn' : 'ok');
}

async function refresh() {
  $('#loading').classList.remove('hidden');
  try {
    const params = new URLSearchParams({
      platform: state.platform,
      month: state.month,
      resell_rate: (Number($('#resell').value) / 100).toString(),
      return_shipping: $('#retship').value || '0',
    });
    renderAll(await api('/api/pnl?' + params));
  } catch (err) {
    banner(err.message, 'err');
  } finally {
    $('#loading').classList.add('hidden');
  }
}

async function loadDatasets() {
  const data = await api('/api/datasets?platform=' + state.platform);
  state.months = data.months;
  const sel = $('#month');
  sel.replaceChildren(...data.months.map((m) => el('option', { value: m.month }, m.label)));
  if (!data.months.length) { banner('No data files found for this platform.', 'warn'); return; }
  state.month = data.months[data.months.length - 1].month;
  sel.value = state.month;
  syncMonthDefaults();
  renderCompareChips();
  await refresh();
}

function syncMonthDefaults() {
  const m = state.months.find((x) => x.month === state.month);
  const pf = state.config.platforms[state.platform] || {};
  const rate = m ? m.resell_rate : (pf.default_resell_rate || 0.7);
  $('#resell').value = Math.round(rate * 100);
  $('#resellOut').value = Math.round(rate * 100) + '%';
  $('#retship').value = pf.return_shipping_per_order || 0;
}

async function init() {
  state.config = await api('/api/config');
  const platforms = await api('/api/platforms');
  $('#platform').replaceChildren(...platforms.platforms.map((p) =>
    el('option', { value: p.key, disabled: p.implemented ? null : 'disabled' },
      p.label + (p.implemented ? '' : ' (coming soon)'))));
  $('#platform').value = state.platform;
  renderConfig();
  await loadDatasets();
}

/* ---------------------------------------------------------------- wiring */
$('#tabs').addEventListener('click', (e) => {
  const btn = e.target.closest('button[data-tab]');
  if (!btn) return;
  document.querySelectorAll('#tabs button').forEach((b) => b.classList.toggle('active', b === btn));
  document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t.id === 'tab-' + btn.dataset.tab));
});

$('#platform').addEventListener('change', async (e) => {
  state.platform = e.target.value;
  await loadDatasets();
});
$('#month').addEventListener('change', async (e) => {
  state.month = e.target.value;
  syncMonthDefaults();
  await refresh();
});
$('#resell').addEventListener('input', (e) => { $('#resellOut').value = e.target.value + '%'; });
$('#refresh').addEventListener('click', refresh);
$('#runCompare').addEventListener('click', () => runCompare().catch((e) => banner(e.message, 'err')));

async function generateReport() {
  const params = new URLSearchParams({
    platform: state.platform,
    month: state.month,
    resell_rate: (Number($('#resell').value) / 100).toString(),
    return_shipping: $('#retship').value || '0',
  });
  const data = await api('/api/report?' + params);
  $('#reportText').value = data.markdown;
  if (!$('#reportPath').value) {
    $('#reportPath').value = 'Finance/' + state.result.month_label.slice(0, 3) + '_Profit_Loss/' + data.filename;
  }
  return data;
}

$('#genReport').addEventListener('click', () => generateReport().then(() => banner('Report generated.', 'ok')).catch((e) => banner(e.message, 'err')));
$('#copyReport').addEventListener('click', async () => {
  if (!$('#reportText').value) await generateReport();
  await navigator.clipboard.writeText($('#reportText').value);
  banner('Copied to clipboard.', 'ok');
});
$('#downloadReport').addEventListener('click', async () => {
  const data = $('#reportText').value ? { markdown: $('#reportText').value, filename: 'pnl.md' } : await generateReport();
  const blob = new Blob([data.markdown || $('#reportText').value], { type: 'text/markdown' });
  const a = el('a', { href: URL.createObjectURL(blob), download: data.filename });
  a.click();
  URL.revokeObjectURL(a.href);
});
$('#saveReport').addEventListener('click', async () => {
  const body = {
    platform: state.platform,
    month: state.month,
    resell_rate: Number($('#resell').value) / 100,
    return_shipping: Number($('#retship').value || 0),
    path: $('#reportPath').value || null,
  };
  const send = async () => api('/api/report/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  try {
    banner('Saved to ' + (await send()).saved, 'ok');
  } catch (e) {
    if (!/already exists/.test(e.message)) { banner(e.message, 'err'); return; }
    if (!confirm(e.message + '\n\nOverwrite it?')) { banner('Save cancelled.', 'warn'); return; }
    body.overwrite = true;
    try { banner('Overwrote ' + (await send()).saved, 'ok'); }
    catch (e2) { banner(e2.message, 'err'); }
  }
});

$('#addSku').addEventListener('click', () => $('#configOut')._addRow());
$('#reloadConfig').addEventListener('click', async () => {
  state.config = await api('/api/config');
  renderConfig();
  banner('Config reloaded from disk.', 'ok');
});
$('#saveConfig').addEventListener('click', async () => {
  try {
    state.config = await api('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectConfig()),
    });
    renderConfig();
    await refresh();
    banner('Config saved and P&L recalculated.', 'ok');
  } catch (e) { banner(e.message, 'err'); }
});

const drop = $('#drop');
['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => {
  e.preventDefault(); drop.classList.add('hot');
}));
['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove('hot')));
drop.addEventListener('drop', (e) => { e.preventDefault(); upload(e.dataTransfer.files); });
$('#fileInput').addEventListener('change', (e) => upload(e.target.files));

async function upload(fileList) {
  if (!fileList || !fileList.length) return;
  const form = new FormData();
  for (const f of fileList) form.append('files', f);
  try {
    const res = await api('/api/upload', { method: 'POST', body: form });
    const out = $('#uploadOut');
    out.replaceChildren(
      res.saved.length ? el('p', { class: 'muted' }, 'Added: ' + res.saved.map((s) => s.name + ' → ' + s.platform).join(', ')) : null,
      res.rejected.length ? el('p', { class: 'muted' }, 'Rejected: ' + res.rejected.map((s) => s.name + ' (' + s.reason + ')').join(', ')) : null);
    await loadDatasets();
    banner(res.saved.length + ' file(s) added.', res.saved.length ? 'ok' : 'warn');
  } catch (e) { banner(e.message, 'err'); }
}

init().catch((e) => banner(e.message, 'err'));
