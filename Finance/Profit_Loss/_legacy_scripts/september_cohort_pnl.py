"""September-2026 order-cohort P&L for Meesho: orders PLACED 01-30 Sep 2026,
combining settled + outstanding payment files, with real per-SKU manufacturing cost.
"""

import glob
import os
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
pd.set_option("display.width", 260)
pd.set_option("display.max_columns", None)

BASE = os.path.dirname(os.path.abspath(__file__))
PD_ = BASE  # xlsx files sit directly in this month's folder

# All-in manufacturing cost per unit (print + velcro + packaging + mailer + labour).
COST = {
    "ST-ABB-03": 262, "ST-ABB-02": 262,
    "ST-MBB-01": 177, "ST-MBB-03": 177,
    "ST-ABB-04": 150, "ST-ABB-01": 150,
    "ST-BGK-01": 57,  "ST-BGK-02": 57,
    "ST-LK-02": 106,  "ST-LK-01": 106,
    "ST-SM-02": 58,   "ST-SM-01": 58,
    "SiGenhwc": 58,   # user-confirmed Sep 2026: same as Shloka & Mantras board book family
    "ST-PCB-01": 122,
    "ST-PCB-04": 122,  # ASSUMED = ST-PCB-01, cost not supplied
    "ST-IMB-01": 160,  # user-confirmed Sep 2026
    "ST-SM-CB": 450,   # user-confirmed Sep 2026: pack-of-10 gift bundle
}
RESELL_RATE = 0.70  # 70% of returned/RTO stock is resellable -> 30% damaged & written off (user directive, Sep 2026)

MONEY = [
    "Final Settlement Amount",
    "Total Sale Amount (Incl. Shipping & GST)",
    "Total Sale Return Amount (Incl. Shipping & GST)",
    "Shipping Charge (Incl. GST)",
    "Return Shipping Charge (Incl. GST)",
    "Quantity",
    "Recovery",
    "Claims",
    "TDS",
    "Compensation",
]


def load_orders(path):
    d = pd.read_excel(path, sheet_name="Order Payments", header=1)
    d = d[d["Sub Order No"].astype(str).str.contains("_", na=False)].copy()
    for c in MONEY:
        d[c] = pd.to_numeric(d.get(c), errors="coerce").fillna(0)
    d["_st"] = d["Live Order Status"].fillna("FEE_ADJ").astype(str).str.strip()
    d["_sku"] = d["Supplier SKU"].astype(str).str.strip()
    d["_od"] = pd.to_datetime(d["Order Date"], errors="coerce")
    d["_src"] = os.path.basename(path)
    d["_paid"] = "PREVIOUS" in path
    return d


def load_ads(path):
    a = pd.read_excel(path, sheet_name="Ads Cost", header=1)
    a = a[pd.to_numeric(a["Ad Cost"], errors="coerce").notna()].copy()
    a["_dur"] = pd.to_datetime(a["Deduction Duration"], errors="coerce")
    for c in ["Ad Cost", "GST", "Total Ads Cost", "Credits / Waivers / Discounts"]:
        a[c] = pd.to_numeric(a[c], errors="coerce").fillna(0)
    return a


files = sorted(glob.glob(os.path.join(PD_, "*.xlsx")))
allo = pd.concat([load_orders(f) for f in files], ignore_index=True)
allads = pd.concat([load_ads(f) for f in files if len(load_ads(f))], ignore_index=True)

# ---------------------------------------------------------------- dedupe
key = ["Sub Order No", "Final Settlement Amount", "Total Sale Amount (Incl. Shipping & GST)", "_st"]
before = len(allo)
allo = allo.drop_duplicates(subset=key).reset_index(drop=True)

print("=" * 100)
print("STEP 1 — BUILD THE SEPTEMBER ORDER COHORT")
print("=" * 100)
print(f"Rows across all payment files               : {before}")
print(f"After de-duplication                       : {len(allo)}")

