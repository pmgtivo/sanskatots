// CSV reading, header auto-mapping for Amazon / Flipkart / Meesho, and CSV writing.

import { makeOrderKey } from './model.js';

/** RFC4180-ish parser that also copes with tab-separated exports. */
export function parseDelimited(text) {
  const clean = text.replace(/^\uFEFF/, '');
  const delimiter = guessDelimiter(clean);
  const rows = [];
  let row = [];
  let field = '';
  let inQuotes = false;

  for (let i = 0; i < clean.length; i += 1) {
    const ch = clean[i];
    if (inQuotes) {
      if (ch === '"') {
        if (clean[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }
    if (ch === '"') {
      inQuotes = true;
    } else if (ch === delimiter) {
      row.push(field);
      field = '';
    } else if (ch === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (ch === '\r') {
      // handled by \n
    } else {
      field += ch;
    }
  }
  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => String(c).trim() !== ''));
}

function guessDelimiter(text) {
  const head = text.slice(0, 5000);
  const counts = { ',': 0, '\t': 0, ';': 0 };
  let inQuotes = false;
  for (const ch of head) {
    if (ch === '"') inQuotes = !inQuotes;
    else if (!inQuotes && counts[ch] !== undefined) counts[ch] += 1;
  }
  return Object.keys(counts).reduce((a, b) => (counts[a] >= counts[b] ? a : b));
}

export function toObjects(rows) {
  if (!rows.length) return { headers: [], records: [] };
  const headers = rows[0].map((h) => String(h).trim());
  const records = rows.slice(1).map((r) => {
    const o = {};
    headers.forEach((h, i) => {
      o[h] = r[i] === undefined ? '' : String(r[i]).trim();
    });
    return o;
  });
  return { headers, records };
}

const norm = (s) => String(s || '').toLowerCase().replace(/[^a-z0-9]/g, '');

// Candidate header names per logical field, per platform. First match wins.
const FIELD_MAP = {
  amazon: {
    orderId: ['order-id', 'amazon-order-id', 'order id'],
    subOrderId: ['order-item-id', 'shipment-item-id'],
    orderDate: ['purchase-date', 'payments-date', 'order date', 'purchase date'],
    sku: ['sku', 'seller-sku', 'merchant-sku'],
    productName: ['product-name', 'item-name', 'title'],
    qty: ['quantity-purchased', 'quantity', 'quantity-shipped', 'qty'],
    sellingPrice: ['item-price', 'item price', 'product sales', 'principal amount', 'price'],
    platformStatus: ['order-status', 'item-status', 'order status'],
    awb: ['tracking-id', 'tracking id', 'tracking-number'],
    courier: ['carrier', 'ship-service-level', 'carrier name'],
    customerState: ['ship-state', 'shipping-state', 'ship state'],
    customerPincode: ['ship-postal-code', 'shipping-postal-code'],
  },
  flipkart: {
    orderId: ['order id', 'order_id', 'orderid'],
    subOrderId: ['order item id', 'order_item_id', 'orderitemid'],
    orderDate: ['ordered on', 'order date', 'order_date', 'order approval date'],
    sku: ['sku', 'sku id', 'seller sku', 'sku code'],
    productName: ['product', 'product title', 'product name', 'title'],
    qty: ['quantity', 'qty', 'item quantity'],
    sellingPrice: [
      'final selling price (incl. commission and fee)',
      'selling price per item',
      'selling price',
      'final selling price',
      'invoice amount',
      'order item value',
    ],
    platformStatus: ['order status', 'event type', 'status', 'order item status'],
    awb: ['tracking id', 'shipment tracking id', 'awb', 'tracking_id'],
    courier: ['courier partner', 'logistics partner', 'courier'],
    customerState: ['customer state', 'state', 'buyer state'],
    customerPincode: ['pincode', 'customer pincode', 'delivery pincode'],
  },
  meesho: {
    orderId: ['order no', 'order number', 'order id', 'sub order no'],
    subOrderId: ['sub order no', 'suborder no', 'sub_order_no'],
    orderDate: ['order date', 'order_date', 'date of order', 'dispatch date'],
    sku: ['sku', 'sku id', 'supplier sku'],
    productName: ['product name', 'product_name', 'catalog name', 'product'],
    qty: ['quantity', 'qty'],
    sellingPrice: [
      'supplier discounted price (incl gst and commision)',
      'supplier discounted price (incl gst and commission)',
      'supplier discounted price',
      'final settlement amount',
      'listed price (incl. gst + commission)',
      'transaction amount',
      'price',
    ],
    platformStatus: ['reason for credit entry', 'order status', 'sub order status', 'live order status', 'status'],
    awb: ['awb number', 'awb', 'awb no', 'tracking id'],
    courier: ['courier partner', 'shipping partner', 'courier'],
    customerState: ['customer state', 'state', 'end customer state name'],
    customerPincode: ['pincode', 'customer pincode'],
  },
};
FIELD_MAP.other = FIELD_MAP.flipkart;

export const LOGICAL_FIELDS = [
  'orderId',
  'subOrderId',
  'orderDate',
  'sku',
  'productName',
  'qty',
  'sellingPrice',
  'platformStatus',
  'awb',
  'courier',
  'customerState',
  'customerPincode',
];

export const REQUIRED_FIELDS = ['orderId', 'sku', 'qty', 'sellingPrice'];

export function detectPlatform(headers, fileName) {
  const h = headers.map(norm);
  const raw = headers.map((x) => String(x).trim().toLowerCase());
  const has = (name) => h.includes(norm(name));
  // Amazon's hyphenated headers collide with Flipkart's spaced ones once
  // normalised ("order-id" vs "Order ID"), so match Amazon on the raw text.
  const hasRaw = (name) => raw.includes(name);
  if (has('sub order no') || has('reason for credit entry') || has('supplier discounted price')) return 'meesho';
  if (hasRaw('order-id') || hasRaw('amazon-order-id') || hasRaw('quantity-purchased') || hasRaw('purchase-date'))
    return 'amazon';
  if (has('order item id') || has('ordered on') || has('fsn')) return 'flipkart';
  const f = norm(fileName || '');
  if (f.includes('meesho')) return 'meesho';
  if (f.includes('amazon')) return 'amazon';
  if (f.includes('flipkart')) return 'flipkart';
  return 'other';
}

/** Returns { field: headerName } best guess for the given platform. */
export function autoMap(headers, platform) {
  const dict = FIELD_MAP[platform] || FIELD_MAP.other;
  const byNorm = {};
  headers.forEach((h) => {
    byNorm[norm(h)] = h;
  });
  const map = {};
  LOGICAL_FIELDS.forEach((field) => {
    const candidates = dict[field] || [];
    for (const c of candidates) {
      if (byNorm[norm(c)]) {
        map[field] = byNorm[norm(c)];
        break;
      }
    }
    if (!map[field]) {
      // loose contains-match as a fallback
      const target = norm(field);
      const hit = headers.find((h) => norm(h) === target || norm(h).includes(target));
      if (hit) map[field] = hit;
    }
  });
  return map;
}

const STATUS_TEXT_MAP = [
  [/cancel/i, 'CANCELLED'],
  // "Unshipped" contains "shipped", so it has to be checked first.
  [/unshipped|not shipped|yet to ship|pending pickup/i, 'NEW'],
  [/rto[_ -]?(complete|delivered|received)/i, 'RTO_RECEIVED'],
  [/rto|return to origin|undelivered/i, 'RTO_IN_TRANSIT'],
  [/exchange/i, 'EXCHANGE_REQUESTED'],
  [/return[_ -]?(complete|received|delivered|to seller)/i, 'RETURN_RECEIVED'],
  [/return|refund/i, 'RETURN_REQUESTED'],
  [/lost|damaged/i, 'LOST'],
  [/deliver/i, 'DELIVERED'],
  [/out for delivery|in transit|intransit|shipped|dispatch/i, 'IN_TRANSIT'],
  [/handed|manifest|picked up|pickup complete/i, 'HANDED_OVER'],
  [/ready to ship|rts|packed|packing/i, 'PACKED'],
  [/label|invoice printed/i, 'LABEL_PRINTED'],
  [/unshipped|pending|new|approved|acknowledged|confirmed/i, 'NEW'],
];

export function mapStatus(text) {
  const t = String(text || '').trim();
  if (!t) return 'NEW';
  for (const [re, status] of STATUS_TEXT_MAP) {
    if (re.test(t)) return status;
  }
  return 'NEW';
}

const MONTHS = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
};

export function parseDate(value) {
  const s = String(value || '').trim();
  if (!s) return null;
  // 2026-07-30 / 2026-07-30T10:11:12
  let m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  // 30-07-2026 or 30/07/2026 (Indian panels are day-first)
  m = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{4})/);
  if (m) return `${m[3]}-${pad(m[2])}-${pad(m[1])}`;
  // 30 Jul 2026 / Jul 30, 2026
  m = s.match(/^(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})/);
  if (m && MONTHS[m[2].slice(0, 3).toLowerCase()] !== undefined) {
    return `${m[3]}-${pad(MONTHS[m[2].slice(0, 3).toLowerCase()] + 1)}-${pad(m[1])}`;
  }
  m = s.match(/^([A-Za-z]{3,})\s+(\d{1,2}),?\s+(\d{4})/);
  if (m && MONTHS[m[1].slice(0, 3).toLowerCase()] !== undefined) {
    return `${m[3]}-${pad(MONTHS[m[1].slice(0, 3).toLowerCase()] + 1)}-${pad(m[2])}`;
  }
  const d = new Date(s);
  if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10);
  return null;
}

