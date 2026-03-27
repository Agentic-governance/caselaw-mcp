"""Legal document generation tool."""

from __future__ import annotations


ALLOWED_DOC_TYPES = {
    "takedown_notice",
    "cease_desist",
    "legal_opinion",
    "contract_clause",
}


def _context_value(context: dict[str, str], key: str, fallback: str = "N/A") -> str:
    value = context.get(key, fallback)
    if value is None:
        return fallback
    return str(value)


def generate_legal_draft(doc_type: str, jurisdiction: str, context: dict) -> str:
    """Generate a concise markdown legal draft for the requested document type."""
    if doc_type not in ALLOWED_DOC_TYPES:
        allowed = ", ".join(sorted(ALLOWED_DOC_TYPES))
        raise ValueError(f"Unsupported doc_type '{doc_type}'. Use one of: {allowed}")

    if not isinstance(context, dict):
        raise ValueError("context must be a dict")

    rights_holder = _context_value(context, "rights_holder")
    respondent = _context_value(context, "respondent")
    work_description = _context_value(context, "work_description")
    basis = _context_value(context, "basis")

    title_map = {
        "takedown_notice": "Takedown Notice Draft",
        "cease_desist": "Cease and Desist Draft",
        "legal_opinion": "Legal Opinion Draft",
        "contract_clause": "Contract Clause Draft",
    }

    header = [
        f"# {title_map[doc_type]}",
        "",
        f"- Jurisdiction: {jurisdiction}",
        f"- Rights Holder: {rights_holder}",
        f"- Respondent: {respondent}",
        "",
    ]

    if doc_type == "takedown_notice":
        body = [
            "## Notice",
            f"This notice concerns unauthorized distribution of {work_description}.",
            f"The legal basis asserted is {basis}.",
            "Please remove or disable access to the identified material promptly and preserve access logs.",
        ]
    elif doc_type == "cease_desist":
        body = [
            "## Demand",
            f"You are requested to cease and desist from further use or distribution of {work_description}.",
            f"This request is grounded in {basis}.",
            "Confirm suspension of infringing activity and provide written assurance of non-repetition.",
        ]
    elif doc_type == "legal_opinion":
        body = [
            "## Preliminary Assessment",
            f"Based on the provided facts, potential exposure exists regarding {work_description}.",
            f"Primary legal basis considered: {basis}.",
            "This draft is a support artifact and should be validated by licensed counsel before external use.",
        ]
    else:
        body = [
            "## Clause",
            f"The counterparty represents and warrants that content related to {work_description} does not infringe third-party rights.",
            f"Upon notice under {basis}, the counterparty shall promptly disable access and cooperate in remediation.",
            "Indemnification applies to losses arising from breach of this clause.",
        ]

    footer = [
        "",
        "## Disclaimer",
        "This draft supports legal workflow and is not a final legal opinion.",
    ]

    return "\n".join(header + body + footer)
