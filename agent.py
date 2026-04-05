from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, TypedDict

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from tavily import TavilyClient

try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIADynamo
except ImportError:
    ChatNVIDIADynamo = None

from data import get_claim_by_id
from rag import query_policies

_tavily_client: TavilyClient | None = None

load_dotenv(Path(__file__).with_name(".env"))


class ModelSpec(TypedDict):
    model_id: str
    label: str
    provider: str
    model_name: str
    api_key_env: str


MODEL_SPECS: dict[str, ModelSpec] = {
    "nvidia/nemotron-3-super-120b-a12b": {
        "model_id": "nvidia/nemotron-3-super-120b-a12b",
        "label": "Nemotron 3 Super 120B (NVIDIA)",
        "provider": "nvidia",
        "model_name": "nvidia/nemotron-3-super-120b-a12b",
        "api_key_env": "NVIDIA_API_KEY",
    },
    "gemini-3-pro-preview": {
        "model_id": "gemini-3-pro-preview",
        "label": "Gemini 3 Pro Preview (Google)",
        "provider": "google",
        "model_name": "gemini-3-pro-preview",
        "api_key_env": "GOOGLE_API_KEY",
    },
    "openai/gpt-oss-120b": {
        "model_id": "openai/gpt-oss-120b",
        "label": "GPT-OSS 120B (Groq)",
        "provider": "groq",
        "model_name": "openai/gpt-oss-120b",
        "api_key_env": "GROQ_API_KEY",
    },
}
MODEL_ALIASES = {
    "gemini-3.1-pro-preview": "gemini-3-pro-preview",
}
MODEL_ORDER = [
    "nvidia/nemotron-3-super-120b-a12b",
    "gemini-3-pro-preview",
    "openai/gpt-oss-120b",
]


def _fmt_currency(amount) -> str:
    if amount is None:
        return "N/A"
    return f"Rs {int(amount):,}"


def _build_claim_summary(claim: dict) -> str:
    status_map = {
        "approved": "APPROVED",
        "denied": "DENIED",
        "partial": "PARTIALLY APPROVED",
        "pending": "PENDING REVIEW",
    }
    status_label = status_map.get(claim["status"], claim["status"].upper())

    lines = [
        f"Claim ID: {claim['claim_id']}",
        f"Status: {status_label}",
        f"Customer: {claim['customer_name']} ({claim['city']}, {claim['state']})",
        f"Plan: {claim['plan_name']}",
        f"Claim Type: {claim['claim_type'].title()} - {claim['sub_type'].replace('_', ' ').title()}",
        f"Provider: {claim['provider']} ({claim['provider_network_status']})",
        f"Date of Service: {claim['date_of_service']}",
        f"Date Submitted: {claim['date_submitted']}",
        f"Date Processed: {claim.get('date_processed') or 'Not yet processed'}",
        f"Amount Claimed: {_fmt_currency(claim['amount_claimed'])}",
        f"Amount Approved: {_fmt_currency(claim['amount_approved'])}",
    ]

    if claim.get("denial_reason"):
        lines.append(f"Denial Reason: {claim['denial_reason']}")
    if claim.get("denial_reason_code"):
        lines.append(f"Denial Code: {claim['denial_reason_code']}")
    if claim.get("applicable_policy_section"):
        lines.append(f"Applicable Policy Section: {claim['applicable_policy_section']}")
    if claim.get("adjuster_notes"):
        lines.append(f"Adjuster Notes: {claim['adjuster_notes']}")
    if claim.get("appeal_deadline"):
        lines.append(f"Appeal Deadline: {claim['appeal_deadline']}")
    if claim.get("can_appeal") is not None:
        lines.append(f"Can Appeal: {'Yes' if claim['can_appeal'] else 'No'}")

    return "\n".join(lines)


def normalize_model_id(model_id: str | None) -> str:
    candidate = MODEL_ALIASES.get(model_id or "", model_id or "")
    if candidate in MODEL_SPECS:
        return candidate
    configured_defaults = [
        spec["model_id"]
        for spec in iter_model_specs()
        if os.getenv(spec["api_key_env"])
    ]
    if configured_defaults:
        return configured_defaults[0]
    return MODEL_ORDER[0]


def iter_model_specs() -> list[ModelSpec]:
    return [MODEL_SPECS[model_id] for model_id in MODEL_ORDER]


def get_default_model_id() -> str:
    return normalize_model_id(None)


def get_model_options() -> list[dict[str, str | bool]]:
    options: list[dict[str, str | bool]] = []
    for spec in iter_model_specs():
        configured = bool(os.getenv(spec["api_key_env"]))
        options.append(
            {
                "model_id": spec["model_id"],
                "label": spec["label"],
                "provider": spec["provider"],
                "configured": configured,
            }
        )
    return options


