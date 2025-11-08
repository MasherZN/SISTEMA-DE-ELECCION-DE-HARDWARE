# -------------------------------------------------------------
# MOTOR DE INFERENCIA - SISTEMA EXPERTO EN HARDWARE
# -------------------------------------------------------------
# Este sistema experto usa un motor de inferencia de encadenamiento
# hacia adelante. A partir de hechos iniciales (perfil, presupuesto),
# aplica reglas basadas en conocimiento para deducir la mejor
# configuración de hardware posible.
# -------------------------------------------------------------

from fastapi import FastAPI
from pydantic import BaseModel
import json, random, traceback
from pathlib import Path
from typing import Optional

# -------------------- CARGA DE BASE DE CONOCIMIENTO --------------------
DATA_PATH = Path(__file__).parent / "base_knowledge.json"

try:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        knowledge = json.load(f)
except Exception as e:
    raise RuntimeError(f"Error al cargar la base de conocimiento: {e}")

# -------------------- DEFINICIÓN DE LA API --------------------
app = FastAPI(title="Motor de Inferencia - Sistema Experto en Hardware", version="3.0")

class UserRequest(BaseModel):
    profile: Optional[str] = ""
    budget: float

# -------------------- MOTOR DE INFERENCIA --------------------
class InferenceEngine:
    def __init__(self, knowledge):
        self.knowledge = knowledge
        self.facts = {}
        self.rules = []

    def add_fact(self, key, value):
        self.facts[key] = value

    def add_rule(self, condition_fn, action_fn, name=""):
        self.rules.append({"condition": condition_fn, "action": action_fn, "name": name})

    def infer(self):
        applied = True
        while applied:
            applied = False
            for rule in self.rules:
                if rule["condition"](self.facts) and not self.facts.get(f"_applied_{rule['name']}", False):
                    rule["action"](self.facts)
                    self.facts[f"_applied_{rule['name']}"] = True
                    applied = True
        return self.facts

# -------------------- FUNCIONES AUXILIARES --------------------
def choose_best(components, max_budget, percent):
    max_price = max_budget * percent * 1.15
    valid = [c for c in components if c["price"] <= max_price]
    if not valid:
        return min(components, key=lambda c: c["price"])
    valid.sort(key=lambda x: (x["performance_score"], -x["price"]), reverse=True)
    return valid[0]

def choose_mobo(mobos, cpu):
    same = [m for m in mobos if m["socket"] == cpu["socket"]]
    return random.choice(same or mobos)

def choose_ram_and_ssd(rams, ssds, profile_info, budget, ram_p, ssd_p):
    ram = choose_best([r for r in rams if r["size_gb"] >= profile_info["min_ram_gb"]], budget, ram_p)
    ssd = choose_best([s for s in ssds if s["size_gb"] >= profile_info["min_ssd_gb"]], budget, ssd_p)
    return ram, ssd

def choose_monitor(monitors, profile, budget):
    if profile == "gamer":
        filt = [m for m in monitors if m["hz"] >= 120]
        return random.choice(filt or monitors)
    if profile == "disenador":
        filt = [m for m in monitors if m["res"] in ["1440p", "4K"]]
        return random.choice(filt or monitors)
    return min(monitors, key=lambda m: abs(m["price"] - budget * 0.1))

def choose_psu(psus, gpu):
    pwr = gpu.get("power_w", 100)
    if pwr <= 100:
        return psus[0]
    elif pwr <= 160:
        return psus[1] if len(psus) > 1 else psus[0]
    elif pwr <= 200:
        return psus[2] if len(psus) > 2 else psus[-1]
    else:
        return psus[-1]

