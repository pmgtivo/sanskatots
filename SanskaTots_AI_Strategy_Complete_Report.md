# SanskaTots — Complete AI Strategy Report
## How AI Can Accelerate Every Department | Deethya Enterprises | June 2026

---

## Executive Summary

SanskaTots is a 2-person team with 40+ book designs, a June 2026 Amazon launch, and a path to ₹1,000 Cr. The existential bottleneck is **people bandwidth**. AI is the force multiplier that lets a 2-person team operate like a 20-person team — across sales, marketing, operations, content, product development, and production — without proportional cost.

This report maps every department to specific AI tools and **custom-coded solutions your engineering team can build** to save money and build proprietary advantage.

---

## Department Map

| # | Department | AI Opportunity | Engineering Build Possible |
|---|---|---|---|
| 1 | Sales & Amazon | High | Yes |
| 2 | Content Creation | Very High | Yes |
| 3 | Operations | High | Yes |
| 4 | Production & Manufacturing | Medium | Yes |
| 5 | Product Innovation | Very High | Yes |
| 6 | Customer Support | High | Yes |
| 7 | Finance & Reporting | Medium | Yes |

---

## Part 1 — Sales & Amazon (Highest Priority)

### 1.1 Amazon Listing Optimization with AI

**Problem:** Amazon A9 algorithm rewards keyword-rich listings, but manual keyword research is slow and guesswork-driven.

**AI Solution:**
- Use **Helium 10 AI** + **ChatGPT** to generate keyword-optimized bullet points for every book
- Run A/B tests on titles using Amazon's Manage Your Experiments (once eligible)
- Use AI to generate 5 listing variations per book and pick the highest CTR version

**Prompt template to use today (free):**
```
Act as an Amazon India listing expert for children's educational books.
Product: [Book Name], [brief description].
Target customer: Indian mothers, 25-35 years, Tier 1 cities, toddlers 1.5-3 years.
Write 5 keyword-rich bullet points (200 chars each), include keywords:
activity book for toddlers, busy book, preschool learning, [regional language], Indian mythology.
```

**Engineering Build — Amazon Keyword Tracker (Cost: ₹0, saves ₹15,000/mo vs Helium 10):**
```python
# Tool: Amazon Keyword Rank Tracker
# Stack: Python + Amazon SP-API + Supabase (free tier)
# What it does: checks your ASINs daily for target keywords, 
#               stores rank history, alerts on rank drops via WhatsApp
# Libraries: python-amazon-sp-api, supabase-py, requests
# Time to build: 2-3 days
```

---

### 1.2 AI-Driven Pricing Intelligence

**Problem:** Manually checking competitor prices is time-consuming. Underpricing kills margin; overpricing kills rank.

**Engineering Build — Competitor Price Monitor:**
```python
# Tool: Price Monitor Bot
# Stack: Python + BeautifulSoup/Playwright + Telegram Bot
# What it does:
#   - Scrapes competitor ASINs every 6 hours
#   - Compares against SanskaTots pricing
#   - Sends Telegram alert when a competitor drops price by >10%
#   - Logs price history in SQLite for trend analysis
# Time to build: 1-2 days
# Cost saved: ₹8,000–12,000/mo vs commercial tools
```

---

### 1.3 AI Review Management

**Problem:** Responding to every Amazon review manually is slow and inconsistent. Negative reviews need instant professional responses.

**Engineering Build — AI Review Responder:**
```python
# Tool: Auto Review Monitor + AI Draft Responder
# Stack: Python + Amazon SP-API + OpenAI API (or local Ollama — FREE)
# What it does:
#   - Pulls new reviews via SP-API every hour
#   - For 1-3 star reviews: generates empathetic response draft, sends for human approval
#   - For 4-5 star reviews: auto-thanks with brand voice
#   - Tags reviews by topic (shipping, quality, content accuracy)
# Monthly cost: ~₹500 (OpenAI) or ₹0 (local LLM via Ollama)
# Time to build: 2-3 days
```

---

### 1.4 Sales Forecasting

