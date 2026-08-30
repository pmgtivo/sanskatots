import {
  STORE_ORDERS,
  STORE_SKUS,
  getAll,
  put,
  putMany,
  del,
  clearStore,
  getSettings,
  setSetting,
  logEvent,
  STORE_SETTINGS,
  STORE_EVENTS,
} from '../lib/db.js';
import {
  PLATFORMS,
  STATUSES,
  STATUS_ORDER,
  ACTIONABLE,
  REASON_CODES,
  RECEIVED_BACK,
  DEFAULT_SETTINGS,
  DEFAULT_FEES,
  computePnl,
  rollup,
  nextStatuses,
  needsAttention,
  makeOrderKey,
} from '../lib/model.js';
import {
  parseDelimited,
  toObjects,
  detectPlatform,
  autoMap,
  recordsToOrders,
  LOGICAL_FIELDS,
  REQUIRED_FIELDS,
  toCsv,
  todayISO,
} from '../lib/csv.js';

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => [...document.querySelectorAll(sel)];

const state = {
  orders: [],
  skus: {},
  settings: { ...DEFAULT_SETTINGS },
  selected: new Set(),
  page: 0,
  pageSize: 100,
  pending: null, // staged import
};

const money = (v) =>
  (v < 0 ? '-' : '') +
  '₹' +
  Math.abs(Math.round(v || 0)).toLocaleString('en-IN');
const pct = (v) => `${(v || 0).toFixed(1)}%`;