sep = allo[(allo["_od"] >= "2026-09-01") & (allo["_od"] < "2026-10-01")].copy()
notsep = allo[~allo.index.isin(sep.index)]
print(f"Rows EXCLUDED (order placed outside Sep)   : {len(notsep)}")
print(f"   of which August orders                  : {(notsep['_od'] < '2026-09-01').sum()}")
print(f"Rows KEPT (order placed 01-30 Sep 2026)     : {len(sep)}")

fee = sep[sep["_st"] == "FEE_ADJ"]
real = sep[sep["_st"] != "FEE_ADJ"].copy()
print(f"   real order lines                        : {len(real)}")
print(f"   fee-adjustment lines (affiliate/claims) : {len(fee)}")
print(f"   unique sub-orders                       : {sep['Sub Order No'].nunique()}")
print(f"\nSettlement status of Sep cohort:")
print(f"   already paid out in Sep   : {real['_paid'].sum()} lines, "
      f"Rs {real[real['_paid']]['Final Settlement Amount'].sum():,.2f}")
print(f"   still receivable (Oct)    : {(~real['_paid']).sum()} lines, "
      f"Rs {real[~real['_paid']]['Final Settlement Amount'].sum():,.2f}")

# ---------------------------------------------------------------- funnel
print("\n" + "=" * 100)
print("STEP 2 — SEPTEMBER ORDER FUNNEL")
print("=" * 100)
f = real.groupby("_st").agg(
    orders=("Sub Order No", "count"),
    units=("Quantity", "sum"),
    gross=("Total Sale Amount (Incl. Shipping & GST)", "sum"),
    settlement=("Final Settlement Amount", "sum"),
)
f["pct"] = (f["orders"] / len(real) * 100).round(2)
print(f.round(2).to_string())
R = len(real)
dl = f["orders"].get("Delivered", 0)
rt = f["orders"].get("Return", 0)
ro = f["orders"].get("RTO", 0)
sh = f["orders"].get("Shipped", 0)
print(f"\nOrders placed in Sep          : {R}")
print(f"Delivered                     : {dl} ({dl/R*100:.2f}%)")
print(f"Returned                      : {rt} ({rt/R*100:.2f}%)")
print(f"RTO                           : {ro} ({ro/R*100:.2f}%)")
print(f"Still in transit              : {sh} ({sh/R*100:.2f}%)")
print(f"Return+RTO leakage            : {(rt+ro)/R*100:.2f}%")
settled_only = R - sh
print(f"Return rate on CLOSED orders   : {rt/settled_only*100:.2f}%  (excludes {sh} in transit)")
print(f"RTO rate on CLOSED orders      : {ro/settled_only*100:.2f}%")

# ---------------------------------------------------------------- ads
print("\n" + "=" * 100)
print("STEP 3 — SEPTEMBER AD SPEND (by date ads actually ran)")
print("=" * 100)
adssep = allads[(allads["_dur"] >= "2026-09-01") & (allads["_dur"] < "2026-10-01")]
adsaug = allads[allads["_dur"] < "2026-09-01"]
AD = abs(adssep["Total Ads Cost"].sum())
print(f"Ad rows with run-date in August (excluded) : {len(adsaug)}  Rs {abs(adsaug['Total Ads Cost'].sum()):,.2f}")
print(f"Ad rows with run-date in September (kept)  : {len(adssep)}")
print(f"   base ad cost                            : Rs {adssep['Ad Cost'].sum():,.2f}")
print(f"   GST @18%                                : Rs {abs(adssep['GST'].sum()):,.2f}")
print(f"   credits/waivers                         : Rs {adssep['Credits / Waivers / Discounts'].sum():,.2f}")
print(f"   TOTAL SEPTEMBER AD SPEND                : Rs {AD:,.2f}")
print(f"   days ads ran                            : {adssep['_dur'].nunique()} of 30")
print("\nBy campaign:")
cmp_ = adssep.groupby("Campaign ID").agg(days=("_dur", "nunique"), spend=("Total Ads Cost", "sum"))
cmp_["spend"] = cmp_["spend"].abs()
cmp_["share%"] = (cmp_["spend"] / cmp_["spend"].sum() * 100).round(1)
print(cmp_.sort_values("spend", ascending=False).round(2).to_string())

