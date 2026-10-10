import json
import os
import sys
import time
import urllib.request
import urllib.parse
import ssl
import base64
import re
import requests
import streamlit as st
import folium
import pandas as pd
import altair as alt
import numpy as np
from streamlit_folium import st_folium
import streamlit.components.v1 as components

# Try importing geopy gracefully
try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

# ── 1. PAGE CONFIG ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Built Environment Analysis",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 2. GLOBAL CONSTANTS & ALL 50 STATES ESG PROFILES ─────────────────────────
STATE_NAME_TO_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA",
    "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA",
    "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
    "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO",
    "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ",
    "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH",
    "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"
}

STATE_ESG_PROFILES = {
    "AL": ("High Risk", "#ef4444", 0.16, "High Risk ─ High environmental justice burden and limited renewable grid capacity."),
    "AK": ("Favorable", "#10b981", 0.13, "Favorable ─ Low cooling loads with abundant clean hydro and wind opportunities."),
    "AZ": ("High Risk", "#ef4444", 0.20, "High Risk ─ Severe water scarcity and extreme ambient cooling requirements."),
    "AR": ("High Risk", "#ef4444", 0.15, "High Risk ─ Flood risk, regional water vulnerability, and minimal clean energy transition."),
    "CA": ("High Risk", "#ef4444", 0.20, "High Risk ─ Extreme wildfire threats, water stress, and elevated grid operating costs."),
    "CO": ("Conditional", "#f59e0b", 0.16, "Conditional ─ Excellent solar capacity balanced by wildfire exposure and water limits."),
    "CT": ("Grid Congestion", "#8b5cf6", 0.16, "Grid Congestion ─ ISO-NE grid congestion, high land costs, and spatial constraints."),
    "DE": ("Grid Congestion", "#8b5cf6", 0.15, "Grid Congestion ─ PJM queue delays, low land availability, and coastal flood risk."),
    "FL": ("High Risk", "#ef4444", 0.18, "High Risk ─ Severe hurricane risk, thermal cooling stress, and coastal inundation."),
    "GA": ("High Risk", "#ef4444", 0.16, "High Risk ─ High thermal loads and moderate environmental justice burdens."),
    "HI": ("Conditional", "#f59e0b", 0.14, "Conditional ─ Ambitious clean energy goals offset by isolated grid boundaries."),
    "ID": ("Favorable", "#10b981", 0.16, "Favorable ─ Low-carbon hydro grid with strong climate resilience."),
    "IL": ("Conditional", "#f59e0b", 0.14, "Conditional ─ High wind generation counterbalanced by Chicago grid bottlenecks."),
    "IN": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Expanding solar development with ongoing grid decarbonization needs."),
    "IA": ("Favorable", "#10b981", 0.16, "Favorable ─ National leader in wind power with minimal transmission congestion."),
    "KS": ("Conditional", "#f59e0b", 0.15, "Conditional ─ Outstanding wind generation potential with moderate regional water stress."),
    "KY": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Grid transitioning from fossil sources alongside localized flood risk."),
    "LA": ("High Risk", "#ef4444", 0.19, "High Risk ─ Elevated hurricane risk, severe flooding, and high carbon intensity."),
    "ME": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Offshore wind expansion capability with localized transmission bounds."),
    "MD": ("Grid Congestion", "#8b5cf6", 0.18, "Grid Congestion ─ Severe PJM interconnection bottlenecks and dense land development."),
    "MA": ("Grid Congestion", "#8b5cf6", 0.16, "Grid Congestion ─ ISO-NE grid saturation and elevated regional development expenses."),
    "MI": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Growing renewable energy portfolio with moderate seasonal grid flux."),
    "MN": ("Favorable", "#10b981", 0.15, "Favorable ─ Expanding wind energy, cool climate, and robust water availability."),
    "MS": ("High Risk", "#ef4444", 0.17, "High Risk ─ Flood vulnerability and limited green power infrastructure."),
    "MO": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Moderate renewable adoption with localized metropolitan grid constraints."),
    "MT": ("Favorable", "#10b981", 0.15, "Favorable ─ Abundant wind resources, cool ambient temperatures, and low density."),
    "NE": ("Conditional", "#f59e0b", 0.15, "Conditional ─ High wind power availability offset by Ogallala aquifer depletion risks."),
    "NV": ("High Risk", "#ef4444", 0.19, "High Risk ─ Desert water scarcity, extreme heat, and Las Vegas grid tension."),
    "NH": ("Conditional", "#f59e0b", 0.12, "Conditional ─ Low climate risk profile coupled with modest renewable generation."),
    "NJ": ("Grid Congestion", "#8b5cf6", 0.17, "Grid Congestion ─ Critical PJM transmission congestion and limited acreage."),
    "NM": ("Conditional", "#f59e0b", 0.16, "Conditional ─ Top-tier solar irradiance limited by regional water availability."),
    "NY": ("Conditional", "#f59e0b", 0.15, "Conditional ─ Clean hydro upstate opposed by NYC metro power constraints."),
    "NC": ("Conditional", "#f59e0b", 0.14, "Conditional ─ Strong solar adoption offset by coastal hurricane exposure."),
    "ND": ("Favorable", "#10b981", 0.18, "Favorable ─ Premier wind resources, cold ambient cooling, and low grid stress."),
    "OH": ("Conditional", "#f59e0b", 0.14, "Conditional ─ Growing data center corridor experiencing increasing PJM queue delays."),
    "OK": ("Conditional", "#f59e0b", 0.16, "Conditional ─ Robust wind energy capacity balanced by severe weather patterns."),
    "OR": ("Favorable", "#10b981", 0.18, "Favorable ─ Low-carbon hydro reliance, favorable ambient temperatures, and low water risk."),
    "PA": ("Conditional", "#f59e0b", 0.15, "Conditional ─ High power capacity facing PJM queue backlogs near urban centers."),
    "RI": ("Grid Congestion", "#8b5cf6", 0.15, "Grid Congestion ─ Constrained grid footprint and limited commercial site scale."),
    "SC": ("High Risk", "#ef4444", 0.16, "High Risk ─ Coastal storm vulnerability and high summertime cooling demand."),
    "SD": ("Favorable", "#10b981", 0.16, "Favorable ─ High wind generation density, cold climate, and ample land."),
    "TN": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Stable TVA power system with moderate renewable development."),
    "TX": ("Conditional", "#f59e0b", 0.18, "Conditional ─ Leading solar and wind capacity counterbalanced by ERCOT grid isolation."),
    "UT": ("Conditional", "#f59e0b", 0.17, "Conditional ─ Prime solar resources alongside Great Basin water scarcity."),
    "VT": ("Conditional", "#f59e0b", 0.12, "Conditional ─ Highly decarbonized energy mix with restricted regional distribution."),
    "VA": ("Grid Congestion", "#8b5cf6", 0.22, "Grid Congestion ─ Data Center Alley congestion with 3 to 5 year PJM queue delays."),
    "WA": ("Favorable", "#10b981", 0.22, "Favorable ─ Low-carbon hydro grid, cool ambient climate, and dry cooling viability."),
    "WV": ("Conditional", "#f59e0b", 0.13, "Conditional ─ High grid carbon intensity undergoing clean transition with topography limits."),
    "WI": ("Conditional", "#f59e0b", 0.13, "Conditional ─ Cool climate advantages paired with steady clean energy transition."),
    "WY": ("Favorable", "#10b981", 0.15, "Favorable ─ World-class wind density, low population impact, and cold ambient air.")
}

@st.cache_data(ttl=86400)
def get_us_states_geojson():
    """Fetches US State GeoJSON safely with reduced timeouts and reliable fallback."""
    urls = [
        "https://raw.githubusercontent.com/python-visualization/folium/main/examples/data/us-states.json",
        "https://raw.githubusercontent.com/PublicAffairs/State-Vector-Maps/master/geojson/us-states.json"
    ]
    for url in urls:
        try:
            resp = requests.get(url, timeout=2.5)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            continue
    return {"type": "FeatureCollection", "features": []}

def geocode_location(query_str):
    """Geocodes location using Nominatim engine safely."""
    if not query_str or not query_str.strip():
        return None
    
    query_clean = query_str.strip()
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query_clean)}&format=json&countrycodes=us&addressdetails=1&limit=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'BuiltEnvironmentInnovationHub/2.0'})
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            if data and len(data) > 0:
                item = data[0]
                lat, lon = float(item['lat']), float(item['lon'])
                address = item.get('address', {})
                
                state_name = address.get('state', '')
                st_code = STATE_NAME_TO_ABBR.get(state_name, None)
                
                if not st_code:
                    state_match = re.search(r'\b([A-Z]{2})\b', query_clean.upper())
                    st_code = state_match.group(1) if state_match and state_match.group(1) in STATE_ESG_PROFILES else "IA"
                
                city_name = address.get('city') or address.get('town') or address.get('village') or address.get('county') or query_clean.title()
                display_title = f"{city_name}, {st_code}"
                
                return {
                    "lat": lat,
                    "lon": lon,
                    "state": st_code,
                    "description": display_title
                }
    except Exception:
        pass

    state_match = re.search(r'\b([A-Z]{2})\b', query_clean.upper())
    st_code = state_match.group(1) if state_match and state_match.group(1) in STATE_ESG_PROFILES else "IA"
    return {"lat": 39.8283, "lon": -98.5795, "state": st_code, "description": query_clean.title()}

METRIC_WEIGHTS = {
    "Energy Feasibility": 0.30,
    "Water Impact": 0.25,
    "Community Impact": 0.20,
    "Climate Resilience": 0.15,
    "Grid Capacity": 0.10,
}

STATE_SCREENING_SCORES = {
    "IA": {"Energy": 8.8, "Water": 7.8, "Community": 7.2, "Climate": 6.8, "Grid": 7.5},
    "WY": {"Energy": 8.8, "Water": 7.2, "Community": 8.5, "Climate": 8.1, "Grid": 7.5},
    "VA": {"Energy": 6.0, "Water": 6.5, "Community": 5.0, "Climate": 6.8, "Grid": 2.5},
    "AZ": {"Energy": 7.5, "Water": 2.0, "Community": 6.0, "Climate": 4.0, "Grid": 6.5},
    "TX": {"Energy": 8.0, "Water": 4.5, "Community": 6.5, "Climate": 5.0, "Grid": 5.5},
}
DEFAULT_SCREENING_SCORES = {"Energy": 7.5, "Water": 7.0, "Community": 7.0, "Climate": 6.5, "Grid": 6.0}

def _state_scores(st_abbr):
    return STATE_SCREENING_SCORES.get(st_abbr, DEFAULT_SCREENING_SCORES)

def _score_label(score):
    if score >= 7.5:
        return "FAVORABLE"
    if score >= 5.0:
        return "CONDITIONAL"
    return "CONSTRAINT"