function toast(msg) {
  const t = $('#toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2600);
}

/* ------------------------------------------------------------------ load */

async function loadAll() {
  const [orders, skus, settings] = await Promise.all([
    getAll(STORE_ORDERS),
    getAll(STORE_SKUS),
    getSettings(),
  ]);
  state.orders = orders || [];
  state.skus = {};
  (skus || []).forEach((s) => {
    state.skus[s.sku] = s;
  });
  state.settings = {
    ...DEFAULT_SETTINGS,
    ...settings,
    fees: { ...DEFAULT_FEES, ...(settings.fees || {}) },
  };
}

function renderAll() {
  $('#bizName').textContent = state.settings.businessName || 'SanskaTots';
  renderPack();
  renderOrders();
  renderSkus();
  renderReports();
  renderSettings();
  refreshSkuDatalist();
}

/* ------------------------------------------------------------- status ops */

async function setStatus(order, status, extra = {}) {
  const now = new Date().toISOString();
  const history = order.statusHistory || [];
  history.push({ from: order.status, to: status, at: now });
  const updated = {
    ...order,
    ...extra,
    status,
    statusHistory: history,
    updatedAt: now,
  };
  if (status === 'PACKED') updated.packedAt = now;
  if (status === 'HANDED_OVER') updated.handedOverAt = now;
  if (status === 'DELIVERED') updated.deliveredAt = now;
  await put(STORE_ORDERS, updated);
  await logEvent(order.id, 'status', `${order.status} → ${status}`);
  const idx = state.orders.findIndex((o) => o.id === order.id);
  if (idx >= 0) state.orders[idx] = updated;
  return updated;
}

/* -------------------------------------------------------------- pack view */

function actionableOrders() {
  const q = ($('#packSearch').value || '').toLowerCase();
  const plat = $('#packPlatform').value;
  const showAll = $('#packShowAll').checked;
  return state.orders.filter((o) => {
    if (plat && o.platform !== plat) return false;
    if (!showAll && !ACTIONABLE.includes(o.status) && !needsAttention(o)) return false;
    if (!q) return true;
    return [o.orderId, o.subOrderId, o.awb, o.sku, o.productName]
      .join(' ')
      .toLowerCase()
      .includes(q);
  });
}

function renderPack() {
  const list = actionableOrders();
  const byStatus = (s) => list.filter((o) => o.status === s);

  const todayOrders = state.orders.filter((o) => o.orderDate === todayISO());
  const stats = [
    { k: 'To print', v: state.orders.filter((o) => o.status === 'NEW').length, cls: 'warn' },
    { k: 'To pack', v: state.orders.filter((o) => o.status === 'LABEL_PRINTED').length, cls: 'warn' },
    { k: 'Ready for pickup', v: state.orders.filter((o) => o.status === 'PACKED').length, cls: 'good' },
    { k: 'In transit', v: state.orders.filter((o) => ['HANDED_OVER', 'IN_TRANSIT'].includes(o.status)).length, cls: '' },
    { k: 'Problems', v: state.orders.filter(needsAttention).length, cls: 'bad' },
    { k: 'Orders today', v: todayOrders.length, cls: '' },
  ];
  $('#packStats').innerHTML = stats
    .map((s) => `<div class="stat ${s.cls}"><div class="k">${s.k}</div><div class="v">${s.v}</div></div>`)
    .join('');

  const lanes = [
    { status: 'NEW', title: '1. Print label' },
    { status: 'LABEL_PRINTED', title: '2. Pick & pack' },
    { status: 'PACKED', title: '3. Hand over to courier' },
  ];
  const problemList = list.filter(needsAttention);

  let html = lanes
    .map((lane) => {
      const items = byStatus(lane.status);
      return `<div class="lane">
        <h3><span>${lane.title}</span><span class="qty-pill">${items.length}</span></h3>
        <p class="lane-hint">${STATUSES[lane.status].hint}</p>
        <div class="lane-list">${items.map(orderCard).join('') || '<p class="muted">Nothing here. </p>'}</div>
      </div>`;
    })
    .join('');

  html += `<div class="lane">
      <h3><span>Needs attention</span><span class="qty-pill">${problemList.length}</span></h3>
      <p class="lane-hint">Returns, RTO and lost parcels. Close these to keep reports honest.</p>
      <div class="lane-list">${problemList.map(orderCard).join('') || '<p class="muted">All clear.</p>'}</div>
    </div>`;

  $('#lanes').innerHTML = html;
}

function orderCard(o) {
  let buttons = nextStatuses(o.status)
    .map(
      (s) =>
        `<button class="btn ${s === 'CANCELLED' ? 'danger ghost' : 'primary'}" data-act="advance" data-id="${escapeAttr(
          o.id
        )}" data-to="${s}">${STATUSES[s].short}</button>`
    )
    .join('');
  if (RECEIVED_BACK.includes(o.status) && o.restockChecked !== true) {
    buttons += `<button class="btn primary" data-act="restock" data-ok="1" data-id="${escapeAttr(
      o.id
    )}">Stock back on shelf</button>
      <button class="btn danger ghost" data-act="restock" data-ok="0" data-id="${escapeAttr(
        o.id
      )}">Damaged — write off</button>`;
  }
  return `<div class="order-card ${o.platform}">
    <div class="oc-top">
      <span>${PLATFORMS[o.platform]?.label || o.platform} · ${escapeHtml(o.orderId)}</span>
      <span class="qty-pill">x${o.qty}</span>
    </div>
    <div class="oc-sku">${escapeHtml(o.sku)}</div>
    <div class="oc-name">${escapeHtml((o.productName || '').slice(0, 70))}</div>
    <div class="oc-top"><span>AWB: ${escapeHtml(o.awb || '—')}</span><span>${escapeHtml(o.orderDate)}</span></div>
    ${
      RECEIVED_BACK.includes(o.status) || STATUSES[o.status]?.group === 'problem'
        ? `<div class="oc-top"><span>${escapeHtml(STATUSES[o.status].label)}${
            o.reasonCode ? ' · ' + escapeHtml(o.reasonCode) : ''
          }</span></div>`
        : ''
    }
    <div class="oc-actions">${buttons}</div>
  </div>`;
}

document.addEventListener('click', async (e) => {
  const restockBtn = e.target.closest('[data-act="restock"]');
  if (restockBtn) {
    const order = state.orders.find((o) => o.id === restockBtn.dataset.id);
    if (!order) return;
    const ok = restockBtn.dataset.ok === '1';
    let reasonCode = order.reasonCode;
    if (!reasonCode) {
      const picked = await askReason();
      if (picked === null) return;
      reasonCode = picked;
    }
    const updated = {
      ...order,
      reasonCode,
      restockChecked: true,
      stockRecovered: ok,
      updatedAt: new Date().toISOString(),
    };
    await put(STORE_ORDERS, updated);
    await logEvent(order.id, 'restock', ok ? 'stock back on shelf' : 'written off as damaged');
    const i = state.orders.findIndex((o) => o.id === order.id);
    if (i >= 0) state.orders[i] = updated;
    renderPack();
    renderOrders();
    renderReports();
    toast(ok ? `${order.sku} back in stock.` : `${order.sku} written off.`);
    return;
  }

  const btn = e.target.closest('[data-act="advance"]');
  if (!btn) return;
  const order = state.orders.find((o) => o.id === btn.dataset.id);
  if (!order) return;
  const to = btn.dataset.to;
  let extra = {};
  if (STATUSES[to]?.needsReason) {
    const reason = await askReason();
    if (reason === null) return;
    extra.reasonCode = reason;
  }
  await setStatus(order, to, extra);
  renderPack();
  renderOrders();
  renderReports();
  toast(`${order.sku} → ${STATUSES[to].label}`);
});

/* ------------------------------------------------------------------ modal */

function showModal({ title, message, fields = [], confirmLabel = 'OK', danger = false }) {
  return new Promise((resolve) => {
    const back = document.createElement('div');
    back.className = 'modal-back';
    back.innerHTML = `<div class="modal">
      <h2>${escapeHtml(title)}</h2>
      ${message ? `<p class="muted">${escapeHtml(message)}</p>` : ''}
      <div class="modal-fields">${fields.map(fieldHtml).join('')}</div>
      <div class="modal-actions">
        <button class="btn ghost" data-modal="cancel">Cancel</button>
        <button class="btn ${danger ? 'danger' : 'primary'}" data-modal="ok">${escapeHtml(confirmLabel)}</button>
      </div>
    </div>`;
    document.body.appendChild(back);
    const first = back.querySelector('select, input');
    if (first) first.focus();

    const close = (value) => {
      back.remove();
      resolve(value);
    };
    const collect = () => {
      const out = {};
      fields.forEach((f) => {
        out[f.name] = back.querySelector(`[data-name="${f.name}"]`).value.trim();
      });
      return out;
    };
    back.addEventListener('click', (e) => {
      if (e.target === back || e.target.closest('[data-modal="cancel"]')) close(null);
      if (e.target.closest('[data-modal="ok"]')) close(collect());
    });
    back.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') close(null);
      if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') close(collect());
    });
  });
}

function fieldHtml(f) {
  if (f.type === 'select') {
    return `<label>${escapeHtml(f.label)}
      <select data-name="${f.name}">${f.options
      .map((o) => `<option value="${escapeAttr(o)}">${escapeHtml(o)}</option>`)
      .join('')}</select></label>`;
  }
  return `<label>${escapeHtml(f.label)}<input data-name="${f.name}" type="text" value="${escapeAttr(
    f.value || ''
  )}" placeholder="${escapeAttr(f.placeholder || '')}" /></label>`;
}

async function askConfirm(title, message, confirmLabel = 'Yes, do it') {
  const r = await showModal({ title, message, confirmLabel, danger: true });
  return r !== null;
}

async function askReason(title = 'Why did this come back?') {
  const r = await showModal({
    title,
    message: 'Pick the closest reason. This is what the monthly report groups by.',
    confirmLabel: 'Save reason',
    fields: [
      { name: 'reason', type: 'select', label: 'Reason', options: REASON_CODES },
      { name: 'note', type: 'text', label: 'Your note (optional)', placeholder: 'e.g. box crushed at hub' },
    ],
  });
  if (r === null) return null;
  return r.note ? `${r.reason} — ${r.note}` : r.reason;
}

/* ------------------------------------------------------------------- scan */

