"""BizPilot AI local demo dashboard."""

import logging

import streamlit as st

from agent import ask_copilot
from config import ai_mode, api_key_available, gemini_key_available
from database.db import connect, ensure_demo_data
from database.seed import today
from tools.finance import get_financial_summary
from tools.growth import create_campaign_brief, get_inactive_customers
from tools.operations import get_inventory, get_low_stock_products, get_pending_tasks
from workflows.inventory_workflow import run_low_stock_workflow


logging.basicConfig(level=logging.INFO)
st.set_page_config(page_title="BizPilot AI", page_icon="📊", layout="wide")
ensure_demo_data()

st.title("BizPilot AI")
st.caption("A local business operations copilot for Bangladeshi SMEs · fictional demo data · BDT")

copilot_tab, operations_tab, growth_tab, finance_tab = st.tabs(
    ["AI Copilot", "Operations", "Growth", "Finance"])

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
                    answer, history = ask_copilot(prompt, st.session_state.sdk_history)
                    st.session_state.sdk_history = history
                except (ValueError, RuntimeError) as error:
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
    st.dataframe(inventory, width="stretch", hide_index=True)
    if st.button("Run low-stock workflow", type="primary"):
        try:
            result = run_low_stock_workflow()
            st.success(f"Checked {result['checked']} variants. Created {result['tasks_created']} task(s); "
                       f"{result['tasks_already_existing']} already open.")
            pending = get_pending_tasks()
        except Exception:
            logging.exception("Inventory workflow failed")
            st.error("The workflow failed. Check the local database and retry.")
    st.markdown("#### Pending and in-progress tasks")
    st.dataframe(pending, width="stretch", hide_index=True)

with growth_tab:
    st.subheader("Customer re-engagement")
    days = st.selectbox("Inactive for", [7, 30, 60], index=1,
                        format_func=lambda value: f"{value} days")
    inactive = get_inactive_customers(days)
    st.metric("Inactive customers", len(inactive))
    st.dataframe(inactive, width="stretch", hide_index=True)
    if st.button("Create draft campaign brief"):
        try:
            brief = create_campaign_brief(
                f"Customers with no delivered purchase in {days} days ({len(inactive)} customers)",
                "Re-engage inactive customers",
            )
            st.session_state.campaign_brief = brief
        except Exception:
            logging.exception("Campaign draft failed")
            st.error("Could not create the campaign draft.")
    if st.session_state.get("campaign_brief"):
        brief = st.session_state.campaign_brief
        st.info("Draft only — no campaign has been sent or published.")
        st.markdown(f"**{brief['campaign_name']}** · {brief['channel']}")
        st.write(brief["message_en"])
        st.write(brief["message_bn_or_banglish"])
    else:
        with connect() as db:
            latest = db.execute("SELECT name, status, channel FROM campaigns ORDER BY id DESC LIMIT 1").fetchone()
        if latest:
            st.caption(f"Latest campaign: {latest['name']} · {latest['status']} · {latest['channel']}")

with finance_tab:
    st.subheader("Today's finances")
    st.caption(f"Bangladesh date: {today().date().isoformat()} · confirmed and delivered orders count as sales")
    finance = get_financial_summary()
    top = st.columns(3)
    top[0].metric("Revenue", f"৳{finance['revenue']:,.0f}")
    top[1].metric("Amount received", f"৳{finance['amount_received']:,.0f}")
    top[2].metric("Expenses", f"৳{finance['expenses']:,.0f}")
    bottom = st.columns(3)
    bottom[0].metric("Net cash flow", f"৳{finance['net_cash_flow']:,.0f}")
    bottom[1].metric("Receivable", f"৳{finance['receivable']:,.0f}")
    bottom[2].metric("Sales orders", finance["order_count"])
    st.caption("Net cash flow = amount received − expenses. Unpaid portions of counted sales are receivables.")
