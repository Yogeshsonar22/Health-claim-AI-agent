# 🏥 Insurance Claim Explanation GenAI Agent
## Complete Project Plan & Architecture Document

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [File Structure](#file-structure)
5. [Module Breakdown](#module-breakdown)
6. [Data Flow](#data-flow)
7. [Synthetic Data Design](#synthetic-data-design)
8. [RAG Pipeline Design](#rag-pipeline-design)
9. [Agent & Tools Design](#agent--tools-design)
10. [UI Design (Streamlit)](#ui-design-streamlit)
11. [Implementation Phases](#implementation-phases)
12. [Dependencies](#dependencies)
13. [Environment Variables](#environment-variables)
14. [Success Metrics](#success-metrics)

---

## 1. Project Overview

A **Generative AI-powered Insurance Claim Explanation Agent** built with Python, LangChain, and Streamlit. The agent accepts a claim ID and relevant policy documents, then delivers a **clear, personalized, plain-English explanation** of:

- Current claim status and what it means
- Why coverage was approved, denied, or partially covered
- What policy clauses apply to the claim
- What actions the customer can take next
- Answers to follow-up questions in real time

### Core Value Proposition
| Problem | Solution |
|---|---|
| Customers confused by claim denials | Plain-English explanation with policy clause citations |
| High call center volume | Self-service agent handles 80%+ of "why" questions |
| Static FAQs don't personalize | Agent uses actual claim data + policy text |
| Opaque processing workflows | Step-by-step status walkthrough |

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND (UI)                       │
│  [Claim ID Input] [Policy Upload] [Chat Interface] [Feedback]   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   LANGCHAIN AGENT CORE                           │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │  RAG Chain   │  │  Tool Router │  │  Explanation Generator│ │
│  │ (PDF/DOCX)   │  │  (LangChain) │  │  (GPT-4 / Claude)     │ │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────────┘ │
└─────────┼─────────────────┼───────────────────────────────────┘
          │                 │
   ┌──────▼──────┐  ┌───────▼──────────────────────────────────┐
   │ VECTOR DB   │  │              TOOLS                        │
   │ (ChromaDB / │  │                                           │
   │  FAISS)     │  │  ┌─────────┐ ┌─────┐ ┌────────────────┐ │
   │             │  │  │ Tavily  │ │ Exa │ │ Google Maps MCP│ │
   │ Policy docs │  │  │Web Search│ │Deep │ │(Hospital/Clinic│ │
   │ indexed here│  │  │         │ │Rsrch│ │ Locator)       │ │
   └─────────────┘  │  └─────────┘ └─────┘ └────────────────┘ │
                    │  ┌──────────────────┐ ┌────────────────┐ │
                    │  │ Claim DB Tool    │ │ Policy Lookup  │ │
                    │  │ (Synthetic JSON) │ │ Tool (RAG)     │ │
                    │  └──────────────────┘ └────────────────┘ │
                    └───────────────────────────────────────────┘
```

---

## 3. Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **UI** | Streamlit | Interactive frontend |
| **Agent Framework** | LangChain (LCEL + AgentExecutor) | Orchestration |
| **LLM** | OpenAI GPT-4o / Anthropic Claude | Explanation generation |
| **RAG - Embeddings** | OpenAI `text-embedding-3-small` | Document embedding |
| **RAG - Vector Store** | ChromaDB (local, persistent) | Policy document retrieval |
| **Document Parsing** | PyMuPDF (PDF), python-docx (DOCX) | File extraction |
| **Web Search 1** | Tavily Search API | General insurance info search |
| **Web Search 2** | Exa API | Deep research / semantic search |
| **Location / Maps** | Google Maps MCP (or `googlemaps` SDK) | Hospital/clinic locator for health claims |
| **Data** | Synthetic JSON + CSV | Claim records simulation |
| **Memory** | LangChain ConversationBufferMemory | Multi-turn chat |
| **Env Management** | `python-dotenv` | Secrets handling |

---

## 4. File Structure

```
insurance-claim-agent/
│
├── app.py                        # Main Streamlit entry point
├── requirements.txt              # All Python dependencies
├── .env.example                  # Template for API keys
├── README.md                     # Setup & run instructions
│
├── agent/
│   ├── __init__.py
│   ├── claim_agent.py            # LangChain AgentExecutor setup
│   ├── tools.py                  # All tools (search, maps, claim lookup, RAG)
│   ├── prompts.py                # System prompts & explanation templates
│   └── memory.py                 # Conversation memory management
│
├── rag/
│   ├── __init__.py
│   ├── document_loader.py        # PDF & DOCX loading + chunking
│   ├── vector_store.py           # ChromaDB setup & retrieval
│   └── embeddings.py             # Embedding model configuration
│
├── data/
│   ├── synthetic_claims.json     # 20+ synthetic claim records
│   ├── synthetic_policies.json   # Policy metadata
│   └── sample_policies/          # Sample PDF/DOCX policy documents
│       ├── health_policy.pdf
│       ├── auto_policy.pdf
│       └── home_policy.docx
│
├── utils/
│   ├── __init__.py
│   ├── claim_parser.py           # Claim data parsing & formatting
│   └── feedback.py               # User rating capture & storage
│
└── tests/
    └── test_agent.py             # Basic integration tests
```

> **Design Principle:** Minimal files, maximum cohesion. Each file is self-contained and well-commented. Total: **~12 Python files**.

---

## 5. Module Breakdown

### `app.py` — Streamlit UI (Main Entry)
- Sidebar: API key config, document uploader, claim type selector
- Main area: Claim ID input → explanation output (streaming)
- Chat interface for follow-up Q&A
- Feedback widget (1–5 star rating + comment)
- Session state management for multi-turn conversation

### `agent/claim_agent.py` — LangChain Agent Core
- Uses **LCEL (LangChain Expression Language)** for chain composition
- `AgentExecutor` with ReAct reasoning pattern
- Tools registered: Tavily Search, Exa Search, Claim Lookup, Policy RAG, Maps
- Streaming enabled for real-time explanation display
- Fallback logic if tools fail

### `agent/tools.py` — All Agent Tools
Five tools in one file:

| Tool Name | Type | What It Does |
|---|---|---|
| `claim_lookup_tool` | Custom Python | Fetches claim from synthetic JSON by Claim ID |
| `policy_rag_tool` | RAG + ChromaDB | Retrieves relevant policy clauses by semantic search |
| `tavily_search_tool` | Tavily API | Searches web for insurance terminology, regulations |
| `exa_search_tool` | Exa API | Deep research on medical procedures, auto repair costs, etc. |
| `maps_location_tool` | Google Maps API | Finds in-network hospitals/clinics near customer location |

### `agent/prompts.py` — Prompt Templates
- **System Prompt:** Agent persona as "InsureAssist AI" — empathetic, clear, non-technical
- **Explanation Template:** Structured output with sections: Status → Reason → Policy Basis → Next Steps
- **Follow-up Prompt:** Context-aware Q&A continuation
- **Research Prompt:** When to trigger web search vs RAG

### `rag/document_loader.py` — Document Ingestion
- Supports: PDF (via PyMuPDF), DOCX (via python-docx)
- Recursive text chunking: chunk_size=1000, overlap=200
- Metadata tagging: policy_type, document_name, page_number
- Batch ingestion from `data/sample_policies/` folder
- Runtime upload ingestion from Streamlit file uploader

### `rag/vector_store.py` — ChromaDB Vector Store
- Persistent local ChromaDB collection: `insurance_policies`
- Similarity search with MMR (Maximal Marginal Relevance) for diverse results
- Top-k=5 retrieval with metadata filtering by policy type
- Auto-rebuild if collection is empty or stale

### `data/synthetic_claims.json` — Synthetic Data
20+ claim records covering:
- Health insurance (approved, denied, partial)
- Auto insurance (collision, theft, liability)
- Home insurance (flood, fire, theft)
- Each record: claim_id, policy_id, customer_name, claim_type, status, amount_claimed, amount_approved, denial_reason, dates, notes

---

## 6. Data Flow

```
USER INPUT (Claim ID: CLM-2024-0042)
         │
         ▼
[Streamlit app.py] ──► validates input ──► calls claim_agent.run()
         │
         ▼
[LangChain AgentExecutor]
    │
    ├──► Tool 1: claim_lookup_tool("CLM-2024-0042")
    │         └── Returns: {status: "Denied", reason: "Out-of-network provider", amount: $2,400}
    │
    ├──► Tool 2: policy_rag_tool("out-of-network coverage exclusions")
    │         └── Returns: "Section 4.2: Services rendered by non-participating providers..."
    │
    ├──► Tool 3: tavily_search_tool("what does out-of-network mean in health insurance")
    │         └── Returns: Web results explaining out-of-network concept
    │
    └──► LLM generates final explanation:
              "Your claim #CLM-2024-0042 was denied because Dr. Smith's clinic
               is not in our provider network. According to your policy Section 4.2,
               out-of-network services are not covered under your Gold Plan.
               Here's what you can do: 1) Request an exception... 2) Appeal within 30 days..."
         │
         ▼
[Streamlit] ──► Streams explanation to user ──► Displays with formatting
         │
         ▼
[Feedback Widget] ──► User rates clarity (1-5 stars) ──► Stored in feedback.json
```

---

## 7. Synthetic Data Design

### Claim Record Schema (`synthetic_claims.json`)
```json
{
  "claim_id": "CLM-2024-0042",
  "policy_id": "POL-GOLD-H-1198",
  "customer": {
    "name": "Anita Sharma",
    "age": 34,
    "city": "Pune",
    "state": "Maharashtra",
    "zip": "411057"
  },
  "claim_type": "health",
  "sub_type": "outpatient",
  "provider": "City Diagnostics Clinic",
  "provider_network_status": "out-of-network",
  "date_of_service": "2024-11-10",
  "date_submitted": "2024-11-15",
  "date_processed": "2024-11-22",
  "amount_claimed": 2400.00,
  "amount_approved": 0.00,
  "status": "denied",
  "denial_reason_code": "OON-001",
  "denial_reason": "Out-of-network provider not covered under plan",
  "applicable_policy_section": "4.2",
  "appeal_deadline": "2024-12-22",
  "adjuster_notes": "Patient advised to seek in-network alternatives",
  "icd_codes": ["Z00.00"],
  "can_appeal": true
}
```

### Claim Types Covered (20+ scenarios)
| # | Type | Sub-type | Status |
|---|---|---|---|
| 1–4 | Health | Hospitalization | Approved / Partial |
| 5–7 | Health | Outpatient | Denied (OON) |
| 8–9 | Health | Prescription | Partial |
| 10–12 | Auto | Collision | Approved / Pending |
| 13–14 | Auto | Theft | Denied (policy lapse) |
| 15–16 | Auto | Third-party liability | Approved |
| 17–18 | Home | Fire damage | Approved |
| 19 | Home | Flood | Denied (exclusion) |
| 20 | Home | Theft | Pending investigation |

---

## 8. RAG Pipeline Design

### Document Ingestion Flow
```
PDF/DOCX Upload or Pre-loaded Policies
            │
            ▼
    [document_loader.py]
    ├── PyMuPDF for PDFs (preserves structure)
    ├── python-docx for DOCX files
    └── Text chunking: RecursiveCharacterTextSplitter
        ├── chunk_size = 1000 tokens
        └── chunk_overlap = 200 tokens
            │
            ▼
    [embeddings.py]
    └── OpenAI text-embedding-3-small
        └── 1536-dim vectors
            │
            ▼
    [vector_store.py]
    └── ChromaDB (persistent, local)
        ├── Collection: "insurance_policies"
        └── Metadata: {policy_type, doc_name, page, section}
```

### Retrieval Strategy
- **Primary:** MMR (Maximal Marginal Relevance) — avoids repetitive chunks
- **Filter:** By claim type (health/auto/home) to limit search scope
- **Top-k:** 5 most relevant chunks
- **Re-ranking:** Simple LLM-based relevance scoring for final top-3

### Sample Policy Documents (Pre-bundled)
1. `health_policy.pdf` — 15-page synthetic health plan document
2. `auto_policy.pdf` — 12-page auto coverage document
3. `home_policy.docx` — 10-page home insurance policy

All documents are **synthetically generated** with realistic clause language, section numbers, exclusions, and definitions.

---

## 9. Agent & Tools Design

### Agent Type: ReAct (Reason + Act)
```
Thought: I need to look up claim CLM-2024-0042 first.
Action: claim_lookup_tool
Action Input: "CLM-2024-0042"
Observation: {status: denied, reason: out-of-network, ...}

Thought: Now I need the relevant policy clause about out-of-network.
Action: policy_rag_tool
Action Input: "out-of-network provider exclusions coverage"
Observation: "Section 4.2 states that services from non-participating..."

Thought: I should also search for what options the customer has.
Action: tavily_search_tool
Action Input: "insurance claim appeal process out-of-network denial India"
Observation: [web results about appeal rights]

Thought: I have enough to generate a complete explanation.
Final Answer: [Full personalized explanation]
```

### Tool Specifications

#### Tool 1: `claim_lookup_tool`
- Input: `claim_id` (string)
- Process: Loads `synthetic_claims.json`, filters by ID
- Output: Formatted claim dict
- Error handling: Returns "Claim not found" with suggestions

#### Tool 2: `policy_rag_tool`
- Input: Natural language query about policy
- Process: ChromaDB MMR search → returns top chunks
- Output: Formatted policy text with section references
- Fallback: If no match, triggers Tavily search

#### Tool 3: `tavily_search_tool`
- Input: Search query string
- Process: Tavily API call, max_results=5
- Output: Summarized search results
- Use case: Regulatory info, terminology, general insurance knowledge

#### Tool 4: `exa_search_tool`
- Input: Deep research query
- Process: Exa API semantic search
- Output: Relevant web content with source URLs
- Use case: Medical procedure costs, repair estimates, legal rights

#### Tool 5: `maps_location_tool`
- Input: `{"location": "Pune, Maharashtra", "query": "in-network hospitals"}`
- Process: Google Maps Places API / MCP → finds nearby providers
- Output: List of nearby in-network providers with address + distance
- Use case: Health claims — suggest in-network alternatives

---

## 10. UI Design (Streamlit)

### Layout Plan

```
┌─────────────────────────────────────────────────────────────┐
│  🏥 InsureAssist AI  │  [Config ⚙️]  [Upload Policy 📄]     │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  SIDEBAR     │  MAIN PANEL                                  │
│              │                                              │
│ [Claim Type] │  ┌──────────────────────────────────────┐   │
│  ○ Health    │  │  Enter Claim ID:                      │   │
│  ○ Auto      │  │  [ CLM-2024-0042          ] [Explain] │   │
│  ○ Home      │  └──────────────────────────────────────┘   │
│              │                                              │
│ [Upload PDF] │  ── Claim Summary Card ──────────────────   │
│              │  Status: ❌ DENIED   │ Amount: ₹2,400       │
│ [Sample IDs] │  Type: Health (OOP) │ Date: Nov 22, 2024   │
│ CLM-2024-001 │                                              │
│ CLM-2024-005 │  ── AI Explanation (Streaming) ────────── │
│ CLM-2024-010 │                                              │
│              │  📋 **Why Your Claim Was Denied**            │
│ [Feedback]   │  Your claim was denied because Dr. Smith's  │
│ ⭐⭐⭐⭐⭐      │  clinic is **not in our provider network**... │
│              │                                              │
│              │  📌 **Relevant Policy Section**              │
│              │  Section 4.2 — Out-of-Network Services...   │
│              │                                              │
│              │  ✅ **What You Can Do**                      │
│              │  1. File an appeal by Dec 22, 2024          │
│              │  2. Find in-network clinics near you →      │
│              │     [City Medical Center - 2.3 km]          │
│              │                                              │
│              │  ── Chat Follow-up ─────────────────────── │
│              │  💬 Ask a follow-up question...              │
│              │  [What documents do I need to appeal?  ][→] │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### Key UI Features
- **Streaming output:** Explanation appears word-by-word (not all at once)
- **Status badge:** Color-coded (green=approved, red=denied, yellow=pending)
- **Expandable sections:** Policy clause text, search sources, tool trace
- **Sample claim IDs:** Clickable quick-fill buttons for demo
- **Feedback widget:** Star rating + optional text comment
- **Map embed:** Nearby provider map for health claim denials
- **Export:** Download explanation as PDF button

---

## 11. Implementation Phases

### Phase 1 — Foundation (Day 1–2)
- [ ] Project scaffold, `requirements.txt`, `.env.example`
- [ ] Synthetic data generation (`synthetic_claims.json`, 20 records)
- [ ] Basic Streamlit UI skeleton (`app.py`)
- [ ] Claim lookup tool (reads from JSON)

### Phase 2 — RAG Pipeline (Day 2–3)
- [ ] Document loader for PDF + DOCX
- [ ] ChromaDB vector store setup
- [ ] Embed sample policy documents
- [ ] Policy RAG tool tested independently

### Phase 3 — Agent + Tools (Day 3–4)
- [ ] LangChain ReAct agent setup
- [ ] Tavily + Exa tools integrated
- [ ] Google Maps tool integrated
- [ ] Agent tested with 5 claim scenarios

### Phase 4 — UI Polish + Streaming (Day 4–5)
- [ ] Streaming output in Streamlit
- [ ] Claim summary card component
- [ ] Feedback capture + storage
- [ ] Sample demo flows finalized

### Phase 5 — Testing + Docs (Day 5)
- [ ] Test all 20 claim scenarios
- [ ] README with setup instructions
- [ ] Demo script prepared
- [ ] Success metric baseline recorded

---

## 12. Dependencies (`requirements.txt`)

```
# Core
streamlit>=1.35.0
langchain>=0.2.0
langchain-openai>=0.1.0
langchain-community>=0.2.0
langchain-chroma>=0.1.0
openai>=1.30.0

# Document Processing
pymupdf>=1.24.0          # PDF parsing (fitz)
python-docx>=1.1.0       # DOCX parsing

# Vector Store
chromadb>=0.5.0

# Web Search Tools
tavily-python>=0.3.0
exa-py>=1.0.0

# Maps
googlemaps>=4.10.0

# Utilities
python-dotenv>=1.0.0
pydantic>=2.0.0

# Data
pandas>=2.0.0            # For CSV claim data if needed

# Optional: Feedback storage
tinydb>=4.8.0            # Lightweight JSON feedback DB
```

---

## 13. Environment Variables (`.env.example`)

```bash
# LLM Provider (pick one)
OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here   # optional alternative

# Web Search Tools
TAVILY_API_KEY=your_tavily_key_here
EXA_API_KEY=your_exa_key_here

# Google Maps
GOOGLE_MAPS_API_KEY=your_google_maps_key_here

# App Config
LLM_MODEL=gpt-4o                            # or claude-3-5-sonnet
EMBEDDING_MODEL=text-embedding-3-small
CHROMA_PERSIST_DIR=./chroma_db
CLAIMS_DATA_PATH=./data/synthetic_claims.json
POLICIES_DIR=./data/sample_policies/
```

---

## 14. Success Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| **Explanation Clarity** | ≥ 4.0 / 5.0 stars | In-app star rating widget |
| **Accuracy (policy match)** | ≥ 85% | Manual review of 20 test claims |
| **Response Time** | < 15 seconds | Timer in Streamlit |
| **Claim Types Handled** | 3 types (health/auto/home) | Demo coverage |
| **Follow-up Q&A** | Multi-turn working | Functional test |
| **Tool Usage** | ≥ 3 tools per complex query | LangChain trace log |
| **RAG Retrieval Precision** | Correct clause cited ≥ 80% | Manual spot-check |

---

## Notes & Design Decisions

1. **Single `tools.py` file** — All 5 tools in one place for simplicity. Each tool is a `@tool`-decorated function with clear docstrings.

2. **ChromaDB over Pinecone** — Local persistence, no extra account needed, perfect for prototype scale.

3. **Synthetic data only** — No real PII. All names, amounts, and claim IDs are generated. Compliant by design.

4. **Streamlit over FastAPI+React** — Faster prototype, built-in session state, native file upload support.

5. **Google Maps as SDK fallback** — If MCP is not available in environment, fall back to `googlemaps` Python SDK directly. Same output, different transport.

6. **Exa for deep research** — Tavily handles broad queries; Exa handles semantic/research queries like "what is usual cost of knee replacement surgery in Maharashtra."

7. **Explanation structure is templated** — The LLM fills in a consistent template (Status → Reason → Policy Basis → Next Steps → Appeal Info), so output is always organized and never freeform rambling.

---

*Document Version: 1.0 | Ready for implementation upon approval*