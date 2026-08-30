# English & Hindi Preschool Ready Busy Book — Aggressive Pre-Print Audit

**File audited:** `English & Hindi Preschool Ready Busy Book.pdf`
**Date:** 25 August 2026 · **Pages:** 27 · **Trim:** 210.1 × 147.9 mm (A5 landscape) · **Colour:** CMYK ✅
**Verdict:** ❌ **DO NOT SEND TO PRINT YET.** 6 blockers, ~20 high-priority fixes.

---

## 0. The Concept Problem You Already Spotted (read this first)

You are right, and it is worse than a naming issue — it is an **active teaching error**.

The book uses Devanagari letters as a *phonetic hint for the English letter*, but places them next to a *Hindi word that starts with a different letter*. On the alphabet cut-out cards (p18–p19), **22 of 26 cards contradict themselves**:

| Card | Devanagari shown | Hindi word printed | Word actually starts with |
|---|---|---|---|
| Aa | अ | सेब | **स** ❌ |
| Bb | ब | केला | **क** ❌ |
| Cc | क | बिल्ली | **ब** ❌ |
| Dd | द | कुत्ता | **क** ❌ |
| Ee | ए | हाथी | **ह** ❌ |
| Ff | फ | मछली | **म** ❌ |
| Gg | ग | अंगूर | **अ** ❌ |
| Hh | ह | मुर्गी | **म** ❌ |
| Ll | ल | शेर | **श** ❌ |
| Mm | म | आम | **आ** ❌ |
| Nn | न | घोंसला | **घ** ❌ |
| Oo | ओ | संतरा | **स** ❌ |
| Pp | प | तोता | **त** ❌ |
| Rr | र | खरगोश | **ख** ❌ |
| Tt | ट | बाघ | **ब** ❌ |
| Uu | उ | छाता | **छ** ❌ |
| Ww | व | घड़ी | **घ** ❌ |

Any Hindi-literate parent, grandparent or preschool teacher will read this as "the publisher does not know Hindi." **This is your #1 one-star-review risk.**

**Additional defects in the same system:**
- **V and W both use the same letter व.** Two different English letters, one Devanagari glyph.
- **The phonetic system is internally inconsistent**: some cards use the letter *sound* (ब, फ, ग, र, स), others use the letter *name* (ए for E, ओ for O, क्यू for Q, क्स for X). Pick one system.
- **K uses क़ (qa, with nukta) — wrong letter.** Should be plain **क**.
- **F uses फ (pha) — wrong.** The English /f/ sound is **फ़** (with nukta). Ironically the nukta is on the letter that shouldn't have it and missing from the one that needs it.
- **D uses द (dental).** English /d/ maps to **ड** (retroflex) in Hindi convention.

### Recommended fix (cheapest, safest)
**Delete the Devanagari letter from every alphabet card.** Keep: big English letter `Aa` + picture + `सेब (Apple)`. The Hindi word then works purely as a *meaning* translation, which is exactly your stated concept — and it becomes 100% correct.

If you want to keep a pronunciation cue, label it explicitly and use letter **names** consistently: `ए (A)`, `बी (B)`, `सी (C)`, `डी (D)`, `ई (E)`, `एफ़ (F)` … `डब्ल्यू (W)` — in small grey type under the English letter, marked `उच्चारण`.

### Also fix the title on p2, p3, p5
The header reads **"वर्णमाला | Learn Alphabet"**. वर्णमाला to an Indian buyer means *Hindi* alphabet. Change to **"अंग्रेज़ी वर्णमाला | Learn English Alphabet"** on all three pages. This single word change prevents a large share of "expected Hindi varnamala, got English" returns.

---

## 1. 🔴 P0 BLOCKERS — Will cost you money if printed as-is