# ---------------------------------------------------------------- per SKU P&L
print("\n" + "=" * 100)
print("STEP 4 — PER-SKU P&L (September order cohort)")
print("=" * 100)
rows = []
for sku, g in real.groupby("_sku"):
    c = COST.get(sku)
    if c is None:
        print(f"   WARNING: no manufacturing cost for SKU {sku!r} — treated as Rs 0")
    u_del = g.loc[g["_st"] == "Delivered", "Quantity"].sum()
    u_shp = g.loc[g["_st"] == "Shipped", "Quantity"].sum()
    u_exc = g.loc[g["_st"] == "Exchange", "Quantity"].sum()
    u_ret = g.loc[g["_st"] == "Return", "Quantity"].sum()
    u_rto = g.loc[g["_st"] == "RTO", "Quantity"].sum()
    affl = fee.loc[fee["_sku"] == sku, "Recovery"].sum()
    clm = fee.loc[fee["_sku"] == sku, "Claims"].sum()
    settle = g["Final Settlement Amount"].sum() + affl + clm
    shipped_out = u_del + u_shp + u_exc  # units that left and stayed with customer
    cogs_sold = c * shipped_out if c else 0
    cogs_wo = c * (u_ret + u_rto) * (1 - RESELL_RATE) if c else 0
    rows.append({
        "SKU": sku,
        "cost/u": c,
        "orders": len(g),
        "u_delivered": u_del,
        "u_transit": u_shp,
        "u_returned": u_ret,
        "u_rto": u_rto,
        "ret%": round(u_ret / g["Quantity"].sum() * 100, 1),
        "gross_sale": g["Total Sale Amount (Incl. Shipping & GST)"].sum(),
        "fwd_ship": g["Shipping Charge (Incl. GST)"].sum(),
        "ret_ship": g["Return Shipping Charge (Incl. GST)"].sum(),
        "affiliate": affl + g["Recovery"].sum(),
        "claims": clm + g["Claims"].sum(),
        "settlement": settle,
        "cogs_sold": -cogs_sold,
        "cogs_writeoff": -cogs_wo,
        "GROSS_PROFIT": settle - cogs_sold - cogs_wo,
    })
P = pd.DataFrame(rows)
P["GP/unit"] = (P["GROSS_PROFIT"] / (P["u_delivered"] + P["u_transit"]).astype(float).replace(0, float("nan"))).round(2)
P["GP%"] = (P["GROSS_PROFIT"] / P["gross_sale"] * 100).round(1)
P = P.sort_values("GROSS_PROFIT", ascending=False)
tot = P.drop(columns=["SKU", "cost/u", "ret%", "GP/unit", "GP%"]).sum()
print(P.round(2).to_string(index=False))
print("\nTOTALS:")
for k, v in tot.items():
    print(f"   {k:<16}{v:>14,.2f}")

# ---------------------------------------------------------------- P&L
print("\n" + "=" * 100)
print("STEP 5 — SEPTEMBER 2026 PROFIT & LOSS STATEMENT")
print("=" * 100)
gross = real["Total Sale Amount (Incl. Shipping & GST)"].sum()
rev_rev = real["Total Sale Return Amount (Incl. Shipping & GST)"].sum()
fwd = real["Shipping Charge (Incl. GST)"].sum()
rsh = real["Return Shipping Charge (Incl. GST)"].sum()
aff = real["Recovery"].sum() + fee["Recovery"].sum()
clm = real["Claims"].sum() + fee["Claims"].sum()
tds = real["TDS"].sum()
settle = real["Final Settlement Amount"].sum() + fee["Final Settlement Amount"].sum()
cogs_sold = -P["cogs_sold"].sum()
cogs_wo = -P["cogs_writeoff"].sum()
gp = settle - cogs_sold - cogs_wo
np_ = gp - AD

