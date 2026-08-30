import { STORE_ORDERS, getAll, getSettings } from '../lib/db.js';
import { STATUSES, rollup } from '../lib/model.js';

const $ = (s) => document.querySelector(s);

(async function () {
  $('#open').addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'open-dashboard' });
    window.close();
  });

  const orders = (await getAll(STORE_ORDERS)) || [];
  const settings = await getSettings();
  const count = (fn) => orders.filter(fn).length;

  $('#cNew').textContent = count((o) => o.status === 'NEW');
  $('#cPack').textContent = count((o) => o.status === 'LABEL_PRINTED');
  $('#cReady').textContent = count((o) => o.status === 'PACKED');
  $('#cProblem').textContent = count((o) => STATUSES[o.status]?.group === 'problem');

  const today = new Date().toISOString().slice(0, 10);
  const todays = orders.filter((o) => o.orderDate === today);
  const r = rollup(todays, {}, settings);
  $('#today').textContent = `Today: ${todays.length} order lines, ₹${Math.round(r.revenue).toLocaleString('en-IN')} booked.`;

  const last = settings.lastBackupAt ? new Date(settings.lastBackupAt) : null;
  const days = last ? Math.floor((Date.now() - last.getTime()) / 86400000) : null;
  if (orders.length && (days === null || days >= 7)) {
    $('#backupHint').textContent = last
      ? `Last backup was ${days} days ago. Take one from Settings.`
      : 'No backup taken yet. Take one from Settings.';
  }
})();