### B1. Zero bleed on a full-bleed book
`MediaBox = TrimBox = BleedBox = 595.5 × 419.25 pt`. **There is no bleed at all.**
Pages 1–16 all have edge-to-edge backgrounds. With normal press trim tolerance (±1–2 mm) you will get **white slivers on the edges of every single page**.
→ Re-export from Canva at **216 × 154.9 mm** (3 mm bleed all round) with crop marks, or ask Canva for "PDF Print → Crop marks and bleed" enabled.

### B2. Marketing claim contradicts the book
- Front cover: **"100+ Reusable Velcro Stickers"**
- Page 17 (internal): **"TOTAL – 95 VELCRO"**
- My own count from the activity pages: 26 (alphabet) + 11 (numbers) + 8 (colours) + 6 (shapes) + 12 (fruit/veg) + 6 (transport) + 7 (farm) + 7 (wild) + 12 (body) = **95**.

**95 ≠ 100+.** This is a false claim on the packaging and on your Amazon/Meesho listing. Either print **"95 Reusable Velcro Stickers"** or add 5+ pieces. Do not ship the overclaim.

### B3. "14 Learning Themes" is also an overclaim
Actual distinct themes: Alphabet, Line Tracing, Alphabet Tracing, Numbers & Counting, Colours, Shapes, Fruits & Vegetables, Transport, Farm Animals, Wild Animals, Body Parts, Five Senses = **12**.
→ Print **"12 Learning Themes"** or add two more spreads.

### B4. Page 17 is an internal production note, not a book page
A blank white page reading **"Book Cuttings / TOTAL – 95 VELCRO"** is a note to your printer/assembler that has ended up in the customer-facing file. It has no design, no page number, and it leaks your BOM.
→ Replace with a properly designed divider: **"कट-आउट स्टिकर शीट्स | Cut-Out Sticker Sheets"** + 3-step usage instructions (cut → stick velcro → play) + a "Adult supervision required" line.

### B5. Trademarked products in the artwork
- **p24 (PINK card):** the shoe has a **clearly visible Nike Swoosh** on both the side panel and the heel.
- **p21 (RECTANGLE card):** a recognisable **iPhone with Apple app icons**.
- **p22:** the motorcycle, car and truck appear to be identifiable licensed vehicle models (Ducati-style fairing / Mazda RX-7-style body / Freightliner-style cab).

Printing third-party trademarks on a commercial product is an infringement exposure and a **guaranteed Amazon IP-complaint takedown**. → Replace all of these with generic assets.

### B6. Page 27 — the elephant has an un-removed background
There is a **visible light-grey rectangular box** around the elephant cut-out (roughly the middle of the page). The background was never knocked out. This will print as an obvious grey rectangle on a white sticker sheet.
→ Re-cut the elephant with a transparent background.

---

## 2. 🟠 P1 HIGH — Fix before print

### Spelling & language errors (confirmed by zoom)

| Page | Printed | Correct | Note |
|---|---|---|---|
| p15 | **सुंघना** | **सूँघना** | Genuine misspelling of the verb "to smell". Appears in the body text of the SMELL card. |
| p24 (Pink) | **फ़राक** | **फ्रॉक** | फ़राक़ means "separation" in Urdu. Wrong word for a frock/dress. |
| p24 (Pink) | **मराल** | **राजहंस** / **फ्लेमिंगो** | मराल = swan, not flamingo. |
| p24 (Blue) | **ब्लूहेल** | **ब्लू व्हेल** / **नीली व्हेल** | "hel" is a mis-transliteration of "whale". |
| p24 (Brown) | **भूरा पाइन शंकु** | **पाइनकोन** / **चीड़ का फल** | Literal machine translation; also the only label that includes a colour word — inconsistent with all other labels. |
| p9 | **घेरा** (Circle) | **वृत्त** or **गोल** | घेरा = enclosure/ring, not the shape "circle". |
| p9 | **डायमंड** | **हीरा** | Raw transliteration where a real Hindi word exists. |
| p21 | **चक्र** (Tyre) | **पहिया** or **टायर** | चक्र is archaic/religious in this context. |
| p21 | **तरबूज टुकड़ा** | **तरबूज़ का टुकड़ा** | Missing the postposition का — grammatically wrong. |
| p21 | **बर्फ़ के छोटे टुकड़े** | **बर्फ़ का टुकड़ा** | Verbose plural for a single ice cube; also set in a much smaller font than every other label on the page. |
| p14 | **पैर = Leg** and **पांव = Foot** | **टाँग = Leg**, **पैर/पाँव = Foot** | पैर and पाँव are synonyms. Teaching them as two different body parts is factually wrong. |
| p11 | **गुब्बारा** (Hot Air Balloon) | **गर्म हवा का गुब्बारा** | गुब्बारा alone = toy balloon. |