# -------------------- CONSTRUCCIÓN DE REGLAS --------------------
def build_rules(engine: InferenceEngine, knowledge):
    profiles = knowledge["profiles"]
    comps = knowledge["components"]
    alloc = knowledge["rules_meta"]["allocation_percentages"]

    # Regla 1: detectar perfil según presupuesto
    def cond_detect(f): return "detected_profile" not in f
    def act_detect(f):
        p = f.get("profile", "").lower()
        b = f["budget"]
        if p in profiles and p != "ninguno":
            f["detected_profile"] = p
        elif b < 10000: f["detected_profile"] = "ofimatico"
        elif b < 20000: f["detected_profile"] = "estudiante"
        elif b < 30000: f["detected_profile"] = "programador"
        elif b < 40000: f["detected_profile"] = "gamer"
        else: f["detected_profile"] = "disenador"

    # Regla 2: elegir CPU
    def cond_cpu(f): return "cpu" not in f and "detected_profile" in f
    def act_cpu(f):
        prof = f["detected_profile"]
        f["cpu"] = choose_best(comps["cpus"], f["budget"], alloc[prof]["cpu"])

    # Regla 3: elegir GPU
    def cond_gpu(f): return "gpu" not in f and "detected_profile" in f
    def act_gpu(f):
        prof = f["detected_profile"]
        pinfo = profiles[prof]
        if not pinfo["gpu_required"]:
            f["gpu"] = next((g for g in comps["gpus"] if g["level"] == "integrated"), comps["gpus"][0])
        else:
            f["gpu"] = choose_best(comps["gpus"], f["budget"], alloc[prof]["gpu"])

    # Regla 4: RAM y SSD
    def cond_mem(f): return "ram" not in f and "ssd" not in f and "detected_profile" in f
    def act_mem(f):
        prof = f["detected_profile"]
        pinfo = profiles[prof]
        f["ram"], f["ssd"] = choose_ram_and_ssd(comps["rams"], comps["ssds"], pinfo,
                                                f["budget"], alloc[prof]["ram"], alloc[prof]["ssd"])

    # Regla 5: Motherboard
    def cond_mobo(f): return "motherboard" not in f and "cpu" in f
    def act_mobo(f): f["motherboard"] = choose_mobo(comps["motherboards"], f["cpu"])

    # Regla 6: PSU
    def cond_psu(f): return "psu" not in f and "gpu" in f
    def act_psu(f): f["psu"] = choose_psu(comps["psus"], f["gpu"])

    # Regla 7: Monitor
    def cond_mon(f): return "monitor" not in f and "detected_profile" in f
    def act_mon(f): f["monitor"] = choose_monitor(comps["monitors"], f["detected_profile"], f["budget"])

    # Añadir reglas al motor
    engine.add_rule(cond_detect, act_detect, "detectar_perfil")
    engine.add_rule(cond_cpu, act_cpu, "elegir_cpu")
    engine.add_rule(cond_gpu, act_gpu, "elegir_gpu")
    engine.add_rule(cond_mem, act_mem, "elegir_memoria")
    engine.add_rule(cond_mobo, act_mobo, "elegir_motherboard")
    engine.add_rule(cond_psu, act_psu, "elegir_fuente")
    engine.add_rule(cond_mon, act_mon, "elegir_monitor")

# -------------------- ENDPOINT PRINCIPAL --------------------
@app.post("/recommend")
def recommend(req: UserRequest):
    try:
        engine = InferenceEngine(knowledge)
        engine.add_fact("profile", (req.profile or "").lower())
        engine.add_fact("budget", float(req.budget))

        build_rules(engine, knowledge)
        facts = engine.infer()

        prof = facts["detected_profile"]
        total = sum(facts[c]["price"] for c in ["cpu","gpu","ram","ssd","motherboard","psu","monitor"])
        alloc = knowledge["rules_meta"]["allocation_percentages"][prof]

        return {
            "profile": prof,
            "budget_input": req.budget,
            "components": {
                "CPU": facts["cpu"],
                "GPU": facts["gpu"],
                "RAM": facts["ram"],
                "SSD": facts["ssd"],
                "Motherboard": facts["motherboard"],
                "PSU": facts["psu"],
                "Monitor": facts["monitor"]
            },
            "total_price_estimate": round(total, 2),
            "exceeds_budget": total > req.budget,
            "allocation_estimate": alloc,
            "note": f"Perfil deducido automáticamente mediante motor de inferencia: {prof.upper()}."
        }

    except Exception as e:
        print("ERROR INTERNO:", traceback.format_exc())
        return {"error": "Error interno del servidor", "detail": str(e)}

# -------------------- HEALTH CHECK --------------------
@app.get("/health")
def health():
    return {"status": "ok"}
