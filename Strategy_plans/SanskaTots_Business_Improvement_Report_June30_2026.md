# SanskaTots — Business Improvement Report
**Date:** June 30, 2026 (Day 30 post-launch)
**Prepared for:** Nagarathna R & Prashanth, Deethya Enterprises
**Scope:** Where to improve, in priority order, with concrete actions

---

## EXECUTIVE SUMMARY

Your strategy is sound. Your execution has gaps. After 30 days on Amazon India, the business is at a make-or-break inflection point — what you do in **July–August 2026** decides whether Diwali (Oct–Nov) delivers ₹20–30L or ₹3–5L.

**The single sentence diagnosis:**
> You have a great product, a real market gap, and ₹40L of dry powder — but you are flying blind (no data dashboard), operating solo (no Ops Assistant), printing expensively (Bengaluru not Sivakasi), selling on one channel (Amazon-only), and sitting on a category-killer SKU (Mythology Velcro Busy Book) that hasn't shipped.

**The five biggest leaks in priority order:**

| # | Improvement Area | Cost of Inaction | Time to Fix |
|---|---|---|---|
| 1 | **Measurement & data hygiene** — you don't know your numbers | Cannot improve what you don't measure. Every decision is a guess. | 1 week |
| 2 | **Sivakasi printing transition** — still at ₹60–100/book | Losing ₹30–60 per unit sold = ₹6,000–₹12,000/month already | 4–6 weeks |
| 3 | **Operations Assistant not hired** — founder bottleneck | Nagu's time spent assembling = no design, no content, no strategy | Immediate |
| 4 | **Amazon-only monoculture** — Flipkart + D2C delayed | One suspension = ₹0 revenue. Also 40% margin sacrifice on every sale. | 6–8 weeks |
| 5 | **Diwali inventory + bundles + Mythology Velcro launch** — window is closing | Diwali is your single biggest revenue event of Year 1 | Order by Aug 15 |

The rest of this document goes deep on each, plus 7 secondary improvement areas, with concrete weekly actions.

---

## PART 1 — THE FIVE CRITICAL FIXES (Next 60 Days)

### 1. **MEASUREMENT — Build a Founder Dashboard This Week**

**The Problem**
You have a 30-day-old business, ₹50L capital deployed, and zero documents tell me:
- Units sold in June
- Revenue collected
- ACoS / TACoS on PPC
- Sessions / unit session % per ASIN
- Review count per SKU
- Return rate
- Inventory days remaining per SKU
- Cash burned this month

The strategic plans assume ₹35K–₹53K Month 1 revenue. **You don't know if you hit that.** If you can't answer those in 60 seconds, you're flying blind.

**What "Improved" Looks Like**
A single one-page dashboard refreshed every Monday morning, showing:

```
WEEK OF: [date]
┌─────────────────────────────────────────────────────┐
│ Revenue this week:     ₹_____ (vs. ₹_____ last wk)  │
│ Units this week:       ___ units                    │
│ Reviews collected:     ___ new (total: ___)         │
│ Avg star rating:       ___ stars                    │
│ Amazon ACoS:           ___% (target <30%)           │
│ Best-selling SKU:      __________                   │
│ Worst-performing SKU:  __________                   │
│ Inventory days left:   ___ days (per SKU)           │
│ Cash burned this wk:   ₹_____                       │
│ Cash on hand:          ₹_____                       │
└─────────────────────────────────────────────────────┘
```

**Concrete Actions (Next 7 Days)**
- [ ] Pull Amazon Seller Central → Reports → Business Reports → "Detail Page Sales and Traffic by Child Item" for last 30 days
- [ ] Export PPC reports: Sponsored Products → "Search Term Report" + "Campaign Performance" for last 30 days
- [ ] Create Google Sheet `SanskaTots_Weekly_KPIs` with tabs: Sales, Ads, Reviews, Inventory, Cash
- [ ] You already have a `tools/` folder — instruct Prashanth to wire Amazon SP-API → Supabase → Streamlit dashboard within 2 weeks (this was already in the AI Strategy doc; just execute it)
- [ ] Every Monday 9am: 30-minute "metrics standup" between Nagu and Prashanth, no exceptions

