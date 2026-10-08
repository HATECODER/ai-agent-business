"""BizPilot AI local demo dashboard."""

import logging
from datetime import datetime, timezone

import streamlit as st

from agent import ask_copilot
from config import ai_mode, api_key_available, deployment_mode, gemini_key_available
from database.db import connect, prepare_database
from database.seed import today
from security.auth import AuthorizationError, actor_from_claims, demo_actor, require_owner
from services.actions import execute_proposal, list_pending_proposals, propose_action, reject_proposal
from services.data_evidence import bounded_rows, data_evidence
from services.run_policy import RunLimitError, daily_usage
from tools.finance import get_financial_summary
from tools.growth import get_inactive_customers
from tools.operations import get_inventory, get_low_stock_products, get_pending_tasks


logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="BizPilot AI", page_icon="📊", layout="wide")


def current_actor():
    if deployment_mode() == "demo":
        return demo_actor()
    if not st.user.is_logged_in:
        st.title("BizPilot AI")
        st.caption("Restricted synthetic-data evaluation pilot")
        st.button("Sign in", on_click=st.login, type="primary")
        st.stop()

    claims = dict(st.user)
    identity_key = f"{claims.get('iss', '')}|{claims.get('sub', '')}"
    if st.session_state.get("identity_key") != identity_key:
        for key in ("chat_messages", "sdk_history", "campaign_brief"):
            st.session_state.pop(key, None)
        st.session_state.identity_key = identity_key
        st.session_state.auth_started_at = datetime.now(timezone.utc)
    try:
        actor = actor_from_claims(claims, st.session_state.auth_started_at)
    except AuthorizationError as error:
        st.error(str(error))
        if claims.get("iss") and claims.get("sub"):
            st.caption("Authenticated identity for administrator allowlisting:")
            st.code(identity_key)
        st.button("Sign out", on_click=st.logout)
        st.stop()
    if st.button("Sign out"):
        for key in list(st.session_state):
            del st.session_state[key]
        st.logout()
    return actor


def show_rows(rows: list[dict]) -> dict:
    page = bounded_rows(rows)
    st.dataframe(page["items"], width="stretch", hide_index=True)
    if page["truncated"]:
        st.caption(f"Showing {page['returned_count']} of {page['total_count']} rows.")
    return page


actor = current_actor()
try:
    require_owner(actor)
    prepare_database()
except (AuthorizationError, RuntimeError, ValueError) as error:
    st.error(str(error))
    st.stop()

evidence = data_evidence()
if st.session_state.get("history_version") != 2:
    st.session_state.pop("chat_messages", None)
    st.session_state.pop("sdk_history", None)
    st.session_state.history_version = 2

st.title("BizPilot AI")
st.caption("A local business operations copilot for Bangladeshi SMEs · fictional demo data · BDT")
st.caption(
    f"Source: {evidence['source']} · version: {evidence['dataset_version']} · "
    f"snapshot seeded: {evidence['dataset_seeded_at'] or 'unknown'} · queried: {evidence['queried_at']}"
)

copilot_tab, operations_tab, growth_tab, finance_tab, approvals_tab = st.tabs(
    ["AI Copilot", "Operations", "Growth", "Finance", "Approvals"])

with copilot_tab:
    st.subheader("Ask BizPilot")
    if ai_mode() == "offline":
        st.info("Offline demo mode: rule-based replies using real local data. No API call or model-generated answer.")
    elif ai_mode() == "gemini" and not gemini_key_available():
        st.info("Gemini mode needs GEMINI_API_KEY in .env. Use offline mode without a key.")
    elif ai_mode() == "gemini":
        st.info("Gemini model mode. Free-tier limits depend on your Google AI Studio project.")
    elif not api_key_available():
        st.info("AI chat needs OPENAI_API_KEY in .env. Operations, Growth, and Finance remain available.")
    if ai_mode() != "offline":
        usage = daily_usage()
        st.caption(
            f"AI budget today: ${usage['used_or_reserved_usd']:.4f} used/reserved "
            f"of ${usage['daily_budget_usd']:.2f}."
        )
    st.caption("Try: kon product stock kom? · ajker financial summary dao · ajke amar ki ki kora uchit?")
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "sdk_history" not in st.session_state:
        st.session_state.sdk_history = []
    for item in st.session_state.chat_messages:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
    prompt = st.chat_input("Ask in English, Bangla, or Banglish")
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Checking business data..."):
                try:
                    require_owner(actor)
                    answer, history = ask_copilot(prompt, st.session_state.sdk_history, actor=actor)
                    st.session_state.sdk_history = history
                except (AuthorizationError, RunLimitError, ValueError, RuntimeError) as error:
                    answer = str(error)
            st.markdown(answer)
        st.session_state.chat_messages.append({"role": "assistant", "content": answer})