function findByScan(code) {
  const c = String(code).trim().toLowerCase();
  if (!c) return [];
  const exact = state.orders.filter(
    (o) =>
      (o.awb || '').toLowerCase() === c ||
      (o.orderId || '').toLowerCase() === c ||
      (o.subOrderId || '').toLowerCase() === c
  );
  if (exact.length) return exact;
  return state.orders.filter(
    (o) =>
      (o.awb && o.awb.toLowerCase().includes(c)) ||
      (o.orderId && o.orderId.toLowerCase().includes(c))
  );
}

async function handleScan(code) {
  const box = $('#scanResult');
  const matches = findByScan(code);
  if (!matches.length) {
    box.className = 'scan-result err';
    box.innerHTML = `<strong>Not found:</strong> ${escapeHtml(code)}<br />Import the order file first, or check the barcode.`;
    beep(false);
    return;
  }
  const target = $('#scanTarget').value;
  const done = [];
  for (const o of matches) {
    let to = target;
    if (target === 'AUTO') {
      const nx = nextStatuses(o.status).filter((s) => s !== 'CANCELLED');
      to = nx[0];
      if (!to) {
        done.push(`${o.sku}: already ${STATUSES[o.status].label}`);
        continue;
      }
    }
    if (o.status === to) {
      done.push(`${o.sku}: already ${STATUSES[to].label}`);
      continue;
    }
    await setStatus(o, to);
    done.push(`${o.sku} x${o.qty} → ${STATUSES[to].label}`);
  }
  const first = matches[0];
  box.className = 'scan-result ok';
  box.innerHTML = `<strong>${PLATFORMS[first.platform]?.label} ${escapeHtml(first.orderId)}</strong><br />${done
    .map(escapeHtml)
    .join('<br />')}`;
  beep(true);
  renderPack();
  renderOrders();
  renderReports();
}

function beep(ok) {
  if (!state.settings.scanBeepEnabled) return;
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = ok ? 880 : 220;
    gain.gain.value = 0.08;
    osc.start();
    setTimeout(() => {
      osc.stop();
      ctx.close();
    }, ok ? 110 : 320);
  } catch (_) {
    /* audio blocked, ignore */
  }
}

/* ----------------------------------------------------------- orders table */

function filteredOrders() {
  const q = ($('#orderSearch').value || '').toLowerCase();
  const plat = $('#filterPlatform').value;
  const st = $('#filterStatus').value;
  const from = $('#filterFrom').value;
  const to = $('#filterTo').value;
  return state.orders
    .filter((o) => {
      if (plat && o.platform !== plat) return false;
      if (st && o.status !== st) return false;
      if (from && o.orderDate < from) return false;
      if (to && o.orderDate > to) return false;
      if (!q) return true;
      return [o.orderId, o.subOrderId, o.awb, o.sku, o.productName, o.courier]
        .join(' ')
        .toLowerCase()
        .includes(q);
    })
    .sort((a, b) => (a.orderDate < b.orderDate ? 1 : a.orderDate > b.orderDate ? -1 : 0));
}

function renderOrders() {
  const rows = filteredOrders();
  const pages = Math.max(1, Math.ceil(rows.length / state.pageSize));
  if (state.page >= pages) state.page = pages - 1;
  const slice = rows.slice(state.page * state.pageSize, (state.page + 1) * state.pageSize);

  $('#ordersTable tbody').innerHTML = slice
    .map((o) => {
      const p = computePnl(o, state.skus, state.settings);
      const meta = STATUSES[o.status] || { label: o.status, group: 'other' };
      return `<tr data-id="${escapeAttr(o.id)}">
      <td><input type="checkbox" class="rowsel" ${state.selected.has(o.id) ? 'checked' : ''} /></td>
      <td>${escapeHtml(o.orderDate)}</td>
      <td><span class="pill ${o.platform}">${PLATFORMS[o.platform]?.label || o.platform}</span></td>
      <td>${escapeHtml(o.orderId)}<br /><span class="muted">${escapeHtml(o.awb || '')}</span></td>
      <td>${escapeHtml(o.sku)}</td>
      <td title="${escapeAttr(o.productName || '')}">${escapeHtml((o.productName || '').slice(0, 40))}</td>
      <td class="num">${o.qty}</td>
      <td class="num">${money(o.sellingPrice)}</td>
      <td class="num ${p.profit >= 0 ? 'pos' : 'neg'}">${money(p.profit)}</td>
      <td><span class="pill ${meta.group}">${meta.label}</span></td>
      <td>${escapeHtml(o.reasonCode || '')}</td>
      <td><button class="btn ghost" data-act="del" data-id="${escapeAttr(o.id)}">✕</button></td>
    </tr>`;
    })
    .join('');

  $('#pageInfo').textContent = `Page ${state.page + 1} of ${pages} · ${rows.length} order lines`;
  $('#selCount').textContent = `${state.selected.size} selected`;
}

/* --------------------------------------------------------------- SKU view */

function skuAggregates() {
  const agg = {};
  state.orders.forEach((o) => {
    if (!agg[o.sku]) agg[o.sku] = { sku: o.sku, units: 0, revenue: 0, profit: 0, rto: 0, shipped: 0, title: o.productName };
    const p = computePnl(o, state.skus, state.settings);
    agg[o.sku].units += o.qty;
    agg[o.sku].revenue += p.revenue;
    agg[o.sku].profit += p.profit;
    if (o.status !== 'CANCELLED') agg[o.sku].shipped += 1;
    if (['RTO_IN_TRANSIT', 'RTO_RECEIVED'].includes(o.status)) agg[o.sku].rto += 1;
  });
  return agg;
}