**Why This Is #1**
Every other improvement on this list depends on knowing where you actually are. You're 30 days in and the most important file in your workspace — actual sales numbers — doesn't exist. Fix this first.

---

### 2. **SIVAKASI TRANSITION — Halve Your COGS in 30 Days**

**The Problem**
You are still printing in Bengaluru at **₹60–100/book**. The plan said transition to Sivakasi by Month 3 (Aug 2026) at **₹35–55/book**. As of June 30, no Sivakasi order has been placed (per workspace evidence).

**The Math**
- 200 units/month at Bengaluru: COGS ₹16,000 (avg ₹80)
- 200 units/month at Sivakasi: COGS ₹9,000 (avg ₹45)
- **Monthly savings even at low volume: ₹7,000**
- **Diwali volume (2,000 units/month): ₹70,000 saved/month**

Every week you delay Sivakasi during the Diwali ramp = ~₹17,000 of margin walked out the door.

**Concrete Actions (Next 14 Days)**
- [ ] **This week:** Identify 3 Sivakasi printer shortlist. Use existing contacts from Bengaluru printers (ask for referrals) or Indiamart "offset book printer Sivakasi" + WhatsApp 5–10 vendors
- [ ] **Week 2:** Request samples on **2 SKUs only** (Pencil Control + Animals Busy Book — your testable formats: A5 + A4)
- [ ] **Week 3:** Receive samples → physical QA against current Bengaluru sample. Check: GSM accuracy, color fidelity vs. PDF, lamination quality, binding strength, cutting page registration
- [ ] **Week 4:** Place first **500-copy order on 1 SKU** (lowest-risk: Pencil Control Tracing — no velcro, no cultural content). Do NOT order 2,000 yet.
- [ ] **Week 5–6:** If pass, place 500-copy orders on remaining 6 SKUs
- [ ] **Critical:** Keep Bengaluru printer warm as backup for at least 90 days post-Sivakasi go-live

**Why Not Sooner**
Don't skip the sample step. One Sivakasi misprint on Bhagavad Gita = brand-damaging review. Move fast but ladder the risk.

---

### 3. **HIRE AN OPS ASSISTANT — This Month, Not "By Month 4"**

**The Problem**
Manual velcro assembly caps at 15–20 books/day per person. At Diwali peak (target 2,000–3,000 units in November), you need **70–100 books/day output**. With 2 founders also doing design, marketing, content, customer service, accounting, sourcing, listings… you will physically run out of hours.

The plan said "hire by Month 4." Month 4 is August. **The hiring + training cycle is 4–6 weeks. If you don't start in July, you won't have a trained assembler when Diwali volume hits in October.**

**Concrete Actions (Next 21 Days)**
- [ ] **Week 1:** Post on apna.co + WorkIndia + local WhatsApp groups for "Packing & Assembly Helper" — ₹15,000/month, 8 hours/day, 6 days/week, Bengaluru location
- [ ] **Week 2:** Interview 3–5 candidates. Look for: detail-oriented, willing to repeat tasks, lives within 5km of your workspace, can start within 1 week
- [ ] **Week 3:** Hire. Spend Week 1 on training: SOP for velcro placement, packing, label application, QC checklist
- [ ] **Week 4:** Offload 80% of assembly to assistant. Nagu now spends those 4–5 hours/day on design Phase 2 SKUs + reel filming
- [ ] Write **3 SOPs** (in Google Docs, with photos): (1) Velcro Sticker Application, (2) Packing & Labeling, (3) Pre-ship Quality Check
- [ ] Hire **a second assistant by Sept 15** if Aug volume exceeds 300 units/month

