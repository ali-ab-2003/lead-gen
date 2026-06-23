"""AI enrichment + scoring via the Groq API (free tier).

For each lead we ask the model to return strict JSON with:
  - lead_score (0-100): how good a prospect for web/digital services
  - score_reason: one short sentence
  - owner_name: inferred decision-maker, ONLY if reasonably supported (else "")
  - outreach_draft: a short, personalised first-contact message

The stage is fully optional: if GROQ_API_KEY is missing it logs and returns the
leads untouched, so the pipeline still completes for free.
"""
from __future__ import annotations

import json
import logging
import time

from .config import Settings, env
from .models import Lead

log = logging.getLogger(__name__)

_SYSTEM = (
    "You are a B2B sales analyst helping a web-design agency qualify local "
    "businesses that currently have NO website. Always reply with a single "
    "valid JSON object and nothing else."
)


def _prompt(lead: Lead, persona: str) -> str:
    return f"""Persona of the sender (who is reaching out):
{persona or "A small agency that builds affordable websites for local businesses."}

Business to evaluate (it has no website):
- Name: {lead.name}
- Category: {lead.category}
- Area: {lead.area}
- Address: {lead.address}
- Phone: {lead.phone or "unknown"}
- Email: {lead.email or "unknown"}
- Rating: {lead.rating if lead.rating is not None else "unknown"} \
({lead.reviews_count if lead.reviews_count is not None else "?"} reviews)
- Known contact source: {lead.source_of_contact or "none"}

Return JSON with exactly these keys:
{{
  "lead_score": <integer 0-100, higher = better prospect for a new website>,
  "score_reason": "<one short sentence>",
  "owner_name": "<the likely owner/decision-maker's name, or empty string if not inferable>",
  "outreach_draft": "<a 2-3 sentence friendly first-contact message, personalised to this business>"
}}
Do not invent an owner name; use an empty string unless it is clearly implied."""


def _parse(content: str) -> dict:
    content = content.strip()
    # Strip code fences if the model added them.
    if content.startswith("```"):
        content = content.strip("`")
        content = content.split("\n", 1)[-1] if "\n" in content else content
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(content[start : end + 1])


def _apply(lead: Lead, data: dict) -> None:
    score = data.get("lead_score")
    try:
        lead.lead_score = max(0, min(100, int(score)))
    except (TypeError, ValueError):
        lead.lead_score = None
    lead.score_reason = str(data.get("score_reason", "")).strip()
    owner = str(data.get("owner_name", "")).strip()
    if owner and not lead.owner_name:
        lead.owner_name = owner
    lead.outreach_draft = str(data.get("outreach_draft", "")).strip()


DEFAULT_PERSONA = (
    "A small agency that builds affordable, fast websites for local businesses "
    "that don't yet have one. Friendly, concise, no hard sell."
)


def _lead_facts(lead: dict) -> str:
    """Human-readable summary of everything we know about a lead (dict form)."""
    def g(k, default="unknown"):
        v = lead.get(k)
        return v if v not in (None, "") else default
    return (
        f"- Name: {g('name')}\n"
        f"- Category: {g('category')}\n"
        f"- Area: {g('area')}\n"
        f"- Address: {g('address')}\n"
        f"- Phone: {g('phone')}\n"
        f"- Email: {g('email')}\n"
        f"- Owner/decision-maker: {g('owner_name')}\n"
        f"- Google rating: {g('rating')} ({g('reviews_count', '?')} reviews)\n"
        f"- They currently have NO website.\n"
        f"- Why they're a good prospect: {g('score_reason', 'n/a')}"
    )


def _chat(messages: list[dict], max_tokens: int = 700) -> str:
    api_key = env("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set.")
    from groq import Groq
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model=env("GROQ_MODEL", "llama-3.3-70b-versatile"),
        messages=messages,
        temperature=0.6,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content.strip()


def generate_call_script(lead: dict, persona: str = DEFAULT_PERSONA) -> str:
    """A cold-call script tailored to one business. Phone is the main channel."""
    return _chat([
        {"role": "system", "content":
            "You write natural, concise cold-call scripts for a salesperson. "
            "Use short spoken sentences, include a friendly opener, a reason for "
            "calling tied to the specific business, one or two likely objections "
            "with responses, and a clear ask (e.g. book a quick chat). Plain text, "
            "labelled sections. No emojis."},
        {"role": "user", "content":
            f"Sender/persona reaching out:\n{persona}\n\n"
            f"Business to call:\n{_lead_facts(lead)}\n\n"
            "Write the call script."},
    ])


def generate_email_draft(lead: dict, persona: str = DEFAULT_PERSONA) -> str:
    """A short outreach email tailored to one business (subject + body)."""
    return _chat([
        {"role": "system", "content":
            "You write short, personalised B2B outreach emails. Start with a line "
            "'Subject: ...' then a blank line then the body. Keep it under 130 words, "
            "specific to the business, warm and low-pressure, with one clear call to "
            "action. Plain text. No emojis."},
        {"role": "user", "content":
            f"Sender/persona:\n{persona}\n\n"
            f"Business to email:\n{_lead_facts(lead)}\n\n"
            "Write the email."},
    ])


def ai_enrich_leads(leads: list[Lead], settings: Settings) -> list[Lead]:
    api_key = env("GROQ_API_KEY")
    if not api_key:
        log.warning("GROQ_API_KEY not set; skipping AI enrichment stage.")
        return leads

    # Imported here so the dependency is only needed when the stage runs.
    from groq import Groq

    client = Groq(api_key=api_key)
    model = env("GROQ_MODEL", "llama-3.3-70b-versatile")
    log.info("AI-enriching %d leads via Groq model %s...", len(leads), model)

    ok = 0
    for lead in leads:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": _SYSTEM},
                    {"role": "user", "content": _prompt(lead, settings.outreach_persona)},
                ],
                temperature=0.4,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            _apply(lead, _parse(resp.choices[0].message.content))
            ok += 1
        except Exception as exc:  # noqa: BLE001 - never let one lead kill the run
            log.warning("AI enrichment failed for %r: %s", lead.name, exc)
        time.sleep(0.6)  # gentle pacing for the free-tier rate limit

    log.info("AI enrichment succeeded for %d/%d leads.", ok, len(leads))
    return leads
