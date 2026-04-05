# InsureAssist Project Overview

## What This Project Is

This project is an AI assistant for insurance claims.

Its job is to help a user:

- ask about an insurance claim in simple language
- upload policy documents such as PDFs and DOCX files
- search those uploaded documents for relevant coverage rules
- combine claim data, policy text, and web search results into one answer

You can think of it like this:

- `data.py` is the filing cabinet with claim records
- `rag.py` is the librarian that reads uploaded policy documents
- `agent.py` is the analyst that combines all the information
- `main.py` is the service desk that receives requests
- `app.py` is the front desk screen the user interacts with

## The Big Idea

Imagine a customer walks into an insurance help center and says:

> "Why was my claim denied, and what can I do next?"

In a traditional company, a human support person might:

1. open the claim record
2. read the insurance policy
3. check the rules or appeal process online
4. explain the result in plain language

This app does the same kind of work, but with AI.

## Main Features

### 1. Claim Explanation

The app can explain:

- whether a claim was approved, denied, or partially approved
- how much money was claimed and approved
- why the decision happened
- whether the user can appeal

### 2. Policy Document Search

Users can upload files like:

- `.pdf`
- `.docx`
- `.txt`
- `.md`

The app extracts text, breaks it into smaller chunks, stores those chunks in a vector database, and later searches them when answering questions.

### 3. AI Agent Reasoning

The AI agent can use tools to:

- look up claim details
- search uploaded policy documents
- search the web for current rules or terminology

This is important because the model is not just "guessing." It can actively fetch supporting information.

### 4. Multiple Model Providers

The backend supports multiple LLM providers:

- Google Gemini
- Groq
- NVIDIA

This means the same app can switch between different AI models without rewriting the whole product.

## Who This Project Is For

This project is useful for:

- hackathons
- AI demos
- internal insurance support tools
- training junior developers on RAG and agent-based systems

## Folder and File Purpose

### Core Files

- `app.py`
  - Streamlit frontend
  - shows the UI
  - sends requests to backend API

- `main.py`
  - FastAPI backend
  - exposes routes like `/health`, `/models`, `/files`, `/upload`, and `/ask`

- `agent.py`
  - builds the LangChain Deep Agent
  - selects the LLM provider
  - defines tools like claim lookup, policy search, and web search

- `rag.py`
  - handles document extraction
  - splits text into chunks
  - stores and searches chunks in ChromaDB

- `data.py`
  - contains synthetic claim data
  - seeds a local claims file used by the app

## How To Think About The System

An easy analogy:

- the frontend is the restaurant menu
- the backend API is the waiter
- the agent is the chef
- the database and document store are the pantry
- the AI model is the cooking brain deciding how to prepare the answer

The user only sees the final meal, but several parts work together behind the scenes.

## Simple End-To-End Story

Here is the simplest story of what happens:

1. A user opens the Streamlit UI.
2. The UI calls the FastAPI backend.
3. The backend sends the question to the agent.
4. The agent may:
   - fetch a claim record
   - search policy chunks
   - search the web
5. The model writes a final explanation.
6. The answer is shown in the UI.

## Why This Project Is Good For Learning

This repo is a good learning project because it shows several real-world concepts in one place:

- frontend and backend together
- API design
- document parsing
- retrieval augmented generation
- agent tool use
- model provider switching
- environment variable based configuration

If you are a junior developer, do not worry if all those words feel heavy right now.

A simpler way to say it is:

> "The app reads structured claim data, reads uploaded documents, uses AI to connect the dots, and shows the answer in a simple interface."