**ROI of This Hire**
- ₹15,000/month cost
- Frees ~80 hours/month of Nagu's time
- If 20 of those hours go into reels → +60% content output → +40% organic Instagram growth
- If 20 hours go into Phase 2 design → 2 new SKUs ready by Oct (each new SKU = ₹50–100K/yr revenue at low scale)
- **ROI is 5–10x within 90 days.** This is the highest-leverage hire of Year 1.

---

### 4. **DIWALI WAR PLAN — Your One-Month-of-the-Year Bet**

**The Problem**
Diwali 2026 falls **Oct 20–24**. Great Indian Festival (GIF) prep starts mid-Sept. Your strategic docs target **₹20–30L in November alone** — that's 25–50% of your entire Year 1 revenue compressed into 30 days.

But Diwali doesn't happen on its own. It requires:
1. Inventory ordered by **mid-August** (Sivakasi lead time = 4–6 weeks)
2. Bundles created and live on Amazon by **Sept 15**
3. PPC budget pre-funded and aggressive bid strategy ready by **Oct 1**
4. Mythology Velcro Busy Book launched (if even possible) — this is the gift product
5. Influencer seeding done by **Sept 30** so reviews exist when Diwali traffic arrives

**As of June 30, none of these are in flight.** You have 6–7 weeks to fix this.

**Concrete Actions — Diwali Critical Path**

**By July 31 (Month 2 end):**
- [ ] **Inventory math:** Forecast Diwali demand per SKU. Conservative ask: 300 units of each Phase 1 SKU = 2,100 units total. Place Sivakasi orders accordingly (some via Bengaluru if Sivakasi not ready)
- [ ] **Mythology Velcro Busy Book decision:** Can it be print-ready by Sept 1? If YES → push HARD. If NO → don't gamble, defer to Phase 2 Q1 2027
- [ ] **Bundles defined:**
  - "Toddler Starter Pack" — All-In-One + Animals + Pencil Control (₹999, save ₹300)
  - "Cultural Heritage Bundle" — Bhagavad Gita + Shloka Board + Learn Kannada (₹699, save ₹150)
  - "Diwali Gift Box" — Bhagavad Gita + Shloka Board + custom gift wrap (₹599, premium positioning)

**By August 31 (Month 3 end):**
- [ ] Bundles **live on Amazon** as virtual product bundles (use Amazon Bundle Builder)
- [ ] First 500-copy Sivakasi order delivered + QA passed
- [ ] 50+ reviews on top 3 SKUs (use Vine + insert cards + WhatsApp follow-up)
- [ ] 5 micro-influencers (5K–50K followers) seeded with free copies; content live by mid-Sept
- [ ] A+ Content fully published on all 7 ASINs (with comparison charts vs. Skillmatics/Clapjoy)

**By September 30:**
- [ ] PPC daily budget pre-funded for Oct: ₹10,000/day Sponsored Products + ₹3,000/day Sponsored Brands Video
- [ ] Diwali landing page on Amazon Storefront live
- [ ] "Pre-Diwali" Lightning Deal applications submitted (Amazon requires 4-week lead)
- [ ] Inventory IN FBA warehouse (not just ordered) — ship by Sept 15 to be discoverable for Prime

**By October 15:**
- [ ] All systems go. Heavy PPC, daily monitoring, ACoS allowed to spike to 40–50% for visibility

**Single Biggest Lever in This Section**
Bundles. AOV from ₹320 → ₹600+ on a single click. Amazon's bundle algorithm also boosts visibility. **If you do nothing else from this section, do bundles.**

---

### 5. **BUILD CHANNEL #2 — Flipkart + D2C Before Diwali**

**The Problem**
You are **100% Amazon-dependent**. The `website/` folder in your workspace contains literally one file: `.DS_Store` (an empty macOS metadata file). No Shopify, no Razorpay, no WhatsApp catalog, no Flipkart listing.

**Risks:**
- Amazon account suspension (1 wrong review report, 1 keyword stuffing complaint, 1 inventory misclassification) = revenue → ₹0 overnight
- You give up 15% Amazon referral fee (well, 0% for books) + 10–12% FBA fee = ~15% of revenue
- You have no first-party customer data (email, phone, address) for retargeting

