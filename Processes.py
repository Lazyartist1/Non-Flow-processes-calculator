"""Conventions and units used throughout this module:
- Pressure: kPa
- Volume: m^3
- Temperature: K
- Mass: kg (default 1 kg)
- Energies: kJ (note: 1 kPa * m^3 = 1 kJ)

Gas properties are stored as specific (per kg) values where possible
so formulas using mass (kg) work consistently.
"""
from __future__ import annotations

from math import log, pow
from typing import Dict, List, Literal, TypedDict, Optional

ProcessType = Literal["constantVolume", "constantPressure", "isothermal", "adiabatic", "polytropic"]


class ProcessInput(TypedDict, total=False):
    P1: float  # kPa
    V1: float  # m^3
    T1: float  # K
    P2: Optional[float]
    V2: Optional[float]
    T2: Optional[float]
    n: Optional[float]


class ProcessResult(TypedDict):
    P1: float
    V1: float
    T1: float
    P2: float
    V2: float
    T2: float
    W: float
    Q: float
    deltaU: float
    deltaS: float
    pvData: List[Dict[str, float]]
    tsData: List[Dict[str, float]]


# Universal gas constant (J/(mol·K))
R_UNIVERSAL = 8.314462618

# Gas properties. M is given in g/mol for readability; R, Cv, Cp are stored as
# specific values in J/(kg·K) where possible.
GAS_PROPERTIES: Dict[str, Dict[str, float]] = {
    "idealGas": {
        "name": "Ideal Gas (air-like)",
        "M": 28.97,  # g/mol (approx air)
        # We'll compute R_specific and convert molar Cv/Cp to specific
        "Cv_molar": 20.8,  # J/(mol·K) (example)
        "Cp_molar": 29.1,  # J/(mol·K)
    },
    "steam": {
        "name": "Steam (H2O)",
        "M": 18.015,  # g/mol
        "R": 461.5,  # J/(kg·K)
        "Cv": 1410.0,  # J/(kg·K)
        "Cp": 1996.0,  # J/(kg·K)
        "gamma": 1.33,
    },
    "methane": {
        "name": "Methane (CH4)",
        "M": 16.04,  # g/mol
        "R": 518.3,  # J/(kg·K)
        "Cv": 1700.0,
        "Cp": 2220.0,
        "gamma": 1.31,
    },
}


def _ensure_specific_properties():
    """Populate/convert per-kg properties for entries that currently have molar values."""
    for key, props in GAS_PROPERTIES.items():
        M_g = props.get("M")
        if M_g is None:
            continue
        M_kg = M_g / 1000.0
        # Compute R if not present
        if "R" not in props:
            props["R"] = R_UNIVERSAL / M_kg
        # Convert molar Cv/Cp to specific if given
        if "Cv" not in props and "Cv_molar" in props:
            props["Cv"] = props["Cv_molar"] / M_kg
        if "Cp" not in props and "Cp_molar" in props:
            props["Cp"] = props["Cp_molar"] / M_kg
        # Compute gamma if not present and Cp/Cv available
        if "gamma" not in props and props.get("Cv") and props.get("Cp"):
            props["gamma"] = props["Cp"] / props["Cv"]


_ensure_specific_properties()


PROCESS_NAMES: Dict[ProcessType, str] = {
    "constantVolume": "Constant Volume (Isochoric)",
    "constantPressure": "Constant Pressure (Isobaric)",
    "isothermal": "Isothermal",
    "adiabatic": "Adiabatic (Isentropic)",
    "polytropic": "Polytropic",
}


PROCESS_EQUATIONS: Dict[ProcessType, str] = {
    "constantVolume": "V = const, P1/T1 = P2/T2",
    "constantPressure": "P = const, V1/T1 = V2/T2",
    "isothermal": "T = const, P1 V1 = P2 V2",
    "adiabatic": "Q = 0, P V^γ = const",
    "polytropic": "P V^n = const",
}


def _validate_input(input_data: ProcessInput) -> None:
    for name in ("P1", "V1", "T1"):
        if name not in input_data or input_data[name] is None:
            raise ValueError(f"Missing required input: {name}")
        if input_data[name] <= 0:
            raise ValueError(f"{name} must be positive")
    # Optional provided values must also be positive if present
    for opt in ("P2", "V2", "T2"):
        if opt in input_data and input_data[opt] is not None:
            if input_data[opt] <= 0:
                raise ValueError(f"{opt} must be positive if provided")


