import traceback
from typing import Dict, Any, Optional, List
from .rules import merge_profiles, auto_select_profile_by_budget, allocation_for_profile, estimate_power_requirement



# ============================================================
#   PROLOG-style rule documentation
# ============================================================
#
#   choose_best_component/4
#
#   Regla general de decisión:
#
#   
#
#   % Regla: seleccionar componente óptimo dentro del presupuesto
#   choose_best_component(Components, BudgetShare, TotalBudget, Component) :-
#       MaxPrice is TotalBudget * BudgetShare * 1.15,
#       member(Component, Components),
#       Component.price =< MaxPrice,
#       (optional) cumple_minimos(Component),
#       (optional) coincide_con_preferencia(Component, PreferLevel),
#       maximize([performance_score, -price]).
#
#   Ideas clave en lógica:
#   - Filtra por precio máximo permitido
#   - Si hay filtro mínimo → lo aplica
#   - Si no quedan candidatos → fallback al más barato
#   - Ordena por (performance_score DESC, precio ASC)
#   - Si prefer_level existe → prioriza coincidencias
#
# ============================================================
def choose_best_component(components: List[Dict[str,Any]], budget_share: float, total_budget: float, min_filter=None, prefer_level=None) -> Optional[Dict[str,Any]]:
    """
    Selección determinista guiada por reglas.
    """
    try:
        max_price = total_budget * budget_share * 1.15

        # FILTRO DE PRECIOS (regla lógica)
        candidates = [c for c in components if c.get("price", 0) <= max_price]

        # FILTRO ADICIONAL (regla condicional)
        if min_filter:
            candidates = [c for c in candidates if min_filter(c)]

        # SI NO HAY CANDIDATOS, REGLA DE RESCATE (fallback):
        if not candidates:
            return min(components, key=lambda x: x.get("price", float("inf")))

        # ORDENACIÓN (regla de maximización)
        candidates.sort(
            key=lambda x: (x.get("performance_score",0), -x.get("price",0)),
            reverse=True
        )

        # REGLA DE PREFERENCIA POR NIVEL
        if prefer_level:
            for c in candidates:
                if c.get("level") == prefer_level:
                    return c

        return candidates[0]

    except Exception:
        traceback.print_exc()
        return None



# ============================================================
#   choose_compatible_motherboard/2
#
#   Regla de compatibilidad :
#
#   compatible(Mobo, CPU) :- Mobo.socket == CPU.socket.
#   choose_compatible_motherboard(Mobos, CPU, FinalMobo) :-
#       member(Mobo, Mobos),
#       compatible(Mobo, CPU),
#       !.   % determinismo: el primero compatible
#
#   Si no hay ninguno compatible → usa un default.
# ============================================================
def choose_compatible_motherboard(mobos: List[Dict[str,Any]], cpu: Dict[str,Any]) -> Dict[str,Any]:
    if not cpu:
        return mobos[0]

    compatibles = [m for m in mobos if m.get("socket") == cpu.get("socket")]
    return compatibles[0] if compatibles else mobos[0]



# ============================================================
#   choose_gpu/3
#
#   Reglas:
#
#   % Si el perfil NO requiere GPU dedicada → usar integrada.
#   choose_gpu(ProfileInfo, GPUs, GPU) :-
#       ProfileInfo.gpu_required == false,
#       member(GPU, GPUs),
#       GPU.level == integrated, !.
#
#   % Si requiere GPU dedicada → usar regla general
#   choose_gpu(ProfileInfo, GPUs, GPU) :-
#       choose_best_component(GPUs, Share, Budget, GPU).
# ============================================================
def choose_gpu(gpus: List[Dict[str,Any]], profile_info: Dict[str,Any], budget: float, gpu_percent: float) -> Dict[str,Any]:
    if not profile_info.get("gpu_required", False):
        integ = next((g for g in gpus if g.get("level") == "integrated"), None)
        return integ or min(gpus, key=lambda x: x.get("price",0))

    return choose_best_component(gpus, gpu_percent, budget)



# ============================================================
#   choose_ram_and_ssd/4
#
#   Reglas de requisitos mínimos:
#
#   requiere_ram(Comp, Profile) :- Comp.size_gb >= Profile.min_ram_gb.
#   requiere_ssd(Comp, Profile) :- Comp.size_gb >= Profile.min_ssd_gb.
#
#   Si no existen componentes que cumplan → usar todos.
#
# ============================================================
def choose_ram_and_ssd(rams: List[Dict[str,Any]], ssds: List[Dict[str,Any]],
                       profile_info: Dict[str,Any], budget: float,
                       ram_percent: float, ssd_percent: float):

    ram_candidates = [r for r in rams if r["size_gb"] >= profile_info["min_ram_gb"]]
    ssd_candidates = [s for s in ssds if s["size_gb"] >= profile_info["min_ssd_gb"]]

    # fallback si no hay candidatos
    if not ram_candidates:
        ram_candidates = rams
    if not ssd_candidates:
        ssd_candidates = ssds

    # reutiliza regla principal
    ram = choose_best_component(ram_candidates, ram_percent, budget)
    ssd = choose_best_component(ssd_candidates, ssd_percent, budget)

    return ram, ssd



# ============================================================
#   choose_psu/2
#
#   Regla:
#
#   potencia_suficiente(PSU, RequiredW) :-
#       PSU.watt >= RequiredW * 1.1.
#
#   choose_psu(PSUs, PSU) :-
#       member(PSU, PSUs),
#       potencia_suficiente(PSU),
#       !.
#
#   Si ninguna PSU cumple → usar la más grande (última).
# ============================================================
def choose_psu(psus: List[Dict[str,Any]], required_w: int) -> Dict[str,Any]:
    candidates = [p for p in psus if p.get("watt",0) >= int(required_w*1.1)]
    return candidates[0] if candidates else psus[-1]



# ============================================================
#   choose_monitor/3
#
#   Reglas:
#
#   precio_maximo(Precio, Presupuesto) :- Precio =< Presupuesto * 0.20.
#
#   preferencia_gamer(Hz) :- Hz >= 144.
#
#   Para perfil gamer:
#       elegir el monitor con mayor Hz permitido por precio.
#
#   Para otros perfiles:
#       elegir el monitor más barato dentro del 20% del presupuesto.
# ============================================================
def choose_monitor(monitors: List[Dict[str,Any]], profile: str, budget: float) -> Dict[str,Any]:
    max_price = budget * 0.20
    candidates = [m for m in monitors if m.get("price",0) <= max_price]

    if not candidates:
        candidates = monitors

    if profile == "gamer":
        candidates.sort(key=lambda x: (x.get("hz",0), x.get("price",0)), reverse=True)
    else:
        candidates.sort(key=lambda x: x.get("price",0))

    return candidates[0]
