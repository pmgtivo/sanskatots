// Platforms, the packing/shipping status machine, and the profit engine.

export const PLATFORMS = {
  amazon: { key: 'amazon', label: 'Amazon', colour: '#ff9900' },
  flipkart: { key: 'flipkart', label: 'Flipkart', colour: '#2874f0' },
  meesho: { key: 'meesho', label: 'Meesho', colour: '#f43397' },
  other: { key: 'other', label: 'Other', colour: '#6b7280' },
};

// The shipping pipeline. `next` drives the big buttons on the Pack & Ship screen.
export const STATUSES = {
  NEW: {
    label: 'New order',
    short: 'New',
    group: 'action',
    hint: 'Order downloaded. Label not printed yet.',
    next: ['LABEL_PRINTED', 'CANCELLED'],
  },
  LABEL_PRINTED: {
    label: 'Label printed',
    short: 'Label done',
    group: 'action',
    hint: 'Label + invoice printed from the seller panel.',
    next: ['PACKED', 'CANCELLED'],
  },
  PACKED: {
    label: 'Packed & label pasted',
    short: 'Packed',
    group: 'action',
    hint: 'Item checked, packed, label stuck on the box.',
    next: ['HANDED_OVER', 'CANCELLED'],
  },
  HANDED_OVER: {
    label: 'Handed over to courier',
    short: 'Handed over',
    group: 'transit',
    hint: 'Pickup done / manifest closed.',
    next: ['IN_TRANSIT', 'DELIVERED', 'RTO_IN_TRANSIT', 'LOST'],
  },
  IN_TRANSIT: {
    label: 'In transit',
    short: 'In transit',
    group: 'transit',
    hint: 'On the way to the customer.',
    next: ['DELIVERED', 'RTO_IN_TRANSIT', 'LOST'],
  },
  DELIVERED: {
    label: 'Delivered',
    short: 'Delivered',
    group: 'closed',
    hint: 'Money will settle for this one.',
    next: ['RETURN_REQUESTED', 'EXCHANGE_REQUESTED'],
  },
  RTO_IN_TRANSIT: {
    label: 'RTO — coming back',
    short: 'RTO transit',
    group: 'problem',
    hint: 'Customer never took it. Package is returning to you.',
    next: ['RTO_RECEIVED', 'LOST'],
  },
  RTO_RECEIVED: {
    label: 'RTO received back',
    short: 'RTO in',
    group: 'closed',
    hint: 'Open it, check condition, put stock back.',
    next: [],
    needsReason: true,
  },
  RETURN_REQUESTED: {
    label: 'Return requested',
    short: 'Return req',
    group: 'problem',
    hint: 'Customer raised a return.',
    next: ['RETURN_RECEIVED'],
    needsReason: true,
  },
  RETURN_RECEIVED: {
    label: 'Return received back',
    short: 'Return in',
    group: 'closed',
    hint: 'Returned parcel is back with you.',
    next: [],
    needsReason: true,
  },
  EXCHANGE_REQUESTED: {
    label: 'Exchange requested',
    short: 'Exchange',
    group: 'problem',
    hint: 'Replacement to be shipped.',
    next: ['LABEL_PRINTED', 'RETURN_RECEIVED'],
    needsReason: true,
  },
  CANCELLED: {
    label: 'Cancelled',
    short: 'Cancelled',
    group: 'closed',
    hint: 'Cancelled before dispatch. No money, no cost.',
    next: [],
  },
  LOST: {
    label: 'Lost / damaged by courier',
    short: 'Lost',
    group: 'problem',
    hint: 'Raise a claim with the platform.',
    next: ['RTO_RECEIVED'],
    needsReason: true,
  },
};

export const STATUS_ORDER = [
  'NEW',
  'LABEL_PRINTED',
  'PACKED',
  'HANDED_OVER',
  'IN_TRANSIT',
  'DELIVERED',
  'RETURN_REQUESTED',
  'EXCHANGE_REQUESTED',
  'RTO_IN_TRANSIT',
  'RTO_RECEIVED',
  'RETURN_RECEIVED',
  'LOST',
  'CANCELLED',
];