function pad(v) {
  return String(v).padStart(2, '0');
}

export function parseMoney(value) {
  const s = String(value || '').replace(/[₹,\s]/g, '');
  const num = Number(s);
  return Number.isFinite(num) ? num : 0;
}

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Convert raw CSV records into order objects using a field map. */
export function recordsToOrders(records, platform, map) {
  const out = [];
  records.forEach((rec) => {
    const pick = (field) => (map[field] ? rec[map[field]] : '');
    const orderId = String(pick('orderId') || '').trim();
    if (!orderId) return;
    const sku = String(pick('sku') || '').trim() || 'UNKNOWN-SKU';
    const subOrderId = String(pick('subOrderId') || '').trim();
    const qtyRaw = Number(String(pick('qty') || '').replace(/[^0-9.-]/g, ''));
    const qty = Number.isFinite(qtyRaw) && qtyRaw > 0 ? qtyRaw : 1;
    const platformStatus = String(pick('platformStatus') || '').trim();
    out.push({
      id: makeOrderKey(platform, orderId, subOrderId, sku),
      platform,
      orderId,
      subOrderId,
      orderDate: parseDate(pick('orderDate')) || todayISO(),
      sku,
      productName: String(pick('productName') || '').trim(),
      qty,
      sellingPrice: parseMoney(pick('sellingPrice')),
      platformStatus,
      status: mapStatus(platformStatus),
      awb: String(pick('awb') || '').trim(),
      courier: String(pick('courier') || '').trim(),
      customerState: String(pick('customerState') || '').trim(),
      customerPincode: String(pick('customerPincode') || '').trim(),
      reasonCode: '',
      note: '',
      stockRecovered: true,
      source: 'csv',
    });
  });
  return dedupe(out);
}

/** Same order line appearing twice in one file (common in settlement exports). */
export function dedupe(orders) {
  const seen = new Map();
  orders.forEach((o) => {
    const prev = seen.get(o.id);
    if (!prev) {
      seen.set(o.id, o);
    } else {
      prev.qty += o.qty;
      prev.sellingPrice += o.sellingPrice;
    }
  });
  return [...seen.values()];
}

export function toCsv(rows, headers) {
  const cols = headers || (rows.length ? Object.keys(rows[0]) : []);
  const esc = (v) => {
    const s = v === null || v === undefined ? '' : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [cols.map(esc).join(',')];
  rows.forEach((r) => lines.push(cols.map((c) => esc(r[c])).join(',')));
  return lines.join('\n');
}
