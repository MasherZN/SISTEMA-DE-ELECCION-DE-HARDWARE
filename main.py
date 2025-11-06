# main.py
from fastapi import FastAPI
from pydantic import BaseModel
import json
import random
import traceback
from pathlib import Path
from typing import Optional

# -------------------- CONFIGURACIÓN INICIAL --------------------
DATA_PATH = Path(__file__).parent / "base_knowledge.json"

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        knowledge = json.load(f)
except FileNotFoundError:
    raise FileNotFoundError(f"No se encontró el archivo {DATA_PATH}.")
except json.JSONDecodeError as e:
    raise ValueError(f"Error de formato en base_knowledge.json: {e}")

required_keys = ["profiles", "components", "rules_meta"]
for key in required_keys:
    if key not in knowledge:
        raise KeyError(f"Falta la clave '{key}' en base_knowledge.json.")

app = FastAPI(title="Sistema Experto en Hardware", version="2.7")

# -------------------- MODELO DE ENTRADA --------------------
class UserRequest(BaseModel):
    profile: Optional[str] = ""
    budget: float

# -------------------- FUNCIONES AUXILIARES --------------------
def choose_best_component(components, max_budget, target_percent, level=None):
    try:
        max_price = max_budget * target_percent * 1.15
        candidates = [c for c in components if c.get("price", 0) <= max_price]
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x.get("performance_score", 0), x.get("price", 0)), reverse=True)
        return random.choice(candidates[:2]) if len(candidates) > 2 else candidates[0]
    except Exception:
        return None

def choose_compatible_motherboard(mobos, cpu):
    if not cpu:
        return None
    compatibles = [m for m in mobos if m.get("socket") == cpu.get("socket")]
    return random.choice(compatibles or mobos)

def choose_gpu_for_profile(gpus, profile_info, budget, gpu_percent):
    if not profile_info.get("gpu_required", False):
        return next((g for g in gpus if g.get("level") == "integrated"), gpus[0] if gpus else None)
    return choose_best_component(gpus, budget, gpu_percent)

def choose_ram_and_ssd(rams, ssds, profile_info, budget, ram_percent, ssd_percent):
    ram_candidates = [r for r in rams if r.get("size_gb", 0) >= profile_info.get("min_ram_gb", 0)]
    ssd_candidates = [s for s in ssds if s.get("size_gb", 0) >= profile_info.get("min_ssd_gb", 0)]
    if not ram_candidates and rams:
        ram_candidates = [min(rams, key=lambda x: x.get("price", float("inf")))]
    if not ssd_candidates and ssds:
        ssd_candidates = [min(ssds, key=lambda x: x.get("price", float("inf")))]
    ram = choose_best_component(ram_candidates, budget, ram_percent) if ram_candidates else None
    ssd = choose_best_component(ssd_candidates, budget, ssd_percent) if ssd_candidates else None
    return ram, ssd

def choose_monitor(monitors, profile, budget):
    try:
        if not monitors:
            return None
        if profile == "gamer" and budget > 20000:
            filtered = [m for m in monitors if m.get("hz", 0) >= 144]
            return random.choice(filtered) if filtered else random.choice(monitors)
        if profile == "disenador" and budget > 30000:
            filtered = [m for m in monitors if m.get("res") in ["1440p", "4K"]]
            return random.choice(filtered) if filtered else random.choice(monitors)
        valid_monitors = [m for m in monitors if m.get("price", float("inf")) <= (budget * 0.2)]
        return random.choice(valid_monitors) if valid_monitors else random.choice(monitors)
    except Exception:
        return None

def choose_psu(psus, gpu):
    if not psus:
        return None
    if not gpu:
        return psus[0]
    power = gpu.get("power_w", 100)
    if power <= 100:
        return psus[0]
    elif power <= 160:
        return psus[1] if len(psus) > 1 else psus[0]
    elif power <= 200:
        return psus[2] if len(psus) > 2 else psus[-1]
    else:
        return psus[-1]

