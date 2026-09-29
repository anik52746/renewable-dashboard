import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_FILE = "renewable_energy_by_state_clean.csv"

COLORS = {
    "renewable": "#009E73",        # green
    "non_renewable": "#7F7F7F",    # neutral gray
    "coal": "#D55E00",             # vermillion
    "wind": "#0072B2",             # blue
    "rooftop_solar": "#E69F00",    # orange
    "largescale_solar": "#CC79A7", # reddish purple
    "highlight": "#009E73",
    "muted": "#BFBFBF",
}

ALL_STATES = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_csv(DATA_FILE)
    # Restrict to the common 16-year window used throughout the analysis
    df = df[df["financial_year"] >= "2008-09"].copy()
    return df


df = load_data()
FY_ORDER = sorted(df["financial_year"].unique())  # string sort = chronological here


def renewable_share(sub_df):
    """% renewable share of generation_gwh in a slice already filtered to one
    state/year (or a range); expects section in {renewable, non-renewable}."""
    totals = sub_df[sub_df["section"].isin(["renewable", "non-renewable"])]
    renew = totals[totals["section"] == "renewable"]["generation_gwh"].sum()
    total = totals["generation_gwh"].sum()
    return round(renew / total * 100, 1) if total else 0.0


# ---------------------------------------------------------------------------
# Page config + header
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Australia's Renewable Energy Transition", layout="wide")

st.title("Australia's Renewable Energy Transition")
st.caption("Electricity generation by state and fuel type, 2008-09 to 2023-24 · Source: Australian Energy Statistics 2025, Table O")

# --- Global filters (apply to every section below) ---
filter_col1, filter_col2 = st.columns([1, 2])
with filter_col1:
    state_choice = st.selectbox("State", ["AUS (National)"] + ALL_STATES, index=0)
with filter_col2:
    start_fy, end_fy = st.select_slider(
        "Year range", options=FY_ORDER, value=(FY_ORDER[0], FY_ORDER[-1])
    )

selected_state = "AUS" if state_choice == "AUS (National)" else state_choice
years_in_range = [fy for fy in FY_ORDER if start_fy <= fy <= end_fy]

st.divider()

# ---------------------------------------------------------------------------
# Section 1 - The national picture
# ---------------------------------------------------------------------------
st.header("1. The national picture")

state_df = df[(df["state"] == selected_state) & (df["financial_year"].isin(years_in_range))]

share_start = renewable_share(state_df[state_df["financial_year"] == start_fy])
share_end = renewable_share(state_df[state_df["financial_year"] == end_fy])

col_stat, col_chart = st.columns([1, 2])
with col_stat:
    st.metric(
        label=f"Renewable share, {end_fy}",
        value=f"{share_end}%",
        delta=f"{round(share_end - share_start, 1)} pts vs {start_fy}",
    )
    st.caption(f"Region: {state_choice}")

with col_chart:
    trend_rows = []
    for fy in years_in_range:
        trend_rows.append({"financial_year": fy, "renewable_share_pct": renewable_share(
            state_df[state_df["financial_year"] == fy]
        )})
    trend_df = pd.DataFrame(trend_rows)

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=trend_df["financial_year"], y=trend_df["renewable_share_pct"],
        mode="lines+markers", name="Renewable share",
        line=dict(color=COLORS["renewable"], width=2),
        marker=dict(size=8),
        hovertemplate="%{x}<br>%{y:.1f}%% renewable<extra></extra>",
    ))
    fig1.update_layout(
        title=f"Renewable share over time - {state_choice}",
        yaxis_title="Renewable share (%)",
        xaxis_title="Financial year",
        showlegend=False,
        height=350,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 2 - Who's ahead, who's behind
# ---------------------------------------------------------------------------
st.header("2. Who's ahead, who's behind")

rows = []
for s in ALL_STATES:
    sdf = df[(df["state"] == s) & (df["financial_year"].isin([start_fy, end_fy]))]
    rows.append({
        "state": s,
        "start_share": renewable_share(sdf[sdf["financial_year"] == start_fy]),
        "end_share": renewable_share(sdf[sdf["financial_year"] == end_fy]),
    })
share_df = pd.DataFrame(rows).sort_values("end_share", ascending=False)

bar_colors_start = [
    COLORS["highlight"] if selected_state == s else COLORS["muted"] for s in share_df["state"]
]
bar_colors_end = [
    COLORS["highlight"] if selected_state == s else COLORS["non_renewable"] for s in share_df["state"]
]

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=share_df["state"], y=share_df["start_share"], name=f"{start_fy}",
    marker_color=COLORS["muted"],
    hovertemplate="%{x} · " + start_fy + "<br>%{y:.1f}%% renewable<extra></extra>",
))
fig2.add_trace(go.Bar(
    x=share_df["state"], y=share_df["end_share"], name=f"{end_fy}",
    marker_color=COLORS["renewable"],
    hovertemplate="%{x} · " + end_fy + "<br>%{y:.1f}%% renewable<extra></extra>",
))
fig2.update_layout(
    title=f"Renewable share by state: {start_fy} vs {end_fy}",
    yaxis_title="Renewable share (%)",
    xaxis_title="State",
    barmode="group",
    height=400,
    margin=dict(l=10, r=10, t=40, b=10),
)
st.plotly_chart(fig2, use_container_width=True)