**Engineering Build — Demand Forecast Dashboard:**
```python
# Tool: Sales Forecast + Reorder Alert
# Stack: Python + Prophet (Facebook's forecasting library) + Streamlit dashboard
# What it does:
#   - Ingests Amazon sales CSV exports
#   - Forecasts next 30/60/90 days demand per SKU
#   - Alerts when inventory will hit zero (with buffer days configurable)
#   - Shows seasonal trends (Diwali, school admission season spikes)
# Time to build: 3-4 days
# Libraries: prophet, pandas, streamlit, plotly
# Cost: ₹0 (all open source)
```

---

### 1.0 Book Design Validator (Engineering Build — Available Now)

**Problem:** Before sending a book to print, you need to manually check every page for spelling errors, text outside safe zones, overlapping elements, and design issues. This is slow and things get missed.

**Engineering Build — PDF Book Validator:**
```
Location: tools/book_validator/
Run:      streamlit run app.py
```
**What it checks (per page):**
- **Spelling** — flags English misspellings; ignores Sanskrit/Kannada/Hindi words automatically
- **Alignment** — text outside 8% safe zone (will be cut in print), overlapping text blocks, images bleeding off page, font size < 7pt
- **AI Visual Review** — sends each page to GPT-4o Vision: design contrast, readability for children, print risk, content accuracy
- **Annotated Output** — renders each page with colored bounding boxes (red = error, orange = warning) so you see exactly where each issue is
- **Export** — downloadable .txt report of all issues

**Cost:** ₹0.50–1.50 per page for AI review. Spell + alignment checks are fully free/offline.

---

## Part 2 — Content Creation (Biggest Leverage for a 2-Person Team)

### 2.1 Reel Script Generation at Scale

**Problem:** Creating 15–20 reels/month manually burns founder time. Each script takes 1–2 hours.

**AI Workflow (saves 20–30 hours/month):**
1. **ChatGPT / Claude** → Generate 10 reel concepts from a single brief
2. **ElevenLabs** → AI voiceover in founder's voice (clone after 5 min sample)
3. **CapCut AI** → Auto-captions, transitions, music sync
4. **Canva AI** → Thumbnail and cover graphics in brand colors

**Engineering Build — Content Calendar Generator:**
```python
# Tool: Monthly Content Plan Generator
# Stack: Python + OpenAI API + Google Sheets API
# What it does:
#   - Takes month theme, product focus, upcoming events (festivals, school seasons)
#   - Generates 30-day content calendar: topic, hook, format, CTA for each post
#   - Auto-populates Google Sheet with ready-to-execute briefs
#   - Tags which content needs filming vs. can be static
# Time to build: 1-2 days
# Monthly cost: ~₹200 (API calls)
```

---

### 2.2 AI-Powered Instagram Caption Engine

**Engineering Build — Caption Generator Web App:**
```javascript
// Tool: SanskaTots Caption Generator
// Stack: Next.js + OpenAI API
// Interface: Simple web form — choose book, choose tone (emotional/educational/cultural),
//            choose CTA (buy link / DM / save), hit generate
// Output: 3 caption variants + 30 hashtags
// Saves: 30 min per post × 20 posts = 10 hours/month
// Deploy free on: Vercel
```

---

### 2.3 YouTube + Shorts Repurposing

**AI Tool Stack (no coding needed):**
- **Opus Clip** → Auto-clips best moments from long videos into 30 Shorts
- **Descript** → AI removes filler words ("um", "uh") from founder videos automatically
- **Pictory** → Convert blog posts / book descriptions into narrated video shorts

---

### 2.4 AI Product Photography

**Problem:** Professional photoshoots cost ₹15,000–₹30,000 per session. Amazon requires lifestyle images.

**Solution:**
- **Photoroom AI** → Remove backgrounds, add professional studio backgrounds
- **Adobe Firefly** → Generate lifestyle mockup images: "child's hand using Montessori Busy Book on wooden table, morning light, Indian home background"
- Cost: ₹0–₹1,500/mo vs. ₹15,000+ for photoshoots

