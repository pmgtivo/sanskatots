"""Book-level August-2026 P&L for Meesho (orders PLACED 01-31 Aug 2026).

SKUs are variants of the same title (different sizes/editions) and are rolled up
into books before reporting.
"""

import glob
import os
import warnings

import pandas as pd

warnings.filterwarnings("ignore")
pd.set_option("display.width", 300)
pd.set_option("display.max_columns", None)

BASE = os.path.dirname(os.path.abspath(__file__))
PD_ = os.path.join(BASE, "Meesho_platform")

BOOK = {
    "ST-ABB-03": "All In One Busy Book",
    "ST-ABB-02": "All In One Busy Book",
    "ST-MBB-01": "Montessori Busy Book",
    "ST-MBB-03": "Montessori Busy Book",
    "ST-ABB-04": "Animals Busy Book",
    "ST-ABB-01": "Animals Busy Book",
    "ST-BGK-01": "BhagavadGita Busy Book",
    "ST-BGK-02": "BhagavadGita Busy Book",
    "ST-LK-01": "Learn Kannada Book",
    "ST-LK-02": "Learn Kannada Book",
    "ST-SM-01": "Shloka and Mantras Book",
    "ST-SM-02": "Shloka and Mantras Book",
    "ST-PCB-01": "Pencil Control Tracing Book",
    "ST-PCB-04": "Pencil Control Tracing Book",  # not in user's map; same family
}

COST = {
    "ST-ABB-03": 262, "ST-ABB-02": 262,
    "ST-MBB-01": 177, "ST-MBB-03": 177,
    "ST-ABB-04": 150, "ST-ABB-01": 150,
    "ST-BGK-01": 57,  "ST-BGK-02": 57,
    "ST-LK-02": 106,  "ST-LK-01": 106,
    "ST-SM-02": 58,   "ST-SM-01": 58,
    "ST-PCB-01": 122, "ST-PCB-04": 122,  # PCB-04 cost assumed = PCB-01
}
RESELL_RATE = 0.50  # 50% of returned/RTO stock is damaged & written off (user directive)

MONEY = [
    "Final Settlement Amount",
    "Total Sale Amount (Incl. Shipping & GST)",
    "Total Sale Return Amount (Incl. Shipping & GST)",
    "Shipping Charge (Incl. GST)",
    "Return Shipping Charge (Incl. GST)",
    "Quantity", "Recovery", "Claims", "TDS",
]


def load_orders(path):
    d = pd.read_excel(path, sheet_name="Order Payments", header=1)
    d = d[d["Sub Order No"].astype(str).str.contains("_", na=False)].copy()
    for c in MONEY:
        d[c] = pd.to_numeric(d.get(c), errors="coerce").fillna(0)
    d["_st"] = d["Live Order Status"].fillna("FEE_ADJ").astype(str).str.strip()
    d["_sku"] = d["Supplier SKU"].astype(str).str.strip()
    d["_book"] = d["_sku"].map(BOOK).fillna("UNMAPPED")
    d["_cost"] = d["_sku"].map(COST).fillna(0)
    d["_od"] = pd.to_datetime(d["Order Date"], errors="coerce")
    d["_paid"] = "PREVIOUS" in path
    return d


def load_ads(path):
    a = pd.read_excel(path, sheet_name="Ads Cost", header=1)
    a = a[pd.to_numeric(a["Ad Cost"], errors="coerce").notna()].copy()
    a["_dur"] = pd.to_datetime(a["Deduction Duration"], errors="coerce")
    for c in ["Ad Cost", "GST", "Total Ads Cost"]:
        a[c] = pd.to_numeric(a[c], errors="coerce").fillna(0)
    return a


files = sorted(glob.glob(os.path.join(PD_, "*.xlsx")))
allo = pd.concat([load_orders(f) for f in files], ignore_index=True)
allo = allo.drop_duplicates(
    subset=["Sub Order No", "Final Settlement Amount",
            "Total Sale Amount (Incl. Shipping & GST)", "_st"]
).reset_index(drop=True)
ads = pd.concat([load_ads(f) for f in files if len(load_ads(f))], ignore_index=True)
adsaug = ads[(ads["_dur"] >= "2026-08-01") & (ads["_dur"] < "2026-09-01")]
AD = abs(adsaug["Total Ads Cost"].sum())

aug = allo[(allo["_od"] >= "2026-08-01") & (allo["_od"] < "2026-09-01")].copy()
fee = aug[aug["_st"] == "FEE_ADJ"]
real = aug[aug["_st"] != "FEE_ADJ"].copy()

