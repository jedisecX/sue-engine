"""Named equations Sue can talk about and store as kind=eq traces."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Equation:
    id: str
    name: str
    domain: str
    form: str
    variables: dict[str, str]
    note: str
    aliases: tuple[str, ...] = ()

LIBRARY = [
    Equation("zscore", "standard score", "psychometrics", "z = (x - μ) / σ", {"z": "distance from the mean in σ units", "x": "raw score", "μ": "mean", "σ": "standard deviation"}, "Places a score on a common scale.", ("z-score", "sigma")),
    Equation("pearson", "Pearson correlation", "psychometrics", "r = cov(x,y)/(sx sy)", {"r": "linear association [-1,1]", "x": "variable one", "y": "variable two"}, "Linear association, not causation.", ("correlation", "pearson")),
    Equation("cronbach", "Cronbach alpha", "psychometrics", "α = (k/(k-1)) (1 - Σσi² / σt²)", {"α": "internal consistency", "k": "items", "σi": "item variance", "σt": "total variance"}, "Reliability, not validity.", ("alpha", "reliability", "cronbach")),
    Equation("irt2pl", "2PL item response", "psychometrics", "P(θ) = 1 / (1 + exp(-a(θ-b)))", {"P": "P(endorse)", "θ": "latent trait", "a": "discrimination", "b": "difficulty"}, "θ is a model parameter.", ("irt", "rasch", "theta")),
    Equation("spearman_g", "Spearman two-factor", "psychometrics", "xi = g + si + ei", {"xi": "observed test", "g": "shared factor", "si": "specific", "ei": "error"}, "A factor model, not a particle.", ("g-factor", "spearman")),
    Equation("schrodinger", "time-dependent Schrödinger", "quantum", "iħ ∂ψ/∂t = Ĥψ", {"i": "imaginary unit", "ħ": "reduced Planck", "ψ": "wavefunction", "t": "time", "Ĥ": "Hamiltonian"}, "Closed-system linear evolution.", ("schrodinger", "wavefunction", "hamiltonian")),
    Equation("born", "Born rule", "quantum", "P = |ψ|²", {"P": "probability density", "ψ": "wavefunction"}, "Amplitudes to frequencies.", ("born",)),
    Equation("heisenberg", "Kennard uncertainty", "quantum", "Δx Δp ≥ ħ/2", {"Δx": "position spread", "Δp": "momentum spread", "ħ": "reduced Planck"}, "State spreads, not clumsy tools.", ("uncertainty", "heisenberg", "hbar")),
    Equation("planck", "Planck relation", "quantum", "E = hν", {"E": "quantum energy", "h": "Planck constant", "ν": "frequency"}, "Photon energy tracks frequency.", ("planck", "photon")),
    Equation("debroglie", "de Broglie wavelength", "quantum", "λ = h / p", {"λ": "wavelength", "h": "Planck constant", "p": "momentum"}, "Matter has a wave number.", ("de broglie", "wavelength")),
    Equation("commutator", "canonical commutator", "quantum", "[x, p] = iħ", {"x": "position operator", "p": "momentum operator", "ħ": "reduced Planck"}, "Why both spreads cannot vanish.", ("commutator",)),
    Equation("newton2", "Newton second law", "physics", "F = dp/dt", {"F": "net force", "p": "momentum", "t": "time"}, "Force is change of momentum.", ("newton", "force")),
    Equation("emc2", "mass-energy", "physics", "E = mc²", {"E": "rest energy", "m": "rest mass", "c": "speed of light"}, "Mass is a form of energy.", ("einstein", "mass energy")),
    Equation("kinetic", "kinetic energy", "physics", "K = 1/2 m v²", {"K": "kinetic energy", "m": "mass", "v": "speed"}, "Energy of motion.", ("kinetic",)),
    Equation("wave", "wave speed", "physics", "c = f λ", {"c": "wave speed", "f": "frequency", "λ": "wavelength"}, "Periodic wave in a linear medium.", ("wave speed",)),
    Equation("entropy", "Clausius entropy", "physics", "dS = δQ_rev / T", {"S": "entropy", "Q": "heat", "T": "temperature"}, "Reversible heat over temperature.", ("entropy", "clausius", "thermodynamics")),
    Equation("shannon", "Shannon entropy", "psychometrics", "H = -Σ pi log pi", {"H": "source uncertainty", "pi": "symbol probability"}, "Information uncertainty. Analogous to Boltzmann, not identical.", ("shannon", "information", "entropy")),
    Equation("coulomb", "Coulomb force", "physics", "F = k q1 q2 / r²", {"F": "force", "q": "charge", "r": "separation"}, "Inverse-square point charges.", ("coulomb", "charge")),
    Equation("maxwell_faraday", "Faraday-Maxwell", "physics", "∇ × E = -∂B/∂t", {"E": "electric field", "B": "magnetic field", "t": "time"}, "Changing B makes circling E.", ("maxwell", "faraday")),
]

def find(text: str) -> list[Equation]:
    raw = text.lower()
    hits = []
    for eq in LIBRARY:
        score = 0
        if eq.id in raw or eq.name.lower() in raw:
            score += 3
        for a in eq.aliases:
            if a in raw:
                score += 2
        if eq.domain in raw:
            score += 1
        if score:
            hits.append((score, eq))
    hits.sort(key=lambda x: -x[0])
    return [eq for _, eq in hits[:4]]

def explain(eq: Equation, focus: str = "") -> str:
    parts = [f"{s} = {m}" for s, m in eq.variables.items()]
    return f"{eq.name} ({eq.domain}): {eq.form}. " + "; ".join(parts) + ". " + eq.note

def bridge(a: Equation, b: Equation) -> str | None:
    if a.id == b.id:
        return None
    shared = set(x.lower() for x in a.variables) & set(x.lower() for x in b.variables)
    wa = (a.note + " " + a.name + " " + " ".join(a.variables.values())).lower()
    wb = (b.note + " " + b.name + " " + " ".join(b.variables.values())).lower()
    for tok in ("entropy", "energy", "wave", "probability", "mass", "time", "force"):
        if tok in wa and tok in wb:
            shared.add(tok)
    if not shared and a.domain == b.domain:
        return f"{a.name} and {b.name} live in {a.domain}; they do not share a symbol here"
    if not shared:
        return None
    return f"bridge {a.id}+{b.id}: shared marks {', '.join(sorted(shared)[:4])}. that is a vocabulary overlap, not a derived law"

def recall_lines(text: str) -> list[str]:
    eqs = find(text)
    if not eqs:
        return []
    out = [explain(eqs[0], text)]
    if len(eqs) >= 2:
        br = bridge(eqs[0], eqs[1])
        if br:
            out.append(br)
    return out
