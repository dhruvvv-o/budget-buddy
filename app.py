# app.py
import os
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# optionally import openai only if key present
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
try:
    if OPENAI_KEY:
        import openai
        openai.api_key = OPENAI_KEY
except Exception:
    openai = None

st.set_page_config(page_title="Budget Buddy", page_icon="💸", layout="centered")
st.title("💸 Budget Buddy — your friendly AI budgeting coach")
st.markdown("Enter your monthly income and expenses. Get a clear budget, a pie chart, and fast, prioritized tips to save more.")

# --- Sidebar Inputs ---
st.sidebar.header("Monthly Snapshot")
income = st.sidebar.number_input("Monthly income (enter 0 if none)", min_value=0.0, value=1000.0, step=50.0, format="%.2f")
savings_goal = st.sidebar.number_input("Savings goal per month (optional)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

st.sidebar.subheader("Common expenses (monthly)")
rent = st.sidebar.number_input("Rent / Housing", min_value=0.0, value=400.0, step=10.0, format="%.2f")
food = st.sidebar.number_input("Food / Groceries", min_value=0.0, value=150.0, step=5.0, format="%.2f")
transport = st.sidebar.number_input("Transport", min_value=0.0, value=50.0, step=5.0, format="%.2f")
subscriptions = st.sidebar.number_input("Subscriptions (streaming, apps)", min_value=0.0, value=20.0, step=1.0, format="%.2f")
utilities = st.sidebar.number_input("Utilities (electricity, internet)", min_value=0.0, value=40.0, step=1.0, format="%.2f")
debt_payment = st.sidebar.number_input("Debt payments (loans, credit)", min_value=0.0, value=0.0, step=10.0, format="%.2f")

# dynamic extra expenses list stored in session
if "extra_expenses" not in st.session_state:
    st.session_state.extra_expenses = []

st.sidebar.subheader("Add an extra expense")
extra_name = st.sidebar.text_input("Expense name", key="extra_name")
extra_amount = st.sidebar.number_input("Amount", min_value=0.0, value=0.0, key="extra_amount", step=5.0, format="%.2f")
if st.sidebar.button("Add expense"):
    if extra_name.strip() and extra_amount > 0:
        st.session_state.extra_expenses.append({"name": extra_name.strip(), "amount": float(extra_amount)})
        st.sidebar.success(f"Added {extra_name} — {extra_amount:.2f}")
    else:
        st.sidebar.error("Give a name and amount > 0")

if st.sidebar.button("Clear extras"):
    st.session_state.extra_expenses = []
    st.sidebar.info("Cleared extra expenses")

# --- Main App Logic ---
col1, col2 = st.columns([2,1])
with col1:
    st.header("Create your budget")
    st.write("Fill the left sidebar and press **Generate budget**.")
with col2:
    st.markdown("**Quick tips**\n- Try the 50/30/20 rule.\n- Add all recurring subscriptions so nothing surprises you.")

if st.button("Generate budget"):
    # consolidate expenses
    expenses = {
        "Rent": float(rent),
        "Food": float(food),
        "Transport": float(transport),
        "Subscriptions": float(subscriptions),
        "Utilities": float(utilities),
        "Debt payments": float(debt_payment),
    }
    for e in st.session_state.extra_expenses:
        expenses[e["name"]] = expenses.get(e["name"], 0.0) + float(e["amount"])

    df = pd.DataFrame(list(expenses.items()), columns=["Category", "Amount"])
    total_expenses = df["Amount"].sum()
    disposable = float(income) - total_expenses
    recommended = {"Needs": 0.5 * income, "Wants": 0.3 * income, "Savings": 0.2 * income}
    needs_categories = ["Rent", "Food", "Transport", "Utilities", "Debt payments"]
    needs_sum = df[df["Category"].isin(needs_categories)]["Amount"].sum()
    wants_sum = total_expenses - needs_sum

    # Summary boxes
    st.subheader("Budget summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Income", f"{income:.2f}")
    c2.metric("Total expenses", f"{total_expenses:.2f}")
    c3.metric("Disposable", f"{disposable:.2f}")

    st.markdown("**Recommended (50/30/20)**")
    st.write(f"- Needs target: {recommended['Needs']:.2f}")
    st.write(f"- Wants target: {recommended['Wants']:.2f}")
    st.write(f"- Savings target: {recommended['Savings']:.2f}")

    st.markdown("**Your current breakdown**")
    st.dataframe(df.style.format({"Amount": "{:.2f}"}), height=260)

    # Pie chart
    fig, ax = plt.subplots(figsize=(5,4))
    if total_expenses > 0:
        ax.pie(df["Amount"], labels=df["Category"], autopct="%1.1f%%", startangle=140)
    else:
        ax.text(0.5, 0.5, "No expenses entered", ha="center", va="center")
    ax.axis("equal")
    st.pyplot(fig)

    # Basic rule-based advice (always available)
    def rule_based_advice():
        adv = []
        if total_expenses > income:
            shortfall = total_expenses - income
            adv.append(f"You're spending {shortfall:.2f} more than your income. Cut wants or subscriptions first.")
        else:
            adv.append("Your expenses fit within your income — good start!")
        if subscriptions > 0.05 * income:
            adv.append(f"Subscriptions are {subscriptions:.2f}, which is >5% of income. Cancel unused services to save quickly.")
        if needs_sum > 0.6 * income:
            adv.append(f"Needs are {needs_sum:.2f} (~{needs_sum/income:.1%} of income). Aim to reduce rent or essential costs if possible.")
        if disposable < recommended["Savings"]:
            adv.append(f"You're under the 20% savings target. Try to increase savings by {recommended['Savings']-max(0, disposable):.2f}.")
        if savings_goal and savings_goal > 0:
            adv.append(f"Your stated savings goal is {savings_goal:.2f} per month — compare it to your current savings rate and adjust.")
        if not adv:
            adv.append("Looks healthy — consider automating your savings.")
        return "\n\n".join(adv)

    basic_advice = rule_based_advice()
    st.subheader("Budget Coach (fast tips)")
    st.write(basic_advice)

    # Advanced AI advice if key present
    st.subheader("AI-powered suggestions (optional)")
    if OPENAI_KEY and openai:
        prompt = (
            f"User monthly income: {income}\n"
            f"User expenses: {expenses}\n"
            f"Provide 6 short, prioritized, actionable suggestions to improve this user's monthly budget. "
            "Keep language friendly, concise, and include one quick 'first action' the user can do in 5 minutes."
        )
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"system","content":"You are a friendly financial coach for students."},
                          {"role":"user","content":prompt}],
                max_tokens=300,
                temperature=0.7
            )
            ai_text = resp["choices"][0]["message"]["content"].strip()
            st.write(ai_text)
        except Exception as e:
            st.error("AI call failed — falling back to rule-based tips.")
            st.write(basic_advice)
    else:
        st.info("No OpenAI key found. Add OPENAI_API_KEY to Replit Secrets for richer AI suggestions.")
        st.write(basic_advice)

    # Download CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download budget CSV", csv, "budget.csv", "text/csv")

