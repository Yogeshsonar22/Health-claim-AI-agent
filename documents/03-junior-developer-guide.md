# Junior Developer Guide

## Start Here

If you are new to coding, start with this idea:

This project is a question-answering app for insurance claims.

It does not magically know everything.
It works because we gave it:

- claim data
- uploaded policy files
- web search access
- a user interface
- a backend API

Your job as a developer is mostly to help those pieces talk to each other clearly.

## Tech Stack

Here is the stack in plain English.

### Frontend

- Streamlit

Why it is used:

- very fast to build UIs
- great for demos and internal tools
- simple for Python developers

### Backend

- FastAPI

Why it is used:

- easy API route creation
- good type hints
- clean request and response handling

### AI Orchestration

- LangChain
- Deep Agents

Why it is used:

- helps connect models, tools, and prompts
- makes tool-using agents easier to build

### Model Providers

- Groq
- Google Gemini
- NVIDIA

Why multiple providers:

- flexibility
- testing different models
- fallback choices

### Retrieval Layer

- ChromaDB

Why it is used:

- stores vectorized document chunks
- supports similarity search for policy text

### File Parsing

- PyMuPDF
- python-docx

Why they are used:

- extract text from PDF and DOCX files

## Beginner-Friendly File Tour

### `main.py`

Read this file if you want to understand:

- what routes exist
- what the frontend calls
- how the backend responds

Good first learning target:

- understand `/ask`
- understand `/upload`

### `app.py`

Read this file if you want to understand:

- the chat UI
- model dropdown behavior
- document upload screen
- how messages are rendered

Good first learning target:

- find where the app sends the POST request to `/ask`

### `agent.py`

Read this file if you want to understand:

- how models are selected
- how tools are defined
- how the deep agent is built

Good first learning target:

- understand `MODEL_SPECS`
- understand `_build_llm()`
- understand `run_agent()`

### `rag.py`

Read this file if you want to understand:

- how documents become searchable
- how text is chunked
- how results are retrieved

Good first learning target:

- understand `extract_text()`
- understand `ingest_document()`
- understand `query_policies()`

### `data.py`

Read this file if you want to understand:

- where sample claim records come from
- what fields a claim contains

Good first learning target:

- compare approved vs denied vs partial claims

## Mental Model For The Full Flow

Imagine this project as a team inside a small office:

- Streamlit is the receptionist
- FastAPI is the dispatcher
- the agent is the analyst
- ChromaDB is the filing room
- the LLM is the specialist consultant
- Tavily is the internet researcher

When a user asks a question:

1. the receptionist takes the question
2. the dispatcher sends it to the analyst
3. the analyst checks the file room and online references
4. the specialist writes the explanation
5. the receptionist shows the answer back to the user

## Common Developer Tasks

### Task: Add A New Model

Where to look:

- `agent.py`

What you usually change:

- add a new item in `MODEL_SPECS`
- add provider logic in `_build_llm()`
- make sure the environment variable exists

### Task: Add A New Tool

Where to look:

- `agent.py`

What you usually change:

- create a new `@tool`
- add it to the `tools` list
- update the system prompt so the agent knows when to use it

### Task: Change The UI

Where to look:

- `app.py`

What you usually change:

- layout
- sidebars
- status messages
- chat rendering

### Task: Change How Documents Are Searched

Where to look:

- `rag.py`

What you usually change:

- chunk size
- chunk overlap
- Chroma query behavior

## Common Mistakes

### 1. Updating `.env` But Not Restarting The Backend

Many environment variable changes only apply when the Python process starts.

Analogy:

Changing `.env` after the app is already running is like changing the recipe card after the chef already started cooking.

### 2. Thinking The Model Automatically Knows Uploaded Files

It does not.

The files must be:

- uploaded
- parsed
- chunked
- stored
- retrieved

### 3. Confusing Frontend Errors With Backend Errors

If the UI says "Request failed," the real issue is often in the API or model configuration.

### 4. Forgetting That Some Storage Is In Memory

`FILES_STORE` is not a permanent database.

If the backend restarts, some file metadata may disappear unless the app is extended to persist it properly.

## Safe Ways To Learn This Repo

If you are new, use this order:

1. Read `01-project-overview.md`
2. Read `02-flow-and-architecture.md`
3. Open `main.py`
4. Open `app.py`
5. Open `agent.py`
6. Open `rag.py`
7. Try one small change only

## Good First Small Changes

- rename a UI label
- add a new sample question
- change a model label
- change the empty-state text
- add one extra line to the system prompt

These are safer than changing the whole agent flow on day one.

## If Something Breaks

Use this debugging order:

1. Check whether the backend is running
2. Check `/health`
3. Check `/models`
4. Confirm `.env` keys are loaded
5. Confirm the selected provider has its package installed
6. Look at the exact traceback

## Final Advice

Do not try to understand everything at once.

A good junior developer does not need to know the whole system in one day.
A good junior developer learns the path of one request, end to end.

That means:

- where the question starts
- where it gets processed
- where data comes from
- where the answer returns

Once you understand that path, the project will feel much less scary.