// Statuses that still need work from you today.
export const ACTIONABLE = ['NEW', 'LABEL_PRINTED', 'PACKED'];

export const REASON_CODES = [
  'Customer not available / refused',
  'Wrong or incomplete address',
  'Damaged in transit',
  'Wrong item sent',
  'Missing parts / pieces',
  'Quality not as expected',
  'Late delivery',
  'Customer changed mind',
  'Ordered by mistake',
  'Cheaper elsewhere',
  'Other',
];

// Sensible India defaults. Every number is editable in Settings.
export const DEFAULT_FEES = {
  amazon: {
    commissionPct: 12,
    fixedFee: 25,
    shippingFee: 65,
    gstOnFeesPct: 18,
    rtoFee: 65,
    returnFee: 65,
    priceIsNetOfFees: false,
  },
  flipkart: {
    commissionPct: 12,
    fixedFee: 20,
    shippingFee: 60,
    gstOnFeesPct: 18,
    rtoFee: 60,
    returnFee: 60,
    priceIsNetOfFees: false,
  },
  meesho: {
    // Meesho pays a "supplier discounted price" that is already net of commission
    // and shipping, so by default we treat the imported price as take-home.
    commissionPct: 0,
    fixedFee: 0,
    shippingFee: 0,
    gstOnFeesPct: 18,
    rtoFee: 0,
    returnFee: 0,
    priceIsNetOfFees: true,
  },
  other: {
    commissionPct: 0,
    fixedFee: 0,
    shippingFee: 0,
    gstOnFeesPct: 18,
    rtoFee: 0,
    returnFee: 0,
    priceIsNetOfFees: true,
  },
};

export const DEFAULT_SETTINGS = {
  fees: DEFAULT_FEES,
  defaultPackagingCost: 8,
  businessName: 'SanskaTots',
  scanBeepEnabled: true,
};

export function makeOrderKey(platform, orderId, subOrderId, sku) {
  const tail = subOrderId || sku || 'item';
  return `${platform}::${String(orderId).trim()}::${String(tail).trim()}`;
}

export function isProblem(status) {
  return (STATUSES[status] || {}).group === 'problem';
}

// A parcel that came back is not finished until you have opened it and decided
// whether the stock is sellable again.
export const RECEIVED_BACK = ['RTO_RECEIVED', 'RETURN_RECEIVED'];

export function needsAttention(order) {
  if (isProblem(order.status)) return true;
  return RECEIVED_BACK.includes(order.status) && order.restockChecked !== true;
}

export function nextStatuses(status) {
  return (STATUSES[status] || {}).next || [];
}

function n(v) {
  const x = Number(v);
  return Number.isFinite(x) ? x : 0;
}

/**
 * Profit for a single order line.
 * state: realized  = delivered, money is yours
 *        projected = shipped but not delivered yet
 *        loss      = RTO / return / lost
 *        void      = cancelled before dispatch
 */
