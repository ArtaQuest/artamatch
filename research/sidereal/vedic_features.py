"""
vedic_features.py — SIDEREAL features for a couple, through PyJHora, at 09:00 LOCAL at each birthplace.

THE CONVENTION. Nobody's birth time is recorded, so every chart in this project is cast at a fixed hour. With the
birthplace known that hour is a LOCAL one: 09:00 at the place, converted to UT through the historical time zone of
the coordinates (timezonefinder -> zoneinfo, whose tables carry the local-mean-time era, so an 1850 Paris birth
gets +0:09:21 and a 1950 one +1:00). That gives the chart an ascendant and houses for the first time in this
project. It is the dataset's convention, stated, not a fact about anyone: the ascendant moves a sign every two
hours, so it is the sign that rises at nine in the morning at that place, whatever the truth was.

PRECISION-AWARE, OR IT WOULD BE FICTION. A training birth may be known only to the year or the month
(`1856-00-00`, `1809-11-00`); dates.concrete() puts those at the 1st so a chart can be cast, and that is right for
slow bodies and wrong for everything that changes within a month. So each feature declares the precision it needs
and is NaN below it: the Moon's nakshatra, the tithi, the lagna and the houses need the DAY; a Sun sign needs the
month; Jupiter, Saturn, Rahu and Ketu are honest at year precision. LightGBM reads NaN natively; nothing is
imputed.

WHAT IS COMPUTED, per person (PyJHora, Lahiri by default; the ayanamsa is a parameter):
  D1  lagna sign and degree; each graha's sign, degree, house from the lagna, retrogradation-free longitude
  vargas  the sign of the lagna and each graha in D2 D3 D4 D7 D9 D10 D12 D16 D20 D24 D27 D30 D60
  panchanga  tithi, nakshatra + pada, yoga, karana, vaara (weekday), the lunar month
  shad bala  the six strengths x seven grahas, and the total
  ashtakavarga  sarva points in each of the 12 houses, and the bhinna points of each graha in its own house
  doshas  manglik (from lagna, Moon, Venus), kala sarpa, ganda moola
  vimsottari  the maha-dasa lord and bhukti lord RUNNING AT THE START DATE (the wedding), and the years into it
and per couple: Ashtakoota with the dad as the boy and the mom as the girl, Moon-sign and lagna distances, each partner's grahas in the other's houses, and
the same-dasa-lord-at-the-wedding indicators.
"""
import datetime as dt
import math
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
_stdout = sys.stdout
sys.stdout = open(os.devnull, "w")           # PyJHora prints its sys.path on import
try:
    from jhora import utils as JU
    from jhora.panchanga import drik
    from jhora.horoscope.chart import charts, ashtakavarga, strength, dosha
    from jhora.horoscope.match import compatibility
    from jhora.horoscope.dhasa.graha import vimsottari
finally:
    sys.stdout = _stdout
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo

AYANAMSA = os.environ.get("AQ_AYANAMSA", "LAHIRI")
drik.set_ayanamsa_mode(AYANAMSA)
_TF = TimezoneFinder()
GRAHA = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
SLOW = {"Jupiter", "Saturn", "Rahu", "Ketu"}          # honest at year precision
MONTHLY = {"Sun"}                                        # honest at month precision (a sign a month)
VARGAS = (2, 3, 4, 7, 9, 10, 12, 16, 20, 24, 27, 30, 60)
HOUR = (9, 0, 0)

_tz_cache = {}

# VIMSOTTARI, computed here rather than through vimsottari.get_running_dhasa_for_given_date, which costs 1.15 s a
# call (it enumerates every bhukti from birth) against about 15 ms for everything else in a chart. The rule is
# arithmetic: nine lords in fixed order with fixed years summing to 120; the first lord is the natal Moon's
# nakshatra modulo 9 (Ashwini -> Ketu); the balance of that first period is the unelapsed fraction of the
# nakshatra times the lord's years; then the periods follow in order. The bhukti inside a maha-dasa splits its
# years in the same nine proportions starting from the maha-dasa lord.
VIM_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_YEARS = [7, 20, 6, 10, 7, 18, 16, 19, 17]
VIM_INDEX = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8}