L = [
    ("Gross Sale Value (incl. shipping & GST)", gross),
    ("Less: Returns & RTO revenue reversal", rev_rev),
    ("NET REVENUE", gross + rev_rev),
    ("", None),
    ("Meesho commission", 0.0),
    ("Forward shipping charge", fwd),
    ("Return shipping charge", rsh),
    ("Affiliate fee", aff),
    ("Claims recovered", clm),
    ("TDS @ 0.1%", tds),
    ("TOTAL SETTLEMENT (Meesho pays you)", settle),
    ("", None),
    ("Less: Manufacturing cost of units sold", -cogs_sold),
    (f"Less: Write-off on returns ({int((1-RESELL_RATE)*100)}% of returned stock)", -cogs_wo),
    ("GROSS PROFIT", gp),
    ("", None),
    ("Less: Meesho Ads (incl. GST)", -AD),
    ("NET PROFIT (September order cohort)", np_),
]
for k, v in L:
    if v is None:
        print("-" * 62)
    else:
        pct = f"{v/gross*100:>8.2f}%" if gross else ""
        print(f"{k:<52}{v:>14,.2f} {pct}")

units_sold = P["u_delivered"].sum() + P["u_transit"].sum()
print("\n" + "-" * 62)
print(f"{'Units sold (delivered + in transit)':<52}{units_sold:>14,.0f}")
print(f"{'Net profit per unit sold':<52}{np_/units_sold:>14,.2f}")
print(f"{'Net profit margin (on gross sale)':<52}{np_/gross*100:>13.2f}%")
print(f"{'Net profit margin (on settlement)':<52}{np_/settle*100:>13.2f}%")
print(f"{'Gross margin %':<52}{gp/gross*100:>13.2f}%")
print(f"{'Blended COGS as % of gross sale':<52}{(cogs_sold+cogs_wo)/gross*100:>13.2f}%")
print(f"{'Avg manufacturing cost per unit sold':<52}{cogs_sold/units_sold:>14,.2f}")
print(f"{'ACOS (Ad spend / Gross Sale)':<52}{AD/gross*100:>13.2f}%")
print(f"{'TACOS (Ad spend / Net Revenue after returns)':<52}{AD/(gross+rev_rev)*100:>13.2f}%")
print(f"{'ROAS (Gross Sale / Ad spend)':<52}{gross/AD:>13.2f}x")

# ---------------------------------------------------------------- cash view
print("\n" + "=" * 100)
print("STEP 6 — CASH POSITION vs ACCRUAL")
print("=" * 100)
paid = real[real["_paid"]]["Final Settlement Amount"].sum() + fee[fee["_paid"]]["Final Settlement Amount"].sum()
due = settle - paid
print(f"Settlement already banked in Sep           : Rs {paid:,.2f}")
print(f"Settlement still receivable (Oct)          : Rs {due:,.2f}")
print(f"Total earned on Sep orders                 : Rs {settle:,.2f}")
print(f"\nCash actually deducted for ads in Sep      : Rs {abs(allads[(allads['_dur']>='2026-09-01')&(allads['_dur']<'2026-10-01')]['Total Ads Cost'].sum()):,.2f}")
print(f"Cash spent on manufacturing (units sold)   : Rs {cogs_sold:,.2f}  <- paid to printer, timing differs")

# ---------------------------------------------------------------- winners/losers
print("\n" + "=" * 100)
print("STEP 7 — WINNERS, LOSERS AND MARGIN STRUCTURE")
print("=" * 100)
d = real[real["_st"] == "Delivered"].copy()
u = []
for sku, g in d.groupby("_sku"):
    c = COST.get(sku, 0)
    n_ = len(g)
    asp = g["Total Sale Amount (Incl. Shipping & GST)"].mean()
    shp = g["Shipping Charge (Incl. GST)"].mean()
    net = g["Final Settlement Amount"].mean()
    u.append({
        "SKU": sku, "n": n_, "ASP": round(asp, 2), "ship": round(shp, 2),
        "settle/u": round(net, 2), "cost/u": c,
        "contrib/u": round(net - c, 2),
        "contrib%": round((net - c) / asp * 100, 1) if asp else 0,
        "ship%ofASP": round(-shp / asp * 100, 1) if asp else 0,
    })