function renderSkus() {
  const agg = skuAggregates();
  const all = new Set([...Object.keys(state.skus), ...Object.keys(agg)]);
  const rows = [...all].sort();
  $('#skuTable tbody').innerHTML = rows
    .map((sku) => {
      const s = state.skus[sku] || {};
      const a = agg[sku] || { units: 0, profit: 0 };
      return `<tr data-sku="${escapeAttr(sku)}">
      <td>${escapeHtml(sku)}</td>
      <td><input class="sku-title" value="${escapeAttr(s.title || a.title || '')}" style="width:260px" /></td>
      <td class="num"><input class="sku-cost num" type="number" step="0.5" value="${s.costPrice ?? ''}" style="width:90px" /></td>
      <td class="num"><input class="sku-pack num" type="number" step="0.5" value="${s.packagingCost ?? ''}" style="width:90px" /></td>
      <td class="num">${a.units}</td>
      <td class="num ${a.profit >= 0 ? 'pos' : 'neg'}">${money(a.profit)}</td>
      <td><button class="btn primary" data-act="save-sku">Save</button></td>
    </tr>`;
    })
    .join('');
}

/* --------------------------------------------------------------- reports */

function periodKey(dateStr, mode) {
  if (mode === 'month') return dateStr.slice(0, 7);
  const d = new Date(`${dateStr}T00:00:00`);
  const day = (d.getDay() + 6) % 7; // Monday = 0
  d.setDate(d.getDate() - day);
  return `Week of ${d.toISOString().slice(0, 10)}`;
}

function renderReports() {
  const mode = $('#reportPeriod').value;
  const plat = $('#reportPlatform').value;
  const orders = state.orders.filter((o) => !plat || o.platform === plat);

  const total = rollup(orders, state.skus, state.settings);
  $('#reportStats').innerHTML = [
    { k: 'Order lines', v: total.orders, cls: '' },
    { k: 'Units', v: total.units, cls: '' },
    { k: 'Revenue booked', v: money(total.revenue), cls: '' },
    { k: 'Delivered revenue', v: money(total.realisedRevenue), cls: 'good' },
    { k: 'Total profit', v: money(total.profit), cls: total.profit >= 0 ? 'good' : 'bad' },
    { k: 'Margin', v: pct(total.marginPct), cls: total.marginPct >= 0 ? 'good' : 'bad' },
    { k: 'RTO rate', v: pct(total.rtoRatePct), cls: total.rtoRatePct > 10 ? 'bad' : 'good' },
    { k: 'Return rate', v: pct(total.returnRatePct), cls: total.returnRatePct > 8 ? 'bad' : 'good' },
    { k: 'Money lost to RTO/returns', v: money(total.lossValue), cls: 'bad' },
  ]
    .map((s) => `<div class="stat ${s.cls}"><div class="k">${s.k}</div><div class="v">${s.v}</div></div>`)
    .join('');

  // by period
  const groups = {};
  orders.forEach((o) => {
    const k = periodKey(o.orderDate, mode);
    (groups[k] = groups[k] || []).push(o);
  });
  const keys = Object.keys(groups).sort().reverse();
  $('#periodTitle').textContent = mode === 'month' ? 'Month by month' : 'Week by week (Mon–Sun)';
  $('#periodTable tbody').innerHTML = keys
    .map((k) => {
      const r = rollup(groups[k], state.skus, state.settings);
      return `<tr>
        <td>${escapeHtml(k)}</td>
        <td class="num">${r.orders}</td>
        <td class="num">${r.units}</td>
        <td class="num">${money(r.revenue)}</td>
        <td class="num">${money(r.commission + r.fixedFee + r.shipping + r.gstOnFees)}</td>
        <td class="num">${money(r.cogs)}</td>
        <td class="num ${r.profit >= 0 ? 'pos' : 'neg'}">${money(r.profit)}</td>
        <td class="num">${pct(r.marginPct)}</td>
        <td class="num">${pct(r.rtoRatePct)}</td>
      </tr>`;
    })
    .join('');

  // by platform
  const platGroups = {};
  state.orders.forEach((o) => (platGroups[o.platform] = platGroups[o.platform] || []).push(o));
  $('#platformTable tbody').innerHTML = Object.keys(platGroups)
    .map((p) => {
      const r = rollup(platGroups[p], state.skus, state.settings);
      return `<tr>
        <td><span class="pill ${p}">${PLATFORMS[p]?.label || p}</span></td>
        <td class="num">${r.orders}</td>
        <td class="num">${money(r.revenue)}</td>
        <td class="num ${r.profit >= 0 ? 'pos' : 'neg'}">${money(r.profit)}</td>
        <td class="num">${pct(r.marginPct)}</td>
        <td class="num">${pct(r.rtoRatePct)}</td>
      </tr>`;
    })
    .join('');

  // by sku
  const agg = skuAggregates();
  $('#skuReportTable tbody').innerHTML = Object.values(agg)
    .sort((a, b) => b.profit - a.profit)
    .map(
      (a) => `<tr>
        <td>${escapeHtml(a.sku)}</td>
        <td class="num">${a.units}</td>
        <td class="num">${money(a.revenue)}</td>
        <td class="num ${a.profit >= 0 ? 'pos' : 'neg'}">${money(a.profit)}</td>
        <td class="num">${pct(a.shipped ? (a.rto / a.shipped) * 100 : 0)}</td>
      </tr>`
    )
    .join('');

  // reasons
  const reasons = {};
  orders.forEach((o) => {
    if (!o.reasonCode) return;
    const p = computePnl(o, state.skus, state.settings);
    if (!reasons[o.reasonCode]) reasons[o.reasonCode] = { count: 0, loss: 0 };
    reasons[o.reasonCode].count += 1;
    if (p.profit < 0) reasons[o.reasonCode].loss += -p.profit;
  });
  const rk = Object.keys(reasons).sort((a, b) => reasons[b].count - reasons[a].count);
  $('#reasonTable tbody').innerHTML =
    rk
      .map(
        (k) =>
          `<tr><td>${escapeHtml(k)}</td><td class="num">${reasons[k].count}</td><td class="num neg">${money(
            reasons[k].loss
          )}</td></tr>`
      )
      .join('') || '<tr><td colspan="3" class="muted">No returns recorded yet. </td></tr>';
}