def build_map(sites_data=None, queued_sites=None):
    """Large tile-free analytical map: state hover intelligence + candidate markers."""
    m = folium.Map(
        location=[39.2, -97.5],
        zoom_start=4,
        tiles=None,
        zoom_control=False,
        control_scale=False,
        prefer_canvas=True,
        min_zoom=3,
        max_zoom=7,
    )

    # Near-black canvas means the state geometry itself becomes the visual interface.
    map_name = m.get_name()
    m.get_root().html.add_child(folium.Element(f"""
    <style>
      #{map_name} {{ background:#08090A !important; }}
      .leaflet-container {{ background:#08090A !important; font-family:Inter,Arial,sans-serif; }}
      .leaflet-tooltip.state-intel {{
        background:rgba(10,10,10,.96); color:#fff; border:1px solid rgba(255,255,255,.20);
        border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,.38); padding:12px 14px;
        font-size:12px; line-height:1.55; min-width:210px;
      }}
      .leaflet-tooltip.state-intel:before {{ display:none; }}
      .leaflet-popup-content-wrapper, .leaflet-popup-tip {{ background:#0B0B0B; color:#fff; }}
      .leaflet-control-attribution {{ background:rgba(8,9,10,.65)!important; color:#777!important; font-size:9px!important; }}
    </style>
    """))

    geojson_data = get_us_states_geojson()
    if geojson_data and geojson_data.get("features"):
        for feature in geojson_data["features"]:
            props = feature.setdefault("properties", {})
            state_name = props.get("name") or feature.get("id", "State")
            st_abbr = STATE_NAME_TO_ABBR.get(state_name, feature.get("id", state_name))
            profile = STATE_ESG_PROFILES.get(st_abbr, ("Pending", "#30343B", 0.10, "Screening profile pending."))
            scores = _state_scores(st_abbr)
            overall = (scores["Energy"]*.30 + scores["Water"]*.25 + scores["Community"]*.20 + scores["Climate"]*.15 + scores["Grid"]*.10)
            weakest = min(scores, key=scores.get)
            props.update({
                "abbr": st_abbr, "status_color": profile[1], "overall": f"{overall:.1f}",
                "energy": f"{scores['Energy']:.1f}", "water": f"{scores['Water']:.1f}",
                "community": f"{scores['Community']:.1f}", "climate": f"{scores['Climate']:.1f}",
                "grid": f"{scores['Grid']:.1f}", "constraint": weakest,
                "band": _score_label(overall),
            })

        def style_function(feature):
            color = feature["properties"].get("status_color", "#30343B")
            return {"fillColor": color, "color": "#6B7078", "weight": .75, "fillOpacity": .22}

        def highlight_function(feature):
            color = feature["properties"].get("status_color", "#FFFFFF")
            return {"fillColor": color, "color": "#FFFFFF", "weight": 1.7, "fillOpacity": .46}

        folium.GeoJson(
            geojson_data,
            style_function=style_function,
            highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "band", "overall", "energy", "water", "community", "climate", "grid", "constraint"],
                aliases=["STATE", "SCREENING", "Overall", "Energy", "Water", "Community", "Climate", "Grid", "Primary constraint"],
                sticky=True,
                labels=True,
                class_name="state-intel",
            ),
        ).add_to(m)

    targets = sites_data if sites_data else queued_sites
    if targets:
        for site in targets:
            st_abbr = site.get("state", "IA")
            score = site.get("overall_score")
            label = site.get("name", site.get("description", "Candidate"))
            band = _score_label(score) if score is not None else "QUEUED"
            marker_color = "#FFFFFF"
            popup = f"<div style='font-family:Inter,sans-serif;min-width:150px'><b>{label}</b><br><span style='color:#aaa'>{band}</span>"
            if score is not None:
                popup += f"<br><span style='font-size:20px;font-weight:700'>{score:.2f}</span><span style='color:#888'> / 10</span>"
            popup += "</div>"
            folium.CircleMarker(
                [site["lat"], site["lon"]], radius=11, color="rgba(255,255,255,.35)",
                weight=1, fill=True, fill_color=marker_color, fill_opacity=.13
            ).add_to(m)
            folium.CircleMarker(
                [site["lat"], site["lon"]], radius=4.5, color="#FFFFFF", weight=2,
                fill=True, fill_color="#FFFFFF", fill_opacity=1, popup=folium.Popup(popup, max_width=260),
                tooltip=f"{label} · {score:.2f}/10" if score is not None else f"{label} · queued"
            ).add_to(m)

    # HUD overlays make the map read like a product visualization rather than a generic basemap.
    candidate_count = len(targets) if targets else 0
    m.get_root().html.add_child(folium.Element(f"""
      <div style='position:absolute;z-index:999;top:22px;left:24px;color:white;pointer-events:none;'>
        <div style='font-size:10px;letter-spacing:.18em;color:#8E939B;'>01 — LOCATE</div>
        <div style='font-size:28px;font-weight:600;letter-spacing:-.03em;margin-top:3px;'>Site Intelligence Map</div>
        <div style='font-size:11px;color:#8E939B;margin-top:5px;'>Hover a state to inspect five-factor screening conditions.</div>
      </div>
      <div style='position:absolute;z-index:999;right:24px;bottom:22px;color:#9CA1A8;pointer-events:none;
                  background:rgba(8,9,10,.72);border:1px solid rgba(255,255,255,.10);border-radius:9px;padding:10px 13px;'>
        <span style='color:white;font-weight:600'>{candidate_count}</span> CANDIDATE{'S' if candidate_count != 1 else ''} IN PIPELINE
      </div>
    """))
    return m

def get_demo_results(queued_sites):
    """Calculates weighted 5-criteria ESG score matrix for all candidate sites in queue."""
    scored = []
    for site in queued_sites:
        st_abbr = site.get("state", "IA")
        profile = STATE_ESG_PROFILES.get(st_abbr, ("Favorable", "#10b981", 0.16, "Favorable state energy profile"))
        status_category = profile[0]
        
        base_scores = _state_scores(st_abbr)

        overall_score = (
            (base_scores["Energy"] * 0.30) +
            (base_scores["Water"] * 0.25) +
            (base_scores["Community"] * 0.20) +
            (base_scores["Climate"] * 0.15) +
            (base_scores["Grid"] * 0.10)
        )

        scored.append({
            "name": site["description"],
            "state": st_abbr,
            "lat": site["lat"],
            "lon": site["lon"],
            "status": status_category,
            "overall_score": overall_score,
            "state_desc": profile[3],
            "scores": {
                "Energy Feasibility": {"score": base_scores["Energy"]},
                "Water Impact": {"score": base_scores["Water"]},
                "Community Impact": {"score": base_scores["Community"]},
                "Climate Resilience": {"score": base_scores["Climate"]},
                "Grid Capacity": {"score": base_scores["Grid"]}
            },
            "top_asset": "Low-carbon grid & high renewable capacity" if overall_score > 7.0 else "Regional fiber proximity",
            "top_risk": "PJM Queue congestion" if st_abbr in ["VA", "MD", "NJ"] else "Water stress / Drought vulnerability" if base_scores["Water"] < 5.0 else "Severe weather events"
        })

    scored.sort(key=lambda x: x["overall_score"], reverse=True)
    for idx, item in enumerate(scored):
        item["rank"] = idx + 1

    return scored

