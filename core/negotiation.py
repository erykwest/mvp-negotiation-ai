from core.llm_client import ask_llm


def format_priorities(priorities: dict, side: str) -> str:
    labels = {
        "salary": "Salary",
        "smart": "Smart work",
        "bonus": "Bonus",
        "car": "Car",
        "benefits": "Benefits",
    }

    lines = []
    for key, label in labels.items():
        value = priorities.get(key, {}).get(side, 3)
        lines.append(f"- {label}: priorità {value}/5")
    return "\n".join(lines)


def build_company_prompt(data: dict, phase: str) -> str:
    company = data["company"]
    candidate = data["candidate"]
    priorities = data.get("priorities", {})

    return f"""
FASE: {phase}

RUOLO:
Sei il negoziatore dell'azienda.
Devi difendere gli interessi dell'azienda senza chiudere la porta a un accordo ragionevole.

CONTESTO COMUNE:
{data["job_description"]}

DATI AZIENDA:
- Nome: {company["name"]}
- Salary: {company["salary"]}
- Smart: {company["smart"]}
- Bonus: {company["bonus"]}
- Car: {company["car"]}
- Benefits: {company["benefits"]}

RICHIESTE CANDIDATO:
- Salary: {candidate["salary"]}
- Smart: {candidate["smart"]}
- Bonus: {candidate["bonus"]}
- Car: {candidate["car"]}
- Benefits: {candidate["benefits"]}

PRIORITÀ AZIENDA:
{format_priorities(priorities, "company")}

PRIORITÀ CANDIDATO:
{format_priorities(priorities, "candidate")}

ISTRUZIONI:
- Scrivi in modo sintetico e professionale.
- Evidenzia cosa è accettabile, cosa è negoziabile e cosa è critico.
- Dai più peso ai topic con priorità 4 o 5.
- Accetta più facilmente compromessi sui topic con priorità 1 o 2.
- Non inventare dati non presenti.
- Massimo 250 parole.
""".strip()


def build_candidate_prompt(data: dict, phase: str) -> str:
    company = data["company"]
    candidate = data["candidate"]
    priorities = data.get("priorities", {})

    return f"""
FASE: {phase}

RUOLO:
Sei il negoziatore del candidato.
Devi massimizzare il valore complessivo dell'offerta senza rompere inutilmente la trattativa.

CONTESTO COMUNE:
{data["job_description"]}

DATI CANDIDATO:
- Nome: {candidate["name"]}
- Salary: {candidate["salary"]}
- Smart: {candidate["smart"]}
- Bonus: {candidate["bonus"]}
- Car: {candidate["car"]}
- Benefits: {candidate["benefits"]}

OFFERTA AZIENDA:
- Salary: {company["salary"]}
- Smart: {company["smart"]}
- Bonus: {company["bonus"]}
- Car: {company["car"]}
- Benefits: {company["benefits"]}

PRIORITÀ AZIENDA:
{format_priorities(priorities, "company")}

PRIORITÀ CANDIDATO:
{format_priorities(priorities, "candidate")}

ISTRUZIONI:
- Scrivi in modo sintetico e professionale.
- Evidenzia cosa è accettabile, cosa è negoziabile e cosa è critico.
- Dai più peso ai topic con priorità 4 o 5.
- Accetta più facilmente compromessi sui topic con priorità 1 o 2.
- Non inventare dati non presenti.
- Massimo 250 parole.
""".strip()


def build_summary_prompt(
    phase: str, company_response: str, candidate_response: str
) -> str:
    return f"""
FASE: {phase}

Sei un analista neutrale.
Leggi le due posizioni e produci SOLO un report markdown strutturato.

POSIZIONE AZIENDA:
{company_response}

POSIZIONE CANDIDATO:
{candidate_response}

OUTPUT OBBLIGATORIO:

## Obiettivo del round
(max 2 righe)

## Punti allineati
- ...

## Punti in conflitto
- ...

## Concessioni / aperture azienda
- ...

## Concessioni / aperture candidato
- ...

## RFI / chiarimenti necessari
- ...

## Prossima mossa consigliata
(max 3 righe)

REGOLE:
- niente introduzioni
- niente saluti
- niente testo narrativo lungo
- massimo 180 parole
""".strip()

def safe_ask(prompt: str) -> str:
    try:
        return ask_llm(prompt)
    except Exception as exc:
        return f"ERRORE LLM: {exc}"


def run_rounds(data: dict) -> dict:
    phases = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]
    results = {}

    for phase in phases:
        company_prompt = build_company_prompt(data, phase)
        candidate_prompt = build_candidate_prompt(data, phase)

        company_response = safe_ask(company_prompt)
        candidate_response = safe_ask(candidate_prompt)

        summary_prompt = build_summary_prompt(
            phase, company_response, candidate_response
        )
        summary_response = safe_ask(summary_prompt)

        results[phase] = {
            "company": company_response,
            "candidate": candidate_response,
            "summary": summary_response,
        }

    return results
    
def run_single_round(data: dict, phase: str) -> dict:
    company_prompt = build_company_prompt(data, phase)
    candidate_prompt = build_candidate_prompt(data, phase)

    company_response = safe_ask(company_prompt)
    candidate_response = safe_ask(candidate_prompt)

    summary_prompt = build_summary_prompt(
        phase, company_response, candidate_response
    )
    summary_response = safe_ask(summary_prompt)

    return {
        "company": company_response,
        "candidate": candidate_response,
        "summary": summary_response,
    }


def run_rounds(data: dict) -> dict:
    phases = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]
    results = {}

    for phase in phases:
        results[phase] = run_single_round(data, phase)

    return results

def run_rounds(data: dict) -> dict:
    phases = ["ALIGNMENT", "NEGOTIATION", "CLOSING"]
    results = {}

    for phase in phases:
        results[phase] = run_single_round(data, phase)

    return results