### Nukta inconsistency — the same book spells the same word two ways
- **p11:** `हवाई जहाज` (no nukta) vs `पानी का जहाज़` (nukta) — **same word, same page, two spellings.**
- **p13:** `ज़ेबरा` vs **p19:** `ज़ेब्रा` — same word, two spellings.
- Missing nuktas where the book uses them elsewhere: `प्याज` → `प्याज़` (p10), `तरबूज` → `तरबूज़` (p10, p24), `दरवाजा` → `दरवाज़ा` (p21), `फोन` → `फ़ोन` (p21), `जिराफ` → `जिराफ़` (p13), `ज़ाइलोफोन` → `ज़ाइलोफ़ोन` (p19).
- Chandrabindu inconsistency on **p14**: `आँखें` uses ँ correctly, but `मुंह` and `पांव` use anusvara → should be `मुँह`, `पाँव`.

→ **Do one global nukta/chandrabindu pass.** Pick a rule and apply it everywhere.

### The reference strip on p3 contradicts the sticker cards
The A–Z picture strip at the bottom of p3 teaches: A=Airplane, B=Boat, C=Car, D=Dinosaur, E=Earth, F=Flamingo, H=Heart, J=Juice, L=Ladybug, M=Map-pin, N=Net, P=Pants, Q=Quail, R=Rocket, S=Shoe, T=Truck, U=Unicorn, V=Volcano, W=Whale, X=X-ray, Y=Yoga.
The velcro cards on p18–19 teach: A=Apple, B=Banana, C=Cat, D=Dog, E=Elephant, F=Fish, H=Hen, J=Jug, L=Lion, M=Mango, N=Nest, P=Parrot, Q=Queen, R=Rabbit, S=Sun, T=Tiger, U=Umbrella, V=Van, W=Watch, X=Xylophone, Y=Yak.

**22 of 26 do not match.** The child sees two different answers for the same letter in the same book.
→ Make the strip match the cards exactly. Also drop **X-ray, Yoga, Volcano, Quail, Map-pin, Earth** — these are not preschool vocabulary.
→ The strip is also **English-only**; add the Hindi word.

### "Qq" prints as "Q9" (p19)
The lowercase **q** on the Queen card is set in a font whose glyph reads as the **digit 9**. In an alphabet-teaching card this is a direct teaching error. → Change the font on that card.

### Text that will be cut off when trimmed
- **p25 (body-part cut-outs):** `FOOT`, `NECK`, `HIP`, `FACE`, `STOMACH`, `MOUTH`, `LEG`, `HAND` all sit **on the circle rim**. `STOMACH` and `MOUTH` extend past the circle on both sides. After cutting, these words are gone.
- **p24:** `पेंगुइन` (Black card), `मराल` (Pink card), `केक` (Brown card), `हिम मानव` (White card) all sit **on or outside the card border**.
→ Pull all labels **at least 4 mm inside** the cut line.

### White text on white background (p24, WHITE card)
`लहसुन`, `दूध`, `खरगोश`, `हिम मानव` are **white text on a white card**, and the white paint-splat icon is invisible too. This card is effectively blank in print.
→ Give the WHITE card a light grey/blue tint background and dark labels.