/* -------------------------------------------------------------- settings */

function renderSettings() {
  $('#setBizName').value = state.settings.businessName || '';
  $('#setPackaging').value = state.settings.defaultPackagingCost ?? 0;
  $('#setBeep').checked = !!state.settings.scanBeepEnabled;

  const fields = [
    ['commissionPct', 'Commission %'],
    ['fixedFee', 'Fixed fee ₹'],
    ['shippingFee', 'Shipping ₹'],
    ['gstOnFeesPct', 'GST on fees %'],
    ['rtoFee', 'RTO charge ₹'],
    ['returnFee', 'Return charge ₹'],
  ];
  $('#feeGrid').innerHTML =
    `<div class="fee-row"><div class="plat"></div>${fields
      .map((f) => `<div class="muted">${f[1]}</div>`)
      .join('')}<div class="muted">Price already net of fees</div></div>` +
    ['amazon', 'flipkart', 'meesho', 'other']
      .map((p) => {
        const f = state.settings.fees[p] || DEFAULT_FEES[p];
        return `<div class="fee-row" data-plat="${p}">
        <div class="plat">${PLATFORMS[p].label}</div>
        ${fields
          .map(
            (fl) =>
              `<input type="number" step="0.1" data-fee="${fl[0]}" value="${f[fl[0]] ?? 0}" />`
          )
          .join('')}
        <label class="chk"><input type="checkbox" data-fee="priceIsNetOfFees" ${
          f.priceIsNetOfFees ? 'checked' : ''
        } /> net</label>
      </div>`;
      })
      .join('');
}

async function saveSettings() {
  const fees = {};
  $$('#feeGrid .fee-row[data-plat]').forEach((row) => {
    const p = row.dataset.plat;
    fees[p] = { ...(state.settings.fees[p] || DEFAULT_FEES[p]) };
    row.querySelectorAll('[data-fee]').forEach((inp) => {
      const key = inp.dataset.fee;
      fees[p][key] = inp.type === 'checkbox' ? inp.checked : Number(inp.value) || 0;
    });
  });
  await setSetting('fees', fees);
  await setSetting('businessName', $('#setBizName').value.trim() || 'SanskaTots');
  await setSetting('defaultPackagingCost', Number($('#setPackaging').value) || 0);
  await setSetting('scanBeepEnabled', $('#setBeep').checked);
  await loadAll();
  renderAll();
  $('#settingsMsg').textContent = 'Saved.';
  setTimeout(() => ($('#settingsMsg').textContent = ''), 2500);
}

/* --------------------------------------------------------------- import */

async function stageFiles(files) {
  const file = files[0];
  const text = await file.text();
  const rows = parseDelimited(text);
  const { headers, records } = toObjects(rows);
  if (!headers.length || !records.length) {
    toast('That file has no readable rows.');
    return;
  }
  const platform = detectPlatform(headers, file.name);
  state.pending = { headers, records, platform, map: autoMap(headers, platform), fileName: file.name, queue: [...files].slice(1) };
  $('#mapPlatform').value = platform;
  $('#mapFileName').textContent = `${file.name} · ${records.length} rows · detected ${PLATFORMS[platform].label}`;
  $('#mapCard').classList.remove('hidden');
  renderMapping();
}

function renderMapping() {
  const { headers, map } = state.pending;
  $('#mapGrid').innerHTML = LOGICAL_FIELDS.map((f) => {
    const req = REQUIRED_FIELDS.includes(f);
    return `<div class="${req ? 'req' : ''}">
      <label>${humanField(f)}${req ? ' *' : ''}
        <select data-field="${f}">
          <option value="">— not in file —</option>
          ${headers
            .map(
              (h) =>
                `<option value="${escapeAttr(h)}" ${map[f] === h ? 'selected' : ''}>${escapeHtml(h)}</option>`
            )
            .join('')}
        </select>
      </label>
    </div>`;
  }).join('');
  renderPreview();
}

function humanField(f) {
  return (
    {
      orderId: 'Order ID',
      subOrderId: 'Sub-order / item ID',
      orderDate: 'Order date',
      sku: 'SKU',
      productName: 'Product name',
      qty: 'Quantity',
      sellingPrice: 'Price you receive',
      platformStatus: 'Platform status',
      awb: 'AWB / tracking ID',
      courier: 'Courier',
      customerState: 'Customer state',
      customerPincode: 'Pincode',
    }[f] || f
  );
}

function renderPreview() {
  const { records, platform, map } = state.pending;
  const orders = recordsToOrders(records.slice(0, 8), platform, map);
  const cols = ['orderDate', 'orderId', 'sku', 'productName', 'qty', 'sellingPrice', 'awb', 'status'];
  $('#previewTable thead').innerHTML = `<tr>${cols.map((c) => `<th>${humanField(c) || c}</th>`).join('')}</tr>`;
  $('#previewTable tbody').innerHTML = orders
    .map((o) => `<tr>${cols.map((c) => `<td>${escapeHtml(String(o[c] ?? '').slice(0, 40))}</td>`).join('')}</tr>`)
    .join('');
}