def calculate_process(process_type: ProcessType, substance: str, input_data: ProcessInput, mass: float = 1.0) -> ProcessResult:
    """Compute final state and energetic quantities for a thermodynamic process.

    Notes:
    - P in kPa, V in m^3, T in K
    - Energies in kJ (P [kPa] * V [m^3] = kJ)
    """
    _validate_input(input_data)
    if mass <= 0:
        raise ValueError("mass must be positive (kg)")

    gas = GAS_PROPERTIES.get(substance)
    if gas is None:
        raise ValueError(f"Unknown substance: {substance}")

    P1 = input_data["P1"]
    V1 = input_data["V1"]
    T1 = input_data["T1"]
    n = input_data.get("n", 1.3)

    P2 = V2 = T2 = 0.0
    W = Q = deltaU = deltaS = 0.0

    # Shortcuts to gas props (validate presence)
    Cv = gas.get("Cv")
    Cp = gas.get("Cp")
    R = gas.get("R")
    if Cv is None or Cp is None or R is None:
        raise ValueError(f"Gas properties incomplete for '{substance}': need Cv, Cp and R")
    # compute gamma safely
    if "gamma" in gas and gas.get("gamma"):
        gamma = float(gas.get("gamma"))
    else:
        if Cv == 0:
            raise ValueError("Invalid gas property: Cv must be non-zero to compute gamma")
        gamma = float(Cp) / float(Cv)

    if process_type == "constantVolume":
        V2 = V1
        T2 = input_data.get("T2", T1 * 1.5)
        if T2 <= 0:
            raise ValueError("Computed T2 must be positive")
        P2 = P1 * (T2 / T1)
        W = 0.0
        deltaU = mass * Cv * (T2 - T1) / 1000.0
        Q = deltaU
        deltaS = mass * Cv * log(T2 / T1) / 1000.0

    elif process_type == "constantPressure":
        P2 = P1
        T2 = input_data.get("T2", T1 * 1.5)
        if T2 <= 0:
            raise ValueError("Computed T2 must be positive")
        V2 = V1 * (T2 / T1)
        W = P1 * (V2 - V1)  # kJ (kPa·m^3)
        deltaU = mass * Cv * (T2 - T1) / 1000.0
        Q = mass * Cp * (T2 - T1) / 1000.0
        deltaS = mass * Cp * log(T2 / T1) / 1000.0

    elif process_type == "isothermal":
        T2 = T1
        V2 = input_data.get("V2", V1 * 2.0)
        if V2 <= 0:
            raise ValueError("V2 must be positive for isothermal process")
        P2 = P1 * V1 / V2
        # Work for isothermal ideal gas: W = P1 V1 ln(V2/V1)
        if V2 / V1 <= 0:
            raise ValueError("Volume ratio must be positive for log calculation")
        W = P1 * V1 * log(V2 / V1)
        deltaU = 0.0
        Q = W
        deltaS = mass * R * log(V2 / V1) / 1000.0

    elif process_type == "adiabatic":
        V2 = input_data.get("V2", V1 * 2.0)
        if V2 <= 0:
            raise ValueError("V2 must be positive for adiabatic process")
        P2 = P1 * pow(V1 / V2, gamma)
        T2 = T1 * pow(V1 / V2, gamma - 1.0)
        Q = 0.0
        deltaU = mass * Cv * (T2 - T1) / 1000.0
        # For an adiabatic closed process: W = -ΔU
        W = -deltaU
        deltaS = 0.0

    elif process_type == "polytropic":
        V2 = input_data.get("V2", V1 * 2.0)
        if V2 <= 0:
            raise ValueError("V2 must be positive for polytropic process")
        # If n == 1, polytropic -> isothermal. Use isothermal formulas.
        if abs(n - 1.0) < 1e-9:
            # isothermal limit
            T2 = T1
            P2 = P1 * V1 / V2
            if V2 / V1 <= 0:
                raise ValueError("Volume ratio must be positive for log calculation")
            W = P1 * V1 * log(V2 / V1)
            deltaU = 0.0
            Q = W
            deltaS = mass * R * log(V2 / V1) / 1000.0
        else:
            P2 = P1 * pow(V1 / V2, n)
            T2 = T1 * pow(V1 / V2, n - 1.0)
            W = (P2 * V2 - P1 * V1) / (1.0 - n)
            deltaU = mass * Cv * (T2 - T1) / 1000.0
            Q = deltaU + W
            # entropy change: ΔS = m*Cv*ln(T2/T1) + m*R*ln(V2/V1)
            if T2 / T1 <= 0 or V2 / V1 <= 0:
                raise ValueError("Temperature and volume ratios must be positive for log calculation")
            deltaS = (mass * Cv * log(T2 / T1) + mass * R * log(V2 / V1)) / 1000.0

    else:
        raise ValueError(f"Unknown process type: {process_type}")

    pv_data = generate_pv_data(process_type, P1, V1, P2, V2, gamma, n)
    ts_data = generate_ts_data(process_type, T1, T2, deltaS, substance, mass)

    result: ProcessResult = {
        "P1": P1,
        "V1": V1,
        "T1": T1,
        "P2": P2,
        "V2": V2,
        "T2": T2,
        "W": W,
        "Q": Q,
        "deltaU": deltaU,
        "deltaS": deltaS,
        "pvData": pv_data,
        "tsData": ts_data,
    }

    return result


