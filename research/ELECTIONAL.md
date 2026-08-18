# Electional astrology, everywhere it exists — a map for the wedding-date input

*Brainstorm, 2026-08-18. Electional (katarchic, muhūrta, 择日 zé rì, ikhtiyārāt) astrology is the choice of a
moment to BEGIN something. For ArtaMatch the thing begun is a relationship, and the moment is the wedding.
Every tradition below is a checklist on that moment; each is marked by what it needs to be computed —
**Y** the year, **M** the month, **D** the day, **H** the hour — and by whether the repo already has it.*

| | |
|---|---|
| ✅ | built in `astro/trad_electional.py`, `trad_muhurta.py`, `trad_wedding_transits.py` (retired from the stack when the start date was dropped; 3,300 lines) |
| 🟡 | partly built, or buildable from what those modules compute |
| ❌ | not built |

**The precision point in one line:** with the start as a **year**, only the slow-planet transits, the year
pillar, the Jupiter/Saturn cycles and the age-at-start rules survive; everything below marked **D** or **H**
— which is most of electional astrology, and all of the famous parts — needs the full date.

---

## 1 · Hellenistic and Roman

| tradition | the claim on the wedding moment | needs | |
|---|---|---|---|
| **Katarchic astrology** — Dorotheus *Carmen* V, Hephaistio III, Petosiris | the Moon's condition at the beginning: waxing, swift, applying to a benefic, not void, not in the *via combusta*, not in the last degrees; benefics angular; the 7th place and its lord fortified | D H | ✅ |
| **Ptolemy** *Tetrabiblos* IV.5 on marriage | Venus/Mars for the parties, the 7th place | D | ✅ |
| **Egyptian lucky/unlucky days** — the Cairo Calendar (P. Cairo 86637), the Sallier IV papyrus | each civil day good/bad/mixed by myth; a 365-day fixed table | D (civil calendar) | ❌ |
| **Roman fasti / nefasti, dies religiosi** — the *Fasti Antiates*, Ovid *Fasti* | days on which no public act was begun; the Kalends/Nones/Ides and the day after each (*dies atri*); May and the first half of June forbidden for weddings (Ovid V.487, VI.219) | M D | ❌ |
| **Mesopotamian hemerologies** — *Iqqur īpuš*, the Babylonian Almanac, *Enūma Anu Enlil* omens | favourable/unfavourable days by month of the lunar calendar; the 7th, 14th, 19th, 21st, 28th as *ūmū lemnūtu* | M D (lunar) | ❌ |
| **Egyptian decans / hour-stars** for a beginning | the rising decan at the hour | H | ❌ (no hour in the data) |

## 2 · Persian, Arabic, medieval and Renaissance Europe

