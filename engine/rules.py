# engine/rules.py
"""
Reglas declarativas y utilidades para el motor de inferencia.
Estas reglas son pequeñas funciones/expresiones que representan
la "base de conocimiento lógica" del sistema.
"""

from typing import Dict, Any

def auto_select_profile_by_budget(budget: float) -> str:
    if budget < 10000:
        return "ofimatico"
    if budget < 20000:
        return "estudiante"
    if budget < 30000:
        return "programador"
    if budget < 40000:
        return "gamer"
    return "disenador"

def merge_profiles(p1: str, p2: str, profiles: Dict[str, Any]) -> Dict[str, Any]:
    """
    Devuelve un profile_info agregado a partir de dos perfiles.
    """
    if p2 == "ninguno" or p2 not in profiles:
        return profiles[p1]
    A = profiles[p1]
    B = profiles[p2]
    # cpu_level orden: low < mid < high < enthusiast
    order = {"low": 0, "mid": 1, "high": 2, "enthusiast": 3}
    cpu_level = A["cpu_level"] if order.get(A["cpu_level"],0) >= order.get(B["cpu_level"],0) else B["cpu_level"]
    merged = {
        "description": f"Combina {p1} + {p2}",
        "min_ram_gb": max(A["min_ram_gb"], B["min_ram_gb"]),
        "min_ssd_gb": max(A["min_ssd_gb"], B["min_ssd_gb"]),
        "gpu_required": A["gpu_required"] or B["gpu_required"],
        "cpu_level": cpu_level
    }
    return merged

def allocation_for_profile(profile: str, rules_meta: Dict[str, Any]) -> Dict[str, float]:
    return rules_meta.get("allocation_percentages", {}).get(profile, rules_meta.get("allocation_percentages", {}).get("estudiante", {}))

def estimate_power_requirement(cpu: Dict[str,Any], gpu: Dict[str,Any]) -> int:
    """
    Estima la potencia necesaria (W) aproximada para el sistema.
    """
    cpu_tdp = cpu.get("tdp", 65) if cpu else 65
    gpu_power = gpu.get("power_w", 0) if gpu else 0
    # margen de seguridad + consumos de otros componentes
    return int(cpu_tdp + gpu_power + 150)
