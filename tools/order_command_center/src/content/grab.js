// Floating "Grab orders" button on the three seller panels.
// It reads the order table that is already rendered on screen and hands the raw
// rows to the extension. Panels change their markup often, so this is a helper --
// the CSV import is the dependable path.

(function () {
  if (window.__occGrabInjected) return;
  window.__occGrabInjected = true;

  const HOSTS = {
    'sellercentral.amazon.in': 'amazon',
    'seller.flipkart.com': 'flipkart',
    'supplier.meesho.com': 'meesho',
  };
  const platform = HOSTS[location.hostname] || 'other';

  const bar = document.createElement('div');
  bar.className = 'occ-bar';
  bar.innerHTML = `
    <button class="occ-btn" id="occGrab">Grab orders from this page</button>
    <button class="occ-btn occ-ghost" id="occOpen">Open dashboard</button>
    <span class="occ-msg" id="occMsg"></span>
    <button class="occ-x" id="occHide" title="Hide">×</button>`;
  document.documentElement.appendChild(bar);

  const msg = (text, ok) => {
    const el = bar.querySelector('#occMsg');
    el.textContent = text;
    el.className = `occ-msg ${ok === true ? 'ok' : ok === false ? 'err' : ''}`;
  };

  bar.querySelector('#occHide').addEventListener('click', () => bar.remove());
  bar.querySelector('#occOpen').addEventListener('click', () =>
    chrome.runtime.sendMessage({ type: 'open-dashboard' })
  );
  bar.querySelector('#occGrab').addEventListener('click', grab);

  function bestTable() {
    const tables = [...document.querySelectorAll('table')];
    let best = null;
    let bestScore = 0;
    tables.forEach((t) => {
      const rows = t.querySelectorAll('tr').length;
      const cols = t.querySelector('tr') ? t.querySelector('tr').children.length : 0;
      const score = rows * cols;
      if (rows > 1 && cols > 1 && score > bestScore) {
        best = t;
        bestScore = score;
      }
    });
    return best;
  }

  function readTable(table) {
    const trs = [...table.querySelectorAll('tr')];
    const cells = (tr) => [...tr.children].map((td) => td.innerText.replace(/\s+/g, ' ').trim());
    const headerRow = trs.find((tr) => tr.querySelector('th')) || trs[0];
    const headers = cells(headerRow);
    const rows = trs
      .filter((tr) => tr !== headerRow)
      .map(cells)
      .filter((r) => r.some((c) => c !== ''));
    return { headers, rows };
  }

  function grab() {
    const table = bestTable();
    if (!table) {
      msg('No order table found on this page. Use the CSV import instead.', false);
      return;
    }
    const { headers, rows } = readTable(table);
    if (!rows.length) {
      msg('Table is empty. Scroll the orders into view and try again.', false);
      return;
    }
    msg('Sending…');
    chrome.runtime.sendMessage({ type: 'grabbed-orders', platform, headers, rows }, (res) => {
      if (chrome.runtime.lastError) {
        msg('Extension not reachable. Reload the page.', false);
        return;
      }
      if (!res || !res.ok) {
        msg(res?.error || 'Could not read these rows. Use CSV import.', false);
        return;
      }
      msg(`${res.added} new, ${res.updated} updated. Open the dashboard to pack them.`, true);
    });
  }
})();
