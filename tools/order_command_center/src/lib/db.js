// IndexedDB wrapper. Everything lives on this machine, nothing leaves the browser.

const DB_NAME = 'sanskatots_occ';
const DB_VERSION = 1;

export const STORE_ORDERS = 'orders';
export const STORE_SKUS = 'skus';
export const STORE_SETTINGS = 'settings';
export const STORE_EVENTS = 'events';

let dbPromise = null;

function openDb() {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE_ORDERS)) {
        const s = db.createObjectStore(STORE_ORDERS, { keyPath: 'id' });
        s.createIndex('platform', 'platform');
        s.createIndex('status', 'status');
        s.createIndex('orderDate', 'orderDate');
        s.createIndex('sku', 'sku');
        s.createIndex('awb', 'awb');
      }
      if (!db.objectStoreNames.contains(STORE_SKUS)) {
        db.createObjectStore(STORE_SKUS, { keyPath: 'sku' });
      }
      if (!db.objectStoreNames.contains(STORE_SETTINGS)) {
        db.createObjectStore(STORE_SETTINGS, { keyPath: 'key' });
      }
      if (!db.objectStoreNames.contains(STORE_EVENTS)) {
        const e = db.createObjectStore(STORE_EVENTS, { keyPath: 'id', autoIncrement: true });
        e.createIndex('at', 'at');
        e.createIndex('orderKey', 'orderKey');
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function tx(store, mode, fn) {
  return openDb().then(
    (db) =>
      new Promise((resolve, reject) => {
        const t = db.transaction(store, mode);
        const os = t.objectStore(store);
        let result;
        try {
          result = fn(os);
        } catch (err) {
          reject(err);
          return;
        }
        t.oncomplete = () => resolve(result && result.__req ? result.__req.result : result);
        t.onerror = () => reject(t.error);
        t.onabort = () => reject(t.error);
      })
  );
}

const wrap = (req) => ({ __req: req });

export function getAll(store) {
  return tx(store, 'readonly', (os) => wrap(os.getAll()));
}

export function get(store, key) {
  return tx(store, 'readonly', (os) => wrap(os.get(key)));
}

export function put(store, value) {
  return tx(store, 'readwrite', (os) => wrap(os.put(value)));
}

export function putMany(store, values) {
  return tx(store, 'readwrite', (os) => {
    values.forEach((v) => os.put(v));
    return values.length;
  });
}

export function del(store, key) {
  return tx(store, 'readwrite', (os) => wrap(os.delete(key)));
}

export function clearStore(store) {
  return tx(store, 'readwrite', (os) => wrap(os.clear()));
}

export function count(store) {
  return tx(store, 'readonly', (os) => wrap(os.count()));
}

export async function logEvent(orderKey, type, detail) {
  return put(STORE_EVENTS, { orderKey: orderKey || '-', type, detail: detail || '', at: new Date().toISOString() });
}

export async function getSettings() {
  const rows = await getAll(STORE_SETTINGS);
  const out = {};
  rows.forEach((r) => {
    out[r.key] = r.value;
  });
  return out;
}

export async function setSetting(key, value) {
  return put(STORE_SETTINGS, { key, value });
}