def _build_llm(model_id: str):
    resolved_model_id = normalize_model_id(model_id)
    spec = MODEL_SPECS[resolved_model_id]
    api_key = os.getenv(spec["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"{spec['label']} requires {spec['api_key_env']} to be configured."
        )

    if spec["provider"] == "google":
        return ChatGoogleGenerativeAI(
            model=spec["model_name"],
            api_key=api_key,
            temperature=0.2,
        )

    if spec["provider"] == "nvidia":
        if ChatNVIDIADynamo is None:
            raise RuntimeError(
                "langchain-nvidia-ai-endpoints is not installed."
            )
        return ChatNVIDIADynamo(
            base_url=os.getenv("NVIDIA_BASE_URL", "http://localhost:8099/v1"),
            api_key=api_key,
            model=spec["model_name"],
            osl=512,
            iat=250,
            latency_sensitivity=1.0,
            priority=1,
        )

    if spec["provider"] == "groq":
        return ChatGroq(
            model=spec["model_name"],
            api_key=api_key,
            temperature=0.2,
        )

    raise RuntimeError(f"Unsupported provider: {spec['provider']}")


def _get_tavily_client() -> TavilyClient | None:
    global _tavily_client
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


@tool
def claim_lookup(claim_id: str) -> str:
    """Look up a claim record by its claim ID (e.g. CLM-2024-0001). Returns full claim details."""
    claim = get_claim_by_id(claim_id)
    if not claim:
        return f"No claim found with ID '{claim_id}'. Please verify the claim ID and try again."
    return _build_claim_summary(claim)


@tool
def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news"] = "general",
) -> str:
    """Search the public web for current insurance regulations, appeal rules, and terminology."""
    client = _get_tavily_client()
    if client is None:
        return "Web search is unavailable because TAVILY_API_KEY is not configured."

    response = client.search(
        query=query,
        max_results=max_results,
        topic=topic,
        include_raw_content=False,
    )
    results = response.get("results", [])
    if not results:
        return f"No relevant web results found for '{query}'."

    parts = []
    for i, result in enumerate(results, 1):
        title = result.get("title") or "Untitled"
        url = result.get("url") or "URL unavailable"
        content = (result.get("content") or "").strip()
        parts.append(f"[Result {i}] {title}\nURL: {url}\n{content}")
    return "\n\n".join(parts)


def make_policy_rag_tool(file_ids: list[str] | None = None):
    @tool
    def policy_rag(query: str) -> str:
        """Search uploaded policy documents for relevant coverage clauses, exclusions, and terms."""
        results = query_policies(query, file_ids=file_ids, n_results=4)
        if not results:
            return "No relevant policy documents found. The user may not have uploaded any policy documents yet."
        parts = []
        for i, r in enumerate(results, 1):
            parts.append(
                f"[Source {i}: {r['filename']}, Page {r['page_number']}]\n{r['content']}"
            )
        return "\n\n---\n\n".join(parts)

    return policy_rag


SYSTEM_PROMPT = """You are InsureAssist, an expert AI assistant for insurance claim explanations. You work for an Indian insurance company.

Your role is to:
1. Look up claim details using the claim_lookup tool when given a claim ID
2. Search policy documents using the policy_rag tool for relevant coverage clauses
3. Search the web using the internet_search tool for current regulatory information, appeal processes, or terminology clarification
4. Generate a clear, empathetic, plain-language explanation of the claim status

When explaining a claim always structure your response with these sections:
- **Claim Summary** - status badge and key numbers
- **What This Means For You** - plain English explanation of the outcome
- **Policy Basis** - which policy section applies and why
- **What You Can Do Next** - actionable steps (appeal process, alternatives, timelines)
- **Additional Help** - any relevant information found via web search

Rules:
- Never use insurance jargon without immediately explaining it
- Always cite policy section numbers when available
- If a claim is denied, always explain appeal rights and deadlines
- If a claim is partial, explain exactly what was covered and what was not
- Be empathetic but factual
- Format all currency amounts in Indian Rupees (Rs)
- Always use the claim_lookup tool first before answering any claim-related question
- Use internet_search whenever the user asks for current rules, latest guidance, or information not present in the claim or uploaded policy files
"""


def build_agent(
    file_ids: list[str] | None = None,
    model_id: str | None = None,
):
    llm = _build_llm(normalize_model_id(model_id))
    policy_rag_tool = make_policy_rag_tool(file_ids)
    tools = [claim_lookup, policy_rag_tool, internet_search]

    return create_deep_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        name="insureassist_agent",
    )


def run_agent(
    question: str,
    history: list[dict],
    file_ids: list[str] | None = None,
    model_id: str | None = None,
) -> tuple[str, list[dict]]:
    agent = build_agent(file_ids=file_ids, model_id=model_id)

    messages: list[dict[str, str]] = []
    for msg in history:
        if msg["role"] == "user":
            messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    result = agent.invoke({"messages": messages})

    last_message = result["messages"][-1]
    answer = last_message.content if hasattr(last_message, "content") else str(last_message)

    return answer, []