async function confirmImport() {
  const { records, platform, map } = state.pending;
  const missing = REQUIRED_FIELDS.filter((f) => !map[f]);
  if (missing.length) {
    toast(`Please map: ${missing.map(humanField).join(', ')}`);
    return;
  }
  const incoming = recordsToOrders(records, platform, map);
  const existing = new Map(state.orders.map((o) => [o.id, o]));
  let added = 0;
  let updated = 0;
  const merged = incoming.map((o) => {
    const prev = existing.get(o.id);
    if (!prev) {
      added += 1;
      return { ...o, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
    }
    updated += 1;
    // Never rewind manual packing progress with a stale file.
    const keepManual = STATUS_ORDER.indexOf(prev.status) > STATUS_ORDER.indexOf(o.status);
    return {
      ...prev,
      productName: o.productName || prev.productName,
      sellingPrice: o.sellingPrice || prev.sellingPrice,
      awb: o.awb || prev.awb,
      courier: o.courier || prev.courier,
      customerState: o.customerState || prev.customerState,
      customerPincode: o.customerPincode || prev.customerPincode,
      platformStatus: o.platformStatus || prev.platformStatus,
      status: keepManual ? prev.status : o.status,
      updatedAt: new Date().toISOString(),
    };
  });
  await putMany(STORE_ORDERS, merged);
  await logEvent('-', 'import', `${platform}: ${added} new, ${updated} updated`);
  const queue = state.pending.queue || [];
  $('#importMsg').textContent = `Imported: ${added} new, ${updated} updated.`;
  state.pending = null;
  $('#mapCard').classList.add('hidden');
  await loadAll();
  renderAll();
  toast(`${added} new orders added, ${updated} updated.`);
  if (queue.length) await stageFiles(queue);
}

/* -------------------------------------------------------------- download */

function download(name, content, type = 'text/csv;charset=utf-8;') {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1500);
}

function ordersToRows(orders) {
  return orders.map((o) => {
    const p = computePnl(o, state.skus, state.settings);
    return {
      order_date: o.orderDate,
      platform: o.platform,
      order_id: o.orderId,
      sub_order_id: o.subOrderId || '',
      sku: o.sku,
      product: o.productName || '',
      qty: o.qty,
      price: round2(o.sellingPrice),
      commission: round2(p.commission),
      fixed_fee: round2(p.fixedFee),
      shipping: round2(p.shipping),
      gst_on_fees: round2(p.gstOnFees),
      cost_of_goods: round2(p.cogs),
      profit: round2(p.profit),
      money_state: p.state,
      status: o.status,
      status_label: STATUSES[o.status]?.label || o.status,
      reason: o.reasonCode || '',
      stock_back_on_shelf: RECEIVED_BACK.includes(o.status) ? (o.restockChecked ? (o.stockRecovered ? 'yes' : 'written off') : 'not checked') : '',
      awb: o.awb || '',
      courier: o.courier || '',
      customer_state: o.customerState || '',
      packed_at: o.packedAt || '',
      handed_over_at: o.handedOverAt || '',
    };
  });
}

const round2 = (v) => Math.round((v || 0) * 100) / 100;

/* ------------------------------------------------------------------ misc */

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
const escapeAttr = escapeHtml;

function refreshSkuDatalist() {
  $('#skuList').innerHTML = Object.keys(state.skus)
    .map((s) => `<option value="${escapeAttr(s)}"></option>`)
    .join('');
}

function fillSelect(sel, options, includeBlank, blankLabel) {
  sel.innerHTML =
    (includeBlank ? `<option value="">${blankLabel}</option>` : '') +
    options.map((o) => `<option value="${o[0]}">${o[1]}</option>`).join('');
}

/* ------------------------------------------------------------------ wire */