### Other low-contrast text that will die in print
- **p19 (R card):** `खरगोश (Rabbit)` is white/silver outline text on a white card.
- **p18 (K card):** `(Kite)` is pale blue on cream.
- **p14:** English body-part labels in pale orange / pale purple on cream (`Hip`, `Face`).
→ Minimum contrast for a kids' book: dark text on light, or vice-versa. Nothing pastel-on-pastel.

### Sticker size vs. landing-zone mismatch (⚠️ measure this before printing)
- Alphabet tiles on p2/p3 are ~**39 mm** wide, and the velcro circle sits **off-centre to the right**, in a gap of only ~16 mm.
- The alphabet cards on p18 are ~**32 mm** and on p19 ~**36 mm** wide.
→ A 32–36 mm card placed on that off-centre circle will **hang over onto the neighbouring tile**.
→ Also, **p18 and p19 cards are different sizes** — your stickers won't be uniform.
**Action:** print one test sheet, physically cut, and place before committing to a run. Standardise all alphabet cards to one size and centre the velcro circle in the tile.

### Cut-out sheets have three different design systems
| Sheet | Border/cut guide | Labels |
|---|---|---|
| p18–19 (alphabet) | Rounded card borders | Hindi **+** English |
| p20 (fruit/veg), p21 (shapes), p23 (counting), p24 (colours) | Rounded card borders | Hindi only (p24), mixed (p21) |
| p22 (transport), p26 (farm), p27 (wild) | **No border, no cut line at all** | **No labels at all** |

→ Standardise. Every cut-out needs a **visible dashed cut line**, and either all get bilingual labels or none do.

### Cut-outs won't match their silhouettes
- **p26 duck** cut-out includes a **blue water puddle + 3 ducklings** as one piece; p12's silhouette is a duck only.
- **p26 pig** includes a **brown mud puddle**; p12's silhouette is a pig only.
- **p26 hen** has a **detached chick + scattered feed grains** (un-cuttable tiny dots).
- **p27 elephant** includes a **water splash + blue pool**; p13's silhouette is an elephant only.
- **p27 monkey** includes the **green vine**.
→ **QC every one of the 95 pieces against its silhouette** before print. This is the single biggest "product doesn't work" review driver in busy books.

---

## 3. 🟡 P2 MEDIUM — Design & consistency

### Page numbering is broken
Missing page-number badges on **p4, p17, p20, p21, p25**. The badge also drifts ~1.5 mm in position between pages (p14 is visibly offset vs p13).

### Layout — massive white space on the cut-out sheets
- **p20 (fruits/veg):** all 12 cards are crammed into the **right half**; the entire **left half of the page is blank**. Rows are unevenly spaced (45 / 57 / 55 px gaps) and columns drift.
- **p22, p25, p26, p27:** bottom **30–45% of each page is empty**.
You are paying for paper you are not using. Consolidating could remove **1–2 sheets** from the book — a direct COGS saving at your ₹150–280 print cost.

### Typography chaos — 15+ font families in 27 pages
Embedded: GlacialIndifference, Borsok, CanvaSans (Regular + Bold), KGPrimaryPenmanship, KGPrimaryDotsLined, Nunito-Black, NotoSansDevanagari-Bold, NotoSans-Bold, OpenSans-Bold, CocoGothic-Bold, FredokaOne, HeroLight-Bold, Quicksand-Medium, Telegraf-Bold, plus Canva "CAGenerated" Type-3 fonts.
→ Reduce to **3**: one display, one body (English), one Devanagari (Noto Sans Devanagari is a good choice — keep it). The Type-3 `CAGenerated` fonts are outline hacks and are the most likely thing to misbehave on an older Indian RIP — ask your printer to confirm they rasterise correctly.