# --- Explain term box ---
st.markdown("---")
st.header("Explain a financial term")
term = st.text_input("Enter a term (APR, emergency fund, compound interest, credit score...)")
eli12 = st.checkbox("Explain like I'm 12", value=True)
if st.button("Explain"):
    fallback_explanations = {
        "apr": "APR (Annual Percentage Rate) is the yearly cost of borrowing money, including interest and fees. Lower is better.",
        "emergency fund": "An emergency fund is money you save for unexpected costs like medical bills or sudden repairs. Aim for 3-6 months of living costs.",
        "compound interest": "Compound interest is 'interest on interest' — your money grows faster because interest gets added to the balance, then interest is calculated on the new total.",
        "credit score": "A credit score is a number that shows how reliable you are at paying back loans. Higher means lenders trust you more."
    }
    term_lower = (term or "").strip().lower()
    if OPENAI_KEY and openai:
        prompt = f"Explain '{term}' in one paragraph. Make it {'very simple' if eli12 else 'concise and clear'} and include one quick tip."
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"system","content":"You are a friendly explainer for everyday people."},
                          {"role":"user","content":prompt}],
                max_tokens=150,
                temperature=0.7
            )
            st.write(resp["choices"][0]["message"]["content"])
        except Exception:
            st.write(fallback_explanations.get(term_lower, "Sorry, no definition available offline. Try adding an OpenAI key."))
    else:
        st.write(fallback_explanations.get(term_lower, "No offline explanation available for that term. Add an OpenAI key to get live explanations."))

st.markdown("**Disclaimer:** Budget Buddy provides educational suggestions, not professional financial advice.")