export function computePnl(order, skuMap, settings) {
  const fees = ((settings && settings.fees) || DEFAULT_FEES)[order.platform] || DEFAULT_FEES.other;
  const skuRow = (skuMap && skuMap[order.sku]) || {};
  const qty = n(order.qty) || 1;
  const packagingCost =
    n(skuRow.packagingCost || (settings && settings.defaultPackagingCost) || 0) * qty;
  const cogs = n(skuRow.costPrice) * qty + packagingCost;
  const gross = n(order.sellingPrice);
  const status = order.status || 'NEW';

  const zero = {
    revenue: 0,
    commission: 0,
    fixedFee: 0,
    shipping: 0,
    gstOnFees: 0,
    cogs: 0,
    profit: 0,
    state: 'void',
  };

  if (status === 'CANCELLED') return zero;

  const commission = fees.priceIsNetOfFees ? 0 : (gross * n(fees.commissionPct)) / 100;
  const fixedFee = fees.priceIsNetOfFees ? 0 : n(fees.fixedFee);
  const shipping = fees.priceIsNetOfFees ? 0 : n(fees.shippingFee);

  // Money never arrives on RTO / return / lost, but the costs do.
  if (status === 'RTO_IN_TRANSIT' || status === 'RTO_RECEIVED') {
    const penalty = n(fees.rtoFee) + shipping;
    const gstOnFees = (penalty * n(fees.gstOnFeesPct)) / 100;
    // Stock comes back, so only packaging is burnt unless you mark it damaged.
    const lostStock = order.stockRecovered === false ? n(skuRow.costPrice) * qty : 0;
    return {
      revenue: 0,
      commission: 0,
      fixedFee: 0,
      shipping: penalty,
      gstOnFees,
      cogs: packagingCost + lostStock,
      profit: -(penalty + gstOnFees + packagingCost + lostStock),
      state: 'loss',
    };
  }

  if (status === 'RETURN_REQUESTED' || status === 'RETURN_RECEIVED' || status === 'EXCHANGE_REQUESTED') {
    const penalty = n(fees.returnFee) + shipping;
    const gstOnFees = (penalty * n(fees.gstOnFeesPct)) / 100;
    const lostStock = order.stockRecovered === false ? n(skuRow.costPrice) * qty : 0;
    return {
      revenue: 0,
      commission: 0,
      fixedFee: 0,
      shipping: penalty,
      gstOnFees,
      cogs: packagingCost + lostStock,
      profit: -(penalty + gstOnFees + packagingCost + lostStock),
      state: 'loss',
    };
  }

  if (status === 'LOST') {
    return {
      revenue: 0,
      commission: 0,
      fixedFee: 0,
      shipping: 0,
      gstOnFees: 0,
      cogs,
      profit: -cogs,
      state: 'loss',
    };
  }

  const gstOnFees = ((commission + fixedFee + shipping) * n(fees.gstOnFeesPct)) / 100;
  const profit = gross - commission - fixedFee - shipping - gstOnFees - cogs;

  return {
    revenue: gross,
    commission,
    fixedFee,
    shipping,
    gstOnFees,
    cogs,
    profit,
    state: status === 'DELIVERED' ? 'realized' : 'projected',
  };
}

export function rollup(orders, skuMap, settings) {
  const acc = {
    orders: 0,
    units: 0,
    revenue: 0,
    commission: 0,
    fixedFee: 0,
    shipping: 0,
    gstOnFees: 0,
    cogs: 0,
    profit: 0,
    realisedRevenue: 0,
    realisedProfit: 0,
    projectedRevenue: 0,
    lossValue: 0,
    delivered: 0,
    rto: 0,
    returned: 0,
    cancelled: 0,
    inPipeline: 0,
  };
  orders.forEach((o) => {
    const p = computePnl(o, skuMap, settings);
    acc.orders += 1;
    acc.units += n(o.qty) || 1;
    acc.revenue += p.revenue;
    acc.commission += p.commission;
    acc.fixedFee += p.fixedFee;
    acc.shipping += p.shipping;
    acc.gstOnFees += p.gstOnFees;
    acc.cogs += p.cogs;
    acc.profit += p.profit;
    if (p.state === 'realized') {
      acc.realisedRevenue += p.revenue;
      acc.realisedProfit += p.profit;
      acc.delivered += 1;
    } else if (p.state === 'projected') {
      acc.projectedRevenue += p.revenue;
      acc.inPipeline += 1;
    } else if (p.state === 'loss') {
      acc.lossValue += -p.profit;
      if (o.status === 'RTO_IN_TRANSIT' || o.status === 'RTO_RECEIVED') acc.rto += 1;
      else acc.returned += 1;
    } else {
      acc.cancelled += 1;
    }
  });
  const shipped = acc.orders - acc.cancelled;
  acc.rtoRatePct = shipped ? (acc.rto / shipped) * 100 : 0;
  acc.returnRatePct = shipped ? (acc.returned / shipped) * 100 : 0;
  acc.marginPct = acc.revenue ? (acc.profit / acc.revenue) * 100 : 0;
  return acc;
}