# ── 3. STYLES ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap');
  
  html, body, [class*="css"], [data-testid="stAppViewContainer"] { 
    font-family: 'Inter', sans-serif; 
    color: #E2E8F0 !important;
    background-color: #08090A !important;
  }
  .stApp { 
    background-color: #08090A !important; 
  }
  #MainMenu, footer, header { visibility: hidden; }

  .portfolio-card {
    background: #12151A;
    border: 1px solid #22262E;
    border-radius: 6px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    transition: all 0.25s ease;
  }
  .portfolio-card:hover {
    border-color: #00F2FE;
    box-shadow: 0 0 18px rgba(0, 242, 254, 0.12);
    transform: translateY(-2px);
  }

  .tech-tag { 
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; 
    font-weight: 700; 
    letter-spacing: 0.12em; 
    text-transform: uppercase; 
    color: #00F2FE !important; 
  }

  .video-hero-container {
    position: relative;
    width: 100%;
    height: 220px;
    border-radius: 8px;
    overflow: hidden;
    margin-bottom: 1.5rem;
    border: 1px solid #22262E;
  }
  .bg-video {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .video-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, rgba(8,9,10,0.4) 0%, rgba(8,9,10,0.85) 100%);
  }
  .video-content {
    position: absolute;
    bottom: 1.5rem;
    left: 1.5rem;
    right: 1.5rem;
    z-index: 2;
  }

  /* Portfolio visual system */
  h1, h2, h3, h4, p, label, .stMarkdown { color: #FFFFFF; }
  h1 { font-weight: 500 !important; letter-spacing: -0.045em !important; }
  h2 { font-weight: 500 !important; letter-spacing: -0.035em !important; }
  h3 { font-weight: 500 !important; letter-spacing: -0.02em !important; }
  p { color: rgba(255,255,255,0.76) !important; line-height: 1.55; }
  .tech-tag { font-family: 'Inter', sans-serif; color: rgba(255,255,255,0.58) !important; font-weight: 500; letter-spacing: .10em; }
  div.stButton > button {
    background: transparent; color: #fff; border: 1px solid rgba(255,255,255,.22);
    border-radius: 999px; padding: .55rem 1rem; font-weight: 500;
  }
  div.stButton > button:hover { border-color: #fff; color: #fff; }
  .hero-copy { font-size: clamp(42px, 6vw, 88px); line-height: .98; letter-spacing: -.055em; font-weight: 500; color: #fff; max-width: 1100px; margin: 16px 0 18px; }
  .hero-sub { font-size: 16px; color: rgba(255,255,255,.64); margin-bottom: 22px; }
  .section-kicker { font-size: 12px; letter-spacing: .14em; text-transform: uppercase; color: rgba(255,255,255,.52); margin-top: 38px; }
</style>
""", unsafe_allow_html=True)

# ── 4. HELPER FUNCTIONS (WITH CACHED MEMORY READS) ───────────────────────────
@st.cache_data
def load_video_b64(file_path):
    """Safely reads & caches video to prevent memory overhead."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return None
    return None

@st.cache_data
def load_glb_b64(file_path):
    """Safely reads & caches a local GLB file for WebGL rendering."""
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return None
    return None

def status_badge(status_str):
    colors = {
        "Favorable": ("#10b981", "rgba(16, 185, 129, 0.15)"),
        "Conditional": ("#f59e0b", "rgba(245, 158, 11, 0.15)"),
        "High Risk": ("#ef4444", "rgba(239, 68, 68, 0.15)"),
        "Grid Congestion": ("#8b5cf6", "rgba(139, 92, 246, 0.15)")
    }
    fg, bg = colors.get(status_str, ("#00F2FE", "rgba(0, 242, 254, 0.15)"))
    return f'<span style="background:{bg}; color:{fg}; border:1px solid {fg}; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700;">{status_str.upper()}</span>'

def dim_row_html(name, score, weight):
    pct = score * 10
    return (
        f'<div style="margin-bottom:0.4rem; font-size:0.75rem;">'
        f'<div style="display:flex; justify-content:space-between; color:#A0AEC0; margin-bottom:2px;">'
        f'<span><b>{name}</b> ({int(weight*100)}%)</span>'
        f'<span><b>{score:.1f}</b>/10</span>'
        f'</div>'
        f'<div style="background:#22262E; height:5px; border-radius:3px; overflow:hidden;">'
        f'<div style="background:#00F2FE; width:{pct}%; height:100%;"></div>'
        f'</div></div>'
    )

@st.cache_data(ttl=3600)
def fetch_city_suggestions(query_str):
    """Fetches up to 10 matching US cities, towns, and municipalities from Nominatim."""
    if not query_str or len(query_str.strip()) < 3:
        return []
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        clean_q = query_str.strip()
        encoded_query = urllib.parse.quote(clean_q)
        url = f"https://nominatim.openstreetmap.org/search?q={encoded_query}&format=json&countrycodes=us&addressdetails=1&limit=10"
        req = urllib.request.Request(url, headers={'User-Agent': 'BuiltEnvironmentInnovationHub/2.0'})
        
        with urllib.request.urlopen(req, context=ctx, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            results = []
            for item in data:
                address = item.get('address', {})
                city_name = (
                    address.get('city') or 
                    address.get('town') or 
                    address.get('village') or 
                    address.get('hamlet') or
                    address.get('municipality') or 
                    address.get('county')
                )
                state_name = address.get('state', '')
                st_code = STATE_NAME_TO_ABBR.get(state_name, '')
                
                if not st_code and len(state_name) == 2:
                    st_code = state_name.upper()
                    
                if not st_code:
                    display_name = item.get('display_name', '')
                    for s_name, s_abbr in STATE_NAME_TO_ABBR.items():
                        if s_name in display_name:
                            st_code = s_abbr
                            break

                if city_name and st_code:
                    display_label = f"{city_name}, {st_code}"
                    if not any(r['description'] == display_label for r in results):
                        results.append({
                            "lat": float(item['lat']),
                            "lon": float(item['lon']),
                            "state": st_code,
                            "description": display_label
                        })
            return results
    except Exception:
        return []

def render_3d_hover_card(glb_b64, title, desc):
    if not glb_b64:
        st.error(f"⚠️ GLB model data missing for {title}")
        return

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/GLTFLoader.js"></script>
      <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/loaders/DRACOLoader.js"></script>
      <style>
        body {{ margin: 0; background: transparent; overflow: hidden; font-family: sans-serif; }}
        .model-card {{
          background: #12151A;
          border: 1px solid #22262E;
          border-radius: 6px;
          padding: 1.2rem;
          box-sizing: border-box;
        }}
        .model-card:hover {{
          border-color: #00F2FE;
          box-shadow: 0 0 20px rgba(0, 242, 254, 0.15);
        }}
        .viewport-container {{
          width: 100%;
          height: 290px;
          background: #161920;
          border-radius: 6px;
          border: 1px solid #2B3240;
          margin: 0.5rem 0;
          position: relative;
          cursor: grab;
        }}
        .viewport-container:active {{ cursor: grabbing; }}
        #three-canvas {{ width: 100%; height: 100%; display: block; }}
        #error-overlay {{
          position: absolute; inset: 0; color: #ef4444;
          font-family: monospace; font-size: 11px; padding: 10px;
          display: none; background: rgba(0,0,0,0.85); z-index: 10;
        }}
      </style>
    </head>
    <body>
      <div class="model-card">
        <span style="font-family: monospace; font-size: 11px; color: #00F2FE; letter-spacing: 0.12em; font-weight:700;">INTERACTIVE 3D CAD</span>
        <h3 style="color: #FFFFFF; margin: 0.3rem 0 0.5rem 0; font-size: 1.1rem;">{title}</h3>
        
        <div class="viewport-container" id="viewport">
          <div id="error-overlay"></div>
          <div id="three-canvas"></div>
        </div>
        
        <p style="color: #E2E8F0; opacity: 0.85; font-size: 0.85rem; line-height: 1.5; margin-top: 0.5rem;">{desc}</p>
      </div>

      <script>
        function showError(msg) {{
          const errDiv = document.getElementById('error-overlay');
          errDiv.style.display = 'block';
          errDiv.innerText = "3D Render Error: " + msg;
        }}

        try {{
          const viewport = document.getElementById('viewport');
          const container = document.getElementById('three-canvas');
          const width = container.clientWidth || 340;
          const height = container.clientHeight || 290;

          const scene = new THREE.Scene();
          scene.background = new THREE.Color(0x161920);
          const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 20000);
          
          const renderer = new THREE.WebGLRenderer({{ antialias: true, powerPreference: "high-performance" }});
          renderer.setSize(width, height);
          renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
          renderer.toneMapping = THREE.ACESFilmicToneMapping;
          renderer.toneMappingExposure = 1.0;
          container.appendChild(renderer.domElement);

          const controls = new THREE.OrbitControls(camera, renderer.domElement);
          controls.enableDamping = true;
          controls.dampingFactor = 0.05;

          const clock = new THREE.Clock();
          let targetSpeed = 0;
          let currentSpeed = 0;
          let isInteracting = false;
          const MAX_SPEED = 0.4;

          viewport.addEventListener('mouseenter', () => {{ if (!isInteracting) targetSpeed = MAX_SPEED; }});
          viewport.addEventListener('mouseleave', () => {{ targetSpeed = 0; isInteracting = false; }});
          viewport.addEventListener('pointerdown', () => {{ isInteracting = true; targetSpeed = 0; }});

          const ambientLight = new THREE.AmbientLight(0xffffff, 1.2);
          scene.add(ambientLight);

          const keyLight = new THREE.DirectionalLight(0xffffff, 1.4);
          keyLight.position.set(100, 200, 100);
          scene.add(keyLight);

          const fillLight = new THREE.DirectionalLight(0x00F2FE, 0.5);
          fillLight.position.set(-100, -50, -100);
          scene.add(fillLight);

          const dracoLoader = new THREE.DRACOLoader();
          dracoLoader.setDecoderPath('https://www.gstatic.com/draco/versioned/decoders/1.5.6/');

          const loader = new THREE.GLTFLoader();
          loader.setDRACOLoader(dracoLoader);

          const base64Str = "{glb_b64}";
          const binaryStr = atob(base64Str);
          const bytes = new Uint8Array(binaryStr.length);
          for (let i = 0; i < binaryStr.length; i++) {{
            bytes[i] = binaryStr.charCodeAt(i);
          }}

          loader.parse(bytes.buffer, '', function (gltf) {{
            const rawModel = gltf.scene;
            const pivotGroup = new THREE.Group();
            scene.add(pivotGroup);

            const lineMat = new THREE.LineBasicMaterial({{ color: 0x0F172A }});

            rawModel.traverse((child) => {{
              child.visible = true;
              child.frustumCulled = false;

              if (child.geometry) {{
                child.geometry.computeBoundingBox();
                child.geometry.computeBoundingSphere();
              }}

              if (child.isMesh && child.geometry) {{
                child.material = new THREE.MeshStandardMaterial({{
                  color: 0xECF0F1, roughness: 0.35, metalness: 0.05,
                  side: THREE.DoubleSide, transparent: false, opacity: 1.0,
                  depthWrite: true, depthTest: true, polygonOffset: true,
                  polygonOffsetFactor: 1, polygonOffsetUnits: 1
                }});

                const edges = new THREE.EdgesGeometry(child.geometry, 30);
                const wireframe = new THREE.LineSegments(edges, lineMat);
                wireframe.frustumCulled = false;
                child.add(wireframe);
              }} else if (child.isLine || child.isLineSegments) {{
                child.material = new THREE.LineBasicMaterial({{ color: 0xECF0F1 }});
              }}
            }});

            const rawBox = new THREE.Box3().setFromObject(rawModel);
            const center = rawBox.getCenter(new THREE.Vector3());
            const size = rawBox.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);

            rawModel.position.set(-center.x, -center.y, -center.z);
            pivotGroup.add(rawModel);

            camera.far = Math.max(20000, maxDim * 30);
            camera.position.set(maxDim * 0.85, maxDim * 0.65, maxDim * 0.95);
            camera.lookAt(0, 0, 0);
            camera.updateProjectionMatrix();

            controls.target.set(0, 0, 0);
            controls.update();

            function animate() {{
              requestAnimationFrame(animate);
              const delta = clock.getDelta();
              const easeFactor = 1 - Math.exp(-6 * delta);
              currentSpeed += (targetSpeed - currentSpeed) * easeFactor;
              
              if (!isInteracting && Math.abs(currentSpeed) > 0.0001) {{
                pivotGroup.rotation.y += currentSpeed * delta;
              }}

              controls.update();
              renderer.render(scene, camera);
            }}
            animate();

          }}, function(err) {{
            showError(err.message || err);
          }});

        }} catch(e) {{
          showError(e.message);
        }}
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=470)

# ── 5. SESSION STATE MANAGEMENT ───────────────────────────────────────────────
if "sites" not in st.session_state: st.session_state.sites = []
if "scored_data" not in st.session_state: st.session_state.scored_data = []
if "expanded_project" not in st.session_state: st.session_state.expanded_project = None
if "page" not in st.session_state: st.session_state.page = "home"


# ── 6. MAIN APPLICATION NAVIGATION ──────────────────────────────────────────
st.markdown('<div class="tech-tag">BUILT ENVIRONMENT ACADEMY & LAB</div>', unsafe_allow_html=True)
st.markdown('<h1 style="color:#FFFFFF; margin-top:0.2rem;">Spatial Design, Real Estate Markets, and Data Analytics</h1>', unsafe_allow_html=True)

tab_home, tab_arch, tab_datacenter, tab_forma, tab5 = st.tabs([
    "Home", 
    "Architecture Portfolio", 
    "Data Center Site Selection", 
    "Autodesk Forma Strategy", 
    "Bay Area Housing Market Research"
])

PROJECT_CARDS = [
    {
        "filename": "Long Term Care Project.glb",
        "title": "Project 01: A Framework for Care",
        "desc": "Exploring 'vertical neighborhood' aggregation for a sustainable and holistic assisted living facility."
    },
    {
        "filename": "airport model.glb",
        "title": "Project 02: SFO New Terminal Vision",
        "desc": "Envisioning the future of airport travel with a proposed centralized hub for transportation, commerce, and innovation."
    },
    {
        "filename": "project 03 model.glb",
        "title": "Project 03: The Carved Culinary Commons",
        "desc": "A community center that eliminates barriers of entry, bringing people together through the art and craft of cooking."
    }
]

def render_project_grid():
    st.subheader("Hover over each model to rotate")
    cols = st.columns(3)

    for idx, project in enumerate(PROJECT_CARDS):
        with cols[idx]:
            b64_data = load_glb_b64(project["filename"])
            if b64_data:
                render_3d_hover_card(b64_data, project["title"], project["desc"])
            else:
                st.warning(f"Place **'{project['filename']}'** in folder to activate 3D viewer.")
            if st.button("View Project →", key=f"home_project_{idx}", use_container_width=True):
                st.session_state.expanded_project = f"proj_0{idx+1}"
                st.info("Open the Architecture Portfolio tab to view the selected project.")

