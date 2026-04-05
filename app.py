from __future__ import annotations

import os
import re
import uuid

import requests
import streamlit as st

APP_TITLE = "InsureAssist AI"
AGENT_NAME = "InsureAssist AI"
AGENT_TAGLINE = "Clear answers about your insurance claims."
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
CHAT_FILE_TYPES = ["pdf", "txt", "md", "docx", "doc"]

SAMPLE_CLAIM_IDS = [
    "CLM-2024-0001",
    "CLM-2024-0002",
    "CLM-2024-0003",
    "CLM-2024-0004",
    "CLM-2024-0005",
    "CLM-2024-0006",
    "CLM-2024-0007",
    "CLM-2024-0008",
]

SAMPLE_QUESTIONS = [
    "Explain claim CLM-2024-0002 in simple terms",
    "Why was claim CLM-2024-0007 denied and can I appeal?",
    "What does partial approval mean for CLM-2024-0003?",
    "What is the status of claim CLM-2024-0008?",
]


def api_is_up() -> bool:
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.ok
    except requests.RequestException:
        return False


def fetch_files() -> list[dict]:
    response = requests.get(f"{API_BASE_URL}/files", timeout=15)
    response.raise_for_status()
    return response.json()


def fetch_models() -> dict:
    response = requests.get(f"{API_BASE_URL}/models", timeout=15)
    response.raise_for_status()
    return response.json()


