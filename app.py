# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect('budget_data.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS data (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_data(data_dict):
    conn = sqlite3.connect('budget_data.db')
    c = conn.cursor()
    for key, value in data_dict.items():
        processed_value = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
        c.execute("INSERT OR REPLACE INTO data (key, value) VALUES (?, ?)", (key, processed_value))
    conn.commit()
    conn.close()

def load_data():
    try:
        conn = sqlite3.connect('budget_data.db')
        c = conn.cursor()
        c.execute("SELECT key, value FROM data")
        rows = c.fetchall()
        conn.close()
        data = {}
        for key, value in rows:
            try:
                data[key] = json.loads(value)
            except:
                try:
                    data[key] = float(value)
                except:
                    data[key] = value
        return data
    except:
        return {}

# --- Dashboard Function for Budget Calculator ---
def display_dashboard(income, savings_goal, subscriptions, df):
    total_expenses = df["Amount"].sum()
    disposable = income - total_expenses
    st.subheader("📊 Your Financial Snapshot")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Income", f"{income:,.2f}")
    col2.metric("Expenses", f"{total_expenses:,.2f}")
    col3.metric("Disposable", f"{disposable:,.2f}")
    col4.metric("Savings Goal", f"{savings_goal:,.2f}")

    if savings_goal > 0:
        progress = disposable / savings_goal
        progress_clamped = max(0.0, min(progress, 1.0))
        st.progress(progress_clamped)
        st.markdown(f"**Savings Goal Progress:** {progress*100:.1f}%")

# --- Initialize ---
st.set_page_config(page_title="Budget Buddy", page_icon="💸", layout="wide")
init_db()

if 'income' not in st.session_state:
    loaded_data = load_data()
    st.session_state.update({
        'income': loaded_data.get('income', 3000.0),
        'savings_goal': loaded_data.get('savings_goal', 500.0),
        'rent': loaded_data.get('rent', 800.0),
        'food': loaded_data.get('food', 400.0),
        'transport': loaded_data.get('transport', 150.0),
        'subscriptions': loaded_data.get('subscriptions', 50.0),
        'utilities': loaded_data.get('utilities', 100.0),
        'debt_payment': loaded_data.get('debt_payment', 0.0),
        'extra_expenses': loaded_data.get('extra_expenses', []),
        'expense_key': 0
    })

# --- Sidebar Navigation ---
st.sidebar.title("💸 Budget Buddy Menu")
page = st.sidebar.radio("Go to:", ["Budget Calculator", "Scenario Simulator"])

# --- Budget Calculator Page ---
if page == "Budget Calculator":
    st.title("💸 Budget Calculator")
    st.subheader("💰 Income & Savings Goal")
    col1, col2 = st.columns(2)
    col1.number_input("Monthly Income", key='income', min_value=0.0, step=1.0, format="%.2f")
    col2.number_input("Monthly Savings Goal", key='savings_goal', min_value=0.0, step=1.0, format="%.2f")

    st.subheader("🧾 Fixed Monthly Expenses")
    col1, col2, col3 = st.columns(3)
    col1.number_input("Rent / Housing", key='rent', min_value=0.0, step=1.0)
    col1.number_input("Food / Groceries", key='food', min_value=0.0, step=1.0)
    col2.number_input("Transport", key='transport', min_value=0.0, step=1.0)
    col2.number_input("Subscriptions", key='subscriptions', min_value=0.0, step=1.0)
    col3.number_input("Utilities", key='utilities', min_value=0.0, step=1.0)
    col3.number_input("Debt Payments", key='debt_payment', min_value=0.0, step=1.0)

    st.subheader("➕ Extra Expenses")
    col1, col2, col3 = st.columns([2,1,1])
    extra_name_key = f"extra_name_input_{st.session_state.expense_key}"
    extra_amount_key = f"extra_amount_input_{st.session_state.expense_key}"
    col1.text_input("Expense Name", "", placeholder="e.g., Coffee, Gym", key=extra_name_key)
    col2.number_input("Amount", min_value=0.0, value=0.0, step=1.0, format="%.2f", key=extra_amount_key)
    with col3:
        st.markdown("<div style='height: 29px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Add Expense", use_container_width=True, type="primary"):
            name = st.session_state[extra_name_key].strip()
            amount = st.session_state[extra_amount_key]
            if name and amount > 0:
                st.session_state.extra_expenses.append({"name": name, "amount": float(amount)})
                st.success(f"Added '{name}' to your expenses.")
                st.session_state.expense_key += 1
            else:
                st.error("Enter a valid name and amount > 0.")

    if st.session_state.extra_expenses:
        st.markdown("**Your Added Expenses:**")
        for i, expense in enumerate(st.session_state.extra_expenses):
            exp_col1, exp_col2, exp_col3 = st.columns([2,1,0.5])
            exp_col1.write(f"- {expense['name']}")
            exp_col2.write(f"{expense['amount']:,.2f}")
            if exp_col3.button("🗑️", key=f"delete_{i}", type="secondary"):
                st.session_state.extra_expenses.pop(i)

    st.markdown("---")
    if st.button("🚀 Generate & Save Budget", use_container_width=True, type="primary"):
        expenses_dict = {
            "Rent": st.session_state.rent,
            "Food": st.session_state.food,
            "Transport": st.session_state.transport,
            "Subscriptions": st.session_state.subscriptions,
            "Utilities": st.session_state.utilities,
            "Debt Payments": st.session_state.debt_payment
        }
        for e in st.session_state.extra_expenses:
            expenses_dict[e["name"]] = expenses_dict.get(e["name"],0) + e["amount"]
        filtered_expenses = {k:v for k,v in expenses_dict.items() if v>0}
        if filtered_expenses:
            df = pd.DataFrame(list(filtered_expenses.items()), columns=["Category","Amount"])
            display_dashboard(st.session_state.income, st.session_state.savings_goal, st.session_state.subscriptions, df)
            save_data({key: st.session_state[key] for key in ['income','savings_goal','rent','food','transport','subscriptions','utilities','debt_payment','extra_expenses']})

