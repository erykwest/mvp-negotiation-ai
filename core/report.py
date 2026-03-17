PHASE_LABELS = {
    "ALIGNMENT": "ROUND 1 · ALIGNMENT",
    "NEGOTIATION": "ROUND 2 · NEGOTIATION",
    "CLOSING": "ROUND 3 · CLOSING",
}

def build_report(data: dict, results: dict) -> str:
    company = data.get("company", {})
    candidate = data.get("candidate", {})

    lines = []
    lines.append("# Negotiation Report")
    lines.append("")
    lines.append("## Oggetto della negoziazione")
    lines.append(data.get("job_description", "_Nessun contenuto_"))
    lines.append("")
    lines.append("## Parti")
    lines.append(f"- Azienda: **{company.get('name', '-')}**")
    lines.append(f"- Candidato: **{candidate.get('name', '-')}**")
    lines.append("")

    for phase in ["ALIGNMENT", "NEGOTIATION", "CLOSING"]:
        if phase not in results:
            continue

        round_content = results[phase]

        lines.append("---")
        lines.append("")
        lines.append(f"## {PHASE_LABELS[phase]}")
        lines.append("")
        lines.append("### Posizione azienda")
        lines.append(round_content.get("company", "_Nessun contenuto_"))
        lines.append("")
        lines.append("### Posizione candidato")
        lines.append(round_content.get("candidate", "_Nessun contenuto_"))
        lines.append("")
        lines.append("### Sintesi")
        lines.append(round_content.get("summary", "_Nessun contenuto_"))
        lines.append("")

        if phase in ["NEGOTIATION", "CLOSING"] and data.get("dynamic_topics"):
            lines.append("### Topic aggiuntivi round 2")
            for t in data["dynamic_topics"]:
                lines.append(f"- [{t['section']}] {t['title']}")
            lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## Stato finale")
    lines.append("Report generato dal prototipo human-in-the-loop.")

    return "\n".join(lines)