### Letterform legibility on p2/p3
The decorative alphabet tiles use a different treatment per letter (hearts, clouds, flags, stars, distortions). **Q reads as a blob with a stick, X is heavily distorted.** For a first-alphabet book the letterforms must be clean and unambiguous. Also `Ll` in the p3 reference strip is indistinguishable from `Ii` in that font.

### Number-tracing stroke order (p6)
The numeral **4 has two strokes both labelled "1"** and one labelled "2". Stroke order must be 1 → 2 → 3.

### Body-parts leader lines (p14)
Several leader lines point at the wrong place: `चेहरा (Face)` terminates in the hair, `गर्दन (Neck)` terminates at the chin/mouth, `पेट (Stomach)` terminates near the hand/arm. The `कूल्हा` and `पेट` lines cross each other.
Also `कान = Ear` (singular) vs `आँखें = Eyes` (plural) — pick one.

### 3D objects used to teach 2D shapes (p21)
SQUARE is taught with a **dice** and an **ice cube** (both cubes), TRIANGLE with a **3D pyramid**, DIAMOND with a **3D gem**, CIRCLE with a **donut** (which has a hole).
→ Swap in flat objects: biscuit, sticky note, carrom board, road sign, chapati, coin.

### Missing/mismatched velcro placement
- **p13:** the monkey's velcro circle is **wider than the monkey's silhouette** — the sticker will hang off the shape.
- **p9:** the DIAMOND velcro circle **overlaps the inner orange outline**.
- **p12:** the 3 small ducklings and the chick are white silhouettes with **no velcro circle** — ambiguous whether the child is meant to cover them.

### Mixed art styles
Photorealistic (zebra, penguin, elephant, garlic, spider, crow, motorbike) sit next to flat cartoon (monkey, lion, giraffe, car) next to 3D-clay render (hands, body parts, five senses). Within a single sheet (p27) you have three styles. Pick one and stick to it.

### Bilingual coverage gaps
- **p4 (Trace The Lines):** 100% English, zero Hindi.
- **p3 reference strip:** English only.
- **p16 back cover:** English only.
- **p25, p26, p27:** English only / no labels.
- **Front cover:** **not a single Devanagari character**, on a book titled "English & Hindi".
→ Add `अंग्रेज़ी और हिंदी` to the cover and a clarifier badge: **"हिंदी अनुवाद सहित · Hindi translations included"**. This also honestly sets expectations so buyers don't expect Hindi varnamala.

### Low-resolution assets
- **p2 and p3 backgrounds are embedded at 24 PPI** (206×206 px stretched to full page width). These will print visibly blocky/banded on coated stock. **Re-export at 300 PPI.**
- **p21, p23, p26, p27** cut-out images run **200–237 PPI** (below the 300 PPI print standard). Acceptable at small sizes but will look soft.
- **p4** line art is at 263–271 PPI.

---

## 4. ⚖️ Compliance — before you list on Amazon / Meesho

### Legal Metrology (Packaged Commodities) Rules, 2011
The back cover currently carries only MRP + "Published by: SanskaTots, Bangalore, India". **Mandatory declarations that are missing:**
- Full **name and complete address of the manufacturer/packer/importer**, including PIN code
- **Net quantity** (e.g. "1 N" / number of pages / number of sticker pieces)
- **Month and year of manufacture/packing**
- **Consumer care details** — name, phone number **and** email
- **Country of Origin: India** (you have the "Made in India" mark — good, but state it in text too)

Missing these is the most common cause of Legal Metrology notices and Amazon listing suppressions for Indian sellers.

### Choking-hazard warning — currently absent
The cover says **"Ages 2–4 Years"** and the product ships with **95 small cut-out pieces**.
→ Add a **small-parts warning**: *"⚠️ Not suitable for children under 3 years. Contains small parts — choking hazard. Adult supervision and adult-assisted cutting required."*
→ Also reconsider the age band. The content (letter tracing, five senses, reading) skews **3–6**, not 2–4.