# ── TAB 1: HOME PAGE OVERVIEW ─────────────────────────────────────────────────
with tab_home:
    hero_html = r"""
    <div style="height:430px;position:relative;overflow:hidden;border-radius:12px;background:#050505;border:1px solid #181818;">
      <canvas id="heroNet" style="position:absolute;inset:0;width:100%;height:100%;"></canvas>
      <div style="position:absolute;left:42px;bottom:38px;right:42px;pointer-events:none;">
        <div style="font:500 11px Inter,sans-serif;letter-spacing:.16em;color:rgba(255,255,255,.55);">MICHAEL TAGUE · SELECTED WORK</div>
        <div style="font:500 clamp(42px,40vw,82px) Inter,sans-serif;letter-spacing:-.055em;line-height:.80;color:white;max-width:1200px;margin-top:10px;">BUILDING A BETTER UNDERSTANDING OF THE BUILT WORLD.</div>
        <div style="font:400 15px Inter,sans-serif;color:rgba(255,255,255,.62);margin-top:18px;">Architecture · Sustainability · Real Estate · Data Analysis</div>
      </div>
    </div>
    <script>
    (() => {
      const c=document.getElementById('heroNet'), x=c.getContext('2d'); let w,h,dpr,pts=[],mouse={x:-9999,y:-9999};
      function resize(){ dpr=Math.min(devicePixelRatio||1,2); w=c.clientWidth;h=c.clientHeight;c.width=w*dpr;c.height=h*dpr;x.setTransform(dpr,0,0,dpr,0,0); pts=[];
        const cols=15,rows=8; for(let j=0;j<rows;j++)for(let i=0;i<cols;i++)pts.push({bx:(i/(cols-1))*w,by:(j/(rows-1))*h*.72+10,phase:Math.random()*6.28});}
      c.addEventListener('mousemove',e=>{const r=c.getBoundingClientRect();mouse.x=e.clientX-r.left;mouse.y=e.clientY-r.top}); c.addEventListener('mouseleave',()=>mouse={x:-9999,y:-9999});
      function frame(t){x.clearRect(0,0,w,h); const time=t*.00045; const cols=15; let now=[];
        pts.forEach((p,k)=>{let px=p.bx,py=p.by+Math.sin(time*2+p.phase)*10+Math.sin(p.bx*.012+time)*14; let dx=px-mouse.x,dy=py-mouse.y,dist=Math.hypot(dx,dy); if(dist<150){let f=(150-dist)/150;px+=dx/(dist||1)*f*28;py+=dy/(dist||1)*f*28;} now[k]=[px,py];});
        x.lineWidth=.7; x.strokeStyle='rgba(255,255,255,.16)'; for(let k=0;k<now.length;k++){let i=k%cols,j=Math.floor(k/cols); if(i<cols-1){x.beginPath();x.moveTo(...now[k]);x.lineTo(...now[k+1]);x.stroke();} if(j<7){x.beginPath();x.moveTo(...now[k]);x.lineTo(...now[k+cols]);x.stroke();}}
        now.forEach((p,k)=>{let pulse=(Math.sin(time*4+k*.71)+1)/2;x.fillStyle=`rgba(255,255,255,${.22+pulse*.5})`;x.beginPath();x.arc(p[0],p[1],1+pulse*1.3,0,Math.PI*2);x.fill();}); requestAnimationFrame(frame);}
      new ResizeObserver(resize).observe(c); resize(); requestAnimationFrame(frame);
    })();
    </script>
    """
    components.html(hero_html, height=445, scrolling=False)

    st.markdown('<div class="section-kicker">Selected Architecture</div>', unsafe_allow_html=True)
    st.markdown('## Three projects. Three scales of intervention.')
    render_project_grid()

    st.markdown('<div class="section-kicker">Digital Tools</div>', unsafe_allow_html=True)
    st.markdown('## Built-environment intelligence, made interactive.')
    st.markdown("""
    <style>
    .home-tools-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:22px 0 38px}
    .home-tool-card{position:relative;min-height:265px;padding:27px 24px 22px;border-radius:14px;
      border:1px solid rgba(255,255,255,.12);background:linear-gradient(155deg,var(--tint),#101215 62%);
      overflow:hidden;transition:transform .22s ease,border-color .22s ease,box-shadow .22s ease}
    .home-tool-card:hover{transform:translateY(-4px);border-color:var(--accent);
      box-shadow:0 14px 42px rgba(0,0,0,.28)}
    .home-tool-card:after{content:"";position:absolute;right:-55px;top:-80px;width:190px;height:190px;
      background:radial-gradient(circle,var(--glow),transparent 70%);pointer-events:none}
    .home-tool-icon{width:49px;height:49px;border-radius:13px;display:flex;align-items:center;
      justify-content:center;background:var(--tint);border:1px solid var(--edge);color:var(--accent);margin-bottom:22px}
    .home-tool-icon svg{width:26px;height:26px;stroke:currentColor;stroke-width:1.65;fill:none;
      stroke-linecap:round;stroke-linejoin:round}
    .home-tool-eyebrow{font:500 10px Inter,sans-serif;letter-spacing:.16em;color:var(--accent);margin-bottom:10px}
    .home-tool-title{font:500 21px Inter,sans-serif;color:#fff;letter-spacing:-.035em;margin-bottom:10px}
    .home-tool-description{font:400 13px/1.65 Inter,sans-serif;color:rgba(255,255,255,.64);min-height:66px}
    .home-tool-footer{border-top:1px solid rgba(255,255,255,.10);margin-top:20px;padding-top:14px;
      font:500 11px Inter,sans-serif;color:var(--accent);letter-spacing:.025em}
    @media(max-width:900px){.home-tools-grid{grid-template-columns:1fr}.home-tool-card{min-height:auto}}
    </style>
    <div class="home-tools-grid">
      <div class="home-tool-card" style="--accent:#59CFC3;--tint:rgba(40,157,148,.12);--edge:rgba(89,207,195,.23);--glow:rgba(89,207,195,.14)">
        <div class="home-tool-icon"><svg viewBox="0 0 24 24"><path d="M3 10.5 12 3l9 7.5V21H3z"/><path d="M8 21v-7h8v7M3 10.5h18"/></svg></div>
        <div class="home-tool-eyebrow">01 / REAL ESTATE INTELLIGENCE</div>
        <div class="home-tool-title">Bay Area Market Explorer</div>
        <div class="home-tool-description">Explore local housing values, rental markets, demographics, and city-by-city comparisons through interactive maps and data.</div>
        <div class="home-tool-footer">Explore in Bay Area Market Intelligence ↗</div>
      </div>
      <div class="home-tool-card" style="--accent:#8AAAF6;--tint:rgba(93,128,220,.12);--edge:rgba(138,170,246,.23);--glow:rgba(138,170,246,.15)">
        <div class="home-tool-icon"><svg viewBox="0 0 24 24"><path d="M4 20V8l6-4 5 3v13M15 11l5-3v12M2 20h20M8 10v2m4-3v2m-4 4v2m4-3v2m6-4v2"/></svg></div>
        <div class="home-tool-eyebrow">02 / COMPUTATIONAL DESIGN</div>
        <div class="home-tool-title">Forma Resilience Engine</div>
        <div class="home-tool-description">Explore a generative design case study examining development geometry and resilience to wildfire, flood, and seismic risk.</div>
        <div class="home-tool-footer">Explore in Autodesk Forma Strategy ↗</div>
      </div>
      <div class="home-tool-card" style="--accent:#D6AA77;--tint:rgba(179,122,65,.11);--edge:rgba(214,170,119,.23);--glow:rgba(214,170,119,.14)">
        <div class="home-tool-icon"><svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="3"/><path d="M7 17v-5m5 5V7m5 10v-8M6 20h12"/></svg></div>
        <div class="home-tool-eyebrow">03 / INFRASTRUCTURE ANALYTICS</div>
        <div class="home-tool-title">Data Center Site Agent</div>
        <div class="home-tool-description">Screen U.S. locations across energy feasibility, water impact, community conditions, climate resilience, and grid capacity.</div>
        <div class="home-tool-footer">Explore in Data Center Diagnostics ↗</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ── TAB 2: ARCHITECTURE PORTFOLIO ─────────────────────────────────────────────
with tab_arch:
    PROJECTS = [
        {
            "id": "proj_01",
            "title": "Project 01: Thermodynamic Envelopes",
            "subtitle": "ACTIVE DESIGN STUDIO • RICHMOND, VA",
            "teaser": "Massing evaluation configuring intensive structural green roof networks and passive solar mitigation strategies across interconnected technical hubs.",
            "hero_img": "project1_render.png",
            "narrative": """Moving out of a home is a profound life transition, yet the current U.S. long-term care system often exacerbates this challenge through clinical, space-constrained environments. This project seeks to subvert these inadequacies by proposing an urban care facility that upholds human dignity and wellbeing. Located in Richmond, VA, the design functions as both a residence and a civic hotspot, prioritizing quality of life through light, nature, and social gathering.

The project operates directly adjacent to an existing retirement home that is devoid of green space and amenities, posing an opportunity to extend the program to create a seamless care block. By sharing resources between the new and existing structures, the site transforms into a holistic campus where residents from both facilities can access communal landscapes designed to foster physical and mental wellbeing.

The residential strategy is oriented around a “vertical neighborhood” aggregation, where units are organized into clusters that transition from the private sanctuary of the home to shared collective spaces on every floor. This strategy ensures that social interaction is an accessible and flexible opportunity, mitigating the isolation often found in traditional double-loaded corridor models.""",
            "metrics": [
                "Total Units: 48",
                "Total Square Footage: ~50,000",
                "Horizontal Vegetative Matrix: 64% total site cover",
                "Carbon Mitigation Coefficient: 2.4kg CO2e/m² per annum",
                "Targeted Daylight Autonomy Index: 78% average site depth"
            ],
            "section_perspective": None,
            "full_width_plan": None,
            "drawings_left": [
                {"title": "Initial Site Observations — Sun Diagramming", "file": "SUN DIAGRAM FINALIZED.png", "desc": "Sunlight patterns on the site guided the orientation of the form, intending to decrease reliance on artificial lighting."},
                {"title": "Selected Architectural Drawings — Primary Plans", "file": "site_plan_.png", "desc": "The architectural articulation defines clear structural rhythms utilizing timber-concrete hybrids."},
                {"title": "Plaza Level Interactive Render", "file": "Image10.jpg", "desc": "Pedestrian circulation channels leading into central communal courtyards."}
            ],
            "drawings_right": [
                {"title": "Axonometric Context Diagram", "file": "Axon Prompt 4.png", "desc": "Overall site integration showing connection pathways to adjacent urban infrastructure."},
                {"title": "Interior Atmospheric Render", "file": "Image13.jpg", "desc": "Natural daylit interior circulation spaces highlighting low-VOC material textures."},
                {"title": "Unit Structural Axonometric", "file": "Unit Axon Prompt 4.png", "desc": "Modular living cluster axonometric breakdown detailing service cores and dual-access balconies."}
            ],
            "long_section": "long section.png"
        },
        {
            "id": "proj_02",
            "title": "Project 02: SFO Terminal Vision",
            "subtitle": "INFRASTRUCTURE & MOBILITY STUDIO • SAN FRANCISCO, CA",
            "teaser": "A visionary proposal for a next-generation terminal at San Francisco International Airport, integrating passenger fluid dynamics with high-span sustainable roof structures.",
            "hero_img": "Image15.png",
            "narrative": """This project proposes a transformative vision for a new passenger terminal at San Francisco International Airport (SFO). Designed to streamline passenger movement in the age of AI, while creating a civic threshold to the Bay Area, the architecture balances structural expressiveness with high-performance environmental systems. The form shows appreciation for Northern California's abundant natural wonders. The wood-coated truss systems resemble the tranquil redwood forests, while the undulating roof shape draws inspiration from the flowing golden hills of the East Bay.

Key focus areas include mass transit connectivity, expansive daylit concourses, intuitive wayfinding, and integrated micro-climate zones that reduce overall terminal energy loads. The terminal serves not only as a hub for aviation travel, but also as a larger transportation, civic, and commercial system. The terminal includes a stop for the BART train system, as well as a ferry port, connecting users fluidly with locations across the Bay Area. A dedicated conference center and machine learning lab inspire innovation and commerce without the need to leave the terminal. Baggage claim, ticketing, and security are tucked below the main level, allowing for reduced stress-levels and a seamless design on the main conourse. AI smart security allows passengers to move quickly through security checks, with built-in bag sensors that can conduct thorough detection without the need for CT scanners. Users not intended to utilize the terminal's transportation sources are encouraged to enjoy the collection of retail and dining experiences.""",
            "metrics": [
                "Terminal Capacity: 18,000 passengers/hour",
                "Structural Clear Span: 120 meters timber-steel hybrid grid",
                "Daylight Autonomy: 84% in main departure hall",
                "Net-Zero Readiness: Integrated PV roof array & displacement ventilation"
            ],
            "section_perspective": {
                "title": "Transverse Section Perspective",
                "file": "airport section perspective.png",
                "desc": "Full building section perspective detailing double-height atrium volumes, roof daylight scoops, structural spans, and multi-level circulation."
            },
            "full_width_plan": {
                "title": "Master Terminal Floor Plan & Passenger Flow Matrix",
                "file": "floor plans.png",
                "desc": "Integrated master terminal level detailing ticketing; modernized AI-assisted security; employee and customer amenities prioritizing wellness and productivity; and multi-modal transit interfaces across the entire terminal footprint."
            },
            "drawings_left": [
                {"title": "01. Terminal Site Master Plan", "file": "Site Plan.jpg", "type": "image", "desc": "Overall airport layout detailing apron layout, runway setbacks, and transit links. The terminal's location provides the most efficient access to both sets of runways, allowing convenience for wide-body and single-body aircraft, as well as wind/weather impacts."},
                {"title": "02. 3D Solar Exposure Matrix", "file": "Sun analysis video.mp4", "type": "video", "desc": "360° solar radiation overlay mapped directly onto 3D terminal geometry. The overhang reduces sunlight glare from the sides, while the tinted glass roof allows a comfortable amount of overhead natural light."},
                {"title": "03. Main Level BART Train System", "file": "BART level.png", "type": "image", "desc": "Direct regional transit connectivity connecting airport passengers with locations across the Bay Area."},
                {"title": "04. Departure Roadway", "file": "departures.png", "type": "image", "desc": "Sectional profile highlighting displacement ventilation airflow and daylight scoops."},
                {"title": "05. Ground Level Ferry Port", "file": "ferry.png", "type": "image", "desc": "Sectional profile highlighting displacement ventilation airflow and daylight scoops."}
            ],
            "drawings_right": [
                {"title": "01. Departure Hall Exterior Perspective", "file": "roof system.png", "desc": "Approach view showing the sweeping roof canopy and curbside drop-off zone."},
                {"title": "02. Central Atrium & Security Hub", "file": "truss system.png", "desc": "Light-filled grand atrium with intuitive sightlines toward security control points."},
                {"title": "03. 3D Solar Energy Optimization Modeling", "file": "Solar energy analysis.mp4", "type": "video", "desc": "A model mapping surfaces where solar energy capture would be highest. Bright yellow coloring indicates most ideal location (where solar energy output = 170kWh/sq. ft. annually or more). In total, the terminal's roof system is able to generate approximately 150,000,000 kWh of solar energy per year. "},
                {"title": "04. Multi-Modal Transit Exchange", "file": "concourse.png", "desc": "South Concourse."},
                {"title": "05. Experiential Perspective", "file": "ground level.png", "desc": "Open double-height transition from security checkpoint to concourse."}
            ],
            "long_section": None
        },
        {
            "id": "proj_03",
            "title": "Project 03: The Carved Culinary Commons",
            "subtitle": "CIVIC & CULINARY HUB • PHILADELPHIA, PA",
            "teaser": "A carved monolithic timber-and-stone civic hub integrating urban culinary education, community gardens, and public market spaces.",
            "hero_img": "Image11.png",
            "narrative": """The Carved Culinary Commons responds to urban food desert conditions by creating an open, accessible civic infrastructure for culinary production, education, and community gathering. Utilizing subtractive carving methodologies, the massing creates daylight micro-courtyards that filter natural light deep into subterranean preparation kitchens and ground-level market halls.

The building functions as a living laboratory for urban agriculture. Integrated greywater filtering terraces wrap around the south-facing elevation, nourishing vertical hydroponic gardens that supply raw produce directly to the community teaching kitchens within.

By blurring the boundary between public plaza and civic interior, the architecture invites neighborhood participation across all levels, reclaiming food preparation as a shared public ritual.""",
            "metrics": [
                "Site Area: 32,500 sq ft",
                "Total Floor Area: ~62,000 sq ft",
                "Community Kitchen Capacity: 120 workshop stations",
                "Hydroponic Produce Yield: 4.2 tons / year",
                "Mass Timber Volume: 1,850 m³ cross-laminated timber"
            ],
            "massing_diagram": {
                "title": "Subtractive Massing & Volumetric Carving Evolution",
                "file": "ISOMETRIC DIAGRAM.jpg",
                "desc": "Sequential massing transformation showing subtractive carving strategies that open micro-courtyards for daylighting and ventilation."
            },
            "drawings_left": [
                {"title": "01. Urban Context Site Plan", "file": "site plan with ground floor.jpg", "desc": "Site plan highlighting pedestrian entry channels and seamless integration into Charlottesville's Downtown Mall."},
                {"title": "02. Street Plaza Exterior Render", "file": "Image10.png", "desc": "Approach view showing the street-level market hall designed to enagage adjacent pedestrian throughfares."},
                {"title": "03. Sunlit Courtyard Render", "file": "Image12.png", "desc": "Atmospheric render of the internal lightwell and outdoor dining terraces."}
            ],
            "drawings_right": [
                {"title": "01. Integrated Environmental & Structural System Axonometric", "file": "AXON PROJECT 3.png", "desc": "Exploded axonometric detailing programmatic use of each floor and attached external glass panels."}
            ],
            "full_width_plan": {
                "title": "Primary Floor Plans & Culinary Circulation Matrix",
                "file": "Project 3 Plans.jpg",
                "desc": "Floor plans - Floor 1: Market hall and food pantry; Floor 2: Office space; Floor 3: Cooking school; Floor 4: Chef living quarters and culinary library; Floor 5: Rooftop restaurant and event venue."
            },
            "section_perspective": {
                "title": "Longitudinal Transverse Section Perspective",
                "file": "Section Perspective.jpg",
                "desc": "Detailed section perspective showing double-height market space, and integrated classroom + library space, and angular design themes."
            }
        }
    ]

    # ── ARCHITECTURE PORTFOLIO RENDERING ──────────────────────────────
    active_proj = None
    if st.session_state.expanded_project:
        active_proj = next((p for p in PROJECTS if p["id"] == st.session_state.expanded_project), None)
        if active_proj is None:
            st.session_state.expanded_project = None

    if active_proj:
        # Project 03 uses a publication-style white presentation theme.
        # This override is active only while Project 03 is the selected architecture project.
        if active_proj["id"] == "proj_03":
            st.markdown("""
            <style>
              .stApp,
              [data-testid="stAppViewContainer"],
              [data-testid="stMain"],
              [data-testid="stMainBlockContainer"] {
                  background: #FFFFFF !important;
              }

              .stApp h1, .stApp h2, .stApp h3, .stApp h4,
              .stApp h5, .stApp h6 {
                  color: #111111 !important;
              }

              .stApp p, .stApp li, .stApp label,
              .stApp [data-testid="stCaptionContainer"],
              .stApp [data-testid="stMarkdownContainer"] {
                  color: #2A2A2A !important;
              }

              .stApp hr {
                  border-color: #DADADA !important;
              }

              .stApp [data-baseweb="tab-list"] {
                  background: #FFFFFF !important;
              }

              .stApp [data-baseweb="tab"] {
                  color: #555555 !important;
              }

              .stApp [data-baseweb="tab"][aria-selected="true"] {
                  color: #111111 !important;
              }

              .stApp .stButton > button {
                  background: #FFFFFF !important;
                  color: #111111 !important;
                  border: 1px solid #BDBDBD !important;
              }

              .stApp .stButton > button:hover {
                  border-color: #111111 !important;
              }
            </style>
            """, unsafe_allow_html=True)

        col_back, _ = st.columns([1, 4])
        with col_back:
            if st.button("← Return to Portfolio", key="btn_return_portfolio", use_container_width=True):
                st.session_state.expanded_project = None
                st.rerun()

        st.markdown(f"## {active_proj['title']}")
        st.markdown(f"**{active_proj['subtitle']}**")

        col_nar, col_met = st.columns([2, 1])
        with col_nar:
            st.markdown("### Design Statement")
            st.write(active_proj["narrative"])
        with col_met:
            st.markdown("### Project Metrics")
            for metric in active_proj["metrics"]:
                st.markdown(f"• {metric}")

        st.markdown("---")

        def render_feature(feature):
            if not feature:
                return
            st.markdown(f"### {feature['title']}")
            if os.path.exists(feature["file"]):
                if feature.get("type") == "video" or feature["file"].lower().endswith(('.mp4', '.mov', '.webm')):
                    st.video(feature["file"])
                else:
                    st.image(feature["file"], use_container_width=True)
            else:
                st.info(f"Media placeholder: `{feature['file']}`")
            st.caption(feature.get("desc", ""))

        def render_drawing_columns(project):
            col_l, col_r = st.columns(2)
            for col, key in [(col_l, "drawings_left"), (col_r, "drawings_right")]:
                with col:
                    for item in project.get(key, []):
                        st.markdown(f"#### {item['title']}")
                        if os.path.exists(item["file"]):
                            if item.get("type") == "video" or item["file"].lower().endswith(('.mp4', '.mov', '.webm')):
                                st.video(item["file"])
                            else:
                                st.image(item["file"], use_container_width=True)
                        else:
                            st.info(f"Media placeholder: `{item['file']}`")
                        st.caption(item["desc"])

        if active_proj["id"] == "proj_03":
            # Project 03 has its own editorial sequence:
            # massing → drawing gallery → plans → section perspective.
            render_feature(active_proj.get("massing_diagram"))
            render_drawing_columns(active_proj)
            render_feature(active_proj.get("full_width_plan"))
            render_feature(active_proj.get("section_perspective"))
        else:
            # Preserve the established sequence for Projects 01 and 02.
            render_feature(active_proj.get("section_perspective"))
            render_feature(active_proj.get("full_width_plan"))
            render_feature(active_proj.get("massing_diagram"))
            render_drawing_columns(active_proj)

        long_section = active_proj.get("long_section")
        if long_section:
            st.markdown("### Longitudinal Section")
            if os.path.exists(long_section):
                st.image(long_section, use_container_width=True)
            else:
                st.info(f"Image placeholder: `{long_section}`")
    else:
        st.markdown("## Architectural Works")
        st.markdown("<p style='color:rgba(255,255,255,.62); margin-top:-.5rem; margin-bottom:2rem;'>Selected architectural investigations across housing, aviation, and civic space.</p>", unsafe_allow_html=True)
        card_cols = st.columns(2)
        for idx, proj in enumerate(PROJECTS):
            with card_cols[idx % 2]:
                if os.path.exists(proj["hero_img"]):
                    st.image(proj["hero_img"], use_container_width=True)
                else:
                    st.markdown("<div style='height:220px;background:#111;border:1px solid #242424;border-radius:4px;display:flex;align-items:center;justify-content:center;color:#777;'>Preview image</div>", unsafe_allow_html=True)
                st.markdown(f"### {proj['title']}")
                st.caption(proj["subtitle"])
                st.write(proj["teaser"])
                if st.button("View Project →", key=f"btn_{proj['id']}", use_container_width=True):
                    st.session_state.expanded_project = proj["id"]
                    st.rerun()