| tradition | the claim | needs | |
|---|---|---|---|
| **Ikhtiyārāt (elections)** — Sahl ibn Bishr *On Elections*, Māshāʾallāh, al-Kindī, Abū Maʿshar *Kitāb al-ikhtiyārāt*, al-Bīrūnī | the Moon's application/separation (*ittiṣāl/insirāf*), reception, the lord of the hour, the benefics on the ascendant and the 7th; a marriage election must not contradict the nativity | D H | ✅ (application/separation exact; hour absent) |
| **Guido Bonatti** *Liber Astronomiae* Tr. 5–6, the 146 Considerations | void Moon, *via combusta*, Moon with a retrograde, malefics on the significators, the election vs the nativity | D | ✅ |
| **William Lilly** *Christian Astrology* | dignities table; combustion 8.5°, beams 17°, cazimi; the Moon increasing and unafflicted; lords of the 1st and 7th in soft aspect with reception | D | ✅ |
| **Ramesey** *Astrologia Restaurata* (1653) — the fullest English electional text; **Gadbury**; **Coley** | the same doctrine with marriage-specific tables | D | 🟡 (rules overlap Lilly's) |
| **Ibn Ezra** *Book of Elections* (*Sefer ha-Mivḥarim*) | Hebrew-Arabic elections; the almuten of the election | D | 🟡 (almuten scoring exists in `trad_persian_arabic`) |
| **Planetary hours** (Chaldean order) for the ceremony | Venus hour for a wedding | H | ❌ (no hour) |
| **Medieval Christian closed seasons** | no weddings in Advent, Lent, Rogationtide (the *tempus clausum*, Council of Trent 1563) | M D (Easter-movable) | ❌ — computable from date via the computus |
| **English/European folk election** | "Marry in May, rue the day"; the wedding-day rhyme (Monday wealth … Saturday no luck at all); the waxing Moon | M D | ❌ (weekday features exist for BIRTHS only) |
| **Renaissance elections against the couple's radices** — Cardano, Morin *Astrologia Gallica* XXI | the wedding chart's ASC/MC on natal planets | H | ❌ (no hour) |

## 3 · Indian, and the Indianised world

| tradition | the claim | needs | |
|---|---|---|---|
| **Vivāha Muhūrta** — Muhūrta Cintāmaṇi, Kālaprakāśikā, Raman *Muhurtha*, Dharma Sindhu | the eleven marriage nakṣatras (Rohiṇī, Mṛgaśira, Maghā, U.Phalgunī, Hasta, Svātī, Anurādhā, Mūla, U.Āṣāḍhā, U.Bhādrapada, Revatī); permitted tithis 2/3/5/7/10/11/13; permitted vāras Mon/Wed/Thu/Fri; the forbidden months (Caturmāsa, Adhika, Kharmās = Sun in Dhanu/Mīna); Guru/Śukra asta (combust Jupiter/Venus); Tārā-bala and Candra-bala from each janma-nakṣatra; the nine bad nitya-yogas; Viṣṭi/Bhadrā karaṇa; Pañcaka; gochara fitness | M D + the natal Moon | ✅ |
| **Rāhu-kāla, Yama-gaṇḍa, Gulika**; the eight *muhūrtas* of the day; Abhijit | forbidden and best portions of the day | H | ❌ (no hour) |
| **Gaṇḍa-mūla, Kāla-sarpa on the day**, **Māṅgalika** timing | | D | 🟡 |
| **Tamil Poruttham & Kalyāṇa muhūrtam** (Kalaprakasika, the Vākya pañcāṅga) | the ten poruthams for the couple + the day | D | ✅ (poruthams) / 🟡 (day) |
| **Bengali/Odia** *Bibāha lagna* books; **Malayalam** *Muhūrtapadavī* | regional variants of the same panchanga rules | D | 🟡 |
| **Nepali** *Bibāha* by the Bikram Sambat calendar; **Sinhala** *nekata* (auspicious times, the *Litha* almanac) | | D H | ❌ |
| **Tibetan** *Jungtsi* (elemental) date selection — the *gyu-kar* 28 mansions, the 12 animal + 5 element day pillars, the *parkha* trigrams and *mewa* numbers, the *tsé-che* black days; Bhutanese and Mongolian *zurkhai* | day pillar vs each partner's year pillar; forbidden days by mansion | D | 🟡 (year-pillar animal × element and rabjung exist; day pillars from JD are trivial to add) |
| **Burmese** *Mahabote* | weekday of the wedding vs each birth weekday (the seven-house wheel; the "enemy" pairs) | D | 🟡 (birth-weekday houses exist; wedding weekday needs the date) |
| **Thai** *Duang / Rerk* (ฤกษ์) — the nine *rerk* classes of the day's mansion; forbidden *wan phra*; the Thai months for weddings (even months; never the 9th? — check the *Horasat*) | | M D | 🟡 (rerk mansions exist for births) |
| **Khmer / Lao** almanac elections | as Thai, with local forbidden days | M D | ❌ |
| **Balinese** *Wariga* — the Pawukon 210-day cycle: the 30 *wuku*, the *tri-/panca-/sapta-wara* concurrent weeks, *dewasa ayu* (good days for a wedding, e.g. *Wraspati Manis*, *Kajeng Kliwon* avoided) | Pawukon position of the wedding day; each partner's *oton* | D | ❌ — a JD-mod-210 computation |
| **Javanese** *Weton* — the 35-day *pasaran × saptawara* cycle; the couple's *neptu* sums for compatibility AND the wedding date's *weton* against them; the *naga dina* direction; forbidden months (Suro) | D M | 🟡 (birth wetons exist in `trad_tibetan_seasia`; the wedding weton is one more mod-35) |

## 4 · Chinese, and the Sinosphere

| tradition | the claim | needs | |
|---|---|---|---|
| **擇日 Zé rì / the Tong Shu almanac** — the *12 Day Officers* (建除 Jiànchú: 建除滿平定執破危成收開閉), the *28 Xiu* of the day, the *Twelve Day Gods* (Yellow/Black), the *Dong Gong* method, the *sha* directions, *Yellow Path days* | is the day 宜嫁娶 "suitable for marriage"? | D | 🟡 (Jianchu officer and 28-xiu-of-day computed for BIRTHS in `trad_chinese`; apply to the wedding JD) |
| **Sexagenary day pillar vs the couple's year pillars** — the six clashes 六沖 (a day whose branch clashes either partner's year branch is forbidden), the three harmonies, the *San Sha* year of each partner | | D + birth years | 🟡 (year branches exist; day pillar = (JD+49) mod 60) |
| **Tai Sui** — marrying in a year that clashes one's own animal (the 犯太歲 rule) | | **Y only** | ✅ possible from `start_year` |
| **Xuan Kong Da Gua** date selection, **Qi Men Dun Jia** date selection, **Zi Wei** day-star selection | hexagram/star of the day and hour vs the couple's | D H | ❌ |
| **Vietnamese** *Xem ngày cưới*; **Korean** *Taegil* (택일) — the *saju* of the wedding day vs the couple's; **Japanese** *Rokuyō* (大安 Taian for weddings, 仏滅 Butsumetsu avoided) and the *kyūsei* nine-star day | | D | ❌ — Rokuyō is (lunar month + lunar day) mod 6, trivial once the lunar date is known |

