# api/main.py
from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
import json

app = FastAPI(title="Sistema Experto Hardware", version="7.0")

DATA_PATH = Path(__file__).parent.parent / "base_knowledge.json"

with open(DATA_PATH, "r", encoding="utf-8") as f:
    knowledge = json.load(f)


# -------------------- MODELO --------------------
class UserRequest(BaseModel):
    budget: float
    device_type: str
    survey: dict


# ============================================================
# NECESIDADES SEGÚN ENCUESTA
# ============================================================
def infer_needs(survey):
    needs = {
        "gpu_needed": False,
        "multi_core_cpu": False,
        "high_ram": False,
        "storage_priority": False,
        "portability": False
    }

    if survey.get("juegas"):
        needs["gpu_needed"] = True
        needs["multi_core_cpu"] = True

    if survey.get("editas"):
        needs["gpu_needed"] = True
        needs["high_ram"] = True

    if survey.get("programas"):
        needs["multi_core_cpu"] = True
        needs["high_ram"] = True

    if survey.get("streamer"):
        needs["gpu_needed"] = True
        needs["high_ram"] = True

    if survey.get("trabajas"):
        needs["high_ram"] = True

    if survey.get("viajas"):
        needs["portability"] = True

    return needs


# ============================================================
# ETIQUETA FINAL DEL USUARIO
# ============================================================
def infer_profile_description(survey):
    if survey.get("juegas") and survey.get("editas"):
        return "gamer-creador"
    if survey.get("juegas"):
        return "gamer"
    if survey.get("programas"):
        return "programador"
    if survey.get("editas"):
        return "creador"
    if survey.get("viajas"):
        return "movil"
    if survey.get("trabajas"):
        return "ofimatico"
    return "general"


# ============================================================
# SELECCIÓN SEGÚN PRESUPUESTO
# ============================================================
def choose_best_level(component_list, budget, factor):
    limit = budget * factor

    items = sorted(component_list, key=lambda x: x["price"])

    best = items[0]
    for item in items:
        if item["price"] <= limit:
            best = item

    return best


# ============================================================
# ENDPOINT PRINCIPAL
# ============================================================
@app.post("/recommend")
def recommend(req: UserRequest):

    comps = knowledge["components"]
    survey = req.survey

    needs = infer_needs(survey)
    profile_desc = infer_profile_description(survey)

    reasoning = []
    warnings = []

    # ==========================================================
    # USO DEL NIVEL DE RENDIMIENTO
    # ==========================================================
    performance = survey.get("performance", "medio")

    if performance == "bajo":
        factors = {
            "cpu": 0.13,
            "gpu": 0.12,
            "ram": 0.06,
            "ssd": 0.07,
            "mobo": 0.06,
            "psu": 0.05,
            "monitor": 0.05
        }
    elif performance == "medio":
        factors = {
            "cpu": 0.22,
            "gpu": 0.28,
            "ram": 0.10,
            "ssd": 0.10,
            "mobo": 0.07,
            "psu": 0.05,
            "monitor": 0.08
        }
    else:  # alto
        factors = {
            "cpu": 0.32,
            "gpu": 0.38,
            "ram": 0.15,
            "ssd": 0.10,
            "mobo": 0.10,
            "psu": 0.08,
            "monitor": 0.12
        }

    reasoning.append(f"Nivel de rendimiento seleccionado: {performance}.")

    # ==========================================================
    # CPU
    # ==========================================================
    if needs["multi_core_cpu"]:
        reasoning.append("Se requiere CPU multinúcleo según tus actividades.")
    cpu = choose_best_level(comps["cpus"], req.budget, factors["cpu"])

    # ==========================================================
    # GPU
    # ==========================================================
    if needs["gpu_needed"]:
        gpu_list = [g for g in comps["gpus"] if g["level"] != "integrated"]
        reasoning.append("Se requiere GPU dedicada.")
        gpu = choose_best_level(gpu_list, req.budget, factors["gpu"])
    else:
        gpu = [g for g in comps["gpus"] if g["level"] == "integrated"][0]
        reasoning.append("No es necesaria una GPU dedicada.")

    # ==========================================================
    # RAM
    # ==========================================================
    ram = choose_best_level(comps["rams"], req.budget, factors["ram"])

    # ==========================================================
    # SSD
    # ==========================================================
    ssd = choose_best_level(comps["ssds"], req.budget, factors["ssd"])

    # ==========================================================
    # Motherboard
    # ==========================================================
    mobo_list = [m for m in comps["motherboards"] if m["socket"] == cpu["socket"]]
    if not mobo_list:
        mobo_list = comps["motherboards"]
    mobo = choose_best_level(mobo_list, req.budget, factors["mobo"])

    # ==========================================================
    # PSU
    # ==========================================================
    psu = choose_best_level(comps["psus"], req.budget, factors["psu"])

    # ==========================================================
    # MONITOR
    # ==========================================================
    if req.device_type == "laptop":
        monitor = {"name": "Pantalla integrada", "price": 0}
    else:
        monitor = choose_best_level(comps["monitors"], req.budget, factors["monitor"])

    # ==========================================================
    # TOTAL
    # ==========================================================
    total = (
        cpu["price"] + gpu["price"] + ram["price"] + ssd["price"] +
        mobo["price"] + psu["price"] + monitor["price"]
    )

    if total > req.budget:
        warnings.append("La configuración supera ligeramente el presupuesto.")

    # ==========================================================
    # ALLOCATION
    # ==========================================================
    allocation = {
        "CPU": cpu["price"],
        "GPU": gpu["price"],
        "RAM": ram["price"],
        "SSD": ssd["price"],
        "Motherboard": mobo["price"],
        "PSU": psu["price"],
        "Monitor": monitor["price"]
    }

    return {
        "profile_description": profile_desc,
        "components": {
            "CPU": cpu,
            "GPU": gpu,
            "RAM": ram,
            "SSD": ssd,
            "Motherboard": mobo,
            "PSU": psu,
            "Monitor": monitor
        },
        "total_price_estimate": total,
        "reasoning": reasoning,
        "warnings": warnings,
        "allocation_estimate": allocation
    }


@app.get("/health")
def health():
    return {"status": "ok"}