**Engineering Build — Bulk Image Processor:**
```python
# Tool: Product Image Batch Processor
# Stack: Python + Pillow + Rembg (open-source background remover)
# What it does:
#   - Takes raw book photos from a folder
#   - Removes background (free, local, no API cost)
#   - Adds white/lifestyle background
#   - Resizes to Amazon specs (2000×2000px, <10MB)
#   - Exports all 7 Amazon image slots ready to upload
# Time to build: 1 day
# Cost: ₹0
```

---

### 2.5 AI-Generated WhatsApp Marketing Messages

**Engineering Build — WhatsApp Broadcast Composer:**
```python
# Tool: WhatsApp Campaign Writer
# Stack: Python + OpenAI API + WhatsApp Business API (or Wati.io)
# What it does:
#   - Generates 5 message variants per campaign (festival sale, new launch, review ask)
#   - Tests message length, emoji use, CTA phrasing
#   - Schedules sends based on best open-time data (Indian moms: 9–11 AM, 8–10 PM)
#   - Tracks link clicks per variant
# Monthly cost: ~₹500 (API) + ₹1,500 (Wati.io free tier)
```

---

## Part 3 — Operations

### 3.1 Inventory & Procurement Automation

**Engineering Build — Inventory Management System (IMS):**
```python
# Tool: Sanskatots IMS
# Stack: Python + FastAPI + SQLite (upgrade to PostgreSQL later) + Streamlit UI
# Features:
#   - Track stock per SKU across: Amazon FBA warehouse, home stock, printer inventory
#   - Auto-generate purchase orders when stock hits reorder point
#   - Connect to Amazon SP-API to sync real-time FBA stock levels
#   - Print-ready PDF PO for your printer partner in Bengaluru
#   - Monthly P&L per SKU (COGS vs. revenue)
# Time to build: 5-7 days
# Cost: ₹0 (replaces ₹5,000–10,000/mo IMS SaaS tools)
```

---

### 3.2 AI for GST & Accounting

**Problem:** GST filings, GSTR-1, GSTR-3B are manual and error-prone for a new business.

**AI + Engineering Solution:**
- **Zoho Books** has AI-powered GST automation (₹999/mo) — recommended first
- **Engineering alternative:** Python script to parse Amazon settlement reports and auto-classify transactions for GST (saves CA 2–3 hours/month = ₹3,000–5,000/filing)

**Engineering Build — Amazon Settlement Parser:**
```python
# Tool: Amazon Settlement Report → GST Classifier
# Stack: Python + pandas
# What it does:
#   - Reads Amazon Seller Central settlement CSVs
#   - Classifies each transaction: book sale (0% GST), service fee (18% GST)
#   - Generates GSTR-1 ready summary: state-wise sales (IGST/CGST/SGST)
#   - Exports Excel for CA
# Time to build: 1-2 days
# Saves: ₹3,000–5,000/month in CA fees
```

---

### 3.3 Shipping & Logistics AI

**Engineering Build — Shipment Tracker Dashboard:**
```python
# Tool: Order Fulfillment Tracker (for D2C / non-FBA orders)
# Stack: Python + Shiprocket API + Telegram Bot
# What it does:
#   - Pulls all active shipments
#   - Detects stuck shipments (no update >48 hours)
#   - Auto-generates customer proactive update messages
#   - Daily 8 AM summary sent to founder WhatsApp
# Time to build: 1-2 days
```

---

## Part 4 — Production & Manufacturing

### 4.1 AI in Book Design & Iteration

**Problem:** Designing new book pages takes hours per page. With 40+ books and more planned, this is a bottleneck.

**AI Tools for Design:**
- **Adobe Firefly (Illustrator AI)** → Generate base illustrations: "Indian girl playing with abacus, flat design, vibrant colors, no background"
- **Midjourney / DALL-E 3** → Rapid concept sketches for new book themes before committing to full design
- **Canva Magic Studio** → Templated book page layouts with AI-generated elements

**Workflow:**
```
AI generates concept art (10 min) → 
Designer refines in Illustrator (2 hours vs. 6 hours from scratch) → 
Review → Print
```
**Time saved per page: 3–4 hours. Across 200 pages: 600–800 hours saved.**