### The ® symbol on the SANSKA TOTS logo
If the trademark is **applied for but not yet registered**, using ® is an offence under **Section 107 of the Trade Marks Act, 1999**. → Verify registration status. If pending, use **™**.

### Copyright line
Currently `Copyright © 2026` with no owner and misaligned spacing.
→ `© 2026 SanskaTots (Deethya Enterprises). All rights reserved.`

### ISBN — ✅ this one is fine
`978-81-685-8086-2` → barcode `9788168580862`, EAN-13 check digit validates correctly. No action.

### Cultural / market fit
- **p15 and p21 use a pepperoni pizza** (visibly non-veg). A meaningful share of your target Indian-mom segment is vegetarian. → Swap for a veggie pizza.
- **p26 uses a Holstein Friesian (Western dairy cow).** For a brand called SanskaTots, an **Indian humped cow (देसी गाय / Gir)** is both more culturally correct and a genuine differentiator vs. the cheap Chinese-import busy books you're competing with on Meesho.
- **p24 (Brown) uses a pine cone and a cardboard box**; **p24 (Green) uses an avocado**. Not relatable for a 3-year-old in India. → Coconut, wooden spoon, chapati, curry leaves, bottle gourd.

---

## 5. 📋 File-structure issues for the printer

1. **The back cover is page 16, with 11 pages after it.** Your printer needs the cover (front + back + spine if applicable) as a **separate file**, and the interior as its own file. Send it as-is and you risk the back cover being bound in the middle.
2. **27 pages is not a multiple of 4.** Confirm the binding method. If saddle-stitch or perfect-bound you need 28. If wiro/spiral (as depicted on the cover) it doesn't matter — but confirm.
3. **File is 81 MB and un-optimised.** Fine for print, but flatten transparency and confirm the printer can handle the Type-3 fonts.
4. **Colour is CMYK throughout ✅** — good, this is often the thing Canva gets wrong. No action.

---

## 6. ✅ Recommended Fix Order

**Round 1 — cannot print without these**
1. Re-export with **3 mm bleed + crop marks**
2. Fix the **Devanagari-letter / Hindi-word contradiction** on p18–19 (recommend: delete the Devanagari letter)
3. Change **"100+" → "95"** and **"14 Themes" → "12 Themes"**
4. Replace **p17** production note with a real instructions divider
5. Remove **Nike swoosh, iPhone, branded vehicles**
6. Fix the **p27 elephant grey background box**

**Round 2 — quality**
7. Hindi spelling pass: सूँघना, फ्रॉक, राजहंस, ब्लू व्हेल, वृत्त, पहिया, टाँग/पैर + global nukta/chandrabindu pass
8. Make the **p3 reference strip match the p18–19 cards**
9. Pull all labels **inside** cut lines (p24, p25); fix the WHITE card
10. Fix the **"Q9"** glyph
11. Standardise sticker card sizes and centre the velcro circles; **physically test-cut one sheet**
12. Add cut lines to p22/p26/p27; standardise labelling across all sticker sheets

**Round 3 — compliance & polish**
13. Add Legal Metrology block + choking-hazard warning + verify ® status
14. Fix page numbers on p4/17/20/21/25
15. Re-export p2/p3 backgrounds at 300 PPI
16. Fix stroke order on numeral 4; fix p14 leader lines
17. Rebalance the empty half-pages (may save 1–2 sheets of print cost)
18. Add Devanagari to the front cover + an honest "Hindi translations included" clarifier
19. Reduce to 3 font families; swap in Indian-relatable and vegetarian imagery

---

*Audit method: all 27 pages rendered at 150 DPI and inspected visually with targeted zoom crops; `pdfinfo -box`, `pdffonts` and `pdfimages -list` used for bleed, font-embedding, colour-space and effective-PPI checks.*
