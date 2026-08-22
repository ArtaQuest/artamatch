# The world's date-keyed marriage systems — coverage, and what each anchor rests on

Operator order, 2026-08-22: *"ensure every electional or non-electional matching algorithm ever popular in any
part of world is included"*.

Three modules implement them: [`world_members_iv.py`](world_members_iv.py) (calendars and the large electional
systems), [`world2_members_iv.py`](world2_members_iv.py) (the remaining matching algorithms),
[`world3_members_iv.py`](world3_members_iv.py) (nine an audit against actual populations found still missing),
with the Myanmar calendar in [`mmcal.py`](mmcal.py). [`world_control_iv.py`](world_control_iv.py) is what reads
them.

## Scope

In scope: anything computable from the three dates we hold (both births, the relationship start) plus the
astronomy derivable from them. Out of scope, and deliberately so: systems needing a **name** (abjad/jummal,
Pythagorean name numerology), a **birth time** (any lagna-based rule — we have no times), a **cast or drawn
lot** (Ifá/Odu, I Ching, geomancy), or a **physical reading** (palm, face). Those are not weaker systems; they
are simply not functions of a date, so this dataset cannot speak to them either way.

## Verification status

The distinction that matters is whether an anchor was **checked against a published value** or **assumed**. An
assumed phase is not a wrong answer, but it is not evidence either, and six anchors were wrong on first
writing — every one caught by a check, none by inspection.

| System | Region | Anchor rests on |
|---|---|---|
| Rokuyō 六曜 | Japan | **Verified** — canonical 1/1=先勝 … 5/1=大安 fixes Taian at index 0, Butsumetsu at 5. *Shipped wrong first: both flags pointed at the wrong day.* |
| 28 mansions 二十八宿 | China | **Verified** — the cycle maps onto the 7-day week (房虛昴星 are always Sunday), then five published August 2026 assignments pin it. *Shipped wrong first: 19 positions out.* |
| 12 Day Officers 建除十二直 | China | **Verified** — solar-term month, boundaries checked at 子→丑 (5 Jan), 丑→寅 (5 Feb), 寅→卯 (5 Mar). *Shipped wrong first: was using the lunisolar month.* |
| Sexagenary day 干支 | China/Korea/Japan | **Verified** — 2000-01-07 = 甲子. |
| Widow / double-spring year 寡婦年·雙春年 | China | **Verified** — Chinese New Year reproduces 2024-02-10, 2025-01-29, 2026-02-17, 2027-02-06; the rule independently reproduces the widow year that made the news. |
| Kua / Ba Zhai 八宅 | China, Vietnam, SE Asia | **Verified** — the unbroken 9-cycle anchored on 1864 = 一白, agreeing with the two-digit mnemonic everywhere it is valid; Lì Chūn year boundary applied. Table checked: same-group ⇔ good relation, Yan Nian reciprocal. |
| Napeum ohaeng 납음오행 | Korea | **Verified** — the named pillars (海中金 metal, 爐中火 fire, 大林木 wood, 路傍土 earth, 大海水 water). |
| 손 없는 날 | Korea | **Verified** — lunar days ending 9 or 0. |
| Aṣṭakūṭa / Guṇa Milan | India | **Verified** — tables complete (gaṇa and nāḍī each partition all 27 nakṣatras 9/9/9, yoni uses 14 animals), maxima total 36, identical charts correctly lose nāḍī at 28/36. |
| Daśakūṭa (rajju, vedha, mahendra, strī dīrgha) | South India | **Verified** — rajju partitions all 27. *A NaN Moon was casting to a garbage int and indexing the table, fabricating kūṭas; masked.* |
| Mangal / Kuja Doṣa | India | Structural — houses 1/2/4/7/8/12 from Moon and Venus, both-Maṅglik cancellation. |
| Vimśottarī Daśā | India | **Verified** — the nine periods total 120 years. |
| Rāhu Kālam | South India, Sri Lanka | **Verified** — all seven weekday eighths against published values. |
| Vivāha Muhūrta (Guru/Śukra Asta, tithi, Bhadrā, Pañcaka) | India | Structural — standard combustion arcs (11°/10°), tithi classes, Viṣṭi karaṇa. |
| Javanese pasaran + weton | Indonesia | **Verified** — 1945-08-17 = Jumat Legi. *Shipped wrong first: off by two.* |
| Balinese Pawukon | Bali | **Verified** — the offset solved so all four published Galungan dates land on pawukon day 70, Wednesday, Kliwon, wuku Dungulan. |
| Yatyaza · Pyathada | Myanmar | **Verified** — the whole Myanmar calendar differential-tested against the reference implementation over 2,784 dates (~1354–2093 CE), zero mismatches. |
| Wan Phra | Thailand, Laos, Cambodia | **Verified** — 8th/15th waxing, 8th/last waning. |
| Hebrew: Omer, Three Weeks, Shabbat, Tu B'Av, Lag BaOmer | Jewish | **Verified** — all four boundary dates. *Shipped wrong first: the Three Weeks sat in midwinter (Shevat/Adar instead of Tammuz/Av).* |
| Christian and Orthodox fasts | Europe | **Verified** — computus reproduces the published Easters 2026–28. |
| Islamic month flags | Islamic world | Library (`convertdate`). |
| Parsi Shahenshahi day-names | Parsi | **Verified** — pinned to Navroz 2023-08-16, 2024-08-15, 2025-08-15; the leap rule then carries it. *Shipped wrong first: 172 days out of phase.* |
| Maya Tzolkʼin · Haabʼ · Long Count | Mesoamerica | **Verified** — 2012-12-21 = 4 Ahau 3 Kʼankʼin, baktun 13. |
| Aztec Tonalpōhualli | Mesoamerica | **ASSUMED** — the Aztec-to-Maya correlation is disputed; pair features are exactly invariant to it, single-date features nearly so. |
| Nine Star Ki 九星気学 | Japan | **Verified** — same 9-cycle as the kua. |
| Tibetan parkha · mewa | Tibet | Structural — 8- and 9-cycles on the birth year. |
| Chinese zodiac matrix (三合·六合·六沖·六害·相刑) | East Asia | Structural — standard trine, harmony, clash, harm and punishment sets. |
| Kaulana Mahina · Maramataka | Hawaiʻi, Aotearoa | Structural — the thirty lunar nights. |
| Igbo four-day week · Akan kra din | West Africa | Structural — 4-cycle; the Akan name **is** the weekday. |
| Ogham tree months · runic half-months | Celtic, Norse | Structural — even divisions of the solar year, as the modern revival defines them. |
| Coptic/Ethiopian, Jalali, Julian, Hebrew, Islamic calendars | various | Library (`convertdate`). |

## What they measure

See the commit history for the numbers. The short version: with the two ages, the era and the exact
date-precision pattern held flat — the configuration at which all references read 0.5000 — every one of these
systems lands between 0.49 and 0.52, and the best of them beats *which day of the month the wedding happened
to be written down on* by about 0.012 AUC.

That is the result, and it is worth stating plainly: the systems are implemented faithfully, anchored against
published values, and given every chance. They do not predict whether a marriage lasts.