leader = share_df.iloc[0]
st.caption(
    f"{leader['state']} leads in {end_fy} at {leader['end_share']}% renewable "
    f"({'AUS is national average' if selected_state == 'AUS' else selected_state + ' is highlighted above'})."
)

st.divider()

# ---------------------------------------------------------------------------
# Section 3 - What's driving it (rooftop vs large-scale solar)
# ---------------------------------------------------------------------------
st.header("3. What's driving it")

solar_df = df[
    (df["financial_year"] == end_fy)
    & (df["fuel_type"].isin(["Small-scale solar PV", "Large-scale solar PV"]))
    & (df["state"] != "AUS")
]

if selected_state != "AUS":
    solar_df = solar_df[solar_df["state"] == selected_state]

pivot = solar_df.pivot_table(index="state", columns="fuel_type", values="generation_gwh").fillna(0)
if not pivot.empty:
    pivot["total"] = pivot.get("Small-scale solar PV", 0) + pivot.get("Large-scale solar PV", 0)
    pivot["rooftop_pct"] = (pivot.get("Small-scale solar PV", 0) / pivot["total"] * 100).round(1)
    pivot = pivot.sort_values("rooftop_pct", ascending=False)

    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=pivot.index, y=pivot.get("Small-scale solar PV", 0), name="Rooftop (small-scale)",
        marker_color=COLORS["rooftop_solar"],
        text=[f"{p}%" for p in pivot["rooftop_pct"]], textposition="inside",
        hovertemplate="%{x}<br>Rooftop: %{y:.0f} GWh<extra></extra>",
    ))
    fig3.add_trace(go.Bar(
        x=pivot.index, y=pivot.get("Large-scale solar PV", 0), name="Large-scale (utility)",
        marker_color=COLORS["largescale_solar"],
        hovertemplate="%{x}<br>Large-scale: %{y:.0f} GWh<extra></extra>",
    ))
    fig3.update_layout(
        title=f"Rooftop vs large-scale solar - {end_fy}",
        yaxis_title="Solar generation (GWh)",
        xaxis_title="State",
        barmode="stack",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("Rooftop's share of each state's total solar is labeled on the bar.")
else:
    st.info("No solar data available for this selection.")

st.divider()

# ---------------------------------------------------------------------------
# Section 4 - Outlook
# ---------------------------------------------------------------------------
st.header("4. Outlook")

outlook_df = df[(df["state"] == selected_state) & (df["financial_year"].isin(years_in_range))]

col_left, col_right = st.columns(2)

with col_left:
    coal = outlook_df[outlook_df["fuel_type"].isin(["Black coal", "Brown coal"])] \
        .groupby("financial_year")["generation_gwh"].sum().reindex(years_in_range)
    renew_total = outlook_df[outlook_df["section"] == "renewable"] \
        .groupby("financial_year")["generation_gwh"].sum().reindex(years_in_range)

    fig4a = go.Figure()
    fig4a.add_trace(go.Scatter(
        x=years_in_range, y=coal, mode="lines+markers", name="Coal",
        line=dict(color=COLORS["coal"], width=2),
        hovertemplate="%{x}<br>Coal: %{y:.0f} GWh<extra></extra>",
    ))
    fig4a.add_trace(go.Scatter(
        x=years_in_range, y=renew_total, mode="lines+markers", name="Renewable",
        line=dict(color=COLORS["renewable"], width=2),
        hovertemplate="%{x}<br>Renewable: %{y:.0f} GWh<extra></extra>",
    ))
    fig4a.update_layout(
        title=f"Coal vs renewable - {state_choice}",
        yaxis_title="Generation (GWh)",
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig4a, use_container_width=True)

with col_right:
    wind = outlook_df[outlook_df["fuel_type"] == "Wind"] \
        .set_index("financial_year")["generation_gwh"].reindex(years_in_range)
    solar_total = outlook_df[outlook_df["fuel_type"].isin(["Small-scale solar PV", "Large-scale solar PV"])] \
        .groupby("financial_year")["generation_gwh"].sum().reindex(years_in_range)

    wind_base = wind.iloc[0] if len(wind) and wind.iloc[0] else None
    solar_base = solar_total.iloc[0] if len(solar_total) and solar_total.iloc[0] else None
    wind_indexed = (wind / wind_base * 100) if wind_base else wind * 0
    solar_indexed = (solar_total / solar_base * 100) if solar_base else solar_total * 0

    fig4b = go.Figure()
    fig4b.add_trace(go.Scatter(
        x=years_in_range, y=wind_indexed, mode="lines+markers", name="Wind (indexed)",
        line=dict(color=COLORS["wind"], width=2),
        hovertemplate="%{x}<br>Wind index: %{y:.0f}<extra></extra>",
    ))
    fig4b.add_trace(go.Scatter(
        x=years_in_range, y=solar_indexed, mode="lines+markers", name="Solar (indexed)",
        line=dict(color=COLORS["rooftop_solar"], width=2),
        hovertemplate="%{x}<br>Solar index: %{y:.0f}<extra></extra>",
    ))
    fig4b.update_layout(
        title=f"Wind vs solar growth (index={start_fy}=100)",
        yaxis_title="Index",
        yaxis_type="log",
        height=380,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig4b, use_container_width=True)

st.divider()

# ---------------------------------------------------------------------------
# Section 5 - Personalised takeaway
# ---------------------------------------------------------------------------
st.header("5. Your takeaway")

take_df = df[(df["state"] == selected_state) & (df["financial_year"] == end_fy)]
fuel_only = take_df[~take_df["section"].isin(["total", "total non-renewable", "total renewable"]) & take_df["fuel_type"].notna()]
fuel_only = fuel_only[fuel_only["section"].isin(["renewable", "non-renewable"])]
top_fuel = fuel_only.sort_values("generation_gwh", ascending=False).iloc[0] if not fuel_only.empty else None

solar_pct_line = ""
solar_take = solar_df if selected_state != "AUS" else df[
    (df["financial_year"] == end_fy)
    & (df["fuel_type"].isin(["Small-scale solar PV", "Large-scale solar PV"]))
    & (df["state"] == selected_state)
]
if not solar_take.empty:
    rooftop_val = solar_take[solar_take["fuel_type"] == "Small-scale solar PV"]["generation_gwh"].sum()
    total_val = solar_take["generation_gwh"].sum()
    if total_val:
        solar_pct_line = f"Rooftop solar makes up **{round(rooftop_val / total_val * 100, 1)}%** of {state_choice}'s total solar generation."

with st.container(border=True):
    st.markdown(f"**In {state_choice}, renewable share went from {share_start}% ({start_fy}) to {share_end}% ({end_fy}).**")
    if top_fuel is not None:
        st.markdown(f"Its largest source of generation in {end_fy} is **{top_fuel['fuel_type']}**.")
    if solar_pct_line:
        st.markdown(solar_pct_line)

st.caption("Change the state or year range above to update every section on this page.")