function wire() {
  $$('.tab').forEach((t) =>
    t.addEventListener('click', () => {
      $$('.tab').forEach((x) => x.classList.remove('active'));
      $$('.panel').forEach((x) => x.classList.remove('active'));
      t.classList.add('active');
      $(`#tab-${t.dataset.tab}`).classList.add('active');
      if (t.dataset.tab === 'pack') $('#scanInput').focus();
    })
  );

  // scan
  const scan = $('#scanInput');
  scan.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter') return;
    e.preventDefault();
    const code = scan.value;
    scan.value = '';
    if (code.trim()) handleScan(code);
  });
  scan.focus();

  ['#packSearch', '#packPlatform', '#packShowAll'].forEach((s) =>
    $(s).addEventListener('input', renderPack)
  );
  $('#printPickList').addEventListener('click', printPickList);

  // orders
  const statusOpts = STATUS_ORDER.map((s) => [s, STATUSES[s].label]);
  fillSelect($('#filterStatus'), statusOpts, true, 'All statuses');
  fillSelect($('#bulkStatus'), statusOpts, true, 'Change status to…');
  fillSelect(
    $('#bulkReason'),
    REASON_CODES.map((r) => [r, r]),
    true,
    'Reason (optional)'
  );
  ['#orderSearch', '#filterPlatform', '#filterStatus', '#filterFrom', '#filterTo'].forEach((s) =>
    $(s).addEventListener('input', () => {
      state.page = 0;
      renderOrders();
    })
  );
  $('#clearFilters').addEventListener('click', () => {
    ['#orderSearch', '#filterPlatform', '#filterStatus', '#filterFrom', '#filterTo'].forEach(
      (s) => ($(s).value = '')
    );
    state.page = 0;
    renderOrders();
  });
  $('#prevPage').addEventListener('click', () => {
    if (state.page > 0) {
      state.page -= 1;
      renderOrders();
    }
  });
  $('#nextPage').addEventListener('click', () => {
    state.page += 1;
    renderOrders();
  });
  $('#ordersTable').addEventListener('change', (e) => {
    const cb = e.target.closest('.rowsel');
    if (!cb) return;
    const id = cb.closest('tr').dataset.id;
    if (cb.checked) state.selected.add(id);
    else state.selected.delete(id);
    $('#selCount').textContent = `${state.selected.size} selected`;
  });
  $('#selAll').addEventListener('change', (e) => {
    const rows = filteredOrders().slice(state.page * state.pageSize, (state.page + 1) * state.pageSize);
    rows.forEach((o) => (e.target.checked ? state.selected.add(o.id) : state.selected.delete(o.id)));
    renderOrders();
  });
  $('#applyBulk').addEventListener('click', async () => {
    const to = $('#bulkStatus').value;
    if (!to || !state.selected.size) return toast('Pick orders and a status first.');
    const reason = $('#bulkReason').value;
    for (const id of state.selected) {
      const o = state.orders.find((x) => x.id === id);
      if (o) await setStatus(o, to, reason ? { reasonCode: reason } : {});
    }
    toast(`${state.selected.size} orders updated.`);
    state.selected.clear();
    renderPack();
    renderOrders();
    renderReports();
  });
  $('#deleteSelected').addEventListener('click', async () => {
    if (!state.selected.size) return;
    if (!(await askConfirm('Delete selected orders?', `${state.selected.size} order lines will be removed. This cannot be undone.`, 'Delete')))
      return;
    for (const id of state.selected) await del(STORE_ORDERS, id);
    state.selected.clear();
    await loadAll();
    renderAll();
    toast('Deleted.');
  });
  $('#ordersTable').addEventListener('click', async (e) => {
    const b = e.target.closest('[data-act="del"]');
    if (!b) return;
    if (!(await askConfirm('Delete this order line?', 'It will be removed from every report.', 'Delete'))) return;
    await del(STORE_ORDERS, b.dataset.id);
    await loadAll();
    renderAll();
  });
  $('#exportOrders').addEventListener('click', () =>
    download(`orders_${todayISO()}.csv`, toCsv(ordersToRows(filteredOrders())))
  );

  // import
  const dz = $('#dropZone');
  $('#browseBtn').addEventListener('click', () => $('#fileInput').click());
  $('#fileInput').addEventListener('change', (e) => e.target.files.length && stageFiles([...e.target.files]));
  ['dragenter', 'dragover'].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.add('drag');
    })
  );
  ['dragleave', 'drop'].forEach((ev) =>
    dz.addEventListener(ev, (e) => {
      e.preventDefault();
      dz.classList.remove('drag');
    })
  );
  dz.addEventListener('drop', (e) => {
    const files = [...(e.dataTransfer?.files || [])];
    if (files.length) stageFiles(files);
  });
  $('#mapGrid').addEventListener('change', (e) => {
    const sel = e.target.closest('[data-field]');
    if (!sel || !state.pending) return;
    state.pending.map[sel.dataset.field] = sel.value;
    renderPreview();
  });
  $('#mapPlatform').addEventListener('change', (e) => {
    if (!state.pending) return;
    state.pending.platform = e.target.value;
    state.pending.map = autoMap(state.pending.headers, e.target.value);
    renderMapping();
  });
  $('#confirmImport').addEventListener('click', confirmImport);
  $('#cancelImport').addEventListener('click', () => {
    state.pending = null;
    $('#mapCard').classList.add('hidden');
  });
  $('#addManual').addEventListener('click', addManualOrder);

  // skus
  $('#skuTable').addEventListener('click', async (e) => {
    const b = e.target.closest('[data-act="save-sku"]');
    if (!b) return;
    const tr = b.closest('tr');
    const sku = tr.dataset.sku;
    await put(STORE_SKUS, {
      sku,
      title: tr.querySelector('.sku-title').value.trim(),
      costPrice: Number(tr.querySelector('.sku-cost').value) || 0,
      packagingCost: tr.querySelector('.sku-pack').value === '' ? undefined : Number(tr.querySelector('.sku-pack').value),
    });
    await loadAll();
    renderSkus();
    renderOrders();
    renderReports();
    toast(`${sku} saved.`);
  });
  $('#pullSkus').addEventListener('click', async () => {
    const found = [...new Set(state.orders.map((o) => o.sku))];
    const rows = found
      .filter((s) => !state.skus[s])
      .map((s) => ({
        sku: s,
        title: (state.orders.find((o) => o.sku === s) || {}).productName || '',
        costPrice: 0,
      }));
    if (!rows.length) return toast('All SKUs are already in the list.');
    await putMany(STORE_SKUS, rows);
    await loadAll();
    renderSkus();
    refreshSkuDatalist();
    toast(`${rows.length} new SKUs added. Now fill their cost price.`);
  });
  $('#exportSkus').addEventListener('click', () =>
    download(
      `sku_costs_${todayISO()}.csv`,
      toCsv(
        Object.values(state.skus).map((s) => ({
          sku: s.sku,
          title: s.title || '',
          costPrice: s.costPrice ?? 0,
          packagingCost: s.packagingCost ?? '',
        })),
        ['sku', 'title', 'costPrice', 'packagingCost']
      )
    )
  );
  $('#importSkusBtn').addEventListener('click', () => $('#importSkusFile').click());
  $('#importSkusFile').addEventListener('change', async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const { records } = toObjects(parseDelimited(await f.text()));
    const rows = records
      .filter((r) => r.sku)
      .map((r) => ({
        sku: String(r.sku).trim(),
        title: r.title || '',
        costPrice: Number(r.costPrice) || 0,
        packagingCost: r.packagingCost === '' || r.packagingCost === undefined ? undefined : Number(r.packagingCost),
      }));
    await putMany(STORE_SKUS, rows);
    await loadAll();
    renderAll();
    toast(`${rows.length} SKU costs loaded.`);
    e.target.value = '';
  });

  // reports
  $('#reportPeriod').addEventListener('change', renderReports);
  $('#reportPlatform').addEventListener('change', renderReports);
  $('#printReport').addEventListener('click', () => window.print());
  $('#exportReport').addEventListener('click', exportReport);

  // settings
  $('#saveSettings').addEventListener('click', saveSettings);
  $('#backupJson').addEventListener('click', async () => {
    const backup = {
      exportedAt: new Date().toISOString(),
      version: 1,
      orders: state.orders,
      skus: Object.values(state.skus),
      settings: state.settings,
    };
    download(`occ_backup_${todayISO()}.json`, JSON.stringify(backup, null, 2), 'application/json');
    await setSetting('lastBackupAt', new Date().toISOString());
    $('#backupMsg').textContent = `Backup taken on ${new Date().toLocaleString('en-IN')}.`;
  });
  $('#exportAllCsv').addEventListener('click', () =>
    download(`all_orders_${todayISO()}.csv`, toCsv(ordersToRows(state.orders)))
  );
  $('#restoreBtn').addEventListener('click', () => $('#restoreFile').click());
  $('#restoreFile').addEventListener('change', async (e) => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      if (!Array.isArray(data.orders)) throw new Error('Not a valid backup file');
      if (
        !(await askConfirm(
          'Restore this backup?',
          `${data.orders.length} orders will be loaded. Orders with the same ID will be overwritten.`,
          'Restore'
        ))
      )
        return;
      await putMany(STORE_ORDERS, data.orders);
      if (Array.isArray(data.skus) && data.skus.length) await putMany(STORE_SKUS, data.skus);
      if (data.settings) {
        for (const [k, v] of Object.entries(data.settings)) await setSetting(k, v);
      }
      await loadAll();
      renderAll();
      toast('Backup restored.');
    } catch (err) {
      await showModal({ title: 'Could not restore', message: err.message, confirmLabel: 'Close' });
    }
    e.target.value = '';
  });
  $('#wipeData').addEventListener('click', async () => {
    const r = await showModal({
      title: 'Delete everything?',
      message: 'This wipes every order, SKU cost and setting stored on this computer. Take a backup first.',
      confirmLabel: 'Delete everything',
      danger: true,
      fields: [{ name: 'confirm', type: 'text', label: 'Type DELETE to confirm', placeholder: 'DELETE' }],
    });
    if (!r || r.confirm !== 'DELETE') return;
    await Promise.all([
      clearStore(STORE_ORDERS),
      clearStore(STORE_SKUS),
      clearStore(STORE_SETTINGS),
      clearStore(STORE_EVENTS),
    ]);
    await loadAll();
    renderAll();
    toast('All data deleted.');
  });

  $('#mDate').value = todayISO();

  if (typeof chrome !== 'undefined' && chrome.runtime?.onMessage) {
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg?.type === 'orders-updated') {
        loadAll().then(() => {
          renderAll();
          toast(`${msg.count} orders captured from ${PLATFORMS[msg.platform]?.label || msg.platform}.`);
        });
      }
    });
  }
}