U = pd.DataFrame(u).sort_values("contrib/u", ascending=False)
print(U.to_string(index=False))

print("\nAd payback: units needed to cover Rs {:,.0f} of September ads".format(AD))
for _, r in U.iterrows():
    if r["contrib/u"] > 0:
        print(f"   {r['SKU']:<12} {AD/r['contrib/u']:>7.0f} units at Rs {r['contrib/u']:.2f} contribution")

print("\n" + "=" * 100)
print("STEP 8 — BREAK-EVEN & SENSITIVITY")
print("=" * 100)
print(f"Break-even ad spend (GP before ads)        : Rs {gp:,.2f}   -> you spent Rs {AD:,.2f} ({AD/gp*100:.1f}% of it)")
print(f"Break-even blended COGS/unit               : Rs {(settle-AD)/units_sold:,.2f}   -> actual Rs {cogs_sold/units_sold:,.2f}")
print(f"Headroom per unit                          : Rs {(settle-AD)/units_sold - cogs_sold/units_sold:,.2f}")
wo_pct = round((1 - RESELL_RATE) * 100)
print(f"\nIf return rate changes (each return costs Rs 157 ship + {wo_pct}% stock write-off):")
avgc = cogs_sold / units_sold
for rr in [0.04, 0.06, 0.08, 0.10, 0.12, 0.15]:
    n_ret = R * rr
    cost = n_ret * (157 + (1 - RESELL_RATE) * avgc)
    base = R * (rt / R) * (157 + (1 - RESELL_RATE) * avgc)
    print(f"   return rate {rr*100:>5.2f}%  ->  return cost Rs {cost:>9,.0f}   net profit Rs {np_ + base - cost:>10,.0f}")

print("\n" + "=" * 100)
print("STEP 9 — CONSERVATIVE VIEW: haircut the in-transit orders")
print("=" * 100)
tr = real[real["_st"] == "Shipped"]
tr_settle = tr["Final Settlement Amount"].sum()
tr_units = tr["Quantity"].sum()
closed_ret = rt / settled_only
closed_rto = ro / settled_only
fail = closed_ret + closed_rto
lost_settle = tr_settle * fail
recovered_cogs = 0.0
for sku, g in tr.groupby("_sku"):
    c = COST.get(sku, 0)
    recovered_cogs += c * g["Quantity"].sum() * fail * RESELL_RATE
extra_ret_ship = tr_units * closed_ret * 157
adj = np_ - lost_settle + recovered_cogs - extra_ret_ship
print(f"In-transit orders                          : {len(tr)} ({tr_units:.0f} units, Rs {tr_settle:,.2f} booked)")
print(f"Applying observed failure rate of {fail*100:.2f}% to them:")
print(f"   settlement at risk                      : Rs {lost_settle:,.2f}")
print(f"   stock recovered back ({RESELL_RATE*100:.0f}% resellable)  : Rs {recovered_cogs:,.2f}")
print(f"   extra return shipping                   : Rs {extra_ret_ship:,.2f}")
print(f"\nREPORTED NET PROFIT                        : Rs {np_:,.2f}")
print(f"CONSERVATIVE NET PROFIT                    : Rs {adj:,.2f}")
print(f"Downside risk                              : Rs {np_-adj:,.2f} ({(np_-adj)/np_*100:.1f}%)")

print("\nWORST CASE - every in-transit order fails:")
wc_cogs = sum(COST.get(s, 0) * g["Quantity"].sum() * RESELL_RATE for s, g in tr.groupby("_sku"))
wc = np_ - tr_settle + wc_cogs - tr_units * 157
print(f"   net profit                              : Rs {wc:,.2f}")
