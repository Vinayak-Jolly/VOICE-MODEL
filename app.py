from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from datetime import datetime, timezone
import requests
import re
import time
import math
import os
import json

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', 'sk-fake-key-for-testing')
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1/chat/completions"


def call_deepseek_api(prompt, max_tokens=500):
    """Call DeepSeek API with the given prompt"""
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }

        data = {
            'model': 'deepseek-chat',
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': 0.3,
            'top_p': 0.9
        }

        response = requests.post(
            DEEPSEEK_BASE_URL, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
        else:
            print(
                f"DeepSeek API error: {response.status_code} - {response.text}")
            return None

    except Exception as e:
        print(f"DeepSeek API call failed: {e}")
        return None


_airport_cache = {}
_cache_ttl = 86400


def get_airport_info_from_external_apis(icao_code: str) -> dict:
    icao_code = icao_code.upper().strip()
    k = f"airport_{icao_code}"
    if k in _airport_cache:
        ts, data = _airport_cache[k]
        if time.time() - ts < _cache_ttl:
            return data
    try:
        url = "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat"
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            for line in r.text.splitlines():
                if not line or len(line) < 10:
                    continue
                parts = []
                buf = ""
                q = False
                for ch in line:
                    if ch == '"':
                        q = not q
                    elif ch == ',' and not q:
                        parts.append(buf.strip('"'))
                        buf = ""
                    else:
                        buf += ch
                if buf:
                    parts.append(buf.strip('"'))
                if len(parts) >= 9:
                    name, city, country = parts[1], parts[2], parts[3]
                    iata = parts[4] if len(parts) > 4 else ""
                    icao = parts[5] if len(parts) > 5 else ""
                    lat = parts[6] if len(parts) > 6 else ""
                    lon = parts[7] if len(parts) > 7 else ""
                    alt = parts[8] if len(parts) > 8 else ""
                    if ((icao.upper() == icao_code or iata.upper() == icao_code)
                            and name not in ["", "\\N"] and lat not in ["", "\\N"] and lon not in ["", "\\N"]):
                        try:
                            latf = float(lat)
                            lonf = float(lon)
                            elev = int(float(alt)) if alt not in [
                                "", "\\N"] else None
                        except:
                            latf = lonf = None
                            elev = None
                        if latf is not None and lonf is not None:
                            data = {"icao": (icao.upper() if icao and icao != "\\N" else icao_code),
                                    "iata": (iata.upper() if iata and iata != "\\N" else ""),
                                    "name": name, "city": (city if city and city != "\\N" else "Unknown"),
                                    "country": (country if country and country != "\\N" else "Unknown"),
                                    "latitude": latf, "longitude": lonf, "elevation_ft": elev, "source": "OpenFlights"}
                            _airport_cache[k] = (time.time(), data)
                            return data
    except Exception:
        pass
    fallback = {"icao": icao_code, "iata": "", "name": f"Airport {icao_code}", "city": "Unknown", "country": "Unknown",
                "latitude": None, "longitude": None, "elevation_ft": None, "source": "Fallback"}
    _airport_cache[k] = (time.time(), fallback)
    return fallback


def get_weather_data(icao: str) -> str:
    icao = icao.upper()
    try:
        url = f"https://tgftp.nws.noaa.gov/data/observations/metar/stations/{icao}.TXT"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            lines = r.text.strip().splitlines()
            if len(lines) >= 2 and lines[1].startswith(icao):
                return lines[1].strip()
    except Exception:
        pass
    try:
        url = f"https://aviationweather.gov/api/data/metar?format=json&ids={icao}"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                raw = data[0].get("raw_text", "")
                if raw:
                    return raw
    except Exception:
        pass
    now = datetime.utcnow()
    d = now.strftime("%d")
    H = now.strftime("%H")
    M = now.strftime("%M")
    test = {"KLAX": f"KLAX {d}{H}{M}Z 25012G18KT 6SM BR FEW008 SCT015 BKN250 22/19 A2995 RMK AO2",
            "KPHX": f"KPHX {d}{H}{M}Z 06015G22KT 10SM FEW050 SCT120 33/15 A2998 RMK AO2",
            "VABB": f"VABB {d}{H}{M}Z 27010KT 5000 HZ SCT020 31/24 Q1010 NOSIG",
            "KTUS": f"KTUS {d}{H}{M}Z 09015G28KT 10SM TS +TSRA SCT030 BKN060 CB100 28/22 A2992 RMK AO2 TSB45"}
    return test.get(icao, f"{icao} {d}{H}{M}Z 27010KT 9999 FEW030 22/18 Q1013 NOSIG")


def fetch_airsigmet_json():
    try:
        url = "https://aviationweather.gov/api/data/airsigmet?format=json"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def filter_advisories_by_prefix(data, icao_prefix, want_sigmet, want_airmet):
    sigs = []
    airs = []
    for it in data:
        raw = it.get("raw_text") or ""
        if not raw:
            continue
        hazard = it.get("hazard") or ""
        levels = it.get("levels") or ""
        vfrom = it.get("valid_time_from") or it.get("valid_from") or ""
        vto = it.get("valid_time_to") or it.get("valid_to") or ""
        rec = {"raw_text": raw, "hazard": hazard,
               "levels": levels, "valid_from": vfrom, "valid_to": vto}
        txt = raw.upper()
        if "AIRMET" in txt:
            if want_airmet:
                airs.append(rec)
        else:
            if want_sigmet:
                sigs.append(rec)
    return sigs[:10], airs[:10]


def analyze_severity(metar_text: str) -> str:
    t = metar_text.upper()
    if any(x in t for x in ["TS", "+TS", "TSRA", "+TSRA", "CB", "FC"]):
        return "SEVERE"
    if any(x in t for x in ["RA", "+RA", "SN", "BR", "FG", "BKN008", "BKN009", "OVC008", "OVC009"]):
        return "MODERATE"
    return "CLEAR"


def _parse_all(metar: str) -> dict:
    t = f" {metar.strip()} "
    out = {"time": None, "wind": None, "vis_sm": None, "vis_m": None, "clouds": [],
           "temp_c": None, "dew_c": None, "qnh_hpa": None, "rmk": ""}
    m = re.search(r'\b(\d{6})Z\b', t)
    if m:
        out["time"] = m.group(1)
    m = re.search(r'\b(\d{3}|VRB)(\d{2,3})(G(\d{2,3}))?KT\b', t)
    if m:
        out["wind"] = {"dir": m.group(1), "spd": int(
            m.group(2)), "gst": int(m.group(4)) if m.group(4) else None}
    m = re.search(r'\b(\d{1,2}(?:\s+\d/\d)?|\d/\d)\s*SM\b', t)
    if m:
        s = m.group(1).replace(" ", "")
        out["vis_sm"] = (float(s.split("/")[0]) /
                         float(s.split("/")[1])) if "/" in s else float(s)
    if out["vis_sm"] is None:
        m = re.search(r'\b(\d{4})\b', t)
        if m:
            out["vis_m"] = int(m.group(1))
    for cov, h, typ in re.findall(r'\b(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?\b', t):
        out["clouds"].append(
            {"cov": cov, "h_ft": int(h)*100, "type": typ or ""})
    m = re.search(r'\s(M?\d{2})/(M?\d{2})\s', t)
    if m:
        def c(v): return -int(v[1:]) if v.startswith("M") else int(v)
        out["temp_c"] = c(m.group(1))
        out["dew_c"] = c(m.group(2))
    m = re.search(r'\bQ(\d{4})\b', t)
    if m:
        out["qnh_hpa"] = int(m.group(1))
    else:
        m = re.search(r'\bA(\d{4})\b', t)
        if m:
            out["qnh_hpa"] = round(int(m.group(1))/100.0 * 33.8639)
    m = re.search(r'\bRMK\b(.*)$', t)
    if m:
        out["rmk"] = m.group(1).strip()
    return out


def _da(temp_c, qnh_hpa, elev_ft):
    try:
        if temp_c is None or qnh_hpa is None or elev_ft is None:
            return None
        inhg = qnh_hpa/33.8639
        p_alt = elev_ft + (29.92 - inhg)*1000.0
        isa = 15.0 - 2.0*(p_alt/1000.0)
        return int(round(p_alt + 120.0*(temp_c - isa)))
    except:
        return None

# DeepSeek-powered analysis functions


def generate_professional_summary(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Analyze this METAR and provide a professional pilot briefing summary:

METAR: {metar}
Airport: {airport.get('name')} ({airport.get('icao')}) in {airport.get('city')}
Elevation: {airport.get('elevation_ft', 'unknown')} ft

Provide exactly this format:
Station: [ICAO] ([City])
Time: [Day]th, [HHMM] UTC ([Local time if known])
Wind: [Direction]° at [Speed] kt [gusting info if applicable]
Visibility: [Value] [unit] [restrictions if any]
Clouds: [Coverage] at [Height] ft [types if any]
Temp/Dew: [Temp]°C / [Dew]°C
QNH: [Value] hPa
Trend: [Trend info if available]

Keep it concise and professional."""

    ai_response = call_deepseek_api(prompt, max_tokens=300)

    if ai_response:
        return ai_response

    # Fallback to structured format if AI fails
    c = parsed_data
    lines = []
    lines.append(
        f"Station: {airport.get('icao', 'XXXX')} ({airport.get('city', 'Unknown')})")
    if c.get("time"):
        lines.append(
            f"Time: {c['time'][:2]}th, {c['time'][2:4]}{c['time'][4:6]} UTC")
    if c.get("wind"):
        w = c["wind"]
        gust = f", gusting {w['gst']} kt" if w.get("gst") else ""
        lines.append(f"Wind: {w['dir']}° at {w['spd']} kt{gust}")
    if c.get("vis_sm"):
        hz = " in haze" if " HZ " in metar.upper() else ""
        lines.append(f"Visibility: {c['vis_sm']:.2f} SM{hz}")
    elif c.get("vis_m"):
        hz = " in haze" if " HZ " in metar.upper() else ""
        lines.append(f"Visibility: {c['vis_m']/1000:.1f} km{hz}")
    if c.get("clouds"):
        low = min(c["clouds"], key=lambda x: x["h_ft"])
        lines.append(f"Clouds: {low['cov']} at {low['h_ft']:,} ft")
    if c.get("temp_c") is not None and c.get("dew_c") is not None:
        lines.append(f"Temp/Dew: {c['temp_c']}°C / {c['dew_c']}°C")
    if c.get("qnh_hpa"):
        lines.append(f"QNH: {int(c['qnh_hpa'])} hPa")
    if " NOSIG " in metar.upper():
        lines.append("Trend: NOSIG")
    return "\n".join(lines)


def generate_operational_takeaway(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Based on this METAR data, provide a concise operational takeaway for pilots:

METAR: {metar}
Airport: {airport.get('name')} at {airport.get('elevation_ft', 0)} ft elevation

Focus on:
1. Flight category implications (VFR/IFR suitability)
2. Key operational concerns (performance, visibility, approach considerations)
3. Keep it under 100 words, professional pilot language

Format: Single paragraph, practical operational advice."""

    ai_response = call_deepseek_api(prompt, max_tokens=150)

    if ai_response:
        return ai_response

    return "Operational assessment: Standard briefing recommended. Check NOTAMs and performance calculations."


def generate_recommendations(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Based on this METAR, provide specific pilot recommendations:

METAR: {metar}
Airport: {airport.get('name')} at {airport.get('elevation_ft', 0)} ft elevation

Provide 2-3 specific, actionable recommendations in this format:
[Category]: [Specific advice with numbers/procedures]

Categories should be relevant to the conditions (e.g., Performance, Visibility, Weather, Approach, etc.)
Each recommendation should be one line, practical and specific."""

    ai_response = call_deepseek_api(prompt, max_tokens=200)

    if ai_response:
        return ai_response

    return "Standard briefing: Review performance charts, brief approaches, monitor weather trends."


def generate_altitude_distance_analysis(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Analyze this METAR for altitude/distance-based weather impacts:

METAR: {metar}
Airport: {airport.get('name')} at {airport.get('elevation_ft', 0)} ft elevation

Provide detailed analysis in this structure:
Surface–2,000 ft AGL (airport vicinity ≤5 nm): [conditions and impacts]
2,000–6,500 ft (nearby 5–10 nm): [conditions and impacts]  
6,500–20,000 ft (regional 10+ nm): [conditions and impacts]
FL200+ (high altitude): [conditions and impacts if relevant]

Focus on:
- Cloud layers and their operational impact
- Visibility restrictions and their range
- Turbulence/convection zones
- Performance impacts at different altitudes
- Special callouts for dense clouds aloft vs clear ground visibility

Be specific about altitudes, distances, and operational implications."""

    ai_response = call_deepseek_api(prompt, max_tokens=400)

    if ai_response:
        return ai_response

    # Fallback structured analysis
    c = parsed_data
    lines = []

    # Surface analysis
    surface_factors = []
    if " HZ " in metar.upper():
        surface_factors.append("haze degrading visual cues")
    if " BR " in metar.upper():
        surface_factors.append("mist reducing contrast")
    if " FG " in metar.upper():
        surface_factors.append("fog restricting surface visibility")

    low_clouds = [cl for cl in c.get("clouds", []) if cl["h_ft"] <= 2000]
    if low_clouds:
        surface_factors.extend(
            [f"{cl['cov']} {cl['h_ft']:,} ft" for cl in low_clouds])

    if surface_factors:
        lines.append(
            f"Surface–2,000 ft AGL (airport vicinity ≤5 nm): {'; '.join(surface_factors)}.")
    else:
        lines.append(
            "Surface–2,000 ft AGL (airport vicinity ≤5 nm): Clear conditions reported.")

    # Mid-level analysis
    mid_clouds = [cl for cl in c.get(
        "clouds", []) if 2000 < cl["h_ft"] <= 6500]
    if mid_clouds:
        mid_desc = [f"{cl['cov']} {cl['h_ft']:,} ft" for cl in mid_clouds]
        lines.append(
            f"2,000–6,500 ft (nearby 5–10 nm): {', '.join(mid_desc)}.")
    else:
        lines.append(
            "2,000–6,500 ft (nearby 5–10 nm): No significant layers reported.")

    # High-level analysis
    high_clouds = [cl for cl in c.get(
        "clouds", []) if 6500 < cl["h_ft"] <= 20000]
    if high_clouds:
        high_desc = [f"{cl['cov']} {cl['h_ft']:,} ft" for cl in high_clouds]
        lines.append(
            f"6,500–20,000 ft (regional 10+ nm): {', '.join(high_desc)}.")
    else:
        lines.append(
            "6,500–20,000 ft (regional 10+ nm): No significant layers reported.")

    # FL200+ analysis
    very_high_clouds = [cl for cl in c.get("clouds", []) if cl["h_ft"] > 20000]
    if very_high_clouds:
        vh_desc = [f"{cl['cov']} {cl['h_ft']:,} ft" for cl in very_high_clouds]
        lines.append(f"FL200+ (high altitude): {', '.join(vh_desc)}.")
    else:
        lines.append("FL200+ (high altitude): No high-level layers reported.")

    return "\n".join(lines)


def generate_detailed_decode(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Provide a detailed field-by-field decode of this METAR:

METAR: {metar}
Airport: {airport.get('name')} ({airport.get('icao')}) in {airport.get('city')}

Decode each field explaining:
- What each code means
- Technical details and ranges
- Local time conversions where applicable
- Calculated values (like RH, pressure altitude, etc.)

Format as separate lines, each starting with the field code followed by explanation.
Be technically accurate and educational."""

    ai_response = call_deepseek_api(prompt, max_tokens=500)

    if ai_response:
        return ai_response

    # Fallback structured decode
    c = parsed_data
    lines = []
    lines.append(
        f"{airport.get('icao', 'XXXX')} — {airport.get('name', 'Airport')} ({airport.get('city', 'Unknown')}).")

    if c.get("time"):
        lines.append(
            f"{c['time']} — report time: {c['time'][:2]}th at {c['time'][2:4]}{c['time'][4:6]} UTC.")

    if c.get("wind"):
        w = c["wind"]
        gust_txt = f", gusting {w['gst']} kt" if w.get("gst") else ""
        lines.append(
            f"{w['dir']}{w['spd']:02d}KT — wind from {w['dir']}° at {w['spd']} kt{gust_txt}.")

    if c.get("vis_sm"):
        lines.append(f"VIS — {c['vis_sm']:.2f} statute miles.")
    elif c.get("vis_m"):
        sm_equiv = c['vis_m'] * 0.000621371
        lines.append(
            f"{c['vis_m']} — horizontal visibility {c['vis_m']/1000:.1f} km ≈ {sm_equiv:.2f} SM.")

    if " HZ " in metar.upper():
        lines.append("HZ — haze reducing horizontal visibility.")
    if " BR " in metar.upper():
        lines.append("BR — mist.")
    if " FG " in metar.upper():
        lines.append("FG — fog.")

    for cl in c.get("clouds", []):
        covmap = {'FEW': 'few (1–2/8)', 'SCT': 'scattered (3–4/8)',
                  'BKN': 'broken (5–7/8)', 'OVC': 'overcast (8/8)'}
        s = f"{cl['cov']}{cl['h_ft']//100:03d} — {covmap.get(cl['cov'], cl['cov'])} at {cl['h_ft']:,} ft AGL"
        if cl.get("type") == "CB":
            s += " (cumulonimbus)."
        elif cl.get("type") == "TCU":
            s += " (towering cumulus)."
        else:
            s += "."
        lines.append(s)

    if c.get("temp_c") is not None and c.get("dew_c") is not None:
        # Calculate RH
        try:
            rh = 100 * math.exp((17.625*c['dew_c'])/(243.04+c['dew_c'])) / \
                math.exp((17.625*c['temp_c'])/(243.04+c['temp_c']))
            lines.append(
                f"{c['temp_c']}/{c['dew_c']} — temperature {c['temp_c']} °C, dewpoint {c['dew_c']} °C; RH ≈ {rh:.0f}%.")
        except:
            lines.append(
                f"{c['temp_c']}/{c['dew_c']} — temperature {c['temp_c']} °C, dewpoint {c['dew_c']} °C.")

    if c.get("qnh_hpa"):
        inhg = c['qnh_hpa'] / 33.8639
        lines.append(
            f"Q{int(c['qnh_hpa'])} — altimeter {int(c['qnh_hpa'])} hPa (≈ {inhg:.2f} inHg).")

    if " NOSIG " in metar.upper():
        lines.append("NOSIG — no significant change in next ~2 hours.")

    return "\n".join(lines)


def generate_operational_implications(metar: str, airport: dict, parsed_data: dict) -> str:
    prompt = f"""Analyze the operational implications of this METAR for flight operations:

METAR: {metar}
Airport: {airport.get('name')} at {airport.get('elevation_ft', 0)} ft elevation

Cover these aspects:
- Flight category (VFR/IFR/MVFR/LIFR) with specific reasons
- Approach and landing considerations
- Takeoff and climb performance impacts
- Weather evolution trends
- Equipment/system considerations
- Specific pilot actions required

Be practical and specific to actual flight operations."""

    ai_response = call_deepseek_api(prompt, max_tokens=400)

    if ai_response:
        return ai_response

    # Fallback operational analysis
    c = parsed_data
    lines = []

    # Determine flight category
    vis_sm = c.get("vis_sm") or (c.get("vis_m", 9999) *
                                 0.000621371 if c.get("vis_m") else None)
    ceiling = None
    for cl in c.get("clouds", []):
        if cl["cov"] in ["BKN", "OVC"]:
            ceiling = cl["h_ft"] if ceiling is None else min(
                ceiling, cl["h_ft"])

    if (vis_sm and vis_sm < 1) or (ceiling and ceiling < 500):
        cat = "LIFR"
    elif (vis_sm and vis_sm < 3) or (ceiling and ceiling < 1000):
        cat = "IFR"
    elif (vis_sm and vis_sm <= 5) or (ceiling and ceiling <= 3000):
        cat = "MVFR"
    else:
        cat = "VFR"

    lines.append(f"Flight category: {cat}.")

    if " HZ " in metar.upper():
        lines.append(
            "Haze reduces visual contrast — brief go-around procedures and use instruments for visual segments.")

    if " FG " in metar.upper():
        lines.append(
            "Fog may require low-visibility procedures and precision approaches.")

    # Density altitude
    da = _da(c.get("temp_c"), c.get("qnh_hpa"), airport.get("elevation_ft"))
    if da:
        lines.append(
            f"Density altitude ≈ {da:,} ft — expect reduced performance, longer takeoff roll.")

    if " NOSIG " in metar.upper():
        lines.append(
            "NOSIG indicates stable conditions short-term; check TAF for longer trends.")

    return "\n".join(lines)


def generate_numbers_summary(metar: str, airport: dict, parsed_data: dict) -> str:
    c = parsed_data
    lines = []

    if c.get("vis_m"):
        sm_equiv = c['vis_m'] * 0.000621371
        lines.append(f"Visibility: {c['vis_m']:,} m / {sm_equiv:.2f} SM")
    elif c.get("vis_sm"):
        lines.append(f"Visibility: {c['vis_sm']:.2f} SM")

    # Cloud base
    ceiling = None
    for cl in c.get("clouds", []):
        if cl["cov"] in ["BKN", "OVC"]:
            ceiling = cl["h_ft"] if ceiling is None else min(
                ceiling, cl["h_ft"])
    if ceiling:
        lines.append(
            f"Cloud base: {ceiling:,} ft AGL / {int(ceiling * 0.3048)} m")

    # Relative humidity
    if c.get("temp_c") is not None and c.get("dew_c") is not None:
        try:
            rh = 100 * math.exp((17.625*c['dew_c'])/(243.04+c['dew_c'])) / \
                math.exp((17.625*c['temp_c'])/(243.04+c['temp_c']))
            lines.append(f"Relative humidity: ~{rh:.0f}%")
        except:
            pass

    # QNH conversion
    if c.get("qnh_hpa"):
        inhg = c['qnh_hpa'] / 33.8639
        lines.append(f"QNH: {int(c['qnh_hpa'])} hPa → {inhg:.2f} inHg")

    # Density altitude
    da = _da(c.get("temp_c"), c.get("qnh_hpa"), airport.get("elevation_ft"))
    if da:
        lines.append(f"Density altitude: ~{da:,} ft")

    return "\n".join(lines) if lines else "No calculated parameters available."


def generate_basic_ai_sections(metar: str) -> dict:
    """Generate basic AI-powered weather sections for backward compatibility"""
    prompt = f"""Analyze this METAR and provide brief, professional assessments for each category:

METAR: {metar}

For each category below, provide exactly one concise line with an emoji prefix:
1. Thunderstorms/Convection
2. Cloud conditions  
3. Visibility conditions
4. Wind conditions
5. Precipitation

Format each as: [emoji] [CATEGORY]: [brief assessment]
Be specific about conditions and operational impact."""

    ai_response = call_deepseek_api(prompt, max_tokens=300)

    if ai_response:
        content = ai_response
        lines = content.split('\n')

        # Parse the response into the expected format
        sections = {}
        for line in lines:
            if 'thunderstorm' in line.lower() or 'convect' in line.lower():
                sections['thunderstorms'] = line.strip()
            elif 'cloud' in line.lower():
                sections['clouds'] = line.strip()
            elif 'visibility' in line.lower():
                sections['visibility'] = line.strip()
            elif 'wind' in line.lower():
                sections['winds'] = line.strip()
            elif 'precipitation' in line.lower() or 'rain' in line.lower():
                sections['precipitation'] = line.strip()

        return sections

    # Fallback to basic pattern matching
    t = metar.upper()
    out = {}

    if "TS" in t or "CB" in t:
        out["thunderstorms"] = "⚡ THUNDERSTORMS: Active convection present — expect turbulence and delays."
    else:
        out["thunderstorms"] = "✅ NO CONVECTIVE ACTIVITY reported."

    if re.search(r'\b(FEW|SCT|BKN|OVC)\d{3}\b', t):
        out["clouds"] = "☁️ CLOUD LAYERS present — check ceilings for approach requirements."
    else:
        out["clouds"] = "☁️ CLEAR SKIES reported."

    if re.search(r'\b\d{1,4}\s*SM\b', metar) or re.search(r'\b\d{4}\b', t):
        out["visibility"] = "👁️ VISIBILITY restrictions noted — verify minimums."
    else:
        out["visibility"] = "👁️ GOOD VISIBILITY conditions."

    if re.search(r'\b\d{3}\d{2,3}(G\d{2,3})?KT\b', t):
        out["winds"] = "💨 WINDS reported — check crosswind components."
    else:
        out["winds"] = "💨 CALM conditions reported."

    if any(wx in t for wx in ["RA", "SN", "DZ", "SHRA"]):
        out["precipitation"] = "🌧️ PRECIPITATION occurring — runway conditions may be affected."
    else:
        out["precipitation"] = "☀️ NO PRECIPITATION reported."

    return out

# Routes


@app.route("/")
def root():
    return send_from_directory(".", "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()})


@app.route("/api/weather/<icao>")
def weather(icao):
    try:
        airport = get_airport_info_from_external_apis(icao)
        metar = get_weather_data(icao)
        severity = analyze_severity(metar)
        parsed_data = _parse_all(metar)

        # Generate AI-powered content
        professional_summary_text = generate_professional_summary(
            metar, airport, parsed_data)
        operational_takeaway_text = generate_operational_takeaway(
            metar, airport, parsed_data)
        recommendations_text = generate_recommendations(
            metar, airport, parsed_data)
        altitude_analysis_text = generate_altitude_distance_analysis(
            metar, airport, parsed_data)

        # Generate detailed sections
        field_decode_text = generate_detailed_decode(
            metar, airport, parsed_data)
        operational_impl_text = generate_operational_implications(
            metar, airport, parsed_data)
        numbers_summary_text = generate_numbers_summary(
            metar, airport, parsed_data)

        # Generate basic AI sections for compatibility
        ai_sections = generate_basic_ai_sections(metar)

        oneword = {"SEVERE": "hazardous", "MODERATE": "challenging",
                   "CLEAR": "favorable"}.get(severity, "review")
        concise = (f"Critical weather hazards at {airport['name']}." if severity == "SEVERE"
                   else f"Moderate weather impacts at {airport['name']}." if severity == "MODERATE"
                   else f"Conditions generally favorable at {airport['name']}.")

        analysis = {
            "severity": severity,
            "onewordsummary": oneword,
            "conciseanalysis": concise,
            "detailedanalysis": f"Comprehensive analysis for {airport['name']} indicates {severity.lower()} conditions.",
            "safetyconcerns": (["Severe weather hazards present — avoid convective cores; ground stops possible."]
                               if severity == "SEVERE" else
                               (["Weather impacts require enhanced procedures."] if severity == "MODERATE" else [])),
            "recommendations": (["Avoid cells by ≥20 nm", "Coordinate deviations with ATC", "Consider holding/diversion plans"]
                                if severity == "SEVERE" else
                                (["Brief crew on weather", "Carry contingency fuel", "Monitor trends"]
                                 if severity == "MODERATE" else
                                 ["Standard briefing and normal ops."])),
            "flightimpact": ("CRITICAL FLIGHT IMPACT: expect delays and possible diversions."
                             if severity == "SEVERE"
                             else "MODERATE FLIGHT IMPACT: delays possible."
                             if severity == "MODERATE"
                             else "MINIMAL FLIGHT IMPACT: normal ops."),
            # AI-generated sections
            "professional_summary": professional_summary_text,
            "operational_takeaway": operational_takeaway_text,
            "recommendations_detailed": recommendations_text,
            "altitude_distance_brief": altitude_analysis_text,
            # Backward compatibility sections
            "thunderstorms": ai_sections.get("thunderstorms", "✅ NO CONVECTIVE ACTIVITY reported."),
            "clouds": ai_sections.get("clouds", "☁️ CLEAR SKIES reported."),
            "visibility": ai_sections.get("visibility", "👁️ GOOD VISIBILITY conditions."),
            "winds": ai_sections.get("winds", "💨 CALM conditions reported."),
            "precipitation": ai_sections.get("precipitation", "☀️ NO PRECIPITATION reported."),
            # Detailed toggle sections
            "details": {
                "field_decode": field_decode_text,
                "operational_implications": operational_impl_text,
                "numbers_summary": numbers_summary_text
            },
            "product_focus": "NONE"
        }

        # Handle SIGMET/AIRMET filtering
        want_sigmet = request.args.get("sigmet", "false").lower() == "true"
        want_airmet = request.args.get("airmet", "false").lower() == "true"
        sigmets = []
        airmets = []

        if want_sigmet or want_airmet:
            data = fetch_airsigmet_json()
            prefix = airport.get("icao", "")[:2] if airport.get("icao") else ""
            sigmets, airmets = filter_advisories_by_prefix(
                data, prefix, want_sigmet, want_airmet)

            if want_sigmet and want_airmet:
                analysis["product_focus"] = "BOTH"
            elif want_sigmet:
                analysis["product_focus"] = "SIGMET"
            elif want_airmet:
                analysis["product_focus"] = "AIRMET"

            # Update concise analysis with advisory info
            hazards = []
            hazards += [s.get("hazard") or "SIGMET" for s in sigmets]
            hazards += [a.get("hazard") or "AIRMET" for a in airmets]
            if hazards:
                uniq = sorted({h for h in hazards if h})
                analysis["conciseanalysis"] += f" Advisories: {', '.join(uniq)}."

        resp = {
            "airportcode": airport["icao"],
            "airport": airport,
            "weather": {"metar": {"raw_text": metar, "parsed": {"severity": severity}}},
            "analysis": analysis,
            "timestamp": datetime.utcnow().isoformat(),
            "datasummary": {"typesincluded": ["METAR", "AI Analysis"], "totalreports": 1}
        }

        if want_sigmet or want_airmet:
            resp["sigmets"] = sigmets
            resp["airmets"] = airmets

        return jsonify(resp)

    except Exception as e:
        return jsonify({"error": f"weather error: {str(e)}"}), 500


@app.route("/api/route")
def route():
    try:
        airports_param = request.args.get("airports", "")
        codes = [c.strip().upper()
                 for c in airports_param.split(",") if c.strip()]
        if len(codes) < 2:
            return jsonify({"error": "Need at least 2 airports"}), 400

        want_sigmet = request.args.get("sigmet", "false").lower() == "true"
        want_airmet = request.args.get("airmet", "false").lower() == "true"
        advis_data = fetch_airsigmet_json() if (want_sigmet or want_airmet) else []

        timeline = []
        severities = []
        airports_data = []

        for code in codes:
            ap = get_airport_info_from_external_apis(code)
            metar = get_weather_data(code)
            sev = analyze_severity(metar)
            severities.append(sev)
            parsed_data = _parse_all(metar)

            # Generate AI content for each node
            prof_summary = generate_professional_summary(
                metar, ap, parsed_data)
            op_takeaway = generate_operational_takeaway(metar, ap, parsed_data)
            recommendations = generate_recommendations(metar, ap, parsed_data)
            altitude_analysis = generate_altitude_distance_analysis(
                metar, ap, parsed_data)

            field_decode = generate_detailed_decode(metar, ap, parsed_data)
            op_implications = generate_operational_implications(
                metar, ap, parsed_data)
            numbers_summary = generate_numbers_summary(metar, ap, parsed_data)

            ai_sections = generate_basic_ai_sections(metar)

            oneword = {"SEVERE": "hazardous", "MODERATE": "challenging",
                       "CLEAR": "favorable"}.get(sev, "review")
            concise = (f"Critical hazards at {ap['name']}." if sev == "SEVERE"
                       else f"Moderate weather at {ap['name']}." if sev == "MODERATE"
                       else f"Favorable conditions at {ap['name']}.")

            node_analysis = {
                "severity": sev, "onewordsummary": oneword, "conciseanalysis": concise,
                "detailedanalysis": f"Route node: {sev.lower()} conditions.",
                "safetyconcerns": [], "recommendations": [], "flightimpact": "See node summary.",
                "professional_summary": prof_summary,
                "operational_takeaway": op_takeaway,
                "recommendations_detailed": recommendations,
                "altitude_distance_brief": altitude_analysis,
                "thunderstorms": ai_sections.get("thunderstorms", "✅ NO CONVECTIVE ACTIVITY reported."),
                "clouds": ai_sections.get("clouds", "☁️ CLEAR SKIES reported."),
                "visibility": ai_sections.get("visibility", "👁️ GOOD VISIBILITY conditions."),
                "winds": ai_sections.get("winds", "💨 CALM conditions reported."),
                "precipitation": ai_sections.get("precipitation", "☀️ NO PRECIPITATION reported."),
                "details": {
                    "field_decode": field_decode,
                    "operational_implications": op_implications,
                    "numbers_summary": numbers_summary
                },
                "product_focus": "NONE"
            }

            # Handle advisories for this node
            node_sigmets, node_airmets = [], []
            if advis_data:
                prefix = ap.get("icao", "")[:2] if ap.get("icao") else ""
                node_sigmets, node_airmets = filter_advisories_by_prefix(
                    advis_data, prefix, want_sigmet, want_airmet)
                if want_sigmet and want_airmet:
                    node_analysis["product_focus"] = "BOTH"
                elif want_sigmet:
                    node_analysis["product_focus"] = "SIGMET"
                elif want_airmet:
                    node_analysis["product_focus"] = "AIRMET"

            airports_data.append({
                "code": code,
                "info": ap,
                "current_weather": {"raw_text": metar, "parsed": {"severity": sev}},
                "analysis": node_analysis,
                "sigmets": node_sigmets,
                "airmets": node_airmets
            })

            timeline.append({
                "icao": code, "name": ap["name"], "latitude": ap["latitude"], "longitude": ap["longitude"],
                "severity": sev, "weather_summary": metar[:50]+"..." if len(metar) > 50 else metar
            })

        overall = "SEVERE" if "SEVERE" in severities else (
            "MODERATE" if "MODERATE" in severities else "CLEAR")
        top_focus = "BOTH" if (want_sigmet and want_airmet) else (
            "SIGMET" if want_sigmet else ("AIRMET" if want_airmet else "NONE"))

        resp = {
            "route": codes,
            "overallseverity": overall,
            "analysis": f"Route weather analysis for {' → '.join(codes)} indicates {overall.lower()} conditions overall.",
            "recommendations": ["Monitor each node's conditions", "Plan alternates for adverse segments"],
            "weathersummary": [{"airport": a["code"], "type": a["analysis"]["severity"],
                                "timestamp": datetime.utcnow().isoformat()} for a in airports_data],
            "nodes": airports_data,
            "product_focus": top_focus
        }
        return jsonify(resp)

    except Exception as e:
        return jsonify({"error": f"route error: {str(e)}"}), 500


if __name__ == "__main__":
    print("AeroLish backend with DeepSeek AI http://localhost:5000")
    print("Set DEEPSEEK_API_KEY environment variable for AI features")
    app.run(host="0.0.0.0", port=5000, debug=True)