# -------------------- LÓGICA PRINCIPAL --------------------
@app.post("/recommend")
def recommend(req: UserRequest):
    try:
        profile_in = (req.profile or "").lower().strip()
        budget = float(req.budget)
        profiles = knowledge["profiles"]
        components = knowledge["components"]
        rules_meta = knowledge["rules_meta"]

        # Detección automática de perfil
        if not profile_in or profile_in not in profiles or profile_in == "ninguno":
            if budget < 10000:
                profile = "ofimatico"
            elif budget < 20000:
                profile = "estudiante"
            elif budget < 30000:
                profile = "programador"
            elif budget < 40000:
                profile = "gamer"
            else:
                profile = "disenador"
            auto_detected = True
        else:
            profile = profile_in
            auto_detected = False

        profile_info = profiles.get(profile)
        allocation = rules_meta["allocation_percentages"].get(profile, {})

        # Calcular costo mínimo base
        min_base = sum(min(comp.get("price", float("inf")) for comp in components[key])
                       for key in ["cpus", "rams", "ssds", "psus", "motherboards", "monitors"])

        if budget < min_base:
            return {
                "error": (
                    "El presupuesto ingresado es demasiado bajo para ensamblar una computadora funcional. "
                    "Por favor, considera aumentar tu presupuesto."
                ),
                "profile": profile,
                "budget_input": budget,
                "minimum_required": round(min_base, 2),
                "debug": {"min_base": round(min_base, 2), "budget": budget, "profile_used": profile}
            }

        # Selección de componentes principales
        cpu = choose_best_component(components["cpus"], budget, allocation.get("cpu", 0.25))
        gpu = choose_gpu_for_profile(components["gpus"], profile_info, budget, allocation.get("gpu", 0.25))
        ram, ssd = choose_ram_and_ssd(components["rams"], components["ssds"], profile_info, budget,
                                      allocation.get("ram", 0.15), allocation.get("ssd", 0.10))
        psu = choose_psu(components["psus"], gpu)
        mobo = choose_compatible_motherboard(components["motherboards"], cpu)
        monitor = choose_monitor(components["monitors"], profile, budget)

        # Verificar si faltan componentes
        missing = [k for k, v in {"cpu": cpu, "gpu": gpu, "ram": ram, "ssd": ssd,
                                  "psu": psu, "motherboard": mobo, "monitor": monitor}.items() if v is None]

        # 🔁 Segunda pasada flexible: usa los componentes más baratos posibles
        if missing:
            cpu = cpu or min(components["cpus"], key=lambda c: c.get("price", float("inf")))
            gpu = gpu or min(components["gpus"], key=lambda g: g.get("price", float("inf")))
            ram = ram or min(components["rams"], key=lambda r: r.get("price", float("inf")))
            ssd = ssd or min(components["ssds"], key=lambda s: s.get("price", float("inf")))
            psu = psu or min(components["psus"], key=lambda p: p.get("price", float("inf")))
            mobo = mobo or choose_compatible_motherboard(components["motherboards"], cpu)
            monitor = monitor or min(components["monitors"], key=lambda m: m.get("price", float("inf")))

            still_missing = [k for k, v in {"cpu": cpu, "gpu": gpu, "ram": ram, "ssd": ssd,
                                            "psu": psu, "motherboard": mobo, "monitor": monitor}.items() if v is None]
            if still_missing:
                return {
                    "error": "No se encontró una combinación posible ni siquiera con los componentes más básicos.",
                    "profile": profile,
                    "budget_input": budget,
                    "debug": {"missing": still_missing, "budget": budget}
                }

            note_fallback = "⚙️ Se usaron componentes mínimos posibles debido al presupuesto ajustado."
        else:
            note_fallback = None

        # Calcular total
        total_price = sum([
            cpu["price"], gpu["price"], ram["price"], ssd["price"],
            psu["price"], mobo["price"], monitor["price"]
        ])

        result = {
            "profile": profile,
            "budget_input": budget,
            "components": {
                "CPU": cpu, "GPU": gpu, "RAM": ram, "SSD": ssd,
                "Motherboard": mobo, "PSU": psu, "Monitor": monitor
            },
            "total_price_estimate": total_price,
            "exceeds_budget": total_price > budget,
            "allocation_estimate": allocation
        }

        # Añadir nota automática si corresponde
        if auto_detected:
            result["note"] = (
                f"El sistema detectó automáticamente el perfil '{profile}'."
                + (" " + note_fallback if note_fallback else "")
            )
        elif note_fallback:
            result["note"] = note_fallback

        return result

    except Exception as e:
        print("ERROR interno:", traceback.format_exc())
        return {"error": "Error interno en el servidor.", "detail": str(e)}

# -------------------- HEALTH CHECK --------------------
@app.get("/health")
def health():
    return {"status": "ok"}
