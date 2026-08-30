import { STORE_ORDERS, getAll, putMany, logEvent } from './lib/db.js';
import { autoMap, recordsToOrders } from './lib/csv.js';
import { STATUS_ORDER } from './lib/model.js';

const DASHBOARD = 'src/dashboard/index.html';

function openDashboard() {
  const url = chrome.runtime.getURL(DASHBOARD);
  chrome.tabs.query({ url }, (tabs) => {
    if (tabs && tabs.length) chrome.tabs.update(tabs[0].id, { active: true });
    else chrome.tabs.create({ url });
  });
}

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === 'install') openDashboard();
});

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg?.type === 'open-dashboard') {
    openDashboard();
    sendResponse({ ok: true });
    return false;
  }
  if (msg?.type === 'grabbed-orders') {
    handleGrab(msg)
      .then(sendResponse)
      .catch((e) => sendResponse({ ok: false, error: e.message }));
    return true; // async
  }
  return false;
});

async function handleGrab({ platform, headers, rows }) {
  const records = rows.map((r) => {
    const o = {};
    headers.forEach((h, i) => {
      o[h] = r[i] === undefined ? '' : r[i];
    });
    return o;
  });
  const map = autoMap(headers, platform);
  if (!map.orderId || !map.sku) {
    return { ok: false, error: 'Could not find Order ID / SKU columns on this page.' };
  }
  const incoming = recordsToOrders(records, platform, map).map((o) => ({ ...o, source: 'page-grab' }));
  if (!incoming.length) return { ok: false, error: 'No order rows recognised.' };

  const existing = new Map((await getAll(STORE_ORDERS)).map((o) => [o.id, o]));
  let added = 0;
  let updated = 0;
  const now = new Date().toISOString();
  const merged = incoming.map((o) => {
    const prev = existing.get(o.id);
    if (!prev) {
      added += 1;
      return { ...o, createdAt: now, updatedAt: now };
    }
    updated += 1;
    const keepManual = STATUS_ORDER.indexOf(prev.status) > STATUS_ORDER.indexOf(o.status);
    return {
      ...prev,
      productName: o.productName || prev.productName,
      sellingPrice: o.sellingPrice || prev.sellingPrice,
      awb: o.awb || prev.awb,
      courier: o.courier || prev.courier,
      platformStatus: o.platformStatus || prev.platformStatus,
      status: keepManual ? prev.status : o.status,
      updatedAt: now,
    };
  });
  await putMany(STORE_ORDERS, merged);
  await logEvent('-', 'grab', `${platform}: ${added} new, ${updated} updated`);
  chrome.runtime.sendMessage({ type: 'orders-updated', platform, count: merged.length }).catch(() => {});
  return { ok: true, added, updated };
}

chrome.action?.onClicked?.addListener(openDashboard);