with operations_tab:
    st.subheader("Inventory and tasks")
    inventory = get_inventory()
    low_stock = get_low_stock_products()
    pending = get_pending_tasks()
    a, b = st.columns(2)
    a.metric("Low-stock variants", len(low_stock))
    b.metric("Open tasks", len(pending))
    st.markdown("#### Inventory")
    show_rows(inventory)
    if st.button("Propose low-stock review tasks", type="primary"):
        try:
            require_owner(actor)
            proposal = propose_action("run_restock_review", {}, actor)
            st.success(
                f"Proposal {proposal['id']} is pending in Approvals. No task or purchase was created."
            )
        except Exception:
            logging.warning("Inventory proposal failed")
            st.error("The proposal failed. Check the local database and retry.")
    st.markdown("#### Pending and in-progress tasks")
    show_rows(pending)

with growth_tab:
    st.subheader("Customer re-engagement")
    days = st.selectbox("Inactive for", [7, 30, 60], index=1,
                        format_func=lambda value: f"{value} days")
    inactive = get_inactive_customers(days)
    st.metric("Inactive customers", len(inactive))
    show_rows(inactive)
    if st.button("Propose campaign draft"):
        try:
            require_owner(actor)
            proposal = propose_action(
                "create_campaign_draft",
                {
                    "segment_description": (
                        f"Customers with no delivered purchase in {days} days ({len(inactive)} customers)"),
                    "objective": "Re-engage inactive customers",
                    "offer": None,
                    "channel": "facebook",
                },
                actor,
            )
            st.success(
                f"Proposal {proposal['id']} is pending in Approvals. Nothing was saved or sent."
            )
        except Exception:
            logging.warning("Campaign proposal failed")
            st.error("Could not create the campaign proposal.")
    with connect() as db:
        latest = db.execute("SELECT name, status, channel FROM campaigns ORDER BY id DESC LIMIT 1").fetchone()
    if latest:
        st.caption(f"Latest confirmed campaign draft: {latest['name']} · {latest['status']} · {latest['channel']}")

with finance_tab:
    st.subheader("Today's finances")
    st.caption(f"Bangladesh date: {today().date().isoformat()} · confirmed and delivered orders count as sales")
    finance = get_financial_summary()
    top = st.columns(3)
    top[0].metric("Revenue", f"৳{finance['revenue']:,.0f}")
    top[1].metric("Receipts on today's orders", f"৳{finance['order_cohort_receipts']:,.0f}")
    top[2].metric("Today's dated expenses", f"৳{finance['dated_expenses']:,.0f}")
    bottom = st.columns(3)
    bottom[0].metric("Cohort receipts − expenses",
                     f"৳{finance['order_cohort_receipts_less_dated_expenses']:,.0f}")
    bottom[1].metric("Receivable on today's orders", f"৳{finance['order_cohort_receivable']:,.0f}")
    bottom[2].metric("Sales orders", finance["order_count"])
    st.warning(finance["metric_note"])

with approvals_tab:
    st.subheader("Pending owner approvals")
    st.caption("Confirm the exact payload below. Editing it requires a new proposal.")
    proposals = list_pending_proposals(actor)
    if not proposals:
        st.info("No pending proposals.")
    for proposal in proposals:
        st.markdown(f"#### {proposal['action_type']} · `{proposal['id']}`")
        st.json(proposal["payload"])
        confirm_col, reject_col = st.columns(2)
        if confirm_col.button("Confirm exact action", key=f"confirm-{proposal['id']}", type="primary"):
            try:
                require_owner(actor)
                result = execute_proposal(proposal["id"], actor)
                st.success(f"Action completed: {result}")
                st.rerun()
            except (AuthorizationError, ValueError, RuntimeError) as error:
                st.error(str(error))
        if reject_col.button("Reject", key=f"reject-{proposal['id']}"):
            try:
                require_owner(actor)
                reject_proposal(proposal["id"], actor)
                st.info("Proposal rejected.")
                st.rerun()
            except (AuthorizationError, ValueError) as error:
                st.error(str(error))
