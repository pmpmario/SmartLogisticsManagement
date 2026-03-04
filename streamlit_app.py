import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from urllib.parse import quote_plus


# Database Connection

password = quote_plus("Alys@003!")
engine = create_engine(f"mysql+pymysql://root:{password}@localhost/logistics_project_1")

@st.cache_data(ttl=300)
def load_data():
    shipments = pd.read_sql("SELECT * FROM shipments", engine)
    tracking = pd.read_sql("SELECT * FROM shipment_tracking", engine)
    costs = pd.read_sql("SELECT * FROM costs", engine)
    couriers = pd.read_sql("SELECT * FROM courier_staff", engine)
    routes = pd.read_sql("SELECT * FROM routes", engine)
    warehouses = pd.read_sql("SELECT * FROM warehouses", engine)
    return shipments, tracking, costs, couriers, routes, warehouses

shipments, tracking, costs, couriers, routes, warehouses = load_data()

st.set_page_config(page_title="Logistics Dashboard", layout="wide")
st.title("🚚 Logistics Intelligence Dashboard")


# A. Shipment Search & Filtering

st.sidebar.header("🔎 Shipment Filters")
status_filter = st.sidebar.multiselect("Status", shipments["status"].unique())
origin_filter = st.sidebar.multiselect("Origin", shipments["origin"].unique())
destination_filter = st.sidebar.multiselect("Destination", shipments["destination"].unique())
courier_filter = st.sidebar.multiselect("Courier", couriers["name"].unique())
shipment_id_filter = st.sidebar.text_input("Shipment ID")
date_range = st.sidebar.date_input("Order Date Range",
                                   [shipments["order_date"].min(), shipments["order_date"].max()])

filtered = shipments.copy()
if status_filter:
    filtered = filtered[filtered["status"].isin(status_filter)]
if origin_filter:
    filtered = filtered[filtered["origin"].isin(origin_filter)]
if destination_filter:
    filtered = filtered[filtered["destination"].isin(destination_filter)]
if courier_filter:
    valid_couriers = couriers[couriers["name"].isin(courier_filter)]["courier_id"]
    filtered = filtered[filtered["courier_id"].isin(valid_couriers)]
if shipment_id_filter:
    filtered = filtered[filtered["shipment_id"].str.contains(shipment_id_filter)]
if date_range:
    filtered = filtered[
        (pd.to_datetime(filtered["order_date"]) >= pd.to_datetime(date_range[0])) &
        (pd.to_datetime(filtered["order_date"]) <= pd.to_datetime(date_range[1]))
    ]

st.subheader("Filtered Shipments")
st.dataframe(filtered)


# B. Operational KPIs

st.subheader("📊 Operational KPIs")
total_shipments = len(shipments)
delivered_pct = (shipments["status"] == "Delivered").mean() * 100
cancelled_pct = (shipments["status"] == "Cancelled").mean() * 100
avg_delivery_time = (pd.to_datetime(shipments["delivery_date"]) - pd.to_datetime(shipments["order_date"])).dt.days.mean()
costs["total_cost"] = costs["fuel_cost"] + costs["labor_cost"] + costs["misc_cost"]
total_cost = costs["total_cost"].sum()

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Shipments", total_shipments)
col2.metric("Delivered %", f"{delivered_pct:.2f}%")
col3.metric("Cancelled %", f"{cancelled_pct:.2f}%")
col4.metric("Avg Delivery Time (days)", f"{avg_delivery_time:.2f}")
col5.metric("Total Operational Cost", f"${total_cost:,.2f}")


# C1. Delivery Performance Insights

st.subheader("📈 Delivery Performance")
shipments_routes = shipments.merge(routes, on=["origin", "destination"], how="left")
shipments_routes["delivery_days"] = (pd.to_datetime(shipments_routes["delivery_date"]) - pd.to_datetime(shipments_routes["order_date"])).dt.days
route_perf = shipments_routes.groupby(["origin","destination"])["delivery_days"].mean().reset_index()
fig1 = px.bar(route_perf, x="origin", y="delivery_days", color="destination", title="Avg Delivery Time per Route")
st.plotly_chart(fig1, use_container_width=True)

most_delayed = route_perf.sort_values("delivery_days", ascending=False).head(10)
st.write("Most Delayed Routes")
st.dataframe(most_delayed)

fig2 = px.scatter(shipments_routes, x="distance_km", y="delivery_days", color="status", title="Delivery Time vs Distance")
st.plotly_chart(fig2, use_container_width=True)


# C2. Courier Performance

st.subheader("🚴 Courier Performance")
couriers_perf = shipments.merge(couriers, on="courier_id", how="left")
couriers_perf["on_time"] = couriers_perf["status"]=="Delivered"
courier_summary = couriers_perf.groupby("name").agg(
    shipments_handled=("shipment_id","count"),
    on_time_pct=("on_time", lambda x: x.mean()*100),
    avg_rating=("rating","mean")
).reset_index()
st.dataframe(courier_summary)

fig3 = px.bar(courier_summary, x="name", y="shipments_handled", title="Shipments per Courier")
st.plotly_chart(fig3, use_container_width=True)

# C3. Cost Analytics

st.subheader("💰 Cost Analytics")
costs_shipments = shipments.merge(costs, on="shipment_id")
fig4 = px.bar(costs_shipments, x="shipment_id", y=["fuel_cost","labor_cost","misc_cost"], title="Cost per Shipment")
st.plotly_chart(fig4, use_container_width=True)

costs_totals = costs[["fuel_cost","labor_cost","misc_cost"]].sum()
fig5 = px.pie(costs_totals, values=costs_totals.values, names=costs_totals.index, title="Cost Contribution")
st.plotly_chart(fig5, use_container_width=True)

high_cost = costs_shipments.sort_values("total_cost", ascending=False).head(10)
st.write("High-Cost Shipments")
st.dataframe(high_cost[["shipment_id","total_cost"]])


# C4. Cancellation Analysis

st.subheader("❌ Cancellation Analysis")
cancel_origin = (shipments["status"]=="Cancelled").groupby(shipments["origin"]).sum() / shipments.groupby("origin").size()
cancel_origin = cancel_origin.fillna(0)
st.bar_chart(cancel_origin)

cancel_courier = (shipments["status"]=="Cancelled").groupby(shipments["courier_id"]).sum() / shipments.groupby("courier_id").size()
cancel_courier = cancel_courier.fillna(0).reset_index().merge(couriers, on="courier_id")
st.bar_chart(cancel_courier.set_index("name")[0])


# C5. Warehouse Insights

st.subheader("🏭 Warehouse Insights")
fig6 = px.bar(warehouses, x="city", y="capacity", title="Warehouse Capacity Comparison")
st.plotly_chart(fig6, use_container_width=True)


# 7. Potential Business Insights

st.subheader("💡 Potential Business Insights")
st.markdown("""
- Highest delays: see Delivery Performance  
- Couriers handling most shipments: see Courier Performance  
- High-rated couriers delivering faster? Compare avg_rating vs on_time_pct  
- Most expensive shipments: see Cost Analytics  
- Cost proportional to weight? Compare shipments['weight'] vs total_cost  
- Cities with most cancellations: see Cancellation Analysis  
- Routes underperforming relative to distance: see Delivery Time vs Distance
""")

st.success("📊 Logistics Dashboard Loaded Successfully!")