## 5 · Judaic and Islamic

| tradition | the claim | needs | |
|---|---|---|---|
| **Halakhic wedding calendar** | no weddings in the *Omer* (except Lag ba-Omer), the Three Weeks, fast days; Tuesday favoured (*ki tov* twice); Rosh Chodesh favoured; the waxing Moon | M D (Hebrew calendar) | ❌ — computable from date via a Hebrew-calendar conversion |
| **Islamic** | no astrological election in orthodox practice; folk avoidance of Muharram/Safar weddings, Ramadan; the *ikhtiyārāt* literature above is the astrological strand | M | ❌ |

## 6 · Africa, the Americas, Oceania

| tradition | the claim | needs | |
|---|---|---|---|
| **Yoruba** *Ifá* day-choosing (the 4-day week: Ogun/Jakuta/Obatala/Orunmila days); **Akan** *Adaduanan* 42-day cycle (good/bad days for rites) | | D | ❌ — both are JD-mod-n |
| **Ethiopian** *Bahire Hasab* — Ge'ez calendar fasts (no weddings in Lent/Filseta), the *Tsome Nebiyat* season | | M D | ❌ |
| **Maya** *Tzolk'in* day-sign and coefficient of the wedding day, the *k'atun* prophecy | | D | 🟡 (Long Count and Calendar Round for BIRTHS exist in `trad_mesoamerican`; apply to the wedding JD) |
| **Aztec** *Tonalpohualli* — the day-sign's *tonalli* (good/indifferent/bad) for a marriage; the *nemontemi* five dead days | | D | ❌ |
| **Polynesian** *maramataka* — the Māori lunar-night names (Rākaunui, Tangaroa nights good; Whiro, Mutuwhenua avoided) for a beginning | | D (lunar) | 🟡 (birth maramataka exists; wedding night needs the date) |

## 7 · Modern Western electional practice

| tradition | the claim | needs | |
|---|---|---|---|
| **The Moon** — void of course, phase (waxing; not the dark of the Moon), sign (Taurus, Cancer, Libra, Pisces favoured; Scorpio, Capricorn avoided for weddings), applying aspects | | D (H for VoC) | ✅ |
| **Venus and Mercury retrograde**, **eclipses** within ±14 days | | D | ✅ / 🟡 (eclipse proximity is in `trad_lunar_calendrical` for births) |
| **Wedding chart transits to both natal charts** — Hand's orbs, applying/separating | | D | ✅ |
| **Progressions and solar arcs to the wedding** — the progressed Moon's sign/phase | | D | ✅ (secondary progressions to the wedding, slots 3–4) |
| **Davison and composite of the couple vs the wedding** | | D | ✅ |
| **Saturn/Jupiter cycles at the wedding** — Saturn return, Jupiter return, Uranus opposition (the "age" rules restated in the sky) | | **Y** | 🟡 — the one family that survives a year-only start |
| **The 7th-house cusp of the wedding chart** (Ptolemy → modern) | | H | ❌ (no hour) |
| **Cosmobiology / Uranian** — wedding midpoints on the natal 90° dial (Ebertin, Witte's marriage pictures Sun/Moon = Venus/Mars) | | D | ✅ |
| **Vedic-Western hybrids** — Muhurta rules with tropical positions | | D | 🟡 |
| **Astro*Carto*Graphy of the wedding place** | | place | ❌ (no place) |

## 8 · What a *year* alone can carry (the current second edition)

Everything electional collapses to five families when the start is a year:

1. **Age at the start**, both partners — not astrology, and it dominates: 0.635 alone held out.
2. **The Jupiter and Saturn cycles** — the wedding falls in which Jupiter year (12-year) and which Saturn phase (29.5-year) of each partner: Saturn return at ~29/58, Saturn opposition ~15/44, Jupiter return at 12/24/36. Resolution ±6 months on a body that moves 12°/yr (Saturn) is usable; Jupiter at 30°/yr is marginal.
3. **The slow-planet transits** — Uranus/Neptune/Pluto to each natal chart, and the wedding-year positions themselves (era clocks again).
4. **The Chinese year pillar of the wedding** — Tai Sui clash with either partner's animal; the stem element vs each partner's; the sexagenary year vs the birth years.
5. **The wedding year's eclipse pairs and the Metonic phase** — the wedding year mod 19 against each birth year mod 19 (same lunar phase pattern), and mod 18.03 (Saros).

Everything else in this file needs the day. The `P580` precision flag (`pqv:P580/wikibase:timePrecision`) is
one added triple in the query and a re-fetch (a few hours with the Azure workers): with it, the day-precision
rows could be marked and every table above could run on the couples that have one — measured on the first
build, that is roughly half of the marriages.