def generate_pv_data(process_type: ProcessType, P1: float, V1: float, P2: float, V2: float, gamma: float, n: float) -> List[Dict[str, float]]:
    points: List[Dict[str, float]] = []
    num_points = 50
    Vmin = min(V1, V2)
    Vmax = max(V1, V2)

    for i in range(num_points + 1):
        t = i / num_points
        if process_type == "constantVolume":
            V = V1
            P = P1 + t * (P2 - P1)
        elif process_type == "constantPressure":
            V = Vmin + t * (Vmax - Vmin)
            P = P1
        elif process_type == "isothermal":
            V = Vmin + t * (Vmax - Vmin)
            P = P1 * V1 / V
        elif process_type == "adiabatic":
            V = Vmin + t * (Vmax - Vmin)
            P = P1 * pow(V1 / V, gamma)
        elif process_type == "polytropic":
            V = Vmin + t * (Vmax - Vmin)
            P = P1 * pow(V1 / V, n)
        else:
            V = Vmin + t * (Vmax - Vmin)
            P = P1
        points.append({"P": P, "V": V})

    return points


def generate_ts_data(process_type: ProcessType, T1: float, T2: float, deltaS: float, substance: str, mass: float) -> List[Dict[str, float]]:
    points: List[Dict[str, float]] = []
    num_points = 50
    gas = GAS_PROPERTIES.get(substance)
    if gas is None:
        raise ValueError(f"Unknown substance for TS generation: {substance}")
    Cv = gas.get("Cv")
    Cp = gas.get("Cp")
    S1 = 0.0

    for i in range(num_points + 1):
        t = i / num_points
        if process_type == "constantVolume":
            T = T1 + t * (T2 - T1)
            if T / T1 <= 0:
                raise ValueError("Temperature ratio must be positive for entropy log calculation")
            S = S1 + mass * Cv * log(T / T1) / 1000.0
        elif process_type == "constantPressure":
            T = T1 + t * (T2 - T1)
            if T / T1 <= 0:
                raise ValueError("Temperature ratio must be positive for entropy log calculation")
            S = S1 + mass * Cp * log(T / T1) / 1000.0
        elif process_type == "isothermal":
            T = T1
            S = S1 + t * deltaS
        elif process_type == "adiabatic":
            T = T1 + t * (T2 - T1)
            S = S1
        elif process_type == "polytropic":
            T = T1 + t * (T2 - T1)
            S = S1 + t * deltaS
        else:
            T = T1 + t * (T2 - T1)
            S = S1 + t * deltaS
        points.append({"T": T, "S": S})

    return points


__all__ = [
    "GAS_PROPERTIES",
    "calculate_process",
    "generate_pv_data",
    "generate_ts_data",
    "PROCESS_NAMES",
    "PROCESS_EQUATIONS",
]