def extract_error_detail(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Unknown request failure."
    detail = payload.get("detail")
    return detail if isinstance(detail, str) else str(detail or "Unknown request failure.")


def refresh_backend_state() -> None:
    records = fetch_files()
    model_payload = fetch_models()
    st.session_state.records = records
    st.session_state.file_map = {record["file_id"]: record for record in records}
    st.session_state.model_options = model_payload["models"]
    st.session_state.model_map = {item["model_id"]: item for item in model_payload["models"]}
    st.session_state.default_model_id = model_payload["default_model_id"]
    if (
        "draft_model_id" not in st.session_state
        or st.session_state.draft_model_id not in st.session_state.model_map
    ):
        st.session_state.draft_model_id = st.session_state.default_model_id


def upload_files_to_api(uploaded_files: list) -> list[dict]:
    uploaded_records: list[dict] = []
    for uploaded_file in uploaded_files:
        files = {
            "file": (
                uploaded_file.name,
                uploaded_file.getvalue(),
                uploaded_file.type or "application/octet-stream",
            )
        }
        response = requests.post(f"{API_BASE_URL}/upload", files=files, timeout=120)
        response.raise_for_status()
        uploaded_records.append(response.json())
    return uploaded_records


def delete_file_from_api(file_id: str) -> None:
    response = requests.delete(f"{API_BASE_URL}/files/{file_id}", timeout=30)
    if not response.ok:
        raise RuntimeError(extract_error_detail(response))


def remove_deleted_file_from_state(file_id: str) -> None:
    st.session_state.draft_file_ids = [
        fid for fid in st.session_state.draft_file_ids if fid != file_id
    ]
    for thread in st.session_state.threads.values():
        thread["file_ids"] = [fid for fid in thread.get("file_ids", []) if fid != file_id]


def create_thread() -> str:
    thread_id = uuid.uuid4().hex
    st.session_state.threads[thread_id] = {
        "title": "New chat",
        "messages": [],
        "file_ids": list(st.session_state.draft_file_ids),
        "use_all_files": bool(st.session_state.draft_use_all_files),
        "model_id": st.session_state.draft_model_id,
    }
    st.session_state.current_thread_id = thread_id
    return thread_id


def start_new_chat() -> None:
    current_thread = get_current_thread()
    if current_thread:
        st.session_state.draft_file_ids = list(current_thread.get("file_ids", []))
        st.session_state.draft_use_all_files = bool(current_thread.get("use_all_files", True))
        st.session_state.draft_model_id = current_thread.get(
            "model_id", st.session_state.default_model_id
        )
    st.session_state.current_thread_id = None


def get_current_thread() -> dict | None:
    thread_id = st.session_state.current_thread_id
    if not thread_id:
        return None
    return st.session_state.threads.get(thread_id)


def get_thread_label(thread: dict) -> str:
    if thread["title"] != "New chat":
        return thread["title"]
    if thread["messages"]:
        first_user = next(
            (
                m["content"].strip()
                for m in thread["messages"]
                if m["role"] == "user" and m["content"].strip()
            ),
            "",
        )
        if first_user:
            return first_user[:48]
    return "Untitled chat"


def update_thread_title(thread: dict, prompt: str) -> None:
    if thread["title"] == "New chat":
        thread["title"] = prompt.strip()[:48] or thread["title"]


def bump_thread(thread_id: str) -> None:
    if thread_id in st.session_state.thread_order:
        st.session_state.thread_order.remove(thread_id)
    st.session_state.thread_order.insert(0, thread_id)


def active_scope_values(thread: dict | None) -> tuple[bool, list[str]]:
    if thread:
        return bool(thread.get("use_all_files", True)), list(thread.get("file_ids", []))
    return bool(st.session_state.draft_use_all_files), list(st.session_state.draft_file_ids)


def active_model_id(thread: dict | None) -> str:
    if thread and thread.get("model_id") in st.session_state.model_map:
        return thread["model_id"]
    if st.session_state.draft_model_id in st.session_state.model_map:
        return st.session_state.draft_model_id
    return st.session_state.default_model_id


def set_active_scope(use_all_files: bool, file_ids: list[str]) -> None:
    thread = get_current_thread()
    if thread:
        thread["use_all_files"] = use_all_files
        thread["file_ids"] = list(file_ids)
    st.session_state.draft_use_all_files = use_all_files
    st.session_state.draft_file_ids = list(file_ids)


def set_active_model(model_id: str) -> None:
    thread = get_current_thread()
    if thread:
        thread["model_id"] = model_id
    st.session_state.draft_model_id = model_id


def add_uploaded_files_to_scope(uploaded_records: list[dict]) -> None:
    if not uploaded_records:
        return
    new_ids = [record["file_id"] for record in uploaded_records]
    thread = get_current_thread()
    use_all_files, file_ids = active_scope_values(thread)
    if use_all_files:
        return
    merged_ids = list(dict.fromkeys(file_ids + new_ids))
    set_active_scope(False, merged_ids)


def apply_ui_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

        html, body, [class*="css"] {
            font-family: 'DM Sans', sans-serif;
        }

        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
        }

        div[data-testid="stButton"] > button[kind="primary"] {
            min-height: 2.65rem;
            border-radius: 7px;
            font-weight: 600;
            background: #1a3a5c;
            border: none;
            color: #fff;
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: #14304f;
        }

        section[data-testid="stSidebar"] {
            background: #0f2035;
        }

        section[data-testid="stSidebar"] * {
            color: #c8d8e8 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] {
            width: 100%;
        }

        section[data-testid="stSidebar"] div[data-testid="stSegmentedControl"] [role="radiogroup"] {
            width: 100%;
        }

        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            justify-content: flex-start;
            min-height: 2.35rem;
            border-radius: 7px;
            border: 1px solid rgba(255,255,255,0.06);
            box-shadow: none;
            background: rgba(255,255,255,0.03);
        }

        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background: rgba(255,255,255,0.08);
        }

        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] p {
            width: 100%;
            text-align: left;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        div[data-testid="stChatInput"] {
            border-radius: 1.2rem;
        }

        div[data-testid="stChatInput"] textarea {
            max-height: 10rem !important;
            overflow-y: auto !important;
        }

        div[data-testid="stExpander"] {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        div[data-testid="stExpander"] details {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        div[data-testid="stExpander"] summary {
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            padding-left: 0 !important;
        }

        .claim-badge-approved {
            display: inline-block;
            background: #d1fae5;
            color: #065f46;
            border-radius: 6px;
            padding: 3px 10px;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
        }

        .claim-badge-denied {
            display: inline-block;
            background: #fee2e2;
            color: #991b1b;
            border-radius: 6px;
            padding: 3px 10px;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
        }

        .claim-badge-partial {
            display: inline-block;
            background: #fef3c7;
            color: #92400e;
            border-radius: 6px;
            padding: 3px 10px;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
        }

        .claim-badge-pending {
            display: inline-block;
            background: #dbeafe;
            color: #1e40af;
            border-radius: 6px;
            padding: 3px 10px;
            font-weight: 600;
            font-size: 0.8rem;
            letter-spacing: 0.04em;
        }

        .sample-chip {
            display: inline-block;
            background: rgba(26,58,92,0.08);
            border: 1px solid rgba(26,58,92,0.15);
            border-radius: 20px;
            padding: 4px 12px;
            font-size: 0.82rem;
            color: #1a3a5c;
            cursor: pointer;
            margin: 3px;
            transition: background 0.15s;
        }

        .sample-chip:hover {
            background: rgba(26,58,92,0.15);
        }

        .empty-state-shell {
            min-height: 54vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem 0 2rem;
        }

        .empty-state-card {
            width: min(520px, 92%);
            text-align: center;
            animation: emptyFadeUp 360ms ease-out;
        }

        .empty-state-wordmark {
            font-family: 'DM Serif Display', serif;
            font-size: 2.4rem;
            color: #1a3a5c;
            margin-bottom: 0.3rem;
            letter-spacing: -0.02em;
        }

        .empty-state-copy {
            color: #64748b;
            font-size: 1.02rem;
            margin-bottom: 1.6rem;
        }

        .empty-state-divider {
            border: none;
            border-top: 1px solid #e2e8f0;
            margin: 1.4rem 0;
        }

        .empty-state-hint {
            font-size: 0.82rem;
            color: #94a3b8;
            margin-bottom: 0.6rem;
        }

        @keyframes emptyFadeUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def split_thinking_blocks(content: str) -> tuple[list[str], str]:
    patterns = [
        r"<think>(.*?)</think>",
        r"<thinking>(.*?)</thinking>",
    ]
    thinking_blocks: list[str] = []
    final_content = content
    for pattern in patterns:
        matches = re.findall(pattern, final_content, flags=re.IGNORECASE | re.DOTALL)
        thinking_blocks.extend(match.strip() for match in matches if match.strip())
        final_content = re.sub(pattern, "", final_content, flags=re.IGNORECASE | re.DOTALL)
    return thinking_blocks, final_content.strip()


def render_assistant_message(message: dict) -> None:
    thinking_blocks, final_content = split_thinking_blocks(message["content"])
    if thinking_blocks:
        with st.expander("Reasoning", expanded=False):
            for block in thinking_blocks:
                st.markdown(block)
    if final_content:
        st.markdown(final_content)
    elif not thinking_blocks:
        st.markdown(message["content"])
    if message.get("sources"):
        with st.expander("Sources", expanded=False):
            for source in message["sources"]:
                page_text = (
                    f"Page {source['page_number']}"
                    if source.get("page_number")
                    else "Page unavailable"
                )
                st.markdown(f"**{source['filename']}**  \n{page_text}")
                st.markdown(source["content"])


def parse_chat_value(value) -> tuple[str, list]:
    if value is None:
        return "", []
    if isinstance(value, str):
        return value.strip(), []
    text = getattr(value, "text", "") or ""
    files = list(getattr(value, "files", []) or [])
    return text.strip(), files


def render_empty_state() -> None:
    sample_ids_html = "".join(
        f'<span class="sample-chip">{cid}</span>' for cid in SAMPLE_CLAIM_IDS[:6]
    )
    st.markdown(
        f"""
        <div class="empty-state-shell">
            <div class="empty-state-card">
                <div class="empty-state-wordmark">{AGENT_NAME}</div>
                <div class="empty-state-copy">{AGENT_TAGLINE}</div>
                <hr class="empty-state-divider"/>
                <div class="empty-state-hint">Try asking about one of these sample claims</div>
                <div>{sample_ids_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title=APP_TITLE, layout="wide")
apply_ui_styles()

if "threads" not in st.session_state:
    st.session_state.threads = {}
if "thread_order" not in st.session_state:
    st.session_state.thread_order = []
if "current_thread_id" not in st.session_state:
    st.session_state.current_thread_id = None
if "draft_file_ids" not in st.session_state:
    st.session_state.draft_file_ids = []
if "draft_use_all_files" not in st.session_state:
    st.session_state.draft_use_all_files = True
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Claims"

if not api_is_up():
    st.error("Backend is not running.")
    st.info("Start it with: `python main.py`")
    st.stop()

refresh_backend_state()

current_thread = get_current_thread()
model_ids = [item["model_id"] for item in st.session_state.model_options]
selected_model_id = active_model_id(current_thread)
if selected_model_id not in model_ids:
    selected_model_id = st.session_state.default_model_id

with st.sidebar:
    st.markdown(
        "<div style='font-family:DM Serif Display,serif;font-size:1.3rem;color:#a8c4e0;"
        "padding:0.4rem 0 1rem;letter-spacing:-0.01em;'>InsureAssist AI</div>",
        unsafe_allow_html=True,
    )

    st.segmented_control(
        "Workspace",
        options=["Claims", "Documents"],
        key="view_mode",
        label_visibility="collapsed",
        width="stretch",
    )

    picked_model_id = st.selectbox(
        "Model",
        options=model_ids,
        index=model_ids.index(selected_model_id),
        format_func=lambda mid: st.session_state.model_map[mid]["label"],
    )
    set_active_model(picked_model_id)  # type: ignore
    picked_model = st.session_state.model_map[picked_model_id]
    st.caption(f"Provider: {str(picked_model.get('provider', 'unknown')).title()}")

    if st.button("New chat", use_container_width=True, type="primary"):
        start_new_chat()
        st.rerun()

    with st.container(height=420, border=False):
        for thread_id in st.session_state.thread_order:
            thread = st.session_state.threads[thread_id]
            label = get_thread_label(thread)
            if st.button(
                label,
                key=f"thread_{thread_id}",
                use_container_width=True,
                type="secondary",
            ):
                st.session_state.current_thread_id = thread_id
                st.rerun()

current_thread = get_current_thread()

if st.session_state.view_mode == "Documents":
    st.markdown("### Policy Documents")
    st.caption("Upload your policy PDF or DOCX files. The agent will reference them when explaining claims.")

    documents_notice = st.session_state.pop("documents_notice", None)
    if documents_notice:
        notice_level, notice_message = documents_notice
        if notice_level == "success":
            st.success(notice_message)
        else:
            st.error(notice_message)

    current_use_all, current_file_ids = active_scope_values(current_thread)
    search_all_files = st.checkbox("Search all uploaded policy documents", value=current_use_all)

    if search_all_files:
        set_active_scope(True, [])
        st.info("The agent will search across all uploaded policy documents.")
    else:
        selected_file_ids = st.multiselect(
            "Search only selected documents",
            options=list(st.session_state.file_map.keys()),
            default=[fid for fid in current_file_ids if fid in st.session_state.file_map],
            format_func=lambda fid: st.session_state.file_map[fid]["filename"],
        )
        set_active_scope(False, selected_file_ids)

    uploaded_files = st.file_uploader(
        "Upload policy documents",
        accept_multiple_files=True,
        type=CHAT_FILE_TYPES,
    )
    if st.button("Upload", use_container_width=True, type="primary"):
        if not uploaded_files:
            st.warning("Choose at least one file.")
        else:
            uploaded_records = upload_files_to_api(uploaded_files)
            add_uploaded_files_to_scope(uploaded_records)
            st.success(f"Uploaded {len(uploaded_records)} document(s) and indexed for search.")
            st.rerun()

    if st.session_state.records:
        for record in st.session_state.records:
            with st.container(border=True):
                col1, col2 = st.columns([0.78, 0.22], vertical_alignment="center")
                with col1:
                    st.markdown(f"**{record['filename']}**")
                with col2:
                    if st.button("Delete", key=f"delete_{record['file_id']}", use_container_width=True):
                        try:
                            delete_file_from_api(record["file_id"])
                        except Exception as exc:
                            st.session_state.documents_notice = (
                                "error",
                                f"Could not delete {record['filename']}: {exc}",
                            )
                        else:
                            remove_deleted_file_from_state(record["file_id"])
                            refresh_backend_state()
                            st.session_state.documents_notice = (
                                "success",
                                f"Deleted {record['filename']}.",
                            )
                        st.rerun()
                status_label = "indexed" if record["has_text"] else "stored only"
                st.caption(f"{record['size']} bytes | {status_label} | {record.get('chunk_count', 0)} chunks")
    else:
        st.info("No policy documents uploaded yet. Upload PDFs or DOCX files to enable policy-based explanations.")

else:
    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    for message in (current_thread or {}).get("messages", []):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                render_assistant_message(message)
            else:
                st.markdown(message["content"])

    chat_value = st.chat_input("Enter a claim ID or ask about your insurance claim...")
    prompt, attached_files = parse_chat_value(chat_value)

    if not (current_thread and current_thread.get("messages")) and not prompt:
        render_empty_state()

    if attached_files:
        uploaded_records = upload_files_to_api(attached_files)
        refresh_backend_state()
        add_uploaded_files_to_scope(uploaded_records)
        if not prompt:
            st.success(f"Uploaded {len(uploaded_records)} file(s).")
            st.rerun()

    if prompt:
        if st.session_state.current_thread_id is None:
            create_thread()

        current_thread = get_current_thread()
        if current_thread is None:
            st.stop()

        history = [
            {"role": m["role"], "content": m["content"]}
            for m in current_thread["messages"]
        ]
        user_message = {"role": "user", "content": prompt}
        current_thread["messages"].append(user_message)
        update_thread_title(current_thread, prompt)
        bump_thread(st.session_state.current_thread_id)  # type: ignore

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing your claim..."):
                use_all_files, selected_file_ids = active_scope_values(current_thread)
                response = requests.post(
                    f"{API_BASE_URL}/ask",
                    json={
                        "question": prompt,
                        "thread_id": st.session_state.current_thread_id,
                        "file_ids": selected_file_ids,
                        "history": history,
                        "model_id": current_thread.get("model_id"),
                        "search_all_files": use_all_files,
                    },
                    timeout=180,
                )

            if response.ok:
                data = response.json()
                assistant_message = {
                    "role": "assistant",
                    "content": data["answer"],
                    "sources": data.get("sources", []),
                }
            else:
                try:
                    detail = response.json().get("detail", response.text)
                except ValueError:
                    detail = response.text
                assistant_message = {
                    "role": "assistant",
                    "content": f"Request failed: {detail}",
                    "sources": [],
                }

            current_thread["messages"].append(assistant_message)
            render_assistant_message(assistant_message)
