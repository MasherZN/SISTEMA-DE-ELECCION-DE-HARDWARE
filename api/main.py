# ============================================================
#   main.py — Motor Experto Integrado (Laptop + PC)
# ============================================================

from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
from typing import Dict, Any
import traceback

# --- Motor experto (reglas)
from engine.utils import load_knowledge
from engine.rules import (
    merge_profiles,
    auto_select_profile_by_budget,
    allocation_for_profile,
    estimate_power_requirement,
)
from engine.inference import (
    choose_best_component,
    choose_compatible_motherboard,
    choose_gpu,
    choose_ram_and_ssd,
    choose_psu,
    choose_monitor,
)

app = FastAPI(title="Sistema Experto Hardware", version="8.0")

DATA_PATH = Path(__file__).parent.parent / "base_knowledge.json"
knowledge = load_knowledge(DATA_PATH)


# ------------------------------------------------------------
# MODELO DEL REQUEST
# ------------------------------------------------------------
class UserRequest(BaseModel):
    budget: float
    device_type: str      # "laptop" o "pc_escritorio"
    survey: dict          # lo que respondió el usuario


# ------------------------------------------------------------
# PERFIL POR ENCUESTA (perfil 1)
# ------------------------------------------------------------
def infer_profile_from_survey(survey: Dict[str,Any]) -> str:
    """
    Asigna perfiles base según uso real del usuario.
    """
    if survey.get("juegas") and survey.get("editas"):
        return "gamer"
    if survey.get("juegas"):
        return "gamer"
    if survey.get("editas"):
        return "disenador"
    if survey.get("programas"):
        return "programador"
    if survey.get("trabajas"):
        return "ofimatico"
    if survey.get("viajas"):
        return "estudiante"
    return "estudiante"