print("=" * 110)
print("SKU -> BOOK MAP (deduplicated)")
print("=" * 110)
m = (
    pd.DataFrame({"SKU": list(BOOK), "Book": [BOOK[k] for k in BOOK], "Cost": [COST[k] for k in BOOK]})
    .groupby("Book")
    .agg(SKUs=("SKU", lambda s: " + ".join(sorted(s))), n_skus=("SKU", "count"),
         cost_range=("Cost", lambda s: f"Rs {s.min()}" if s.min() == s.max() else f"Rs {s.min()}-{s.max()}"))
)
print(m.to_string())
print(f"\n14 SKUs consolidated into {len(m)} books")
print("Unmapped SKUs in data:", sorted(set(real.loc[real['_book'] == 'UNMAPPED', '_sku'])) or "none")

# ------------------------------------------------------------------ book P&L
rows = []
for bk, g in real.groupby("_book"):
    fg = fee[fee["_book"] == bk]
    u_del = g.loc[g["_st"] == "Delivered", "Quantity"].sum()
    u_shp = g.loc[g["_st"] == "Shipped", "Quantity"].sum()
    u_exc = g.loc[g["_st"] == "Exchange", "Quantity"].sum()
    u_ret = g.loc[g["_st"] == "Return", "Quantity"].sum()
    u_rto = g.loc[g["_st"] == "RTO", "Quantity"].sum()
    o_del = (g["_st"] == "Delivered").sum()
    o_shp = (g["_st"] == "Shipped").sum()
    o_ret = (g["_st"] == "Return").sum()
    o_rto = (g["_st"] == "RTO").sum()
    closed = len(g) - o_shp
    sold = u_del + u_shp + u_exc
    cogs_sold = (g.loc[g["_st"].isin(["Delivered", "Shipped", "Exchange"]), "_cost"]
                 * g.loc[g["_st"].isin(["Delivered", "Shipped", "Exchange"]), "Quantity"]).sum()
    lost = g[g["_st"].isin(["Return", "RTO"])]
    cogs_wo = (lost["_cost"] * lost["Quantity"]).sum() * (1 - RESELL_RATE)
    settle = g["Final Settlement Amount"].sum() + fg["Final Settlement Amount"].sum()
    gp = settle - cogs_sold - cogs_wo
    d = g[g["_st"] == "Delivered"]
    rows.append({
        "Book": bk,
        "orders": len(g),
        "units_sold": sold,
        "delivered": o_del,
        "in_transit": o_shp,
        "cust_returns": o_ret,
        "rto": o_rto,
        "return%": round(o_ret / closed * 100, 2) if closed else 0,
        "rto%": round(o_rto / closed * 100, 2) if closed else 0,
        "combined_fail%": round((o_ret + o_rto) / closed * 100, 2) if closed else 0,
        "ASP": round(d["Total Sale Amount (Incl. Shipping & GST)"].mean(), 2) if len(d) else 0,
        "gross_sale": g["Total Sale Amount (Incl. Shipping & GST)"].sum(),
        "fwd_ship": g["Shipping Charge (Incl. GST)"].sum(),
        "ret_ship": g["Return Shipping Charge (Incl. GST)"].sum(),
        "affiliate": g["Recovery"].sum() + fg["Recovery"].sum(),
        "claims": g["Claims"].sum() + fg["Claims"].sum(),
        "settlement": settle,
        "cogs": -cogs_sold,
        "writeoff": -cogs_wo,
        "GROSS_PROFIT": gp,
        "GP_per_unit": round(gp / sold, 2) if sold else 0,
        "GP%": round(gp / g["Total Sale Amount (Incl. Shipping & GST)"].sum() * 100, 1),
        "avg_cost": round(cogs_sold / sold, 2) if sold else 0,
    })
B = pd.DataFrame(rows).sort_values("GROSS_PROFIT", ascending=False).reset_index(drop=True)
B["profit_share%"] = (B["GROSS_PROFIT"] / B["GROSS_PROFIT"].sum() * 100).round(1)
B["rev_share%"] = (B["gross_sale"] / B["gross_sale"].sum() * 100).round(1)
B["unit_share%"] = (B["units_sold"] / B["units_sold"].sum() * 100).round(1)

print("\n" + "=" * 110)
print("BOOK-LEVEL SALES & RETURNS")
print("=" * 110)
print(B[["Book", "orders", "units_sold", "delivered", "in_transit", "cust_returns", "rto",
         "return%", "rto%", "combined_fail%", "unit_share%"]].to_string(index=False))