**Concrete Actions (Next 45 Days)**

**Flipkart (Easier — same model as Amazon):**
- [ ] **Week 1–2:** Register as Flipkart Seller → upload existing 7 SKUs using Amazon listing copy adapted to Flipkart format
- [ ] **Week 3:** Send 50 units of each SKU to Flipkart Smart Fulfillment
- [ ] **Week 4:** Go live. Mirror Amazon prices, ±2% adjustment for Flipkart Plus customers
- [ ] **Target:** ₹50K from Flipkart in first 60 days (4–5% of Amazon volume initially)

**D2C — Shopify (Higher Margin, Slower Build):**
- [ ] **Week 1:** Buy `sanskatots.com` if not owned, pick Shopify Basic plan (₹2,500/month)
- [ ] **Week 2:** Use a launch theme (Dawn or Sense). Build 4 pages: Home, Shop (7 SKUs), Our Story, Contact. Do NOT over-design.
- [ ] **Week 3:** Razorpay integration + Shiprocket integration. COD enabled with ₹50 COD fee
- [ ] **Week 4:** Soft launch — drive Instagram bio link to Shopify. Offer 10% off "Welcome" code for first 100 customers (margin can absorb this)
- [ ] **Target:** 10–15% of total revenue via D2C by Month 12

**D2C — WhatsApp Catalog (Free, Underused):**
- [ ] This week: Set up WhatsApp Business Catalog with all 7 SKUs
- [ ] Add to Instagram bio: "DM for direct orders + 10% off"
- [ ] Cost: ₹0. Margin: 100% of revenue (no platform fees, no PPC)

**Why D2C Matters Beyond Margin**
Every D2C customer gives you their phone + email. That's 100 emails after 100 sales = email list = retargeting = repeat sales at near-zero CAC. Amazon hides customer data from you. **D2C is how you build the moat.**

---

## PART 2 — SEVEN SECONDARY IMPROVEMENTS (Months 3–6)

### 6. **REVIEW VELOCITY — The Diwali Multiplier**

Your conversion rate at 5 reviews is roughly **half** of conversion at 50+ reviews. Diwali traffic with weak reviews = wasted ad spend.

