import os
import json
import re
import time
import math
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/radiant-pex-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2").strip()
CUSTOM_RADIANT = os.environ.get("CUSTOM_RADIANT", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_radiant.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

_CACHED_MODELS = None

# Format: (Project / Equipment Name, Heated Area Sq Ft, PEX Spacing Inches, PEX Size, Max Loop Length Ft, BTU per Sq Ft)
SEED_RADIANT = [
    ("24x24 Two-Car Garage Slab (576 Sq Ft) Radiant PEX Setup", 576, 12, "1/2-Inch O2 PEX", 280, 30),
    ("30x40 Pole Barn & Shop Slab (1,200 Sq Ft) Radiant PEX Setup", 1200, 12, "1/2-Inch O2 PEX", 300, 30),
    ("40x60 Commercial Shop Slab (2,400 Sq Ft) 5/8\" Radiant PEX", 2400, 12, "5/8-Inch O2 PEX", 400, 30),
    ("24x36 Three-Car Garage Slab (864 Sq Ft) Radiant PEX Setup", 864, 12, "1/2-Inch O2 PEX", 290, 30),
    ("1,000 Sq Ft Walkout Basement Concrete Slab Radiant PEX", 1000, 9, "1/2-Inch O2 PEX", 280, 25),
    ("1,500 Sq Ft Whole-House Subfloor Aluminum Heat Transfer Plates", 1500, 8, "1/2-Inch PEX-AL-PEX", 250, 28),
    ("Taco 007e-F2 ECM High-Efficiency Hydronic Circulator Pump", 1200, 12, "1/2-Inch O2 PEX", 300, 30),
    ("Taco 0015e3 3-Speed ECM Hydronic Radiant Circulator Pump", 1600, 12, "1/2-Inch O2 PEX", 300, 30),
    ("Grundfos ALPHA2 15-55F AutoAdapt Radiant Circulator Pump", 1500, 12, "1/2-Inch O2 PEX", 300, 30),
    ("Grundfos UPS15-58FC 3-Speed Cast-Iron Hydronic Circulator", 1200, 12, "1/2-Inch O2 PEX", 280, 30),
    ("Uponor / Wirsbo hePEX 1/2-Inch Oxygen-Barrier Radiant Loop", 900, 9, "1/2-Inch PEX-A", 300, 28),
    ("Uponor EP & Stainless 6-Loop Hydronic Radiant Manifold", 1200, 12, "1/2-Inch PEX-A", 280, 30),
    ("Watts Radiant / Viega 8-Loop Stainless Flow-Meter Manifold", 1600, 12, "1/2-Inch O2 PEX", 280, 30),
    ("Caleffi 521 MixCal 3-Way Thermostatic Radiant Mixing Valve", 1200, 12, "1/2-Inch O2 PEX", 300, 30),
    ("Schluter Ditra-Heat Electric Tile Floor Heating (100 Sq Ft)", 100, 3, "Electric Ditra Cable", 150, 15),
    ("Schluter Ditra-Heat Master Bathroom Floor (60 Sq Ft 120V)", 60, 3, "Electric Ditra Cable", 120, 15),
    ("SunTouch TapeMat Electric Underfloor Heating (120 Sq Ft)", 120, 3, "Electric Heating Mat", 150, 12),
    ("WarmlyYours TempZone Electric Radiant Bathroom Floor (80 Sq Ft)", 80, 3, "Electric Heating Mat", 120, 15),
    ("500 Sq Ft Driveway & Sidewalk Snow-Melt Hydronic PEX Setup", 500, 6, "5/8-Inch O2 PEX", 220, 120),
    ("800 Sq Ft Concrete Patio & Apron Snow-Melt Glycol PEX Setup", 800, 6, "5/8-Inch O2 PEX", 220, 120),
    ("1/2-Inch vs 5/8-Inch vs 3/4-Inch Radiant PEX Loop Length", 1200, 12, "1/2-Inch vs 5/8\" PEX", 300, 30),
    ("6-Inch vs 9-Inch vs 12-Inch On-Center PEX Spacing Comparison", 800, 9, "1/2-Inch O2 PEX", 280, 28),
    ("4-Loop Stainless Hydronic Manifold (800 Sq Ft Garage Slab)", 800, 12, "1/2-Inch O2 PEX", 250, 30),
    ("6-Loop Stainless Hydronic Manifold (1,200 Sq Ft Shop Slab)", 1200, 12, "1/2-Inch O2 PEX", 250, 30),
    ("10-Loop Stainless Hydronic Manifold (2,000 Sq Ft Barn Slab)", 2000, 12, "1/2-Inch O2 PEX", 250, 30),
    ("12-Loop Stainless Hydronic Manifold (2,400 Sq Ft Estate Slab)", 2400, 12, "1/2-Inch O2 PEX", 250, 30),
    ("Closed-Loop Tankless Water Heater + Radiant Floor PEX Setup", 900, 12, "1/2-Inch O2 PEX", 280, 28),
    ("40% Propylene Glycol Antifreeze Volume in 1/2\" Radiant PEX", 1200, 12, "1/2-Inch O2 PEX", 300, 30),
    ("2-Inch XPS Rigid Foam Under-Slab Insulation & PEX Stapler", 1000, 12, "1/2-Inch O2 PEX", 280, 25),
    ("Spirovent Microbubble Air Eliminator & Hydronic Expansion Tank", 1400, 12, "1/2-Inch O2 PEX", 300, 30)
]


def load_json(filepath, default):
    """Self-healing JSON loader: otomatis pulih jika file korup atau kosong."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, type(default)) else default
        except Exception as e:
            print(f"[SELF-HEAL] Recovering {filepath} due to read notice: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=1000.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def get_active_gemini_model(api_key):
    """
    LAPIS 1: Mesin Pemindai Versi Otomatis berbasis Regex tanpa angka versi manual.
    Otomatis mendeteksi model Gemini Flash STABIL generasi tertinggi lintas tahun.
    """
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def discover_google_radiant_queries(published_slugs):
    """
    LAPIS 4: 3-Tier Infinite Keyword Supply:
    Tier A: Seed List -> Tier B: Google Suggest US -> Tier C: Combinatorial Slab × PEX Spacing Permutator.
    """
    discovered = []
    seeds = [
        "radiant floor pex calculator ",
        "how much pex for radiant heat ",
        "taco circulator pump ",
        "schluter ditra heat calculator "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "calculator" in pref or "how much" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|how much|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        dim_m = re.search(r"(\d{2})x(\d{2})", cleaned)
                        if dim_m:
                            area_v = int(dim_m.group(1)) * int(dim_m.group(2))
                        else:
                            sq_m = re.search(r"(\d{3,4})\s*sq", cleaned)
                            area_v = int(sq_m.group(1)) if sq_m else 1000
                        discovered.append((cleaned.title(), area_v, 12, "1/2-Inch O2 PEX", 280, 30))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")

    # Tier C Fallback: Combinatorial Permutator (Anti-Habis Lintas Tahun)
    slab_sizes = [
        ("20x24 Garage Slab", 480),
        ("24x30 Workshop Slab", 720),
        ("28x36 Pole Barn Slab", 1008),
        ("30x50 Metal Building Slab", 1500),
        ("36x48 Agricultural Shop Slab", 1728),
        ("40x50 Commercial Garage Slab", 2000)
    ]
    spacings = [
        (6, "6-Inch High-Output Spacing"),
        (9, "9-Inch Residential Spacing"),
        (12, "12-Inch Slab-on-Grade Spacing")
    ]
    for s_name, s_area in slab_sizes:
        for sp_in, sp_desc in spacings:
            combo_title = f"{s_name} ({s_area} Sq Ft) at {sp_desc}"
            test_slug = slugify(f"{combo_title}-pex-loop-manifold-calculator")
            if test_slug not in published_slugs:
                discovered.append((combo_title, s_area, sp_in, "1/2-Inch O2 PEX", 280, 30))
                if len(discovered) >= 25:
                    return discovered
    return discovered


def build_deterministic_radiant_data(rad_tuple):
    """
    LAPIS 3: Mesin Fisika Hidronik Radiant PEX, Manifold Loop & Circulator GPM (100% Bebas Gagal).
    """
    project_name, area_sqft, spacing_in, pex_spec, max_loop_ft, btu_per_sqft = rad_tuple

    # Rumus Panjang Pipa PEX (Linear Feet):
    # Multiplier = 12 / Spacing_Inches (misal 12" spacing = 1.0 ft/sq ft; 9" = 1.33 ft/sq ft; 6" = 2.0 ft/sq ft)
    multiplier = 12.0 / max(3.0, float(spacing_in))
    active_grid_ft = int(round(area_sqft * multiplier))

    # Jumlah cabang/loop pada Manifold (agar setiap loop <= max_loop_ft [280 ft untuk 1/2" PEX])
    num_loops = max(1, int(math.ceil((active_grid_ft * 1.08) / float(max_loop_ft))))
    # Tambahkan 20 kaki leader/tail (10 ft supply + 10 ft return ke manifold) untuk setiap loop
    total_pex_linear_ft = int(round(active_grid_ft + (num_loops * 20), -1))
    avg_loop_len_ft = int(round(total_pex_linear_ft / num_loops))

    # Beban Termal BTU/hr & Debit Pompa Sirkulasi (GPM = BTU/hr / (500 * Delta_T), dengan Delta_T = 15°F untuk lantai)
    total_btu_hr = int(round(area_sqft * btu_per_sqft, -2))
    required_gpm = round(total_btu_hr / (500.0 * 15.0), 1)
    required_gpm = max(1.0, required_gpm)

    # Kehilangan Tekanan Head (Feet of Water) pada loop terpanjang (1/2" PEX @ ~0.8 GPM/loop ~ 3.8 ft head / 100 ft pipe)
    head_loss_ft = round((avg_loop_len_ft / 100.0) * 3.8 + 3.5, 1)
    # Volume cairan (air/glycol) di dalam 1/2" PEX (0.92 galon per 100 kaki linear)
    fluid_gallons = round((total_pex_linear_ft / 100.0) * 0.92, 1)

    return {
        "project_name": project_name,
        "pex_spec": pex_spec,
        "seo_title": f"{project_name} PEX Loop, Manifold & Pump GPM Calculator (2026)",
        "meta_description": f"Calculate exact radiant PEX tubing length ({total_pex_linear_ft:,} linear ft), manifold circuits ({num_loops} loops @ {avg_loop_len_ft} ft ea), heat load ({total_btu_hr:,} BTU/hr), and circulator pump ({required_gpm} GPM @ {head_loss_ft} ft head) for {project_name}.",
        "specs": {
            "heated_area_sqft": area_sqft,
            "on_center_spacing_in": spacing_in,
            "pex_pipe_spec": pex_spec,
            "total_pex_linear_ft": total_pex_linear_ft,
            "manifold_loop_count": num_loops,
            "avg_loop_length_ft": avg_loop_len_ft,
            "total_btu_hr": total_btu_hr,
            "circulator_gpm": required_gpm,
            "pump_head_loss_ft": head_loss_ft,
            "system_fluid_gallons": fluid_gallons
        },
        "hydronic_verdict": f"Heating {area_sqft:,} sq. ft. ({project_name}) at {spacing_in}-inch on-center spacing requires {total_pex_linear_ft:,} linear feet of {pex_spec} (including manifold supply/return leaders), divided into {num_loops} balanced circuits of ~{avg_loop_len_ft} feet each so no single loop exceeds the {max_loop_ft}-foot friction limit. Delivering {total_btu_hr:,} BTU/hr across a 15°F design temperature drop ($\\Delta T$) requires a hydronic circulator pump rated for {required_gpm} GPM against {head_loss_ft} feet of head pressure, holding ~{fluid_gallons} gallons of water/propylene-glycol fluid inside the loops.",
        "hardware_bundle": [
            {
                "badge": f"{total_pex_linear_ft:,} ft {pex_spec.split()[0]} PEX",
                "title": f"{max(300, int(round(total_pex_linear_ft, -2))):,} ft DIN-4726 Oxygen-Barrier Radiant Heating PEX Tubing Coil",
                "price_range": "$159 - $649",
                "amazon_query": f"1/2 Inch Oxygen Barrier PEX Tubing Radiant Floor Heating 500ft 1000ft",
                "rad_note": f"EVOH oxygen-diffusion barrier prevents dissolved oxygen from corroding cast-iron boilers, heat exchangers, and air vents."
            },
            {
                "badge": f"{num_loops}-Loop Stainless Manifold",
                "title": f"{num_loops}-Branch Stainless Steel Hydronic Radiant Manifold Set with Visual GPM Flow Meters",
                "price_range": "$129 - $389",
                "amazon_query": f"{num_loops} Loop Branch Stainless Steel Radiant Floor Heating Manifold PEX",
                "rad_note": f"Balances all {num_loops} circuits (~{round(required_gpm / num_loops, 2)} GPM per loop) and includes automatic air bleeder and drain valves."
            },
            {
                "badge": f"{required_gpm} GPM ECM Circulator",
                "title": "Variable-Speed ECM Hydronic Circulator Pump (Taco 007e / Grundfos ALPHA2) + Isolator Flanges",
                "price_range": "$145 - $349",
                "amazon_query": "Taco 007e Grundfos Alpha2 Hydronic Circulator Pump Flanges",
                "rad_note": f"Automatically adjusts impeller torque to maintain {required_gpm} GPM at {head_loss_ft} ft head while using 85% less watts than old 3-speed pumps."
            },
            {
                "badge": "Foam Stapler & Uncoiler",
                "title": "Stand-Up PEX Foamboard Stapler Gun + 1,650 1-1/2\" Barbed Staples & Heavy-Duty PEX Decoiler",
                "price_range": "$119 - $279",
                "amazon_query": "Stand Up PEX Foamboard Stapler Gun Staples Radiant Floor Heating",
                "rad_note": "Anchors 1/2\" or 5/8\" PEX directly to 2-inch XPS rigid foam insulation in 1/4 the time without kinking the coil."
            }
        ],
        "slab_checklist": [
            "Lay 2-Inch High-Density XPS Rigid Foam Insulation (R-10 minimum, 25 PSI compressive strength) under the entire concrete slab AND vertically along the perimeter stem wall; pouring heated concrete directly on bare earth loses 45%+ of your BTU output downward.",
            f"Never exceed 300 feet on a single 1/2-inch PEX loop (or 400 feet on 5/8-inch PEX): split {total_pex_linear_ft:,} linear feet into {num_loops} equal loops (~{avg_loop_len_ft} ft each) so all circuits balance effortlessly on the manifold flow meters.",
            "Pressurize the completed PEX manifold assembly to 60–100 PSI with air (or water) and leave the pressure gauge attached during the entire concrete pour so any rebar/trowel puncture is detected immediately.",
            "Install a 3-Way Thermostatic Mixing Valve between your heat source and manifold to temper slab supply water to 105°F–120°F; sending raw 160°F+ boiler water directly into a concrete slab causes thermal expansion cracking."
        ],
        "faqs": [
            {
                "q": f"How many feet of PEX and how many manifold loops do I need for {project_name}?",
                "a": f"At {spacing_in}-inch on-center spacing ({multiplier:.2f} linear feet per sq. ft.), {area_sqft:,} sq. ft. requires {active_grid_ft:,} ft of floor grid plus {num_loops * 20} ft of manifold supply/return tails = {total_pex_linear_ft:,} total linear feet, divided into {num_loops} manifold loops of ~{avg_loop_len_ft} feet each."
            },
            {
                "q": f"What size circulator pump GPM and head do I need for {area_sqft:,} sq ft of radiant heat?",
                "a": f"Using the hydronic heat-transfer formula ($\\text{{GPM}} = \\text{{BTU/hr}} \\div [500 \\times \\Delta T]$), delivering {total_btu_hr:,} BTU/hr across a 15°F temperature drop requires {required_gpm} GPM against ~{head_loss_ft} feet of head pressure (a single Loop loses head in parallel, not multiplied by all {num_loops} loops)."
            },
            {
                "q": f"How many gallons of water or glycol does {total_pex_linear_ft:,} feet of 1/2-inch PEX hold?",
                "a": f"Standard 1/2-inch PEX holds 0.92 gallons per 100 linear feet (5/8-inch PEX holds 1.34 gal/100 ft). Your {total_pex_linear_ft:,} feet of tubing holds ~{fluid_gallons} gallons, plus ~2.5 gallons for the boiler/header and expansion tank."
            }
        ]
    }


def generate_radiant_data(rad_tuple):
    """
    LAPIS 2: Memanggil model Gemini stabil dengan proteksi Cooldown HTTP 429 & Fallback Otomatis.
    """
    if not GEMINI_API_KEY:
        return build_deterministic_radiant_data(rad_tuple)

    project_name, area_sqft, spacing_in, pex_spec, max_loop_ft, btu_per_sqft = rad_tuple
    det_fallback = build_deterministic_radiant_data(rad_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Certified RPA (Radiant Professionals Alliance) Hydronic Heating Engineer & Master Mechanical Contractor. Create an accurate 2026 radiant floor heating PEX loop length, stainless manifold circuit count, circulator pump GPM/head, and slab BTU guide for: "{project_name}".
Baseline specs: Area={area_sqft} sq ft, Spacing={spacing_in} inches OC, Pipe={pex_spec}, Total PEX={sp['total_pex_linear_ft']} linear ft, Manifold={sp['manifold_loop_count']} Loops (~{sp['avg_loop_length_ft']} ft/loop), Heat Load={sp['total_btu_hr']} BTU/hr, Circulator Pump={sp['circulator_gpm']} GPM @ {sp['pump_head_loss_ft']} ft head, Fluid Volume={sp['system_fluid_gallons']} gal.
Return ONLY a valid JSON object matching this exact schema:
{{
  "project_name": "{project_name}",
  "pex_spec": "{pex_spec}",
  "seo_title": "{project_name} PEX Loop, Manifold & Pump GPM Calculator (2026)",
  "meta_description": "Calculate exact radiant floor PEX linear feet, manifold loop count, BTU heat load, and circulator pump GPM for {project_name}.",
  "specs": {{
    "heated_area_sqft": {area_sqft},
    "on_center_spacing_in": {spacing_in},
    "pex_pipe_spec": "{pex_spec}",
    "total_pex_linear_ft": {sp['total_pex_linear_ft']},
    "manifold_loop_count": {sp['manifold_loop_count']},
    "avg_loop_length_ft": {sp['avg_loop_length_ft']},
    "total_btu_hr": {sp['total_btu_hr']},
    "circulator_gpm": {sp['circulator_gpm']},
    "pump_head_loss_ft": {sp['pump_head_loss_ft']},
    "system_fluid_gallons": {sp['system_fluid_gallons']}
  }},
  "hydronic_verdict": "3-sentence technical summary stating linear feet of oxygen-barrier PEX, number of manifold loops, BTU/hr output, and circulator pump GPM at 15F Delta-T.",
  "hardware_bundle": [
    {{
      "badge": "{sp['total_pex_linear_ft']} ft O2-Barrier PEX",
      "title": "DIN-4726 Oxygen-Barrier Radiant Heating PEX Tubing Coil ({pex_spec})",
      "price_range": "$159 - $649",
      "amazon_query": "1/2 Inch Oxygen Barrier PEX Tubing Radiant Floor Heating",
      "rad_note": "1-sentence EVOH oxygen barrier corrosion protection note"
    }},
    {{
      "badge": "{sp['manifold_loop_count']}-Loop Stainless Manifold",
      "title": "{sp['manifold_loop_count']}-Branch Stainless Steel Hydronic Radiant Manifold with Flow Meters",
      "price_range": "$129 - $389",
      "amazon_query": "{sp['manifold_loop_count']} Loop Stainless Steel Radiant Floor Heating Manifold PEX",
      "rad_note": "1-sentence loop balancing and air elimination note"
    }},
    {{
      "badge": "{sp['circulator_gpm']} GPM ECM Circulator",
      "title": "Variable-Speed ECM Hydronic Circulator Pump (Taco 007e / Grundfos ALPHA2)",
      "price_range": "$145 - $349",
      "amazon_query": "Taco 007e Grundfos Alpha2 Hydronic Circulator Pump",
      "rad_note": "1-sentence Delta-T flow and head pressure note"
    }},
    {{
      "badge": "Foam Stapler & Decoiler",
      "title": "Stand-Up PEX Foamboard Stapler Gun + 1-1/2\" Barbed Staples & PEX Uncoiler",
      "price_range": "$119 - $279",
      "amazon_query": "Stand Up PEX Foamboard Stapler Gun Staples Radiant Floor",
      "rad_note": "1-sentence 2-inch XPS foam installation speed note"
    }}
  ],
  "slab_checklist": [
    "Step 1 regarding 2-inch R-10 XPS rigid foam insulation under slab and perimeter",
    "Step 2 regarding keeping 1/2-inch PEX loops under 300 feet of equal length",
    "Step 3 regarding 60-100 PSI pressure test during concrete pour",
    "Step 4 regarding 3-way thermostatic mixing valve for 110F-120F slab water"
  ],
  "faqs": [
    {{"q": "How many feet of PEX and manifold loops do I need for {project_name}?", "a": "Exact linear feet, spacing multiplier, and number of loops."}},
    {{"q": "What size circulator pump GPM do I need for {area_sqft} sq ft?", "a": "Exact GPM = BTU / (500 x 15F Delta-T) and parallel head loss explanation."}},
    {{"q": "How many gallons of glycol/water are in {sp['total_pex_linear_ft']} ft of PEX?", "a": "Exact gallon calculation at 0.92 gal per 100 ft of 1/2-inch PEX."}}
  ]
}}
"""

    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id} for '{project_name}': {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice for '{project_name}': {e}")
                break

    return det_fallback


def build_radiant_html_page(data, slug, mon_cfg):
    proj_name = data.get("project_name", "Radiant Floor Heating System")
    sp = data.get("specs", {})
    area_sqft = int(safe_float(sp.get("heated_area_sqft", 1000), 1000))
    spacing_in = int(safe_float(sp.get("on_center_spacing_in", 12), 12))
    pex_s = sp.get("pex_pipe_spec", "1/2-Inch O2 PEX")
    tot_pex_ft = int(safe_float(sp.get("total_pex_linear_ft", 1100), 1100))
    loops = int(safe_float(sp.get("manifold_loop_count", 4), 4))
    avg_loop = int(safe_float(sp.get("avg_loop_length_ft", 275), 275))
    btu_hr = int(safe_float(sp.get("total_btu_hr", 30000), 30000))
    gpm = round(safe_float(sp.get("circulator_gpm", 4.0), 4.0), 1)
    head_ft = round(safe_float(sp.get("pump_head_loss_ft", 13.9), 13.9), 1)
    fluid_gal = round(safe_float(sp.get("system_fluid_gallons", 10.1), 10.1), 1)

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Oxygen+Barrier+PEX+Tubing+Radiant+Manifold+Taco+Pump"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{proj_name} PEX Loop & Manifold Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Oxygen Barrier PEX Manifold")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-orange-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Hydronic Gear')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$119+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">🔥 {item.get('rad_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Slab Area vs PEX Linear Feet, Manifold Loops & GPM Reference Matrix Table
    slab_tiers = [
        ("500 Sq Ft (20x25 Garage)", "560 ft (1/2\" O2 PEX)", "2-Loop Manifold (~280 ft/ea)", "15,000 BTU/hr", "2.0 GPM Circulator"),
        ("800 Sq Ft (24x34 Shop)", "880 ft (1/2\" O2 PEX)", "3-Loop Manifold (~290 ft/ea)", "24,000 BTU/hr", "3.2 GPM Circulator"),
        ("1,200 Sq Ft (30x40 Barn)", "1,300 ft (1/2\" O2 PEX)", "5-Loop Manifold (~260 ft/ea)", "36,000 BTU/hr", "4.8 GPM Circulator"),
        ("1,800 Sq Ft (36x50 Shop)", "1,940 ft (1/2\" O2 PEX)", "7-Loop Manifold (~277 ft/ea)", "54,000 BTU/hr", "7.2 GPM Circulator"),
        ("2,400 Sq Ft (40x60 Building)", "2,580 ft (1/2\" or 5/8\" PEX)", "9-Loop Manifold (~286 ft/ea)", "72,000 BTU/hr", "9.6 GPM Circulator")
    ]
    matrix_rows_html = ""
    for a_lbl, p_lbl, m_lbl, b_lbl, g_lbl in slab_tiers:
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{a_lbl}</td>
          <td class="py-3 px-4 font-bold text-orange-400">{p_lbl}</td>
          <td class="py-3 px-4 text-emerald-400 font-semibold">{m_lbl}</td>
          <td class="py-3 px-4 text-slate-300">{b_lbl}</td>
          <td class="py-3 px-4 text-xs text-slate-300">{g_lbl}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("slab_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-orange-500 rounded cursor-pointer rad-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>RPA Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', proj_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', proj_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-orange-500 text-slate-950 px-2 py-0.5 rounded font-black">RADIANT</span>PEXIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Radiant PEX & Manifolds →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-orange-500 text-slate-950 px-3 py-1 rounded-full">{tot_pex_ft:,} ft PEX ({loops} Loops)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">{btu_hr:,} BTU/hr | {gpm} GPM Pump</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">{spacing_in}" Spacing | Fluid: ~{fluid_gal} Gal</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', proj_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-orange-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>RPA Hydronic Loop & Circulator Verdict:</strong> {data.get('hydronic_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE RADIANT PEX LENGTH, MANIFOLD LOOP & CIRCULATOR PUMP GPM CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {proj_name} PEX, Manifold & Pump Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your heated slab/floor square footage, PEX on-center spacing, tubing diameter, and heat load factor to compute exact linear feet of O2-barrier PEX, manifold branch count, and circulator pump GPM.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="areaSlider" class="text-slate-300">Heated Slab or Subfloor Area (Sq Ft)</label>
              <span class="text-orange-400 font-bold"><span id="areaVal">{area_sqft:,}</span> sq ft</span>
            </div>
            <input id="areaSlider" type="range" min="100" max="3600" step="50" value="{area_sqft}" class="w-full accent-orange-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="spaceSelect" class="block text-xs font-medium text-slate-400 mb-1">PEX On-Center Spacing</label>
              <select id="spaceSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="6" {"selected" if spacing_in == 6 else ""}>6" OC (2.0 ft/ft² — Snow Melt / Bath)</option>
                <option value="8" {"selected" if spacing_in == 8 else ""}>8" OC (1.5 ft/ft² — Joist Plates)</option>
                <option value="9" {"selected" if spacing_in == 9 else ""}>9" OC (1.33 ft/ft² — House Slab)</option>
                <option value="12" {"selected" if spacing_in >= 12 else ""}>12" OC (1.0 ft/ft² — Garage / Shop)</option>
              </select>
            </div>
            <div>
              <label for="pipeSelect" class="block text-xs font-medium text-slate-400 mb-1">PEX Pipe Size & Max Loop</label>
              <select id="pipeSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-orange-500">
                <option value="200|0.53">3/8" O2 PEX (Max 200 ft/loop)</option>
                <option value="280|0.92" selected>1/2" O2 PEX (Max 280 ft/loop)</option>
                <option value="380|1.34">5/8" O2 PEX (Max 380 ft/loop)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="btuSlider" class="text-slate-300">Design Heat Loss Factor (BTU/hr per Sq Ft)</label>
              <span class="text-orange-400 font-bold"><span id="btuFactorVal">30</span> BTU/ft²</span>
            </div>
            <input id="btuSlider" type="range" min="15" max="60" step="5" value="30" class="w-full accent-orange-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-orange-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-orange-400 font-bold">Total PEX & Manifold</span>
            <div class="text-xl sm:text-2xl font-black text-white mt-1"><span id="pexFtOut">{tot_pex_ft:,}</span> <span class="text-xs font-normal text-slate-400">ft</span></div>
            <p id="loopOut" class="text-xs text-orange-400 font-semibold mt-1">{loops}-Loop Manifold (~{avg_loop} ft/ea)</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">BTU & Circulator Pump</span>
            <div class="text-xl sm:text-2xl font-black text-emerald-400 mt-1"><span id="gpmOut">{gpm}</span> <span class="text-xs font-normal text-slate-400">GPM</span></div>
            <p id="btuGalOut" class="text-xs text-slate-300 font-semibold mt-1">{btu_hr // 1000}k BTU/hr (~{fluid_gal} Gal Fluid)</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-orange-950/40 border border-orange-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="radAdviceBanner" class="text-sm text-orange-100 font-medium"></div>
        <a id="dynamicRadBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched PEX, Manifold & Pump on Amazon →
        </a>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {proj_name} PEX, Manifold & Circulator Kit</h2>
        <span class="text-xs text-slate-400">DIN-4726 Oxygen-Barrier & NSF-pw Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">Heated Slab Area, 1/2" PEX Linear Feet, Manifold Loops & Pump GPM Chart (12" OC)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Slab Floor Area</th>
              <th class="py-3.5 px-4 text-orange-400">Total O2-Barrier PEX</th>
              <th class="py-3.5 px-4 text-emerald-400">Stainless Manifold Size</th>
              <th class="py-3.5 px-4">Thermal Output</th>
              <th class="py-3.5 px-4">Circulator Flow (@15°F ΔT)</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">RPA Slab Insulation, Loop Balancing & Pressure Test Checklist</h2>
        <span id="radBadge" class="text-xs font-bold bg-slate-800 text-orange-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({proj_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} RadiantPEXIndex. Independent Hydronic Radiant Floor Heating & Loop Sizing Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const areaSlider = document.getElementById('areaSlider');
    const spaceSelect = document.getElementById('spaceSelect');
    const pipeSelect = document.getElementById('pipeSelect');
    const btuSlider = document.getElementById('btuSlider');
    const areaVal = document.getElementById('areaVal');
    const btuFactorVal = document.getElementById('btuFactorVal');
    const pexFtOut = document.getElementById('pexFtOut');
    const loopOut = document.getElementById('loopOut');
    const gpmOut = document.getElementById('gpmOut');
    const btuGalOut = document.getElementById('btuGalOut');
    const radAdviceBanner = document.getElementById('radAdviceBanner');
    const dynamicRadBtn = document.getElementById('dynamicRadBtn');

    function recalculateRadiant() {{
      const sqft = parseInt(areaSlider.value, 10);
      const spaceIn = parseInt(spaceSelect.value, 10);
      const pipeParts = pipeSelect.value.split('|');
      const maxLoopFt = parseInt(pipeParts[0], 10);
      const galPer100 = parseFloat(pipeParts[1]);
      const btuPerSqft = parseInt(btuSlider.value, 10);

      areaVal.textContent = sqft.toLocaleString();
      btuFactorVal.textContent = btuPerSqft;

      const mult = 12.0 / spaceIn;
      const gridFt = Math.round(sqft * mult);
      const loopCount = Math.max(1, Math.ceil((gridFt * 1.08) / maxLoopFt));
      const totalPexFt = Math.ceil((gridFt + (loopCount * 20)) / 10) * 10;
      const avgLoopFt = Math.round(totalPexFt / loopCount);

      const totalBtu = sqft * btuPerSqft;
      const pumpGpm = Math.max(1.0, (totalBtu / (500.0 * 15.0))).toFixed(1);
      const fluidGals = ((totalPexFt / 100.0) * galPer100).toFixed(1);

      pexFtOut.textContent = totalPexFt.toLocaleString();
      loopOut.textContent = `${{loopCount}}-Loop Manifold (~${{avgLoopFt}} ft/ea)`;
      gpmOut.textContent = pumpGpm;
      btuGalOut.textContent = `${{Math.round(totalBtu / 1000)}}k BTU/hr (~${{fluidGals}} Gal Fluid)`;

      radAdviceBanner.innerHTML = `🔥 <strong>RPA Hydronic Spec:</strong> Order <strong>${{totalPexFt.toLocaleString()}} linear ft of Oxygen-Barrier PEX</strong>, a <strong>${{loopCount}}-Branch Stainless Flow-Meter Manifold</strong>, and an <strong>ECM Circulator Pump (${{pumpGpm}} GPM @ 15°F ΔT)</strong>.`;
      dynamicRadBtn.href = `https://${{amzDomain}}/s?k=1/2+Inch+Oxygen+Barrier+PEX+Tubing+${{loopCount}}+Loop+Stainless+Radiant+Manifold+Taco+Pump&tag=${{amzTag}}`;
    }}

    areaSlider.addEventListener('input', recalculateRadiant);
    spaceSelect.addEventListener('change', recalculateRadiant);
    pipeSelect.addEventListener('change', recalculateRadiant);
    btuSlider.addEventListener('input', recalculateRadiant);
    recalculateRadiant();

    const checks = document.querySelectorAll('.rad-check');
    const badge = document.getElementById('radBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Oxygen+Barrier+PEX+Tubing+Radiant+Manifold+Taco+Pump"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-orange-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-orange-500 text-slate-950 px-2.5 py-0.5 rounded">{item.get('pex_ft', 1200):,} ft PEX ({item.get('loops', 5)} Loops)</span>
            <span class="text-xs text-slate-400">{item.get('btu', 36000) // 1000}k BTU | {item.get('gpm', 4.8)} GPM</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-orange-400 transition">{item['project_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-orange-400">Calculate PEX Loops, Manifold & Pump GPM →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RadiantPEXIndex — Radiant Floor Heating PEX Loop, Manifold & Circulator Pump Calculator (2026)</title>
  <meta name="description" content="Calculate exact radiant floor heating oxygen-barrier PEX linear feet, stainless manifold loop count, slab BTU heat load, and Taco/Grundfos circulator pump GPM for garage slabs, pole barns, basements, and bathrooms.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="RadiantPEXIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-orange-500 text-slate-950 px-2 py-0.5 rounded font-black">RADIANT</span>PEXIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-orange-500 hover:bg-orange-400 text-slate-950 font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Radiant PEX & Manifolds →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">Radiant Floor Heating PEX Loop, Manifold & Pump GPM Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your garage slab, pole barn, basement, or hydronic equipment below to calculate exact O2-barrier PEX linear footage, balanced manifold branch loops, and circulator pump GPM.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search slab size or equipment (e.g. 30x40 Pole Barn, 24x24 Garage, Taco 007e, Grundfos Alpha2, Ditra-Heat, 6-Loop Manifold...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-orange-500">
      </div>
    </div>

    <div id="radGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} RadiantPEXIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('radGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>RadiantPEXIndex Hydronic Radiant Floor Heating Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive Radiant Floor PEX Loop Length, Manifold Circuit & Circulator Pump GPM Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    """Multi-Endpoint Search Engine Pinger (IndexNow Global + Bing + Google WebSub)."""
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    for idx_endpoint in ["https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"]:
        try:
            req = urllib.request.Request(
                idx_endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json; charset=utf-8"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                print(f"[INDEXNOW] Pushed {len(new_urls)} URLs to {idx_endpoint} (HTTP {resp.status})")
                break
        except Exception as e:
            print(f"[WARN] IndexNow ({idx_endpoint}) notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published if "slug" in item}

    candidates = []
    if CUSTOM_RADIANT:
        candidates.append((CUSTOM_RADIANT.strip(), 1200, 12, "1/2-Inch O2 PEX", 280, 30))
    candidates.extend(SEED_RADIANT)
    candidates.extend(discover_google_radiant_queries(published_slugs))

    new_urls = []
    count = 0

    for rad_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        p_name = rad_tuple[0]
        slug = slugify(f"{p_name}-pex-loop-manifold-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating radiant floor PEX & manifold calculator for: {p_name}...")
        try:
            data = generate_radiant_data(rad_tuple)
            build_radiant_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "project_name": data.get("project_name", p_name),
                "slug": slug,
                "title": data.get("seo_title", f"{p_name} Radiant PEX Calculator"),
                "description": data.get("meta_description", ""),
                "pex_ft": int(safe_float(sp.get("total_pex_linear_ft", 1300), 1300)),
                "loops": int(safe_float(sp.get("manifold_loop_count", 5), 5)),
                "btu": int(safe_float(sp.get("total_btu_hr", 36000), 36000)),
                "gpm": round(safe_float(sp.get("circulator_gpm", 4.8), 4.8), 1),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            if count < PAGES_PER_RUN:
                time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {p_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new radiant floor PEX & manifold calculator pages.")


if __name__ == "__main__":
    main()