print("\n" + "=" * 110)
print("BOOK-LEVEL PROFIT & LOSS")
print("=" * 110)
print(B[["Book", "units_sold", "ASP", "gross_sale", "fwd_ship", "ret_ship", "affiliate", "claims",
         "settlement", "avg_cost", "cogs", "writeoff", "GROSS_PROFIT", "GP_per_unit", "GP%",
         "rev_share%", "profit_share%"]].to_string(index=False))

# ------------------------------------------------------------------ ad allocation
print("\n" + "=" * 110)
print("NET PROFIT PER BOOK (ads allocated pro-rata by gross sale)")
print("=" * 110)
B["ad_alloc"] = -(B["gross_sale"] / B["gross_sale"].sum() * AD).round(2)
B["NET_PROFIT"] = (B["GROSS_PROFIT"] + B["ad_alloc"]).round(2)
B["NP_per_unit"] = (B["NET_PROFIT"] / B["units_sold"]).round(2)
B["NP%"] = (B["NET_PROFIT"] / B["gross_sale"] * 100).round(1)
print(B[["Book", "units_sold", "gross_sale", "GROSS_PROFIT", "ad_alloc", "NET_PROFIT",
         "NP_per_unit", "NP%"]].to_string(index=False))

T = B[["orders", "units_sold", "delivered", "in_transit", "cust_returns", "rto", "gross_sale",
       "fwd_ship", "ret_ship", "affiliate", "claims", "settlement", "cogs", "writeoff",
       "GROSS_PROFIT", "ad_alloc", "NET_PROFIT"]].sum()
print("\nTOTALS:")
for k, v in T.items():
    print(f"   {k:<16}{v:>15,.2f}")
closed_all = len(real) - (real["_st"] == "Shipped").sum()
print(f"\n   Overall return% (closed) : {(real['_st']=='Return').sum()/closed_all*100:.2f}%")
print(f"   Overall RTO%    (closed) : {(real['_st']=='RTO').sum()/closed_all*100:.2f}%")
print(f"   Net profit per unit      : Rs {T['NET_PROFIT']/T['units_sold']:.2f}")
print(f"   Net margin on gross sale : {T['NET_PROFIT']/T['gross_sale']*100:.2f}%")

# ------------------------------------------------------------------ SKU detail
print("\n" + "=" * 110)
print("SKU DETAIL INSIDE EACH BOOK (which variant is doing the work)")
print("=" * 110)
for bk in B["Book"]:
    g = real[real["_book"] == bk]
    print(f"\n--- {bk} ---")
    sub = []
    for sku, s in g.groupby("_sku"):
        sd = s[s["_st"] == "Delivered"]
        o_ret = (s["_st"] == "Return").sum()
        o_rto = (s["_st"] == "RTO").sum()
        cl = len(s) - (s["_st"] == "Shipped").sum()
        sold = s.loc[s["_st"].isin(["Delivered", "Shipped", "Exchange"]), "Quantity"].sum()
        c = COST.get(sku, 0)
        sub.append({
            "SKU": sku, "cost": c, "orders": len(s), "units_sold": sold,
            "returns": o_ret, "rto": o_rto,
            "return%": round(o_ret / cl * 100, 1) if cl else 0,
            "ASP": round(sd["Total Sale Amount (Incl. Shipping & GST)"].mean(), 2) if len(sd) else 0,
            "settle/u": round(sd["Final Settlement Amount"].mean(), 2) if len(sd) else 0,
            "contrib/u": round(sd["Final Settlement Amount"].mean() - c, 2) if len(sd) else 0,
        })
    print(pd.DataFrame(sub).sort_values("units_sold", ascending=False).to_string(index=False))

print("\n" + "=" * 110)
print("RETURN COST PER BOOK")
print("=" * 110)
rc = B[["Book", "cust_returns", "rto", "ret_ship", "writeoff"]].copy()
rc["total_return_cost"] = rc["ret_ship"] + rc["writeoff"]
rc["% of book GP"] = (-rc["total_return_cost"] / B["GROSS_PROFIT"] * 100).round(1)
rc["cost_per_return"] = (rc["total_return_cost"] / (rc["cust_returns"] + rc["rto"]).replace(0, pd.NA)).round(2)
print(rc.to_string(index=False))
print(f"\nTotal return cost across all books: Rs {abs(rc['total_return_cost'].sum()):,.2f}"
      f"  = {abs(rc['total_return_cost'].sum())/T['NET_PROFIT']*100:.1f}% of net profit")
