"""Dukan AI - Digital Munshi for Small Shops"""
import streamlit as st
from PIL import Image
import pandas as pd

import config
import database
import ai_engine
import stock_counter
import voice_assistant
import utils

# Page configuration must be at the top level
st.set_page_config(
    page_title="Dukan AI - Digital Munshi",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Sidebar Completely
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

# Initialize database
database.init_db()

# Initialize session state for auth
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def show_auth_page():
    st.title("🏪 Dukan AI Login")
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab_login, tab_signup = st.tabs(["Login", "Create Account"])
        
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submit_login = st.form_submit_button("Login")
                
                if submit_login:
                    if database.check_user(email, password):
                        st.session_state.logged_in = True
                        st.success("Login Successful!")
                        st.rerun()
                    else:
                        st.error("Ghalat Email ya Password")
                        
        with tab_signup:
            with st.form("signup_form"):
                new_email = st.text_input("Email", key="signup_email")
                new_password = st.text_input("Password", type="password", key="signup_password")
                submit_signup = st.form_submit_button("Sign Up")
                
                if submit_signup:
                    if new_email and new_password:
                        if database.add_user(new_email, new_password):
                            st.success("Account created successfully! Please log in.")
                        else:
                            st.error("Account already exists with this email.")
                    else:
                        st.warning("Please fill in all fields.")

# GATE - If not logged in, show Auth Page and stop execution
if not st.session_state.logged_in:
    show_auth_page()
    st.stop()

# DASHBOARD HEADER WITH LOGOUT
head_col1, head_col2, head_col3 = st.columns([6, 2, 2])

with head_col1:
    st.title("🏪 Dukan AI")
    st.caption("Digital Munshi - اب کا ڈیجٹل منشی")

# API Key config
api_key = st.secrets["GEMINI_API_KEY"]
config.GEMINI_API_KEY = api_key
ai_engine._client = None

with head_col2:
    alerts = database.get_low_stock_alerts()
    if alerts:
        st.warning(f"⚠️ {len(alerts)} Low Stock")
    else:
        st.success("✅ Stock OK")

with head_col3:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.divider()
st.caption("Built with Streamlit + Gemini + YOLO")
tab_dashboard, tab_stock, tab_photo, tab_pricing, tab_chat, tab_sales = st.tabs(
    ["📊 Dashboard", "📦 Stock", "📸 Photo Counter",
     "💰 Smart Pricing", "💬 AI Chat", "🧾 Sales"]
)

with tab_dashboard:
    st.header(utils.time_greeting())
    st.subheader(f"Welcome to {config.SHOP_NAME}")

    stats = database.get_dashboard_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Total Products", stats["total_products"])
    col2.metric("💰 Stock Value", utils.format_pkr(stats["stock_value"]))
    col3.metric("📈 Today's Sales", utils.format_pkr(stats["sales_today"]))
    col4.metric("⚠ Low Stock Items", stats["low_stock_count"])

    st.divider()
    df = database.get_all_products()

    if not df.empty:
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("📂 Stock by Category")
            cat_summary = df.groupby("category").agg(
                items=("id", "count"),
                total_value=("cost_price",
                             lambda x: (x * df.loc[x.index, "quantity"]).sum()),
            ).reset_index()
            st.dataframe(cat_summary, use_container_width=True, hide_index=True)

        with col_right:
            st.subheader("⚠ Low Stock Items")
            if alerts:
                for a in alerts:
                    level_label, _ = utils.stock_level_badge(
                        a["quantity"], a["max_stock"]
                    )
                    st.markdown(
                        f"- **{a['name']}** ({a['name_urdu'] or ''}) — "
                        f"{a['quantity']} {a['unit']} — **{level_label}**"
                    )
            else:
                st.info("All items well stocked!")

        st.subheader("📊 Stock Levels Overview")
        chart_data = df[["name", "quantity", "max_stock"]].copy()
        chart_data["stock_pct"] = (
            chart_data["quantity"] / chart_data["max_stock"] * 100
        ).round(1)
        chart_data = chart_data.sort_values("stock_pct")
        st.bar_chart(chart_data.set_index("name")["stock_pct"])

with tab_stock:
    st.header("📦 Stock Management")

    with st.expander("➕ Add New Product"):
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Product Name (English)")
            new_urdu = st.text_input("Product Name (Urdu)")
            new_category = st.selectbox(
                "Category",
                ["Grocery", "Spices", "Beverages", "Dairy", "Bakery",
                 "Household", "Clothes", "Electronics", "Other"],
            )
            new_cost = st.number_input(
                "Cost Price (PKR)", min_value=0.0, step=10.0
            )
        with col2:
            new_sell = st.number_input(
                "Sell Price (PKR)", min_value=0.0, step=10.0
            )
            new_qty = st.number_input("Quantity", min_value=0.0, step=1.0)
            new_unit = st.selectbox(
                "Unit", ["pcs", "kg", "ltr", "dozen", "box"]
            )
            new_max = st.number_input(
                "Max Stock", min_value=1.0, value=50.0, step=5.0
            )
            new_yolo = st.text_input(
                "YOLO label (optional)",
                help="Example: bottle, cup, person. Use a label the YOLO model can detect.",
            )

        if st.button("Add Product", type="primary"):
            if new_name.strip():
                try:
                    database.add_product(
                        new_name.strip(), new_urdu.strip(), new_category,
                        new_cost, new_sell, new_qty, new_unit, new_max,
                        new_yolo.strip() or None,
                    )
                    st.success(f"Added '{new_name}' successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a product name.")

    st.divider()
    df = database.get_all_products()

    if df.empty:
        st.info("No products yet.")
    else:
        col_search, col_cat = st.columns([2, 1])
        with col_search:
            search = st.text_input("🔍 Search products...", key="stock_search")
        with col_cat:
            categories = ["All"] + df["category"].unique().tolist()
            selected_cat = st.selectbox(
                "Category filter", categories, key="stock_cat"
            )

        filtered = df.copy()
        if search:
            mask = (
                filtered["name"].str.contains(search, case=False, na=False)
                | filtered["name_urdu"].fillna("").str.contains(
                    search, case=False, na=False
                )
            )
            filtered = filtered[mask]
        if selected_cat != "All":
            filtered = filtered[filtered["category"] == selected_cat]

        for _, row in filtered.iterrows():
            level_label, _ = utils.stock_level_badge(
                row["quantity"], row["max_stock"]
            )
            margin = utils.profit_margin(
                row["cost_price"], row["sell_price"]
            )

            with st.expander(
                f"**{row['name']}** ({row['name_urdu'] or ''}) — "
                f"{row['quantity']} {row['unit']} @ "
                f"{utils.format_pkr(row['sell_price'])} [{level_label}]"
            ):
                c1, c2, c3 = st.columns(3)
                c1.metric("Cost Price", utils.format_pkr(row["cost_price"]))
                c2.metric("Sell Price", utils.format_pkr(row["sell_price"]))
                c3.metric("Margin", f"{margin:.1f}%")

                a1, a2, a3, a4 = st.columns(4)
                with a1:
                    sell_qty = st.number_input(
                        "Sell qty", min_value=0.0, step=1.0,
                        key=f"sell_{row['id']}",
                    )
                    if st.button(
                        "💸 Record Sale", key=f"btn_sell_{row['id']}"
                    ):
                        if sell_qty > 0:
                            try:
                                database.record_sale(int(row["id"]), sell_qty)
                                st.success(f"Sold {sell_qty} {row['unit']}!")
                                st.rerun()
                            except ValueError as e:
                                st.error(str(e))

                with a2:
                    restock_qty = st.number_input(
                        "Restock qty", min_value=0.0, step=1.0,
                        key=f"restock_{row['id']}",
                    )
                    if st.button(
                        "📥 Restock", key=f"btn_restock_{row['id']}"
                    ):
                        if restock_qty > 0:
                            database.record_restock(
                                int(row["id"]), restock_qty
                            )
                            st.success(
                                f"Added {restock_qty} {row['unit']}!"
                            )
                            st.rerun()

                with a3:
                    new_price = st.number_input(
                        "New sell price", min_value=0.0,
                        value=float(row["sell_price"]), step=5.0,
                        key=f"price_{row['id']}",
                    )
                    if st.button(
                        "✏ Update Price", key=f"btn_price_{row['id']}"
                    ):
                        database.update_prices(
                            int(row["id"]), float(row["cost_price"]), new_price
                        )
                        st.success("Price updated!")
                        st.rerun()

                with a4:
                    if st.button("🗑 Delete", key=f"btn_del_{row['id']}"):
                        database.delete_product(int(row["id"]))
                        st.success("Deleted!")
                        st.rerun()

with tab_photo:
    st.header("📸 Stock Photo Counter")
    st.caption("Upload a photo of your shelf → AI counts detectable objects")

    uploaded_file = st.file_uploader(
        "📷 Upload shelf photo",
        type=["jpg", "jpeg", "png"],
    )

    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        col_original, col_annotated = st.columns(2)

        with col_original:
            st.subheader("Original Photo")
            st.image(image, use_container_width=True)

        with st.spinner("🔍 Analysing shelf with AI..."):
            try:
                result = stock_counter.full_analysis(image)
            except Exception as e:
                st.error(f"Detection error: {e}")
                result = None

        if result:
            with col_annotated:
                st.subheader("AI Detection Result")
                st.image(result["annotated_image"], use_container_width=True)

            if result["counts"]:
                st.subheader("📊 Detected Items")
                count_df = pd.DataFrame(result["counts"])
                count_df.columns = ["Item Detected", "Count"]
                st.dataframe(count_df, use_container_width=True, hide_index=True)
            else:
                st.warning("No items detected. Try a clearer photo.")

            df = database.get_all_products()
            matches = stock_counter.match_detections_to_products(
                result["counts"], df
            )

            if matches:
                st.subheader("🔗 Matched to Your Inventory")
                for m in matches:
                    st.markdown(
                        f"- **{m['product_name']}**: detected "
                        f"{m['detected_count']} "
                        f"(current stock: {m['current_stock']} {m['unit']})"
                    )
                    if st.button(
                        f"✅ Update stock to {m['detected_count']}",
                        key=f"match_{m['product_id']}",
                    ):
                        database.update_stock(
                            m["product_id"], m["detected_count"]
                        )
                        st.success(
                            f"Updated {m['product_name']} stock!"
                        )
                        st.rerun()

            if result["unmatched_labels"]:
                st.info(
                    "Unmatched detections: "
                    + ", ".join(result["unmatched_labels"])
                )

            st.subheader("🤖 AI Stock Analysis")
            with st.spinner("Asking AI for advice..."):
                st.markdown(ai_engine.analyze_stock_image(result["counts"]))

with tab_pricing:
    st.header("💰 Smart Pricing Advisor")
    st.caption("AI suggests prices from cost and desired profit margin")

    col1, col2 = st.columns(2)
    df = database.get_all_products()

    with col1:
        st.subheader("From Inventory")
        if not df.empty:
            product_names = df["name"].tolist()
            selected = st.selectbox("Select product", product_names)
            selected_row = df[df["name"] == selected].iloc[0]
            st.metric(
                "Current Cost Price",
                utils.format_pkr(selected_row["cost_price"])
            )
            st.metric(
                "Current Sell Price",
                utils.format_pkr(selected_row["sell_price"])
            )
            default_margin = int(
                max(5, min(50, utils.profit_margin(
                    selected_row["cost_price"], selected_row["sell_price"]
                )))
            )
            margin_input = st.slider(
                "Desired profit margin (%)", 5, 50, default_margin
            )
            if st.button("🤖 Get AI Price Suggestion", key="price_inv"):
                with st.spinner("Analysing..."):
                    st.markdown(ai_engine.suggest_price(
                        selected_row["name"],
                        selected_row["cost_price"],
                        margin_input,
                    ))
        else:
            st.info("Add products first.")

    with col2:
        st.subheader("New Product Pricing")
        new_prod_name = st.text_input("Product name")
        new_prod_cost = st.number_input(
            "Cost price (PKR)", min_value=0.0, step=10.0
        )
        new_prod_margin = st.slider(
            "Desired margin (%)", 5, 50, 15, key="new_margin"
        )
        if st.button("🤖 Get AI Price Suggestion", key="price_new"):
            if new_prod_name and new_prod_cost > 0:
                with st.spinner("Analysing..."):
                    st.markdown(ai_engine.suggest_price(
                        new_prod_name, new_prod_cost, new_prod_margin
                    ))
            else:
                st.warning("Please enter product name and cost price.")

    st.divider()
    st.subheader("📊 Current Margins Overview")
    if not df.empty:
        pricing_df = df[
            ["name", "cost_price", "sell_price", "category"]
        ].copy()
        pricing_df["margin_pct"] = pricing_df.apply(
            lambda r: utils.profit_margin(
                r["cost_price"], r["sell_price"]
            ), axis=1
        ).round(1)
        pricing_df["profit_per_unit"] = (
            pricing_df["sell_price"] - pricing_df["cost_price"]
        ).round(2)
        pricing_df = pricing_df.sort_values(
            "margin_pct", ascending=False
        )
        st.dataframe(
            pricing_df, use_container_width=True, hide_index=True
        )

with tab_chat:
    st.header("💬 Dukan AI Chat")
    st.caption("Ask about your shop in English, Roman Urdu, or Urdu")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input(
        "Ask Dukan AI anything... e.g. 'chawal ka kya rate hai?'"
    )

    if user_input:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        cmd = utils.parse_voice_command(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
                if cmd["action"] == "sell":
                    df = database.get_all_products()
                    match = df[
                        df["name"].str.contains(
                            cmd["product"], case=False, na=False
                        )
                    ]
                    if not match.empty:
                        prod = match.iloc[0]
                        try:
                            database.record_sale(
                                int(prod["id"]), cmd["quantity"]
                            )
                            reply = (
                                f"✅ Sold {cmd['quantity']} {prod['unit']} of "
                                f"**{prod['name']}** for "
                                f"{utils.format_pkr(cmd['quantity'] * prod['sell_price'])}!"
                            )
                        except ValueError as e:
                            reply = f"❌ {e}"
                    else:
                        reply = (
                            f"Sorry, I couldn't find a product matching "
                            f"'{cmd['product']}'."
                        )

                elif cmd["action"] == "query":
                    df = database.get_all_products()
                    match = df[
                        df["name"].str.contains(
                            cmd["product"], case=False, na=False
                        )
                    ]
                    if not match.empty:
                        prod = match.iloc[0]
                        reply = (
                            f"**{prod['name']}** ({prod['name_urdu'] or ''}): "
                            f"{prod['quantity']} {prod['unit']} in stock. "
                            f"Selling at {utils.format_pkr(prod['sell_price'])}."
                        )
                    else:
                        reply = (
                            f"Sorry, I couldn't find a product matching "
                            f"'{cmd['product']}'."
                        )

                elif cmd["action"] == "restock":
                    df = database.get_all_products()
                    match = df[
                        df["name"].str.contains(
                            cmd["product"], case=False, na=False
                        )
                    ]
                    if not match.empty:
                        prod = match.iloc[0]
                        database.record_restock(
                            int(prod["id"]), cmd["quantity"]
                        )
                        reply = (
                            f"✅ Restocked **{prod['name']}** with "
                            f"{cmd['quantity']} {prod['unit']}!"
                        )
                    else:
                        reply = (
                            f"Sorry, I couldn't find a product matching "
                            f"'{cmd['product']}'."
                        )

                elif cmd["action"] == "price_query":
                    df = database.get_all_products()
                    match = df[
                        df["name"].str.contains(
                            cmd["product"], case=False, na=False
                        )
                    ]
                    if not match.empty:
                        prod = match.iloc[0]
                        reply = (
                            f"**{prod['name']}** currently sells for "
                            f"{utils.format_pkr(prod['sell_price'])}. "
                            f"You can use the Smart Pricing tab for an AI suggestion."
                        )
                    else:
                        reply = (
                            f"I couldn't find a product matching "
                            f"'{cmd['product']}'."
                        )
                else:
                    reply = ai_engine.chat(user_input)

            st.markdown(reply)
            st.session_state.chat_history.append(
                {"role": "assistant", "content": reply}
            )

    st.divider()
    c1, c2 = st.columns([1, 4])
    with c1:
        if voice_assistant.is_voice_available():
            if st.button("🎤 Speak"):
                with st.spinner("Listening..."):
                    text = voice_assistant.listen()
                if text and not text.startswith("⚠"):
                    st.info(f"You said: {text}")
                    st.session_state.chat_history.append(
                        {"role": "user", "content": text}
                    )
                    st.session_state.chat_history.append(
                        {"role": "assistant", "content": ai_engine.chat(text)}
                    )
                    st.rerun()
                else:
                    st.warning(text or "No speech detected.")
        else:
            st.button("🎤 Speak", disabled=True)
    with c2:
        st.caption("Click to speak in Urdu or English")

    if st.button("🗑 Clear Chat"):
        st.session_state.chat_history = []
        st.rerun()

with tab_sales:
    st.header("🧾 Sales History")
    sales_df = database.get_sales_history()

    if sales_df.empty:
        st.info("No sales recorded yet. Start selling from the Stock tab!")
    else:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Sales", utils.format_pkr(sales_df["total"].sum()))
        col2.metric("Transactions", len(sales_df))
        col3.metric("Avg Sale", utils.format_pkr(sales_df["total"].mean()))

        st.divider()
        st.subheader("Recent Transactions")
        display_df = sales_df.copy()
        display_df["sold_at"] = pd.to_datetime(
            display_df["sold_at"]
        ).dt.strftime("%d %b %Y, %I:%M %p")
        display_df.columns = [
            "ID", "Product", "Qty", "Price", "Total", "Date"
        ]
        st.dataframe(
            display_df, use_container_width=True, hide_index=True
        )

        st.divider()
        if st.button("🤖 Generate AI Daily Summary"):
            with st.spinner("Generating summary..."):
                st.markdown(ai_engine.daily_summary())