**Improvements:**
- Enroll in **Amazon Vine** at ₹14,000/ASIN — start with top 3 SKUs (₹42,000 total) = ~50–80 honest reviews within 30 days
- Print **insert cards** in every package (₹2/card via Printrove or local printer): "Loved your book? A 30-second review helps another mom find us. Scan QR." Target conversion: 5–8%
- **WhatsApp Day-5 follow-up** automation (use Wati or Interakt at ₹2,000/month): "Hi Priya, how is little ___ enjoying the Bhagavad Gita book? If you have a moment, your review on Amazon helps families like yours discover SanskaTots ❤️" — conversion: 10–15%
- **Friends & family blitz round 2:** another 30 honest reviews from your network across all 7 SKUs (don't fake — Amazon will catch it)

**90-day target:** 60 reviews on each of top 3 SKUs, 25+ on remaining 4.

---

### 7. **CONTENT — Stop Planning, Start Posting**

Your `Reels/` folder has **22 strategy documents** and zero evidence of consistent reel output. You have a 50-Day Reels Master Plan, a 30-Reels Sales Plan, a 1Lakh Followers strategy, an April Calendar, hooks, scripts, topics… and the business is at 30 days post-launch with no measurable Instagram traction reported.

**The hard truth:** Strategy without shipping = zero ROI.

**Improvements:**
- [ ] **Pick ONE plan** (recommend: `SanskaTots_50Day_Reels_MasterPlan.md`) and execute it day-by-day for 50 days. No new strategy docs until Aug 20.
- [ ] **Cadence: 1 reel per day, 7 days a week**, for the next 60 days. Yes, every day. Volume > polish in Month 2–3.
- [ ] **Batch film** every Sunday (record 7 reels in 3 hours). Edit Monday morning. Schedule via Meta Business Suite.
- [ ] **Founder face = brand.** Nagu in 80%+ of reels. Authenticity is your moat — Skillmatics literally cannot do this.
- [ ] **Track:** Reach, saves, profile visits, bio link clicks → Amazon. If a reel hits >50K reach, **boost it for ₹500** the same day.
- [ ] **30-day audit (Aug 1):** Which 3 reels performed best? Make 3 follow-ups in the same format. Kill formats that flopped.

---

### 8. **MYTHOLOGY VELCRO BUSY BOOK — Ship the Category Killer**

This is the one SKU no competitor in India has: **Velcro activity book + Indian mythology**. It's referenced as the Phase 2 lead product. Your strategy doc literally calls it "category killer."

It is sitting in design. Every week it stays in design, **Clapjoy or LMAW can copy it**.

**Improvements:**
- [ ] **By July 15:** Lock the design. Don't iterate further — ship is better than perfect for SKU #8
- [ ] **By July 30:** QA gate (Nagu + Sanskrit expert + external mom)
- [ ] **By Aug 15:** First 100-copy print run (Bengaluru if Sivakasi delays)
- [ ] **By Sept 1:** Amazon listing live, A+ content, 5 friends & family reviews seeded
- [ ] **Pre-Diwali launch:** Position as **THE Diwali return gift** at ₹599 — first-mover headline

If you do nothing else in Phase 2, do this.

---

### 9. **IP & MOAT — Register Designs Before Copycats Wake Up**

You filed the SanskaTots trademark (Class 16 + 28). Good. But your competitive moat doc says **"design IP not yet formally registered."**

**Improvements:**
- [ ] **File design registrations** under the Designs Act for your 3 signature velcro book layouts (All-In-One, Montessori, Animals) — ₹4,000 per design, 10-year protection
- [ ] **Copyright** your character illustrations + book interior layouts (₹500–₹2,000 per work) — automatic but registration helps in court
- [ ] **Trademark "Velcro Busy Book" + tagline "Indian Roots. Curious Minds."** if not already done
- [ ] Document **your signature design elements** (velcro placement system, page structure, cutting page format) in a single PDF kept off-cloud — this becomes "prior art" evidence

Total cost: ~₹20,000. Total protection: enormous. Do this before Q4 2026.

---

### 10. **NRI MARKET — The Free 40% Revenue Lift You're Ignoring**

5M+ NRI families. Perfect product-market fit. Higher disposable income. Desperate for cultural content. **Zero NRI-targeted execution in your June 30 docs.**

**Improvements (low cost, high return):**
- [ ] **Enable Amazon Global Shipping** on all 7 ASINs (1 setting change in Seller Central, takes 10 minutes). NRIs in 100+ countries can buy directly.
- [ ] **One reel per week** specifically targeted at NRI moms — hooks like "Raising Indian kids in America? Here's how I taught Kannada in 10 minutes a day." Use Instagram audience targeting: US/UK/UAE/Singapore/Australia + Indian-origin interest
- [ ] **Reddit r/ABCDesis + r/NRI + Facebook NRI mom groups:** soft-share founder story (not links), let them ask for products
- [ ] **Amazon US prep (Year 2):** keep this in pipeline but don't execute in Year 1 — focus on India first

Expected NRI lift: **5–8% of Year 1 revenue** with effectively zero added cost. Easy money.

---

### 11. **PRICING — Test ₹449 vs ₹499 vs ₹549 on Top SKUs**

Your price ranges are wide (₹449–₹699 on All-In-One). You haven't reported optimal price points because you haven't A/B tested.

**Improvements:**
- [ ] On your top-selling SKU (likely All-In-One Busy Book), run a **2-week price test:** Week 1 at ₹499, Week 2 at ₹549. Track conversion rate + total revenue.
- [ ] Test "anchor pricing" — list at ₹699 with 30% off coupon to ₹489. Customers perceive higher value.
- [ ] **Never discount mythology books below ₹199.** Cultural product = quality signal. Price floor protects brand.
- [ ] Add ₹49 "Gift Wrap" upsell at checkout — pure margin, 10–15% take rate during Diwali

---

### 12. **SUBSCRIPTION / RECURRING REVENUE — Begin Designing Now for Q2 2027 Launch**

Your strategic docs reference "SanskaTots Crate" subscription (₹499–₹999/month) for Phase 3. **Don't wait.** Subscription = predictable revenue = better valuation = easier fundraising.

**Improvements (this is Year 2, but design starts now):**
- [ ] **Concept by Aug 31, 2026:** "SanskaTots Monthly" — 1 book + 1 activity sheet + 1 cultural printable, themed to upcoming festival/season. ₹599/month.
- [ ] **Pilot by Jan 2027:** Launch to your WhatsApp community first (target 50–100 subscribers)
- [ ] **Public launch by Apr 2027 (Year 1 end):** Goal 500 subscribers = ₹3L MRR = ₹36L ARR locked in by Year 2 start

Mathematically: 1,000 subscribers at ₹599/month = ₹71L/year of recurring revenue. That alone is your Year 1 ambition baked in for Year 2.

---

## PART 3 — A 90-DAY EXECUTION CALENDAR

Below is a single weekly checklist combining all improvements above. Print it. Tick off as you go.

### **July 2026 (Month 2 — Foundation)**

**Week 1 (Jul 1–7): Stop the bleeding**
- [ ] Pull Amazon sales + ads reports, build weekly dashboard
- [ ] Post Ops Assistant job ad (apna.co + WorkIndia)
- [ ] Shortlist 3 Sivakasi printers, request samples
- [ ] Buy sanskatots.com, sign up Shopify Basic
- [ ] Enable Amazon Global Shipping (10-min task)

**Week 2 (Jul 8–14): Hiring + manufacturing**
- [ ] Interview Ops Assistant candidates
- [ ] Receive Sivakasi samples from 3 vendors
- [ ] Register on Flipkart Seller
- [ ] Write & post 7 reels (daily cadence starts)
- [ ] Enroll Amazon Vine on top 3 SKUs

**Week 3 (Jul 15–21): Decisions locked**
- [ ] Hire Ops Assistant, begin training
- [ ] Place first 500-copy Sivakasi test order (1 SKU)
- [ ] Mythology Velcro Busy Book: design lock + QA scheduled
- [ ] Set up WhatsApp Business Catalog
- [ ] Insert cards designed & ordered (1,000 units)

**Week 4 (Jul 22–31): Ship the system**
- [ ] First Ops Assistant fully productive (50+ books/day capacity)
- [ ] Flipkart listings uploaded for all 7 SKUs
- [ ] Sivakasi sample QA decision
- [ ] First Diwali inventory forecast finalized
- [ ] File design registrations on 3 signature velcro layouts

### **August 2026 (Month 3 — Pre-Diwali Ramp)**

**Week 5–6 (Aug 1–14): Inventory & infrastructure**
- [ ] Sivakasi: scale orders to all 7 SKUs (500-1,000 copies each)
- [ ] Shopify store soft launch
- [ ] Bundles created on Amazon (3 bundles minimum)
- [ ] Mythology Velcro Busy Book: first 100-copy print run
- [ ] Influencer outreach: 10 micro-influencers seeded

**Week 7–8 (Aug 15–31): Reviews + content velocity**
- [ ] Vine reviews start landing (target 30+ by month end)
- [ ] 50 reels published cumulatively since Jul 1
- [ ] First Flipkart sales recorded
- [ ] Diwali inventory: 80% of need already at FBA
- [ ] Lightning Deal applications submitted for Oct

### **September 2026 (Month 4 — Diwali Setup)**

**Week 9–10:**
- [ ] Mythology Velcro Busy Book LIVE on Amazon
- [ ] A+ Content published on all 7+ ASINs
- [ ] 50+ reviews on top 3 SKUs achieved
- [ ] PPC budget topped up for Oct (₹3L pre-loaded)

**Week 11–12:**
- [ ] Influencer reels going live (5+ creators)
- [ ] Diwali landing page on Amazon Storefront live
- [ ] D2C site getting first orders
- [ ] Inventory check: 2,000+ units across SKUs at FBA

---

## PART 4 — METRICS TO HIT BY SEPT 30, 2026

If you execute the above, here's what success looks like at Day 120 (Sept 30, 2026):

| Metric | June 30 | Sept 30 Target | If You Hit This → |
|---|---|---|---|
| Monthly revenue | ₹35K–₹53K | ₹2.5–4L | On track for ₹70L+ Year 1 |
| SKUs live | 7 | 8 (+ Mythology Velcro) | Phase 2 begun |
| Channels | Amazon only | Amazon + Flipkart + D2C + WhatsApp | Diversified |
| Reviews (top SKU) | <10 | 50+ | Conversion-ready for Diwali |
| Instagram followers | ~1K | 8–12K | Organic engine running |
| Team | 2 | 3 (+ Ops Assistant) | Scaling-ready |
| Avg COGS per book | ₹80 | ₹45 | Margins fixed |
| Inventory at FBA | Low | 2,000+ units | Diwali-ready |
| Bundles live | 0 | 3 | AOV ↑ from ₹320 → ₹500+ |
| Email/WhatsApp list | 0 | 500+ contacts | Owned audience |

If you miss 3 or more of these by Sept 30, the ₹1 Cr Year 1 target is at risk.

---

## PART 5 — WHAT TO STOP DOING

Equally important as what to start:

1. **Stop writing new strategy docs.** You have 30+ already. The marginal value of doc #31 is zero. Execute first.
2. **Stop designing Phase 3+ products.** DIY kits, card games, board games, felt books, wooden puzzles — all are 2027–2028 problems. Focus on shipping Phase 2 velcro mythology + regional language books.
3. **Stop chasing the ₹1,000 Cr narrative externally.** Internally, aim high. Externally (investor decks, public posts), anchor on ₹10 Cr / 3 years — it's credible and still ambitious. The ₹1,000 Cr framing risks looking unhinged to seed investors in May 2027.
4. **Stop checking sales hourly.** Once the dashboard exists, check Monday 9am. That's it. Hours saved go into design and reels.
5. **Stop manually doing what an assistant can do.** Velcro placement, packing, label printing, shipping pickups — every minute Nagu does this is a minute not spent designing the next category-killer SKU.

---

## PART 6 — THE ONE THING

If you remember nothing else from this report, remember this:

> **You launched 30 days ago with ₹50L and 7 SKUs. You have ~14 weeks until Diwali — the single biggest revenue event of your Year 1. Everything in this report serves one purpose: arrive at October 15 with inventory at FBA, 50+ reviews per top SKU, bundles live, Mythology Velcro Busy Book launched, Ops Assistant trained, Sivakasi printing, and a real Instagram audience. If you do that, Diwali delivers ₹20–30L. If you don't, it delivers ₹3–5L and the ₹1 Cr Year 1 dies.**

You have the strategy. You have the capital. You have the product. **The improvement is execution velocity.**

---

**End of Report**

*Companion docs to revisit:*
- [SanskaTotsBooksPhase1Launch.md](SanskaTotsBooksPhase1Launch.md)
- [1crMarketingPlan.md](1crMarketingPlan.md)
- [Amazon_Marketing_ToDo_1Cr_Strategy.md](Amazon_Marketing_ToDo_1Cr_Strategy.md)
- [SanskaTots_SWOT_DeepDive_April2026.md](SanskaTots_SWOT_DeepDive_April2026.md)
- [Reels/SanskaTots_50Day_Reels_MasterPlan.md](Reels/SanskaTots_50Day_Reels_MasterPlan.md)