---

### 4.2 Print Quality Control via AI Vision

**Problem:** Manually checking printed pages for defects (color mismatch, misalignment, cut errors) is slow and misses issues.

**Engineering Build — Print QC Tool:**
```python
# Tool: Print Quality Checker
# Stack: Python + OpenCV + PIL
# What it does:
#   - Compares scanned printed page against original design PDF
#   - Detects: color deviation >10%, text blurriness, alignment shift
#   - Outputs pass/fail with highlighted defect zones
#   - Works with a ₹3,000 document scanner
# Time to build: 3-4 days
# Replaces: Manual QC that misses ~15% of defects
```

---

### 4.3 AI-Optimized Print Ordering

**Engineering Build — Print Cost Calculator:**
```python
# Tool: Print Cost Optimizer
# Stack: Python + Streamlit
# What it does:
#   - Input: book specs (pages, size, paper type, qty)
#   - Queries 3 Bengaluru printer rate cards (stored in config)
#   - Calculates total cost, per-unit cost, margin at different price points
#   - Recommends optimal order quantity for 45% margin target
#   - Shows breakeven units on Amazon at current pricing
# Time to build: 1 day
```

---

## Part 5 — Product Innovation & New Product Lines

### 5.1 AI for Market Gap Discovery

**The Opportunity:** SanskaTots has 40+ books ready but needs to prioritize what to launch next. AI can surface what the market is missing.

**Engineering Build — Amazon Market Gap Finder:**
```python
# Tool: Product Opportunity Scanner
# Stack: Python + Selenium/Playwright + OpenAI API
# What it does:
#   - Scrapes top 50 results for target keywords on Amazon India
#   - Extracts: title, price, reviews, rating, BSR
#   - Sends to GPT-4: "What customer needs are NOT being met by these products?"
#   - Returns: gaps in age groups, themes, languages, formats
#   - Generates 10 new product ideas with estimated demand
# Time to build: 3-4 days
# Monthly cost: ~₹1,000 (API calls)
```

**Immediate AI Analysis (Run Now):**
Product gaps AI identifies consistently in Indian kids' books market:
- Tamil, Telugu, Malayalam busy books (zero competition, 150M+ speaker base)
- Islamic mythology books (underserved but large market)
- Busy books for 3–5 year age group (currently all 1–3)
- Write & Wipe reusable formats (Skillmatics dominates but lacks Indian themes)
- Prenatal/newborn sensory books (emerging trend, zero Indian cultural content)

---

### 5.2 AI-Powered Customer Feedback → Product Brief

**Engineering Build — Review → Product Brief Generator:**
```python
# Tool: Review Intelligence → New Product Ideas
# Stack: Python + Amazon SP-API + OpenAI API
# What it does:
#   - Collects all reviews mentioning "wish", "if only", "next time", "would love"
#   - Groups by theme using GPT-4 clustering
#   - Generates structured product brief: target age, format, content theme, price point
#   - Outputs as Notion page or Google Doc
# Time to build: 2-3 days
# This is your unfair advantage: building products your customers explicitly asked for
```

---

### 5.3 New Product Categories to Explore (AI-Researched)

Based on Amazon India trend data and SanskaTots' competencies:

| Category | AI Research Score | Engineering Needed | Timeline |
|---|---|---|---|
| Regional Language Flash Cards (Kannada, Tamil, Telugu) | ★★★★★ | No | Q3 2026 |
| Reusable Write & Wipe Activity Mats | ★★★★☆ | No | Q4 2026 |
| Hindu Festival Activity Kits (Diwali, Navratri) | ★★★★★ | No | Q3 2026 (Diwali timing) |
| Shloka Audio Cards (NFC-enabled) | ★★★☆☆ | Yes (NFC + app) | Q1 2027 |
| Personalized Activity Books (child's name printed) | ★★★★☆ | Yes (print automation) | Q4 2026 |
| Wooden Toy + Book Bundles | ★★★★☆ | No | Q2 2027 |

---

### 5.4 Personalized Books — Engineering Build

This is a **major revenue opportunity** and requires engineering:

```python
# Tool: Personalized Book Generator
# Stack: Python + PIL/ReportLab + FastAPI + Razorpay + WhatsApp delivery
# What it does:
#   - Customer orders on website/WhatsApp: "Arjun, age 2, Kannada book"
#   - System inserts child's name into pre-designed book template
#   - Generates print-ready PDF automatically
#   - Sends to printer via email (auto-generated PO)
#   - Confirms delivery timeline to customer via WhatsApp
# Revenue opportunity: ₹100–200 premium per personalized book vs. standard
# Time to build: 5-7 days
# This is a MOAT — Amazon can't replicate personalized books at scale
```

---

## Part 6 — Customer Support & CRM

### 6.1 AI WhatsApp Support Bot

**Engineering Build — WhatsApp Customer Support Bot:**
```javascript
// Tool: SanskaTots WhatsApp AI Bot
// Stack: Node.js + WhatsApp Business API + OpenAI API
// Handles:
//   - "Where is my order?" → Queries Shiprocket API, replies with tracking link
//   - "Can I return this?" → Returns policy statement
//   - "Which book for 2-year-old?" → Age-based book recommendation flow
//   - "Custom book with my child's name?" → Collects details, routes to founder
// Escalation: Tags unresolved chats for human follow-up
// Time to build: 3-5 days
// Saves: 2-3 hours/day of founder time
```

---

### 6.2 AI Customer Segmentation & Retention

**Engineering Build — Customer Intelligence Dashboard:**
```python
# Tool: Customer Lifecycle Tracker
# Stack: Python + pandas + Streamlit
# Data sources: Amazon orders CSV + WhatsApp purchase list
# Segments automatically:
#   - One-time buyers (target with new launch campaigns)
#   - Repeat buyers (offer loyalty discount, early access)
#   - High-value NRI customers (premium pricing, gift bundles)
#   - Churned (no purchase >90 days) → Win-back campaign
# Output: Ready-to-send WhatsApp message list per segment
# Time to build: 2-3 days
```

---

### 6.3 AI-Powered Review Solicitation

**Engineering Build — Post-Purchase Review Funnel:**
```python
# Tool: Smart Review Request Bot
# Stack: Python + Amazon SP-API + Twilio (WhatsApp)
# What it does:
#   - 7 days after delivery: "How is [Book Name] going?"
#   - If positive response → Direct to Amazon review link
#   - If negative → Escalate to founder immediately (protect rating)
#   - Tracks review conversion rate per campaign variant
# Time to build: 2-3 days
# Impact: 3× increase in review velocity (critical for Amazon rank)
```

---

## Part 7 — Marketing Intelligence

### 7.1 AI Influencer Matching

**Problem:** Finding the right mom influencers manually takes days of scrolling.

**Engineering Build — Influencer Finder:**
```python
# Tool: Instagram Mom Influencer Scraper + Scorer
# Stack: Python + Instagram Graph API / Apify + GPT-4
# What it does:
#   - Searches hashtags: #momsofinstagram #indianmom #toddlermom #bengaluruparents
#   - Filters: 5K–200K followers, engagement rate >3%, posts in last 30 days
#   - GPT-4 scores profile: cultural fit with SanskaTots (1–10)
#   - Exports: name, follower count, email (if public), fit score, DM template
# Time to build: 2-3 days
# Replaces: ₹5,000–10,000/mo influencer platform subscriptions
```

---

### 7.2 AI Competitor Intelligence

**Engineering Build — Weekly Competitor Report:**
```python
# Tool: Competitor Weekly Intelligence Report
# Stack: Python + Playwright + OpenAI API
# Monitors:
#   - Top 10 competitor ASINs (Skillmatics, Dreamland, local sellers)
#   - Tracks: price changes, new reviews, new products launched, BSR movement
#   - GPT generates 1-page "What changed this week + recommended SanskaTots response"
#   - Delivered every Monday 9 AM to founder WhatsApp
# Time to build: 3-4 days
```

---

### 7.3 Ad Copy Generator

**Engineering Build — Amazon & Instagram Ad Copy Tool:**
```python
# Tool: Ad Copy Generator
# Stack: Python + OpenAI API + Streamlit UI
# Input: Product name, target emotion, offer, platform
# Output: 
#   - 5 Amazon Sponsored Product ad headlines
#   - 3 Instagram ad primary texts (with hook + CTA)
#   - 2 WhatsApp broadcast messages
# Time to build: 1 day
# Saves: ₹15,000–25,000/mo in copywriting costs
```

---

## Part 8 — Finance & Reporting

### 8.1 Automated P&L Dashboard

**Engineering Build — Business Intelligence Dashboard:**
```python
# Tool: SanskaTots Business Dashboard
# Stack: Python + Streamlit + Plotly + pandas
# Data: Amazon settlement CSVs + manual expense entries
# Shows:
#   - Revenue per SKU per day/week/month
#   - Gross margin per book (COGS breakdown: print + velcro + shipping + Amazon fees)
#   - Ad spend vs. revenue (ACOS)
#   - Cash flow forecast (30/60/90 days)
#   - Inventory value at cost
# Time to build: 4-5 days
# Replaces: Manual Excel work (2-3 hours/week)
```

---

### 8.2 Investor-Ready Reporting (For Fundraising)

**Engineering Build — Investor Metrics Auto-Report:**
```python
# Tool: Monthly Investor Update Generator
# Stack: Python + OpenAI API + python-pptx / reportlab
# What it does:
#   - Pulls metrics from dashboard
#   - GPT writes narrative: "This month we grew 23% MoM driven by..."
#   - Generates PDF investor update automatically
#   - Maintains metric history for trend charts
# Time to build: 2-3 days
# Use case: Critical for Shark Tank / Angel investor communication
```

---

## Part 9 — AI Tools Master Stack (Categorized by Cost)

### Free / Open-Source (Recommended First)
| Tool | Use | Save vs. Paid |
|---|---|---|
| Ollama (LLaMA 3, Mistral) | Local AI — runs on laptop, no API cost | ₹5,000–10,000/mo |
| Rembg | Background removal for product photos | ₹1,500/mo |
| Prophet | Sales forecasting | ₹3,000/mo |
| Streamlit | Internal dashboards | ₹5,000/mo |
| CapCut | Reel editing with AI captions | ₹1,200/mo |

### Low Cost (< ₹2,000/month)
| Tool | Cost | Use |
|---|---|---|
| OpenAI API (GPT-4o mini) | ~₹500–1,500/mo | Content, copy, analysis |
| ElevenLabs | ₹850/mo | AI voiceover for Reels |
| Canva Pro | ₹4,000/yr | Design + AI Magic Studio |
| Photoroom Pro | ₹1,200/mo | Product photography |

### Mid-Tier (₹2,000–5,000/month — Defer until ₹5 Lakh/mo revenue)
| Tool | Cost | Use |
|---|---|---|
| Descript | ₹2,400/mo | Video editing, transcription |
| Helium 10 | ₹4,500/mo | Amazon keyword research |
| Opus Clip | ₹2,000/mo | Auto-clip long videos to Shorts |

---

## Part 10 — Engineering Build Roadmap

### Sprint 1 — Week 1–2 (Highest ROI)
| Build | Time | Impact |
|---|---|---|
| Amazon Settlement → GST Parser | 1–2 days | Saves ₹3,000–5,000/filing |
| Bulk Product Image Processor | 1 day | Saves ₹15,000/photoshoot |
| Ad Copy Generator (Streamlit) | 1 day | Saves ₹15,000/mo |
| Print Cost Calculator | 1 day | Better margin control |

### Sprint 2 — Week 3–4
| Build | Time | Impact |
|---|---|---|
| Sales Forecast Dashboard | 3–4 days | Never stockout / overstock |
| Competitor Price Monitor | 2 days | Pricing intelligence |
| WhatsApp Review Request Bot | 2–3 days | 3× review velocity |
| Content Calendar Generator | 1–2 days | 10 hours/month saved |

### Sprint 3 — Month 2
| Build | Time | Impact |
|---|---|---|
| Amazon Keyword Rank Tracker | 2–3 days | Replaces ₹4,500/mo Helium 10 |
| Inventory Management System | 5–7 days | Operational backbone |
| AI Review Responder | 2–3 days | Brand reputation management |
| Customer Segmentation Dashboard | 2–3 days | Retention marketing |

### Sprint 4 — Month 3 (Moat Builders)
| Build | Time | Impact |
|---|---|---|
| Personalized Book Generator | 5–7 days | ₹100–200 premium per order, zero competition |
| WhatsApp AI Support Bot | 3–5 days | Saves 2–3 hrs/day founder time |
| Influencer Finder Tool | 2–3 days | Replaces ₹10,000/mo platform |
| Weekly Competitor Report | 3–4 days | Strategic intelligence |

---

## Part 11 — Total Cost Savings from Engineering Builds

| Category | Current Cost (if using SaaS) | Engineering Cost | Monthly Saving |
|---|---|---|---|
| Amazon keyword tool (Helium 10) | ₹4,500/mo | ₹0 (after build) | ₹4,500 |
| Copywriting / ad copy | ₹15,000–25,000/mo | ~₹500 API cost | ₹14,500–24,500 |
| Product photography | ₹15,000/session | ₹0 (rembg + AI) | ₹15,000 |
| Influencer platform | ₹5,000–10,000/mo | ₹0 | ₹5,000–10,000 |
| Competitor intelligence | ₹5,000/mo | ~₹1,000 API cost | ₹4,000 |
| CA / accounting hours | ₹5,000–8,000/mo | ₹0 (scripts handle it) | ₹5,000–8,000 |
| IMS / inventory software | ₹5,000–10,000/mo | ₹0 | ₹5,000–10,000 |
| **Total Monthly Saving** | | | **₹53,000–77,000/mo** |

**That is ₹6–9 Lakhs/year saved — which at a 45% margin means ₹13–20 Lakhs less revenue you need to cover costs.**

---

## Part 12 — AI for the Founder: Daily Workflow

A simple AI-powered daily workflow for a 2-person team:

### Morning (30 minutes)
1. **8:00 AM** — Telegram bot delivers: yesterday's sales, top review, competitor price change alert
2. **8:15 AM** — Review AI-drafted responses to any negative Amazon reviews (approve/edit in 5 min)
3. **8:30 AM** — WhatsApp bot auto-sent review request to customers who received orders 7 days ago

### Midday (20 minutes)
4. **12:00 PM** — Review AI-generated social caption for today's post (approve/tweak in 5 min)
5. **12:15 PM** — AI-drafted WhatsApp broadcast for active campaign is ready to send

### Evening (15 minutes)
6. **7:00 PM** — Dashboard shows daily P&L, stock levels, any reorder needed
7. **7:15 PM** — Review next 3 content ideas generated by AI for this week's reels

**Total active AI management time: 65 minutes/day (down from 5–6 hours/day without AI)**

---

## Summary: Where to Start

**This week (no engineering needed):**
1. Set up ChatGPT for all Amazon listing copy (free, immediate impact)
2. Use Photoroom AI for product images (₹1,200/mo, saves photoshoot cost)
3. Use CapCut AI for reel captions and editing (free tier)
4. Set up ElevenLabs voiceover for reels (₹850/mo)

**This month (engineering builds, Sprint 1):**
1. Amazon Settlement GST Parser (1–2 days, saves money immediately)
2. Bulk Image Processor (1 day, free product photography forever)
3. Ad Copy Generator (1 day, eliminates copywriting cost)
4. Sales Forecast Dashboard (3–4 days, prevents stockouts)

**Within 3 months:**
1. Full Inventory Management System
2. Personalized Book Generator (your biggest competitive moat)
3. WhatsApp AI Support Bot
4. All competitor and keyword intelligence tools running

---

*Report prepared for Deethya Enterprises / SanskaTots — June 2026*
*All cost estimates in INR. Engineering time estimates assume one mid-level Python developer.*