def vimsottari_at(moon_lon, years_after_birth):
    """(maha-dasa lord, bhukti lord, years into the maha-dasa) running `years_after_birth` years after birth, for a
    natal sidereal Moon at `moon_lon` degrees. Lords as GRAHA indices."""
    span = 360.0 / 27.0
    nak = int(moon_lon // span)
    frac_left = 1.0 - (moon_lon - nak * span) / span
    i = nak % 9
    t = frac_left * VIM_YEARS[i]                       # end of the first (partial) maha-dasa, in years from birth
    start = 0.0
    if years_after_birth < t:
        into = years_after_birth
        maha_len_elapsed_frac = 1.0 - (t - years_after_birth) / VIM_YEARS[i]
    else:
        start = t
        i = (i + 1) % 9
        while start + VIM_YEARS[i] <= years_after_birth:
            start += VIM_YEARS[i]
            i = (i + 1) % 9
        into = years_after_birth - start
        maha_len_elapsed_frac = into / VIM_YEARS[i]
    # bhukti: the maha-dasa's years split in the nine proportions from its own lord
    j, acc = i, 0.0
    for _ in range(9):
        piece = VIM_YEARS[j] / 120.0
        if maha_len_elapsed_frac < acc + piece:
            break
        acc += piece
        j = (j + 1) % 9
    return VIM_INDEX[VIM_LORDS[i]], VIM_INDEX[VIM_LORDS[j]], into


def tz_hours(lat, lon, y, m, d):
    """UTC offset in hours of local time at (lat, lon) on that date, from the historical zone tables. Cached per
    (zone, year, month) -- the offset does not change inside a month often enough to matter at 09:00."""
    key = (round(lat, 2), round(lon, 2))
    zone = _tz_cache.get(key)
    if zone is None:
        zone = _TF.timezone_at(lng=lon, lat=lat) or _TF.closest_timezone_at(lng=lon, lat=lat) or "UTC"
        _tz_cache[key] = zone
    try:
        off = dt.datetime(y, m, d, HOUR[0], HOUR[1], tzinfo=ZoneInfo(zone)).utcoffset()
        return off.total_seconds() / 3600.0
    except Exception:
        return lon / 15.0                                 # local mean time as the fallback


def precision(dob):
    if dob == "0000-00-00":
        return 0
    if dob.endswith("-00-00"):
        return 1
    if dob.endswith("-00"):
        return 2
    return 3


def person(dob, lat, lon, start=None):
    """All single-chart features for one person. Returns a dict name -> float (NaN where undefined)."""
    F = {}
    prec = precision(dob)
    if prec == 0 or lat is None or lon is None or (isinstance(lat, float) and math.isnan(lat)):
        return F                                          # nothing castable: an absent partner or no place
    y, m, d = int(dob[:4]), max(1, int(dob[5:7])), max(1, int(dob[8:10]))
    tz = tz_hours(lat, lon, y, m, d)
    place = drik.Place("p", float(lat), float(lon), tz)
    jd = JU.julian_day_number((y, m, d), HOUR)
    F["tz_hours"] = tz
    F["lat"] = float(lat); F["lon"] = float(lon)
    day_ok, month_ok = prec == 3, prec >= 2

    pp = charts.rasi_chart(jd, place)                     # [['L',(sign,deg)], [0,(sign,deg)], ...]
    lagna_sign = pp[0][1][0]
    F["lagna_sign"] = float(lagna_sign) if day_ok else np.nan
    F["lagna_deg"] = float(pp[0][1][1]) if day_ok else np.nan
    for row in pp[1:]:
        g = GRAHA[row[0]]
        sign, deg = row[1]
        ok = day_ok or (g in SLOW) or (g in MONTHLY and month_ok)
        lon_s = sign * 30.0 + deg
        F[f"{g}_lon"] = lon_s if ok else np.nan
        F[f"{g}_sign"] = float(sign) if ok else np.nan
        F[f"{g}_lon_cos"] = math.cos(math.radians(lon_s)) if ok else np.nan
        F[f"{g}_lon_sin"] = math.sin(math.radians(lon_s)) if ok else np.nan
        F[f"{g}_house"] = float((sign - lagna_sign) % 12 + 1) if day_ok else np.nan
        F[f"{g}_nakshatra"] = float(int(lon_s / (360 / 27)) + 1) if (day_ok or g in SLOW) else np.nan
    # vargas: sign of lagna + grahas in each divisional chart (day precision only -- a varga sign changes within
    # a day for the lagna and within days for the Moon)
    if day_ok:
        for D in VARGAS:
            dc = charts.divisional_chart(jd, place, divisional_chart_factor=D)
            F[f"D{D}_lagna_sign"] = float(dc[0][1][0])
            for row in dc[1:]:
                F[f"D{D}_{GRAHA[row[0]]}_sign"] = float(row[1][0])
                F[f"D{D}_{GRAHA[row[0]]}_house"] = float((row[1][0] - dc[0][1][0]) % 12 + 1)
    # panchanga
    if day_ok:
        try:
            t = drik.tithi(jd, place); F["tithi"] = float(t[0])
            n = drik.nakshatra(jd, place); F["moon_nakshatra"] = float(n[0]); F["moon_pada"] = float(n[1])
            yg = drik.yogam(jd, place); F["yoga"] = float(yg[0])
            k = drik.karana(jd, place); F["karana"] = float(k[0])
            F["vaara"] = float(drik.vaara(jd, place))
            lm = drik.lunar_month(jd, place); F["lunar_month"] = float(lm[0]); F["adhika_masa"] = float(bool(lm[1]))
        except Exception:
            pass
        # shad bala: 7 grahas x 6 components + total
        try:
            sb = strength.shad_bala(jd, place)
            names = ["sthana", "dig", "kala", "cheshta", "naisargika", "drik", "total", "rupas", "ratio"]
            for ci, comp in enumerate(sb[:len(names)]):
                for gi, val in enumerate(comp[:7]):
                    F[f"sb_{names[ci]}_{GRAHA[gi]}"] = float(val)
        except Exception:
            pass
        # ashtakavarga
        try:
            h2p = JU.get_house_planet_list_from_planet_positions(pp)
            bav, sav, _ = ashtakavarga.get_ashtaka_varga(h2p)
            for h in range(12):
                F[f"sav_house{h+1}"] = float(sav[h])
            for gi in range(7):
                # the graha's own bhinna points in the house it occupies
                sign_g = int(F.get(f"{GRAHA[gi]}_sign", np.nan)) if not math.isnan(F.get(f"{GRAHA[gi]}_sign", np.nan)) else None
                if sign_g is not None:
                    F[f"bav_{GRAHA[gi]}_own"] = float(bav[gi][sign_g])
        except Exception:
            pass
        # doshas: manglik reads the chart, kala sarpa the house list, ganda moola the Moon's star
        try:
            mg = dosha.manglik(pp)
            F["manglik"] = float(bool(mg[0])) if isinstance(mg, (list, tuple)) else float(bool(mg))
        except Exception:
            pass
        try:
            F["kala_sarpa"] = float(bool(dosha.kala_sarpa(JU.get_house_planet_list_from_planet_positions(pp))))
        except Exception:
            pass
        try:
            mn = F.get("moon_nakshatra")
            if mn is not None and not math.isnan(mn):
                F["ganda_moola"] = float(bool(dosha.ganda_moola(int(mn) - 1)))
        except Exception:
            pass
    # vimsottari at the START (the wedding): needs the natal Moon (day precision) and the start date
    if day_ok and start and not math.isnan(F.get("Moon_lon", np.nan)):
        try:
            sy, sm, sd = int(start[:4]), max(1, int(start[5:7])), max(1, int(start[8:10]))
            yrs = (JU.julian_day_number((sy, sm, sd), (12, 0, 0)) - jd) / 365.25
            if 0 <= yrs <= 120:
                md, bh, into = vimsottari_at(F["Moon_lon"], yrs)
                F["dasa_lord_at_start"] = float(md); F["bhukti_lord_at_start"] = float(bh)
                F["years_into_dasa_at_start"] = float(into)
        except Exception:
            pass
    return F


_MUH_CACHE = {}
VIVAHA_NAK = {4, 5, 10, 12, 13, 15, 17, 19, 21, 26, 27}     # Rohini Mrigasira Magha U.Phalguni Hasta Svati Anuradha Mula U.Ashadha U.Bhadrapada Revati (1-based)
GOOD_TITHI = {2, 3, 5, 7, 10, 11, 13}
GOOD_VAARA = {1, 3, 4, 5}                                     # Mon Wed Thu Fri (0 = Sunday)
_GREENWICH = drik.Place("greenwich", 51.48, 0.0, 0.0)


def _panchanga_at(start):
    if start in _MUH_CACHE:
        return _MUH_CACHE[start]
    y, m, d = int(start[:4]), int(start[5:7]), int(start[8:10])
    jd = JU.julian_day_number((y, m, d), (12, 0, 0))
    out = {}
    try:
        out["tithi"] = int(drik.tithi(jd, _GREENWICH)[0]); out["nak"] = int(drik.nakshatra(jd, _GREENWICH)[0])
        out["yoga"] = int(drik.yogam(jd, _GREENWICH)[0]); out["karana"] = int(drik.karana(jd, _GREENWICH)[0])
        out["vaara"] = int(drik.vaara(jd, _GREENWICH)); lm = drik.lunar_month(jd, _GREENWICH)
        out["lunar_month"] = int(lm[0]); out["adhika"] = int(bool(lm[1]))
        pp = charts.rasi_chart(jd, _GREENWICH)
        pos = {GRAHA[r[0]]: r[1] for r in pp[1:]}
        out["lon"] = {g: float(v[0] * 30 + v[1]) for g, v in pos.items()}
        out["sun_sign"] = int(pos["Sun"][0]); out["moon_sign"] = int(pos["Moon"][0])
        out["jup_sign"] = int(pos["Jupiter"][0]); out["ven_sign"] = int(pos["Venus"][0])
        # combustion of Jupiter / Venus (Guru / Shukra asta): within 11 / 10 degrees of the Sun (Raman)
        sl = pos["Sun"][0] * 30 + pos["Sun"][1]
        for g, orb in (("Jupiter", 11.0), ("Venus", 10.0)):
            gl = pos[g][0] * 30 + pos[g][1]; d_ = abs((gl - sl + 180) % 360 - 180)
            out[f"{g}_combust"] = int(d_ < orb)
    except Exception:
        pass
    _MUH_CACHE[start] = out
    return out


def muhurta(start, nak_o, nak_y, moon_o, moon_y):
    """Vivaha muhurta features of the wedding day against the two natal Moons. All keys prefixed wed_."""
    P = _panchanga_at(start)
    F = {}
    if not P:
        return F
    F["wed_tithi"] = float(P["tithi"]); F["wed_nakshatra"] = float(P["nak"]); F["wed_yoga"] = float(P["yoga"])
    F["wed_karana"] = float(P["karana"]); F["wed_vaara"] = float(P["vaara"]); F["wed_lunar_month"] = float(P["lunar_month"])
    F["wed_adhika_masa"] = float(P["adhika"])
    F["wed_vivaha_nakshatra"] = float(P["nak"] in VIVAHA_NAK)
    F["wed_good_tithi"] = float(P["tithi"] in GOOD_TITHI or (P["tithi"] - 15) in GOOD_TITHI)
    F["wed_good_vaara"] = float(P["vaara"] in GOOD_VAARA)
    F["wed_kharmas"] = float(P["sun_sign"] in (8, 11))               # Sun in Dhanu / Meena (0-based 8, 11)
    F["wed_guru_asta"] = float(P.get("Jupiter_combust", 0)); F["wed_shukra_asta"] = float(P.get("Venus_combust", 0))
    F["wed_sun_sign"] = float(P["sun_sign"]); F["wed_moon_sign"] = float(P["moon_sign"])
    F["wed_jupiter_sign"] = float(P["jup_sign"]); F["wed_venus_sign"] = float(P["ven_sign"])
    for who, nk, ms in (("dad", nak_o, moon_o), ("mom", nak_y, moon_y)):
        if nk is not None and not (isinstance(nk, float) and math.isnan(nk)):
            tara = ((P["nak"] - int(nk)) % 27) % 9 + 1                 # 1..9 from the janma nakshatra
            F[f"wed_tara_{who}"] = float(tara)
            F[f"wed_tara_bad_{who}"] = float(tara in (3, 5, 7))          # Vipat, Pratyari, Naidhana
        if ms is not None and not (isinstance(ms, float) and math.isnan(ms)):
            cb = (P["moon_sign"] - int(ms)) % 12 + 1                     # transit Moon from the janma rasi
            F[f"wed_chandra_{who}"] = float(cb)
            F[f"wed_chandra_bad_{who}"] = float(cb in (4, 8, 12))
    return F


def couple(dob_o, lat_o, lon_o, dob_y, lat_y, lon_y, start=None):
    """Both persons plus the pair features. First person = DAD, second = MOM. Keys are prefixed dad_/mom_/pair_."""
    O = person(dob_o, lat_o, lon_o, start)
    Y = person(dob_y, lat_y, lon_y, start)
    F = {f"dad_{k}": v for k, v in O.items()}
    F.update({f"mom_{k}": v for k, v in Y.items()})
    # Ashtakoota in its own orientation: the tradition's "boy" is the dad and "girl" the mom, which the dad/mom
    # ordering of this edition makes literal (the two-dates editions had no sex and scored both orderings).
    no, po = O.get("moon_nakshatra"), O.get("moon_pada")
    ny, py = Y.get("moon_nakshatra"), Y.get("moon_pada")
    if all(v is not None and not (isinstance(v, float) and math.isnan(v)) for v in (no, po, ny, py)):
        KUTA = ["varna", "vasiya", "tara", "yoni", "maitri", "gana", "bhakoot", "nadi", "total"]
        try:
            sc = compatibility.Ashtakoota(int(no), int(po), int(ny), int(py)).compatibility_score()
            for ki, kn in enumerate(KUTA):
                F[f"pair_ak_{kn}"] = float(sc[ki])
        except Exception:
            pass
        F["pair_nakshatra_distance"] = float(min((no - ny) % 27, (ny - no) % 27))
        F["pair_same_nakshatra"] = float(no == ny)
    for k in ("Moon_sign", "lagna_sign", "Sun_sign", "Venus_sign", "Jupiter_sign", "Saturn_sign", "Rahu_sign"):
        a, b = O.get(k), Y.get(k)
        if a is not None and b is not None and not (math.isnan(a) or math.isnan(b)):
            F[f"pair_{k}_distance"] = float(min((a - b) % 12, (b - a) % 12))
            F[f"pair_{k}_same"] = float(a == b)
    # each partner's grahas in the other's houses (transposition), from the two lagnas
    lo, ly = O.get("lagna_sign"), Y.get("lagna_sign")
    if lo is not None and ly is not None and not (math.isnan(lo) or math.isnan(ly)):
        for g in GRAHA:
            so, sy = O.get(f"{g}_sign"), Y.get(f"{g}_sign")
            if so is not None and not math.isnan(so):
                F[f"pair_dad_{g}_in_mom_house"] = float((so - ly) % 12 + 1)
            if sy is not None and not math.isnan(sy):
                F[f"pair_mom_{g}_in_dad_house"] = float((sy - lo) % 12 + 1)
    # VIVAHA MUHURTA -- the wedding day itself, read as the muhurta texts read it, for rows whose start has a
    # real day (a YYYY-01-01 start is a year-only record and gets NaN here). The panchanga at noon UT is
    # place-independent to within the day; the lagna of the wedding would need the wedding place, which the data
    # does not have, so it is not fabricated. Tara bala and chandra bala are read from EACH partner's natal Moon.
    if start:
        try:
            P = _panchanga_at(start)
            real_day = not start.endswith("-00")
            for g, lon in P.get("lon", {}).items():
                # the wedding sky, sidereal, noon UT: every graha on a real day; on a year-only start (published
                # as 1 January) only the bodies that move slowly enough for the year to place them
                if real_day or g in SLOW:
                    F[f"wed_{g}_lon"] = lon
            if real_day:
                F.update(muhurta(start, O.get("moon_nakshatra"), Y.get("moon_nakshatra"), O.get("Moon_sign"), Y.get("Moon_sign")))
        except Exception:
            pass
    for k in ("dasa_lord_at_start", "bhukti_lord_at_start", "manglik", "kala_sarpa"):
        a, b = O.get(k), Y.get(k)
        if a is not None and b is not None:
            F[f"pair_{k}_same"] = float(a == b)
            F[f"pair_{k}_either"] = float(bool(a) or bool(b)) if k in ("manglik", "kala_sarpa") else np.nan
    return F


if __name__ == "__main__":
    import json, time
    t = time.time()
    f = couple("1850-06-15", 48.85, 2.35, "1858-02-03", 51.5, -0.12, start="1880-05-01")
    print(f"  couple: {len(f)} features in {(time.time()-t)*1000:.0f} ms")
    for k in list(f)[:12] + [k for k in f if k.startswith("pair_")][:10]:
        print(f"    {k:<36} {f[k]}")
    g = couple("1856-00-00", 48.85, 2.35, "1858-02-03", 51.5, -0.12)
    nan = sum(1 for v in g.values() if isinstance(v, float) and math.isnan(v))
    print(f"  year-only dad: {len(g)} features, {nan} NaN (day-dependent ones), "
          f"dad Jupiter sign = {g.get('dad_Jupiter_sign')}, dad Moon nakshatra = {g.get('dad_Moon_nakshatra')}")