async function addManualOrder() {
  const platform = $('#mOrderPlatform').value;
  const orderId = $('#mOrderId').value.trim();
  const sku = $('#mSku').value.trim();
  if (!orderId || !sku) return toast('Order ID and SKU are needed.');
  const order = {
    id: makeOrderKey(platform, orderId, '', sku),
    platform,
    orderId,
    subOrderId: '',
    orderDate: $('#mDate').value || todayISO(),
    sku,
    productName: state.skus[sku]?.title || '',
    qty: Number($('#mQty').value) || 1,
    sellingPrice: Number($('#mPrice').value) || 0,
    awb: $('#mAwb').value.trim(),
    courier: '',
    status: 'NEW',
    platformStatus: 'Manual entry',
    reasonCode: '',
    stockRecovered: true,
    source: 'manual',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
  await put(STORE_ORDERS, order);
  await loadAll();
  renderAll();
  ['#mOrderId', '#mSku', '#mPrice', '#mAwb'].forEach((s) => ($(s).value = ''));
  $('#mQty').value = 1;
  toast('Order added.');
}

function printPickList() {
  const items = actionableOrders().filter((o) => ['NEW', 'LABEL_PRINTED'].includes(o.status));
  if (!items.length) return toast('Nothing to pick right now.');
  const bySku = {};
  items.forEach((o) => {
    bySku[o.sku] = bySku[o.sku] || { sku: o.sku, name: o.productName, qty: 0, orders: [] };
    bySku[o.sku].qty += o.qty;
    bySku[o.sku].orders.push(`${PLATFORMS[o.platform]?.label}: ${o.orderId}`);
  });
  const rows = Object.values(bySku)
    .sort((a, b) => b.qty - a.qty)
    .map(
      (r) =>
        `<tr><td>${escapeHtml(r.sku)}</td><td>${escapeHtml(r.name || '')}</td><td style="text-align:right;font-size:18px"><strong>${r.qty}</strong></td><td>${escapeHtml(
          r.orders.join(', ')
        )}</td></tr>`
    )
    .join('');
  const w = window.open('', '_blank');
  w.document.write(`<html><head><title>Pick list ${todayISO()}</title>
    <style>body{font-family:sans-serif;padding:24px}h1{font-size:18px}table{border-collapse:collapse;width:100%}
    td,th{border:1px solid #ccc;padding:8px;font-size:13px;text-align:left}th{background:#eee}</style></head>
    <body><h1>${escapeHtml(state.settings.businessName)} — pick list ${todayISO()}</h1>
    <p>${items.length} order lines · ${Object.keys(bySku).length} SKUs</p>
    <table><thead><tr><th>SKU</th><th>Product</th><th>Total qty</th><th>Orders</th></tr></thead><tbody>${rows}</tbody></table>
    </body></html>`);
  w.document.close();
  w.print();
}

function exportReport() {
  const mode = $('#reportPeriod').value;
  const plat = $('#reportPlatform').value;
  const orders = state.orders.filter((o) => !plat || o.platform === plat);
  const groups = {};
  orders.forEach((o) => {
    const k = periodKey(o.orderDate, mode);
    (groups[k] = groups[k] || []).push(o);
  });
  const rows = Object.keys(groups)
    .sort()
    .reverse()
    .map((k) => {
      const r = rollup(groups[k], state.skus, state.settings);
      return {
        period: k,
        orders: r.orders,
        units: r.units,
        revenue: round2(r.revenue),
        delivered_revenue: round2(r.realisedRevenue),
        platform_fees: round2(r.commission + r.fixedFee + r.shipping + r.gstOnFees),
        cost_of_goods: round2(r.cogs),
        profit: round2(r.profit),
        margin_pct: round2(r.marginPct),
        rto_pct: round2(r.rtoRatePct),
        return_pct: round2(r.returnRatePct),
        money_lost: round2(r.lossValue),
      };
    });
  download(`report_${mode}_${plat || 'all'}_${todayISO()}.csv`, toCsv(rows));
}

/* ------------------------------------------------------------------ boot */

(async function init() {
  wire();
  await loadAll();
  renderAll();
})();