# ------------------------------------------------------------
# ENDPOINT PRINCIPAL
# ------------------------------------------------------------
@app.post("/recommend")
def recommend(req: UserRequest):

    try:
        comps = knowledge["components"]
        profiles = knowledge["profiles"]
        rules_meta = knowledge.get("meta", {})

        # --------------------------------------------------------
        # 1) PERFIL DEL USUARIO SEGÚN ENCUESTA
        # --------------------------------------------------------
        profile_from_user = infer_profile_from_survey(req.survey)

        # --------------------------------------------------------
        # 2) PERFIL SUGERIDO POR PRESUPUESTO
        # --------------------------------------------------------
        profile_auto = auto_select_profile_by_budget(req.budget)

        # --------------------------------------------------------
        # 3) UNIR PERFILES 
        # --------------------------------------------------------
        profile_info = merge_profiles(profile_from_user, profile_auto, profiles)

        reasoning = [
            f"Perfil por respuestas del usuario: {profile_from_user}.",
            f"Perfil por capacidad económica: {profile_auto}.",
            f"Perfil final combinado: CPU nivel {profile_info['cpu_level']}, "
            f"RAM mínima {profile_info['min_ram_gb']}GB, "
            f"SSD mínimo {profile_info['min_ssd_gb']}GB, "
            f"GPU requerida: {profile_info['gpu_required']}."
        ]

        # ========================================================
        # =====================   LAPTOP   =======================
        # ========================================================
        if req.device_type.lower() == "laptop":

            laptops = comps.get("laptops", [])
            if not laptops:
                return {"error": "No hay laptops en la base de conocimiento"}

            # Filtrar por presupuesto
            candidates = [l for l in laptops if l["price"] <= req.budget]

            if not candidates:
                chosen = min(laptops, key=lambda x: x["price"])
                reasoning.append("No hay laptops dentro del presupuesto. Se selecciona la más económica.")
            else:
                # Si requiere GPU dedicada → prioridad
                if profile_info["gpu_required"]:
                    gpu_laps = [l for l in candidates if l["gpu"] == "dedicated"]
                    if gpu_laps:
                        chosen = max(gpu_laps, key=lambda x: x["price"])
                        reasoning.append("Se requiere GPU dedicada → se selecciona laptop con GPU dedicada.")
                    else:
                        reasoning.append("Se requiere GPU dedicada, "
                                         "pero el presupuesto solo alcanza para integradas.")
                        chosen = max(candidates, key=lambda x: x["price"])
                else:
                    chosen = max(candidates, key=lambda x: x["price"])
                    reasoning.append("No se requiere GPU dedicada → mejor laptop dentro del presupuesto.")

            total = chosen["price"]

            components_result = {
                "Laptop": {
                    "name": chosen["name"],
                    "price": chosen["price"]
                },
                "CPU": {"name": f"CPU nivel {chosen['cpu_level']}", "price": 0},
                "GPU": {"name": f"GPU: {chosen['gpu']}", "price": 0},
                "RAM": {"name": f"{chosen.get('ram_gb', 8)} GB", "price": 0},
                "SSD": {"name": "Almacenamiento incluido", "price": 0},
                "Motherboard": {"name": "Integrada", "price": 0},
                "PSU": {"name": "Cargador incluido", "price": 0},
                "Monitor": {"name": "Pantalla integrada", "price": 0},
            }

            allocation = {"Laptop": total}

            return {
                "profile_description": f"{profile_from_user}-{profile_auto}",
                "components": components_result,
                "total_price_estimate": total,
                "reasoning": reasoning,
                "warnings": [],
                "allocation_estimate": allocation
            }

        # ========================================================
        # ==================   PC DE ESCRITORIO   ===============
        # ========================================================

        # Distribución presupuestal según perfil
        allocation_pct = allocation_for_profile(profile_from_user, {
            "allocation_percentages": {
                "ofimatico":  {"cpu": 0.20, "gpu": 0.05, "ram": 0.10, "ssd": 0.10, "mobo": 0.10, "psu": 0.10, "monitor": 0.20},
                "estudiante": {"cpu": 0.22, "gpu": 0.10, "ram": 0.10, "ssd": 0.10, "mobo": 0.10, "psu": 0.10, "monitor": 0.18},
                "programador":{"cpu": 0.28, "gpu": 0.05, "ram": 0.12, "ssd": 0.12, "mobo": 0.10, "psu": 0.08, "monitor": 0.15},
                "gamer":      {"cpu": 0.22, "gpu": 0.35, "ram": 0.10, "ssd": 0.08, "mobo": 0.08, "psu": 0.10, "monitor": 0.15},
                "disenador":  {"cpu": 0.25, "gpu": 0.30, "ram": 0.12, "ssd": 0.10, "mobo": 0.08, "psu": 0.10, "monitor": 0.15},
            }
        })

        # Selección general con reglas
        cpus = comps["cpus"]
        gpus = comps["gpus"]
        rams = comps["rams"]
        ssds = comps["ssds"]
        mobos = comps["motherboards"]
        psus = comps["psus"]
        monitors = comps["monitors"]

        cpu = choose_best_component(cpus, allocation_pct["cpu"], req.budget,
                                    prefer_level=profile_info["cpu_level"])
        reasoning.append(f"CPU seleccionada: {cpu['name']}")

        gpu = choose_gpu(gpus, profile_info, req.budget, allocation_pct["gpu"])
        reasoning.append(f"GPU seleccionada: {gpu['name']}")

        ram, ssd = choose_ram_and_ssd(
            rams, ssds, profile_info,
            req.budget,
            allocation_pct["ram"], allocation_pct["ssd"]
        )

        mobo = choose_compatible_motherboard(mobos, cpu)

        required_watts = estimate_power_requirement(cpu, gpu)
        psu = choose_psu(psus, required_watts)

        monitor = choose_monitor(monitors, profile_from_user, req.budget)

        total = sum([
            cpu["price"], gpu["price"], ram["price"], ssd["price"],
            mobo["price"], psu["price"], monitor["price"]
        ])

        allocation = {
            "CPU": cpu["price"], "GPU": gpu["price"], "RAM": ram["price"],
            "SSD": ssd["price"], "Motherboard": mobo["price"],
            "PSU": psu["price"], "Monitor": monitor["price"]
        }

        return {
            "profile_description": f"{profile_from_user}-{profile_auto}",
            "components": {
                "CPU": cpu, "GPU": gpu, "RAM": ram, "SSD": ssd,
                "Motherboard": mobo, "PSU": psu, "Monitor": monitor
            },
            "total_price_estimate": total,
            "reasoning": reasoning,
            "warnings": [] if total <= req.budget else [f"La PC supera el presupuesto: {total} MXN"],
            "allocation_estimate": allocation,
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


# ------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