# ── ZERO-COST DEMO AGENT ─────────────────────────────────────────────────────
def generate_demo_agent_brief(site):
    """Create a deterministic, portfolio-safe site brief with no LLM/API call."""
    scores = {k: float(v["score"]) for k, v in site["scores"].items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    strongest_name, strongest_score = ranked[0]
    second_name, second_score = ranked[1]
    weakest_name, weakest_score = ranked[-1]
    overall = float(site["overall_score"])

    if overall >= 7.5:
        posture = "strong candidate for continued diligence"
        next_step = "advance to utility, land-control, and entitlement validation"
    elif overall >= 6.25:
        posture = "conditional candidate that merits targeted diligence"
        next_step = f"resolve {weakest_name.lower()} constraints before committing significant development capital"
    else:
        posture = "higher-constraint candidate under this screening framework"
        next_step = f"treat {weakest_name.lower()} as a gating issue before advancing"

    risk_note = {
        "Grid Capacity": "Interconnection timing and deliverable power should be validated directly with the serving utility; queue position can materially change project schedule.",
        "Water Impact": "Cooling strategy and water availability should be tested early, including dry- or hybrid-cooling alternatives where appropriate.",
        "Community Impact": "Land-use compatibility, community benefits, noise, traffic, and local entitlement conditions should be evaluated before site control.",
        "Climate Resilience": "Hazard exposure should be translated into design standards, insurance assumptions, redundancy requirements, and lifecycle cost.",
        "Energy Feasibility": "Power price, carbon intensity, renewable procurement options, and substation proximity should be validated at parcel scale."
    }.get(weakest_name, "The lowest-scoring dimension should be validated with parcel-level diligence before advancing.")

    return {
        "headline": f"{site['name']} is a {posture}.",
        "summary": (
            f"The screening model assigns an overall suitability score of {overall:.2f}/10. "
            f"Its strongest dimensions are {strongest_name} ({strongest_score:.1f}/10) and "
            f"{second_name} ({second_score:.1f}/10), while {weakest_name} ({weakest_score:.1f}/10) "
            f"is the principal constraint."
        ),
        "risk": risk_note,
        "next_step": next_step.capitalize() + ".",
        "basis": "Deterministic demo output generated from the portfolio's five-factor scoring model; no external AI model or paid API is used."
    }

# ── TAB 3: DATA CENTER SITE SELECTION & DIAGNOSTICS ──────────────────────────
with tab_datacenter:
    st.markdown("### Spatial Data Center Analytics Platform")
    st.caption("Screen candidate markets through energy, water, community, climate, and grid constraints.")

    # Compact command bar; the analytical map is the visual centerpiece below it.
    search_col, select_col = st.columns([1.15, 1])
    with search_col:
        city_query = st.text_input(
            "Search Any US City, Town, or Township",
            placeholder="e.g., Richmond, Cheyenne, Phoenix...",
            key="city_search_input"
        )

    selected_location = None
    clean_q = city_query.strip()
    with select_col:
        if len(clean_q) >= 3:
            suggestions = fetch_city_suggestions(clean_q)
            if suggestions:
                options_map = {item["description"]: item for item in suggestions}
                chosen_label = st.selectbox("Select matching location", list(options_map.keys()), key="city_results_select")
                selected_location = options_map[chosen_label]
        else:
            st.selectbox("Select matching location", ["Enter 3+ letters to search"], disabled=True)

    col_btn_add, col_btn_run, col_btn_clear, pipeline_info = st.columns([1, 1.15, .7, 2.15])
    with col_btn_add:
        if st.button("+ Queue Location", use_container_width=True, type="primary"):
            target_site = selected_location or geocode_location(clean_q)
            if target_site:
                if not any(s["description"].lower() == target_site["description"].lower() for s in st.session_state.sites):
                    st.session_state.sites.append(target_site)
                    st.rerun()
    with col_btn_run:
        if st.button("Analyze Pipeline", use_container_width=True):
            if st.session_state.sites:
                st.session_state.scored_data = get_demo_results(st.session_state.sites)
                st.rerun()
    with col_btn_clear:
        if st.button("Reset", use_container_width=True):
            st.session_state.sites = []
            st.session_state.scored_data = []
            st.rerun()
    with pipeline_info:
        status_text = f"{len(st.session_state.sites)} candidate(s) queued"
        if st.session_state.scored_data:
            status_text = f"{len(st.session_state.scored_data)} candidate(s) analyzed · hover states for screening intelligence"
        st.caption(status_text)

    map_obj = build_map(
        sites_data=st.session_state.scored_data if st.session_state.scored_data else None,
        queued_sites=st.session_state.sites if not st.session_state.scored_data else None
    )
    st_folium(
        map_obj,
        width=None,
        height=690,
        key="dc_map_engine",
        returned_objects=[],
        use_container_width=True,
    )

    st.markdown(
        "<div style='display:flex;gap:22px;margin:-6px 0 18px 2px;font-size:10px;letter-spacing:.10em;color:#8B8B8B;'>"
        "<span>01 LOCATE</span><span>→</span><span>02 DIAGNOSE</span><span>→</span><span>03 COMPARE</span><span>→</span><span>04 ADVISE</span></div>",
        unsafe_allow_html=True
    )

    if st.session_state.scored_data:
        st.markdown("---")
        st.markdown("### Candidate Site ESG Scorecards")
        st.caption("Five-factor screening model · click any metric to inspect the development implication.")

        METRIC_NOTES = {
            "Energy Feasibility": {
                "high": "Strong energy-market fundamentals support data-center operations and long-term power procurement.",
                "mid": "Power-market conditions are workable, but pricing, generation mix, and utility capacity require diligence.",
                "low": "Energy availability or cost presents a material development constraint that should be resolved early.",
                "action": "Validate utility service, tariff structure, power price exposure, and renewable procurement options."
            },
            "Water Impact": {
                "high": "Water availability and regional conditions are comparatively supportive of cooling demand.",
                "mid": "Water conditions are manageable, but cooling strategy and local resource pressure should be tested.",
                "low": "Water scarcity materially increases operational and community risk for water-intensive cooling systems.",
                "action": "Test dry/closed-loop cooling, watershed stress, withdrawal limits, and local water pricing."
            },
            "Community Impact": {
                "high": "The screening model indicates comparatively favorable community-development conditions.",
                "mid": "Community impacts are mixed and warrant targeted stakeholder and land-use diligence.",
                "low": "Community burden or development friction may create entitlement, infrastructure, or reputational risk.",
                "action": "Review land use, tax structure, workforce effects, environmental justice indicators, and stakeholder concerns."
            },
            "Climate Resilience": {
                "high": "The location has a comparatively resilient physical-risk profile under this screening framework.",
                "mid": "Climate exposure is manageable but should be incorporated into site design and insurance assumptions.",
                "low": "Physical climate hazards could materially affect uptime, insurance, cooling loads, or capital expenditure.",
                "action": "Stress-test heat, flood, wildfire, storm, and insurance exposure before detailed site selection."
            },
            "Grid Capacity": {
                "high": "Grid conditions are comparatively favorable for large-load interconnection and project delivery.",
                "mid": "Grid access is plausible, but queue position and deliverable capacity remain important schedule variables.",
                "low": "Interconnection constraints represent a gating risk to project schedule and achievable load delivery.",
                "action": "Confirm deliverable MW, substation capacity, network upgrades, queue timing, and energization schedule with the utility."
            },
        }

        def score_band(score):
            if score >= 7.5:
                return "FAVORABLE", "high"
            if score >= 5.0:
                return "CONDITIONAL", "mid"
            return "CONSTRAINT", "low"

        def scorecard(site):
            ordered = list(METRIC_WEIGHTS.keys())
            strongest = max(ordered, key=lambda m: site["scores"][m]["score"])
            weakest = min(ordered, key=lambda m: site["scores"][m]["score"])
            overall_label, _ = score_band(site["overall_score"])

            st.markdown(
                f"""
                <div style="border:1px solid #2A2A2A;border-radius:12px;padding:20px 22px 14px 22px;background:#0E0E0E;margin-bottom:12px;">
                  <div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;">
                    <div>
                      <div style="font-size:11px;letter-spacing:.12em;color:#8B8B8B;">RANK #{site['rank']} · {site['state']}</div>
                      <div style="font-size:24px;font-weight:650;color:white;margin-top:3px;">{site['name']}</div>
                    </div>
                    <div style="text-align:right;">
                      <div style="font-size:11px;letter-spacing:.10em;color:#8B8B8B;">OVERALL SUITABILITY</div>
                      <div style="font-size:30px;font-weight:700;color:white;line-height:1.05;">{site['overall_score']:.2f}<span style="font-size:14px;color:#8B8B8B;"> / 10</span></div>
                      <div style="font-size:10px;letter-spacing:.12em;color:#BDBDBD;margin-top:4px;">{overall_label}</div>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True
            )
            st.progress(min(max(site["overall_score"] / 10.0, 0.0), 1.0))

            for metric in ordered:
                score = site["scores"][metric]["score"]
                weight = METRIC_WEIGHTS[metric]
                label, band = score_band(score)
                icon = {
                    "Energy Feasibility": "⚡",
                    "Water Impact": "◌",
                    "Community Impact": "◎",
                    "Climate Resilience": "△",
                    "Grid Capacity": "⌁",
                }[metric]

                with st.expander(f"{icon}  {metric}  ·  {score:.1f}/10  ·  {int(weight*100)}% weight  ·  {label}"):
                    st.progress(min(max(score / 10.0, 0.0), 1.0))
                    note = METRIC_NOTES[metric][band]
                    st.markdown("**Screening interpretation**")
                    st.write(note)
                    st.markdown("**Development diligence**")
                    st.write(METRIC_NOTES[metric]["action"])
                    contribution = score * weight
                    st.caption(f"Weighted contribution to overall score: {contribution:.2f} points")

            a, b = st.columns(2)
            with a:
                st.markdown("**TOP ASSET**")
                st.markdown(f"### {strongest}")
                st.caption(f"{site['scores'][strongest]['score']:.1f}/10")
            with b:
                st.markdown("**PRIMARY CONSTRAINT**")
                st.markdown(f"### {weakest}")
                st.caption(f"{site['scores'][weakest]['score']:.1f}/10")

        # One full-width scorecard per candidate keeps the five dimensions readable.
        for site in st.session_state.scored_data:
            scorecard(site)
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        # Side-by-side comparison becomes useful as soon as 2+ candidates are analyzed.
        if len(st.session_state.scored_data) > 1:
            st.markdown("### Cross-Site Comparison")
            comparison_rows = []
            for metric, weight in METRIC_WEIGHTS.items():
                row = {"Metric": f"{metric} ({int(weight*100)}%)"}
                for site in st.session_state.scored_data:
                    row[site["name"]] = site["scores"][metric]["score"]
                comparison_rows.append(row)
            overall_row = {"Metric": "OVERALL"}
            for site in st.session_state.scored_data:
                overall_row[site["name"]] = round(site["overall_score"], 2)
            comparison_rows.append(overall_row)
            comparison_df = pd.DataFrame(comparison_rows).set_index("Metric")
            def score_cell_style(value):
                try:
                    score = float(value)
                except (TypeError, ValueError):
                    return ""
                if score >= 7.5:
                    return "background-color: rgba(34,197,94,.18); color:#86efac; font-weight:600;"
                elif score >= 5.0:
                    return "background-color: rgba(245,158,11,.18); color:#fcd34d; font-weight:600;"
                return "background-color: rgba(239,68,68,.18); color:#fca5a5; font-weight:600;"

            styled_comparison = comparison_df.style.format("{:.1f}").map(score_cell_style)
            st.dataframe(styled_comparison, use_container_width=True)
            st.caption("Higher scores indicate more favorable screening conditions. Weights are shown beside each metric.")

        st.markdown("---")
        st.markdown("### Demo Agent Briefs")
        st.caption("Zero-cost deterministic analysis — no Anthropic/OpenAI key, tokens, or paid model calls.")

        for site in st.session_state.scored_data:
            brief = generate_demo_agent_brief(site)
            with st.expander(f"{site['name']} · Site Intelligence Brief", expanded=(site['rank'] == 1)):
                st.markdown(f"#### {brief['headline']}")
                st.write(brief["summary"])
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Primary diligence issue**")
                    st.write(brief["risk"])
                with c2:
                    st.markdown("**Recommended next step**")
                    st.write(brief["next_step"])
                st.caption(brief["basis"])

# ── TAB 4: AUTODESK FORMA SUSTAINABILITY ADVISING ─────────────
with tab_forma:
    st.markdown("## Autodesk Forma Spatial Integration & Environmental Strategy")
    st.markdown(
        "**3233 Deer Hill Road, Lafayette, CA** — "
        "Wildfire, Seismic Slope, and Flood Vulnerability Analysis."
    )

    forma_url = os.getenv(
        "FORMA_EXTENSION_URL",
        "http://localhost:5175"
    )

    st.info("Interactive Forma sandbox connected locally.")

    components.iframe(
        forma_url,
        height=850,
        scrolling=False
    )

# ── TAB 5: BAY AREA MARKET INTELLIGENCE ───────────────────────────────────────
with tab5:
    from pathlib import Path

    st.markdown("""
    <div style="padding:2.5rem 0 1.25rem 0;">
      <div class="tech-tag">MARKET RESEARCH / BAY AREA</div>
      <h1 style="margin:.35rem 0 .7rem 0;">Bay Area Market Intelligence</h1>
      <p style="max-width:820px;font-size:1.05rem;">
        A multi-source real estate research pipeline translating city-level housing and demographic data,
        regional employment conditions, and macro capital-market indicators into comparative market intelligence.
      </p>
    </div>
    """, unsafe_allow_html=True)

    # Restrained teal, blue, and amber accents, scoped to the market tab only.
    st.markdown("""<style>
    [data-testid="stTabsContent"] [data-testid="stTabPanel"]:nth-child(5) h2,
    [data-testid="stTabsContent"] [data-testid="stTabPanel"]:nth-child(5) h3 {color:#DCEFF1!important;}
    [data-testid="stTabsContent"] [data-testid="stTabPanel"]:nth-child(5) [data-testid="stMetricValue"] {color:#77D7CD!important;}
    </style>""", unsafe_allow_html=True)

    # Palette used only by Tab 5 components, preserving the other tabs.
    MARKET_ACCENTS = ["#55CFC2", "#79A8F8", "#D5A86B", "#B49AE7"]

    MARKET_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

    @st.cache_data(show_spinner=False)
    def load_market_cache(data_dir_str):
        data_dir = Path(data_dir_str)
        markets = {}
        errors = []
        if not data_dir.exists():
            return markets, [f"Market data folder not found: {data_dir}"]

        for file_path in sorted(data_dir.glob("*.json")):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                city = data.get("city") or file_path.stem.replace("_", " ").title()
                markets[city] = data
            except Exception as exc:
                errors.append(f"{file_path.name}: {exc}")
        return markets, errors

    def _num(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        try:
            cleaned = str(value).replace("$", "").replace(",", "").replace("%", "").strip()
            return float(cleaned)
        except (TypeError, ValueError):
            return None

    def _fmt_money(value, compact=False):
        value = _num(value)
        if value is None:
            return "N/A"
        if compact and abs(value) >= 1_000_000:
            return f"${value/1_000_000:.2f}M"
        if compact and abs(value) >= 1_000:
            return f"${value/1_000:.0f}K"
        return f"${value:,.0f}"

    def _fmt_number(value, compact=False):
        value = _num(value)
        if value is None:
            return "N/A"
        if compact and abs(value) >= 1_000_000:
            return f"{value/1_000_000:.2f}M"
        if compact and abs(value) >= 1_000:
            return f"{value/1_000:.1f}K"
        return f"{value:,.0f}"

    def _fmt_pct(value, signed=False):
        value = _num(value)
        if value is None:
            return "N/A"
        return f"{value:+.1f}%" if signed else f"{value:.1f}%"

    def _metric(metrics, *keys):
        for key in keys:
            if metrics.get(key) is not None:
                return metrics.get(key)
        return None

    markets, market_load_errors = load_market_cache(str(MARKET_DATA_DIR))

    if not markets:
        st.error("No cached Bay Area market files were found.")
        st.code("portfolio/\n├── dashboard.py\n└── market_data/\n    ├── walnut_creek.json\n    ├── oakland.json\n    └── ...", language="text")
        if market_load_errors:
            with st.expander("Cache loading details"):
                for err in market_load_errors:
                    st.caption(err)
        st.stop()

    market_names = sorted(markets.keys())
    pending_market = st.session_state.pop("bay_area_pending_market", None)
    if pending_market in markets:
        st.session_state["bay_area_market_selector"] = pending_market
    default_index = market_names.index("Walnut Creek") if "Walnut Creek" in market_names else 0

    top_left, top_right = st.columns([1.2, 2.8])
    with top_left:
        st.markdown('<div class="tech-tag">SELECT MARKET</div>', unsafe_allow_html=True)
        selected_market = st.selectbox(
            "Market",
            market_names,
            index=default_index,
            label_visibility="collapsed",
            key="bay_area_market_selector"
        )
        st.caption(f"{len(market_names)} cached Bay Area markets available · no live API calls")

    market = markets[selected_market]
    metrics = market.get("portfolio_metrics", {})
    census = market.get("SHEET_1_DEMOGRAPHICS", {}).get("census_data", {})
    employment = market.get("SHEET_1_DEMOGRAPHICS", {}).get("employment_data", {})
    financials = market.get("SHEET_3_FINANCIALS", {})
    housing = market.get("SHEET_4_GEOGRAPHIC_STRUCTURAL", {}).get("census_housing_composition", {})
    fred = financials.get("fred_macro_indicators", {})

    county = market.get("county", "Bay Area")
    generated_raw = market.get("report_generated", "")
    generated = generated_raw[:10] if generated_raw else "Cached research"

    with top_right:
        st.markdown(f"""
        <div style="border:1px solid rgba(85,207,194,.30);border-left:3px solid #55CFC2;border-radius:10px;padding:1.25rem 1.5rem;background:linear-gradient(115deg,rgba(24,76,78,.24),rgba(18,25,36,.32) 70%,rgba(8,9,10,.15));">
          <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-end;">
            <div>
              <div class="tech-tag">ACTIVE MARKET</div>
              <div style="font-size:2rem;font-weight:500;letter-spacing:-.04em;margin-top:.2rem;color:#D8F8F2;">{selected_market}, CA</div>
              <div style="color:rgba(255,255,255,.55);">{county} County</div>
            </div>
            <div style="text-align:right;">
              <div class="tech-tag">CACHED MARKET RESEARCH</div>
              <div style="color:rgba(255,255,255,.55);margin-top:.3rem;">Updated {generated}</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Support both the corrected city-level names and earlier cache-key names.
    home_value = _metric(metrics, "zillow_home_value_index", "home_value")
    home_yoy = _metric(metrics, "home_value_yoy_pct")
    rent_index = _metric(metrics, "zillow_observed_rent_index", "zori_rent_index", "rent_index")
    rent_yoy = _metric(metrics, "rent_yoy_pct")
    city_population = _metric(metrics, "city_population", "county_population")
    city_income = _metric(metrics, "city_median_household_income", "county_median_household_income")

    st.markdown("### Market Snapshot")
    snapshot = [
        (_fmt_money(home_value, compact=True), "ZILLOW HOME VALUE", f"{_fmt_pct(home_yoy, signed=True)} YoY" if home_yoy is not None else "City-level ZHVI"),
        (_fmt_money(rent_index), "ZILLOW RENT INDEX", f"{_fmt_pct(rent_yoy, signed=True)} YoY" if rent_yoy is not None else "City-level ZORI"),
        (_fmt_number(city_population, compact=True), "CITY POPULATION", census.get("data_year", "ACS city/place")),
        (_fmt_money(city_income, compact=True), "MEDIAN HH INCOME", "City-level ACS"),
    ]
    kcols = st.columns(4)
    for idx, (col, (value, label, note)) in enumerate(zip(kcols, snapshot)):
        accent = MARKET_ACCENTS[idx]
        with col:
            st.markdown(f"""
            <div style="min-height:145px;border:1px solid {accent}44;border-top:3px solid {accent};border-radius:9px;padding:1rem;background:linear-gradient(160deg,{accent}15,rgba(255,255,255,.012) 80%);">
              <div style="font-size:2.15rem;font-weight:500;letter-spacing:-.045em;color:{accent};">{value}</div>
              <div style="font-size:.69rem;letter-spacing:.12em;font-weight:650;margin-top:.55rem;color:{accent};">{label}</div>
              <div style="font-size:.84rem;color:rgba(255,255,255,.58);margin-top:.55rem;">{note}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Four-Pillar Market Screen")

    job_growth = _metric(metrics, "metro_job_growth_pct") or employment.get("yoy_job_growth_pct")
    jobs_added = _metric(metrics, "metro_jobs_added") or employment.get("yoy_jobs_added")
    sfr_share = _metric(metrics, "sfr_detached_share_pct")
    mf_share = _metric(metrics, "multifamily_5plus_share_pct")
    owner_share = _metric(metrics, "owner_occupied_share_pct")
    renter_share = _metric(metrics, "renter_occupied_share_pct")
    mortgage = _metric(metrics, "mortgage_rate_30yr_pct")
    housing_units = housing.get("total_housing_units", "N/A")

    pillars = [
        ("01 — DEMAND DRIVERS", "City fundamentals + regional employment",
         f"{_fmt_money(city_income, compact=True)} median HH income",
         f"{_fmt_number(city_population, compact=True)} city population. Regional employment growth is {_fmt_pct(job_growth, signed=True)} with {_fmt_number(jobs_added)} jobs added year over year."),
        ("02 — HOUSING MARKET", "Current pricing and rent trajectory",
         f"{_fmt_money(home_value, compact=True)} ZHVI · {_fmt_money(rent_index)} ZORI",
         f"City-level Zillow research shows home values changing {_fmt_pct(home_yoy, signed=True)} year over year and observed rents changing {_fmt_pct(rent_yoy, signed=True)}."),
        ("03 — MARKET STRUCTURE", "Housing composition and tenure",
         f"{_fmt_pct(sfr_share)} detached SFR · {_fmt_pct(mf_share)} 5+ unit MF",
         f"The city contains {housing_units} housing units. {_fmt_pct(owner_share)} of occupied units are owner-occupied and {_fmt_pct(renter_share)} are renter-occupied."),
        ("04 — CAPITAL MARKETS", "U.S. macro context",
         f"{_fmt_pct(mortgage)} 30-year mortgage rate",
         "FRED indicators provide national capital-market context rather than city-specific fundamentals. Use them to frame financing conditions around the local housing-market signals above."),
    ]

    pcols = st.columns(2)
    for i, (title, headline, metric_text, body) in enumerate(pillars):
        accent = MARKET_ACCENTS[i]
        with pcols[i % 2]:
            st.markdown(f"""
            <div style="border:1px solid {accent}40;border-left:3px solid {accent};border-radius:9px;padding:1.35rem 1.4rem;margin-bottom:1rem;min-height:225px;background:linear-gradient(125deg,{accent}10,rgba(255,255,255,.012) 72%);">
              <div style="font-size:.70rem;font-weight:650;letter-spacing:.12em;color:{accent};">{title}</div>
              <div style="font-size:1.35rem;font-weight:500;letter-spacing:-.025em;margin:.7rem 0 .35rem 0;">{headline}</div>
              <div style="font-size:1.05rem;margin-bottom:.8rem;color:{accent};">{metric_text}</div>
              <div style="color:rgba(255,255,255,.62);line-height:1.55;">{body}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("### Research Detail")
    detail_a, detail_b, detail_c = st.columns(3)
    with detail_a:
        st.markdown('<div class="tech-tag">CITY / PLACE</div>', unsafe_allow_html=True)
        st.markdown(f"**{census.get('geography', selected_market + ', California')}**")
        st.caption(f"Population · income · housing composition · tenure | {census.get('data_year', 'ACS')}")
    with detail_b:
        st.markdown('<div class="tech-tag">REGIONAL ECONOMY</div>', unsafe_allow_html=True)
        st.markdown(f"**{employment.get('total_nonfarm_payroll', 'N/A')} nonfarm payroll**")
        st.caption(f"{employment.get('period', 'BLS regional context')} · {_fmt_pct(job_growth, signed=True)} YoY")
    with detail_c:
        st.markdown('<div class="tech-tag">MACRO / CAPITAL</div>', unsafe_allow_html=True)
        st.markdown(f"**{_fmt_pct(mortgage)} 30Y mortgage**")
        st.caption(f"FRED · {metrics.get('mortgage_rate_as_of', fred.get('mortgage_rate_30yr', {}).get('date', 'latest cached'))}")

    st.markdown("---")
    with st.expander("Methodology + data quality"):
        st.markdown(f"""
        **Research pipeline.** City-level Census ACS demographics and housing composition are combined with
        city-level Zillow ZHVI/ZORI, regional BLS employment conditions, and FRED macroeconomic indicators.

        **Geographic discipline.** Census and Zillow figures shown as local fundamentals are city/place-level.
        BLS employment is regional context, while FRED indicators are broader macro context; the interface does
        not present those broader indicators as city-specific measurements.

        **Portfolio deployment.** This page reads precomputed JSON files from `market_data/`. Visitors do not
        trigger paid AI calls or authenticated research APIs.

        **Cache note.** {market.get('data_quality', 'Source availability varies by market. Missing values are displayed as N/A rather than estimated.')}
        """)

        health = market.get("source_health", {})
        if health:
            st.caption("SOURCE HEALTH · " + " · ".join(f"{k.replace('_',' ').upper()}: {v.upper()}" for k, v in health.items()))

        if market_load_errors:
            st.caption(f"{len(market_load_errors)} cache file(s) could not be loaded. See details below.")
            for err in market_load_errors:
                st.caption(err)
    st.divider()
    st.subheader("Bay Area Market Explorer")
    st.caption("Explore city-level Zillow and Census indicators. Select a marker to update the market profile above.")
    st.markdown('<div style="height:3px;width:100%;border-radius:5px;background:linear-gradient(90deg,#376C94,#55CFC2,#B49AE7);opacity:.65;margin:.35rem 0 1.15rem;"></div>', unsafe_allow_html=True)

    map_options = {
        "Home Value": ("zillow_home_value_index", "home_value"),
        "Monthly Rent": ("zillow_observed_rent_index", "zori_rent_index", "rent_index"),
        "Population": ("city_population", "county_population"),
        "Median Household Income": ("city_median_household_income", "county_median_household_income"),
        "Home Value Growth YoY": ("home_value_yoy_pct",),
        "Rent Growth YoY": ("rent_yoy_pct",),
    }
    map_metric = st.selectbox("Visualize a market indicator", list(map_options), key="bay_area_map_metric")
    city_coordinates = {
    # Alameda County
    "Alameda": [37.7652, -122.2416],
    "Berkeley": [37.8715, -122.2730],
    "Castro Valley": [37.6941, -122.0864],
    "Dublin": [37.7022, -121.9358],
    "Fremont": [37.5485, -121.9886],
    "Hayward": [37.6688, -122.0808],
    "Livermore": [37.6819, -121.7680],
    "Oakland": [37.8044, -122.2712],
    "Pleasanton": [37.6624, -121.8747],
    "San Leandro": [37.7249, -122.1561],
    "Union City": [37.5934, -122.0438],

    # Contra Costa County
    "Antioch": [38.0049, -121.8058],
    "Brentwood": [37.9319, -121.6958],
    "Concord": [37.9780, -122.0311],
    "Danville": [37.8216, -121.9999],
    "Hercules": [38.0171, -122.2886],
    "Pittsburg": [38.0280, -121.8847],
    "Richmond": [37.9358, -122.3477],
    "San Ramon": [37.7799, -121.9780],
    "Walnut Creek": [37.9101, -122.0652],

    # Marin County
    "Novato": [38.1074, -122.5697],
    "San Rafael": [37.9735, -122.5311],

    # Napa County
    "Napa": [38.2975, -122.2869],

    # San Francisco County
    "San Francisco": [37.7749, -122.4194],

    # San Mateo County
    "Daly City": [37.6879, -122.4702],
    "Foster City": [37.5585, -122.2711],
    "Redwood City": [37.4852, -122.2364],
    "San Bruno": [37.6305, -122.4111],
    "San Mateo": [37.5630, -122.3255],
    "South San Francisco": [37.6547, -122.4077],

    # Santa Clara County
    "Campbell": [37.2872, -121.9500],
    "Cupertino": [37.3229, -122.0322],

        # Sonoma County
    "Petaluma": [38.2324, -122.6367],
    "Santa Rosa": [38.4404, -122.7141],

    # Solano County
    "Fairfield": [38.2494, -122.0400],
    "Vacaville": [38.3566, -121.9877],
    "Vallejo": [38.1041, -122.2566],
    "Gilroy": [37.0058, -121.5683],
    "Milpitas": [37.4323, -121.8996],
    "Mountain View": [37.3861, -122.0839],
    "Palo Alto": [37.4419, -122.143],
    "San Jose": [37.3382, -121.8863],
    "Santa Clara": [37.3541, -121.9552],
    "Sunnyvale": [37.3688, -122.0363],
    }


    # Build a single map, using ONLY cities for which cached research exists.
    city_values = {}
    for city, report in markets.items():
        if city not in city_coordinates:
            continue
        value = _num(_metric(report.get("portfolio_metrics", {}), *map_options[map_metric]))
        city_values[city] = value

    valid_values = sorted(v for v in city_values.values() if v is not None)
    low, high = (valid_values[0], valid_values[-1]) if valid_values else (0.0, 1.0)
    # A restrained navy → teal color ramp; missing observations are muted gray.
    def map_color(value):
        if value is None:
            return "#65707D"
        t = (value - low) / (high - low) if high != low else 0.5
        a, b = (48, 94, 130), (94, 218, 190)
        return "#" + "".join(f"{round(x+(y-x)*t):02x}" for x, y in zip(a, b))

    def map_value_label(value):
        if value is None:
            return "N/A"
        if map_metric in ("Home Value", "Monthly Rent", "Median Household Income"):
            return _fmt_money(value, compact=map_metric != "Monthly Rent")
        if "Growth" in map_metric:
            return _fmt_pct(value, signed=True)
        return _fmt_number(value)

    selected_coords = city_coordinates.get(selected_market, [37.85, -122.15])
    market_map = folium.Map(
        location=selected_coords,
        zoom_start=9,
        tiles="OpenStreetMap",
        control_scale=True,
        prefer_canvas=True,
    )
    for city, value in city_values.items():
        report = markets[city]
        pm = report.get("portfolio_metrics", {})
        chosen = city == selected_market
        popup_html = (
            f'<div style="font-family:Arial,sans-serif;min-width:180px">'
            f'<b style="font-size:15px">{city}</b><br>'
            f'<span>{map_metric}: <b>{map_value_label(value)}</b></span><hr>'
            f'Home value: {_fmt_money(_metric(pm, "zillow_home_value_index", "home_value"))}<br>'
            f'Monthly rent: {_fmt_money(_metric(pm, "zillow_observed_rent_index", "zori_rent_index", "rent_index"))}<br>'
            f'Population: {_fmt_number(_metric(pm, "city_population", "county_population"))}<br>'
            f'Median HH income: {_fmt_money(_metric(pm, "city_median_household_income", "county_median_household_income"))}'
            f'</div>'
        )
        folium.CircleMarker(
            location=city_coordinates[city],
            radius=11 if chosen else 6,
            color="#FFFFFF" if chosen else "#DCE7EA",
            weight=3 if chosen else 1,
            fill=True,
            fill_color=map_color(value),
            fill_opacity=1 if chosen else 0.85,
            tooltip=city,
            popup=folium.Popup(popup_html, max_width=300),
        ).add_to(market_map)

    if valid_values:
        st.caption(f"COLOR SCALE · Low {map_value_label(low)}  →  High {map_value_label(high)} · Gray = unavailable · White outline = selected city")
    map_result = st_folium(
        market_map,
        height=520,
        use_container_width=True,
        key="bay_area_market_explorer",
        returned_objects=["last_object_clicked_tooltip"],
    )
    clicked_city = (map_result or {}).get("last_object_clicked_tooltip")
    if clicked_city in markets and clicked_city != selected_market:
        st.session_state["bay_area_pending_market"] = clicked_city
        st.rerun()

    unmapped = sorted(set(markets) - set(city_coordinates))
    if unmapped:
        st.caption("Cached markets without map coordinates: " + ", ".join(unmapped))

    st.divider()
    st.subheader("Comparative Market Analysis")
    st.caption("Compare two cached cities using matched, city-level market observations.")
    left, right = st.columns(2)
    with left:
        city_a = st.selectbox("Market A", market_names, index=market_names.index(selected_market), key="bay_compare_a")
    with right:
        city_b = st.selectbox("Market B", market_names, index=(market_names.index("Oakland") if "Oakland" in market_names and city_a != "Oakland" else (1 if len(market_names)>1 else 0)), key="bay_compare_b")
    compare_specs = [
        ("Zillow Home Value Index", ("zillow_home_value_index", "home_value"), "money"),
        ("Zillow Observed Rent Index", ("zillow_observed_rent_index", "zori_rent_index", "rent_index"), "money"),
        ("Population", ("city_population", "county_population"), "number"),
        ("Median Household Income", ("city_median_household_income", "county_median_household_income"), "money"),
        ("Home Value Growth YoY", ("home_value_yoy_pct",), "pct"),
        ("Rent Growth YoY", ("rent_yoy_pct",), "pct"),
        ("Detached Single-Family Share", ("sfr_detached_share_pct",), "pct"),
        ("Multifamily 5+ Unit Share", ("multifamily_5plus_share_pct",), "pct"),
        ("Owner-Occupied Share", ("owner_occupied_share_pct",), "pct"),
    ]
    def comparison_value(city, keys):
        return _num(_metric(markets[city].get("portfolio_metrics", {}), *keys))
    def comparison_fmt(value, kind):
        return _fmt_money(value) if kind == "money" else _fmt_pct(value, signed=False) if kind == "pct" else _fmt_number(value)
    comparison_rows = []
    if city_a == city_b:
        st.caption("Choose a different Market B for a meaningful comparison.")
    for label, keys, kind in compare_specs:
        av, bv = comparison_value(city_a, keys), comparison_value(city_b, keys)
        comparison_rows.append({"Indicator": label, city_a: comparison_fmt(av, kind), city_b: comparison_fmt(bv, kind)})
    st.dataframe(pd.DataFrame(comparison_rows), hide_index=True, use_container_width=True)

    chart_choice = st.selectbox("Compare visually", [spec[0] for spec in compare_specs], key="bay_compare_chart")
    chosen_spec = next(spec for spec in compare_specs if spec[0] == chart_choice)
    chart_vals = {city: comparison_value(city, chosen_spec[1]) for city in (city_a, city_b)}
    if city_a == city_b:
        st.info("Select two different cities to compare markets.")
    elif all(v is not None for v in chart_vals.values()):
        chart_data = pd.DataFrame({"City": list(chart_vals), chart_choice: list(chart_vals.values())}).set_index("City")
        comparison_chart = (
            alt.Chart(chart_data.reset_index())
            .mark_bar(cornerRadiusEnd=5)
            .encode(color=alt.Color("City:N", scale=alt.Scale(domain=[city_a, city_b], range=["#55CFC2", "#79A8F8"]), legend=None))
            .encode(
                x=alt.X("City:N", axis=alt.Axis(labelAngle=0, labelColor="#E2E8F0", title=None)),
                y=alt.Y(f"{chart_choice}:Q", title=chart_choice),
                tooltip=["City:N", alt.Tooltip(f"{chart_choice}:Q", format=",.2f")],
            )
            .properties(height=300)
            .configure_view(strokeOpacity=0)
            .configure_axis(gridColor="#2B3540", labelColor="#CBD5E1", titleColor="#CBD5E1")
        )
        st.altair_chart(comparison_chart, use_container_width=True)
    else:
        st.info("One or both cities have no cached value for this indicator.")

    def derived_ratios(city):
        pm = markets[city].get("portfolio_metrics", {})
        hv = _num(_metric(pm, "zillow_home_value_index", "home_value"))
        rent = _num(_metric(pm, "zillow_observed_rent_index", "zori_rent_index", "rent_index"))
        income = _num(_metric(pm, "city_median_household_income", "county_median_household_income"))
        return ((hv / income if hv is not None and income and income > 0 else None),
                (rent * 12 / hv * 100 if rent is not None and hv and hv > 0 else None))
    a_price_income, a_rent_value = derived_ratios(city_a)
    b_price_income, b_rent_value = derived_ratios(city_b)
    st.markdown("#### Relative Housing Indicators")
    st.dataframe(pd.DataFrame([
        {"Indicator": "Home value / annual household income", city_a: f"{a_price_income:.1f}×" if a_price_income is not None else "N/A", city_b: f"{b_price_income:.1f}×" if b_price_income is not None else "N/A"},
        {"Indicator": "Annual rent / home value (proxy)", city_a: _fmt_pct(a_rent_value), city_b: _fmt_pct(b_rent_value)},
    ]), hide_index=True, use_container_width=True)
    st.caption("These ratios use aggregate Zillow indices and Census income, not matched properties or household cohorts. The rent-to-value proxy is not a cap rate, NOI yield, or investment return. Regional BLS and national FRED measures are intentionally excluded from city rankings.")
    st.download_button(
        "Download market comparison CSV",
        data=pd.DataFrame(comparison_rows).to_csv(index=False).encode("utf-8"),
        file_name="bay_area_market_comparison.csv",
        mime="text/csv",
        key="bay_compare_download",
    )