# --- Scenario Simulator Page ---
elif page == "Scenario Simulator":
    st.title("🔮 Scenario Simulator")
    st.markdown("Adjust your expenses to see how they affect disposable income and savings goal.")

    income = st.number_input("Income", value=st.session_state.income, step=1.0)
    savings_goal = st.number_input("Savings Goal", value=st.session_state.savings_goal, step=1.0)

    expenses = {}
    st.subheader("Fixed Expenses")
    for key in ['rent','food','transport','subscriptions','utilities','debt_payment']:
        expenses[key] = st.number_input(key.replace("_"," ").title(), value=st.session_state[key], step=1.0)

    st.subheader("Extra Expenses")
    for i, exp in enumerate(st.session_state.extra_expenses):
        expenses[exp['name']] = st.number_input(exp["name"], value=exp['amount'], step=1.0)

    total_expenses = sum(expenses.values())
    disposable = income - total_expenses

    st.markdown("---")
    st.metric("Total Expenses", f"{total_expenses:,.2f}")
    st.metric("Disposable Income", f"{disposable:,.2f}")

    # --- Live Bar Chart ---
    scenario_df = pd.DataFrame({
        "Category": ["Total Expenses", "Disposable Income", "Savings Goal"],
        "Amount": [total_expenses, disposable, savings_goal]
    })
    fig = px.bar(scenario_df, x="Category", y="Amount", color="Category",
                 color_discrete_sequence=["#ff4b4b","#28a745","#ffc400"],
                 text="Amount", title="Financial Scenario Projection")
    fig.update_traces(texttemplate='%{text:,.2f}', textposition='outside')
    fig.update_layout(yaxis_title="Amount", xaxis_title="", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- Interactive Savings Goal Timeline ---
    if disposable > 0:
        months_to_goal = savings_goal / disposable
        st.subheader("⏳ Savings Goal Timeline")
        st.markdown(f"At your current disposable income, it will take approximately **{months_to_goal:.1f} months** to reach your savings goal.")

        timeline_df = pd.DataFrame({
            "Month": range(1, int(months_to_goal)+2),
            "Cumulative Savings": [disposable * m for m in range(1, int(months_to_goal)+2)]
        })
        timeline_df.loc[timeline_df["Cumulative Savings"] > savings_goal, "Cumulative Savings"] = savings_goal  # cap at goal
        fig_timeline = px.line(
            timeline_df,
            x="Month",
            y="Cumulative Savings",
            title="Savings Goal Progress Over Time",
            markers=True
        )
        fig_timeline.update_layout(yaxis_title="Cumulative Savings", xaxis_title="Month")
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.info("Your expenses exceed your income. Increase income or reduce expenses to start saving.")
