# =========================
# CONFIGURATION AND DATA INPITS
# =========================

# =========================
# IMPORTS
# =========================
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import geopandas as gpd
import plotly.express as px
from streamlit_plotly_events import plotly_events
import re
import time


# =====================================
# PASSWORD PROTECTION
# =====================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:

    entered_password = st.text_input(
        "Password",
        type="password"
    )

    if st.button("Login"):

        if entered_password == st.secrets["password"]:

            st.session_state.authenticated = True
            st.rerun()

        else:

            st.error(
                "Incorrect password"
            )

    st.stop()

start_time = time.time()

# =========================
# BASE DATA LOCATION
# =========================

HOST_FOLDER = "data"

# =========================
# TAB 1
# =========================

DATA_FILE = fr"{HOST_FOLDER}/rr_jfmp2026_2028_dashboard.xlsx"

NARRATIVE_FILE = fr"{HOST_FOLDER}/mgf_burn_priorities_test.txt"

SHAPEFILE = fr"{HOST_FOLDER}/JFMP_2027_Draft_FINAL/JFMP_2027_Draft_FINAL.shp"

APP_TITLE = "Regional Burn Priorities"

DEFAULT_TOP_N = 10
SHOW_CUMULATIVE = True
SHOW_INDIVIDUAL = True

# =========================
# TAB 2
# =========================

RR_MG_NARRATIVE_FILE = fr"{HOST_FOLDER}/residual_risk_narrative_golfields.txt"

RR_MG_SHEET = "Murray Goldfields"

#Shared data below Tab2 and 3

RR_XLS = fr"{HOST_FOLDER}/JFMP_RR.xlsx"
LOCALITY_LOSS_XLS = fr"{HOST_FOLDER}/JFMP_LocalityLoss.xlsx"
LOCALITY_LOSS_SHEET = 0  # First worksheet in the workbook

# =========================
# TAB 3
# =========================

#Consider shared data sources from TAB2

RR_MAL_NARRATIVE_FILE = fr"{HOST_FOLDER}/residual_risk_narrative_mallee.txt"

RR_MAL_SHEET = "Mallee"

# =========================
# TAB 4
# =========================

SPRING_PRIORITIES = fr"{HOST_FOLDER}/SpringPriorities.txt"
SPRING_NARRATIVE = fr"{HOST_FOLDER}/SpringNarrative.txt"

# =========================
# STYLE
# =========================

PRIMARY = "#1d3557"
ACCENT = "#e63946"
BG = "#f8f9fa"
CARD = "#ffffff"
TEXT = "#111111"

# =========================
# CACHED LOADERS
# =========================

@st.cache_data
def build_map_gdf(_gdf, df):

    df_map = df[
        [
            "Treatment Name",
            "district",
            "JFMP Year",
            "Residual Risk",
            "Treatment Type"
        ]
    ].copy()

    df_map["NAME_JOIN"] = (
        df_map["Treatment Name"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return _gdf.merge(
        df_map,
        on="NAME_JOIN",
        how="inner"
    )


@st.cache_data
def load_excel(path):

    return pd.read_excel(path)


@st.cache_data
def load_excel_sheet(
    path,
    sheet_name
):

    return pd.read_excel(
        path,
        sheet_name=sheet_name
    )


@st.cache_data
def load_shapefile(path):
    
    gdf = gpd.read_file(path)

    gdf = gdf.to_crs(
        epsg=4326
    )

    gdf["NAME_JOIN"] = (
        gdf["NAME"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    return gdf


@st.cache_data
def load_text(path):

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return f.read()



# =========================
# HELPER FUNCTIONS
# =========================


#RESET MAP - CLICKABLE GRAPH

def clear_chart_map_focus():

    st.session_state["map_focus_burn"] = None

    st.session_state["chart_reset_version"] += 1


# CHART CLICK HANDLERS

def get_clicked_burn(chart_key):

    chart_event = st.session_state.get(
        chart_key,
        {}
    )

    try:

        selected_points = chart_event[
            "selection"
        ]["points"]

    except (KeyError, TypeError):

        selected_points = []

    if selected_points:

        clicked_burn = selected_points[0].get(
            "customdata"
        )

        # Plotly may return customdata as a list
        if isinstance(clicked_burn, (list, tuple)):

            clicked_burn = clicked_burn[0]

        if clicked_burn:

            st.session_state[
                "map_focus_burn"
            ] = clicked_burn


def focus_map_from_bar():

    bar_chart_key = st.session_state.get(
        "active_bar_chart_key"
    )

    if not bar_chart_key:
        return

    chart_event = st.session_state.get(
        bar_chart_key,
        {}
    )

    try:
        selected_points = chart_event[
            "selection"
        ]["points"]

    except (KeyError, TypeError):
        selected_points = []

    if selected_points:

        clicked_burn = selected_points[0].get(
            "customdata"
        )

        if isinstance(clicked_burn, (list, tuple)):
            clicked_burn = clicked_burn[0]

        if clicked_burn:
            st.session_state[
                "map_focus_burn"
            ] = clicked_burn

   


# =========================
# LOAD TAB 1 DATA
# =========================

df = load_excel(DATA_FILE)

df.columns = df.columns.str.strip()

df = df.sort_values(
    by="Residual Risk",
    ascending=False
)

gdf = load_shapefile(SHAPEFILE)


# =========================
# LOAD TAB 2 DATA
# =========================

locality_loss = load_excel_sheet(
    LOCALITY_LOSS_XLS,
    LOCALITY_LOSS_SHEET
)

locality_loss.columns = locality_loss.columns.str.strip()

locality_loss["Difference"] = pd.to_numeric(
    locality_loss["Difference"],
    errors="coerce"
)

locality_loss = locality_loss.dropna(
    subset=["Locality", "Difference"]
)
locality_loss = locality_loss[
    locality_loss["Difference"] > 0
].copy()

locality_loss = locality_loss[
    locality_loss["District"] == "MURRAY GOLDFIELDS"
].copy()


rr_mg = load_excel_sheet(
    RR_XLS,
    RR_MG_SHEET
)

rr_mg.columns = rr_mg.columns.str.strip()
rr_mg = rr_mg.dropna(subset=["Season"])

projection_rows = rr_mg[
    rr_mg[
        [
            "Projected Residual Risk with JFMP",
            "Projected Residual Risk without JFMP"
        ]
    ].notna().any(axis=1)
].copy()

last_projection_season = projection_rows["Season"].max()

rr_mg_plot = rr_mg[
    rr_mg["Season"] <= last_projection_season
].copy()


# =========================
# LOAD TAB 3 DATA
# =========================

locality_loss_mal = load_excel_sheet(
    LOCALITY_LOSS_XLS,
    LOCALITY_LOSS_SHEET
)

locality_loss_mal.columns = locality_loss_mal.columns.str.strip()

locality_loss_mal["Difference"] = pd.to_numeric(
    locality_loss_mal["Difference"],
    errors="coerce"
)

locality_loss_mal = locality_loss_mal.dropna(
    subset=["Locality", "Difference"]
)

locality_loss_mal = locality_loss_mal[
    locality_loss_mal["Difference"] > 0
].copy()

locality_loss_mal = locality_loss_mal[
    locality_loss_mal["District"] == "MALLEE"
].copy()

rr_mal = load_excel_sheet(
    RR_XLS,
    RR_MAL_SHEET
)

rr_mal.columns = rr_mal.columns.str.strip()

rr_mal = rr_mal.dropna(
    subset=["Season"]
)

projection_rows_mal = rr_mal[
    rr_mal[
        [
            "Projected Residual Risk with JFMP",
            "Projected Residual Risk without JFMP"
        ]
    ].notna().any(axis=1)
].copy()

last_projection_season_mal = (
    projection_rows_mal["Season"].max()
)

rr_mal_plot = rr_mal[
    rr_mal["Season"] <= last_projection_season_mal
].copy()

# =========================
# LOAD TAB 4 DATA
# =========================

spring_narrative = load_text(
    SPRING_NARRATIVE
)

spring_priorities = load_text(
    SPRING_PRIORITIES
)


# =========================
# PAGE SETUP
# =========================

st.set_page_config(layout="wide")

# Burn selected by clicking a chart
if "map_focus_burn" not in st.session_state:
    st.session_state["map_focus_burn"] = None

if "chart_reset_version" not in st.session_state:
    st.session_state["chart_reset_version"] = 0



st.markdown(f"""
<style>

.stApp {{
    background-color: {BG};
    color: {TEXT};
}}

.card {{
    background-color: {CARD};
    padding: 15px;
    border-radius: 8px;
}}

.title {{
    color: {PRIMARY};
    font-size: 36px;
    font-weight: bold;
}}

.narrative {{
    font-size: 16px;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 8px;
}}

.stTabs [data-baseweb="tab"] {{
    background-color: #e9ecef;
    border-radius: 8px 8px 0px 0px;
    padding: 12px 24px;
    font-size: 16px;
    font-weight: 600;
}}

.stTabs [aria-selected="true"] {{
    background-color: #1d3557;
    color: white;
}}

</style>
""", unsafe_allow_html=True)


st.markdown(
    """
    <div style="
        background-color:#1d3557;
        padding:20px;
        border-radius:10px;
        margin-bottom:10px;
    ">
        <h1 style="
            color:white;
            margin:0;
            font-size:2.2rem;
        ">
            🔥 Loddon Mallee Joint Fuel Management Program: Risk Intelligence Dashboard
        </h1>

    """,
    unsafe_allow_html=True
)

# =========================
# TABS
# =========================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "Burn Priorities",
        "Murray Goldfields Residual Risk",
        "Mallee Residual Risk",
        "Spring Priorities"
    ]
)

# ==========================================================
# TAB 1 - BURN PRIORITIES
# ==========================================================

with tab1:

    st.markdown(
        f'<div class="title">{APP_TITLE}</div>',
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1, 2])

    # =====================================================
    # NARRATIVE PANNEL TOP LEFT
    # =====================================================
    #
    with col_left:
    
        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.subheader("Overview")

        try:
            with open(NARRATIVE_FILE, "r") as f:
                text = f.read()
                st.markdown(f'<div class="narrative">{text}</div>', unsafe_allow_html=True)
        except:
            st.write("No narrative file found.")

        st.markdown('</div>', unsafe_allow_html=True)

        # =====================================================
        # INTERACTIVE BURN MAP
        # =====================================================

        st.markdown(
            '<div class="card">',
            unsafe_allow_html=True
        )

        st.subheader("Burn Map")

        try:

            # -------------------------------------------------
            # PREPARE SHAPEFILE
            # -------------------------------------------------

            gdf_web = gdf

            # Clean the join fields to reduce failures caused by
            # leading/trailing spaces or inconsistent capitalisation

            gdf_web["NAME_JOIN"] = (
                gdf_web["NAME"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            df_map_attributes = df[
                [
                    "Treatment Name",
                    "district",
                    "JFMP Year",
                    "Residual Risk",
                    "Treatment Type"
                ]
            ].copy()

            df_map_attributes["NAME_JOIN"] = (
                df_map_attributes["Treatment Name"]
                .astype(str)
                .str.strip()
                .str.upper()
            )

            # Ensure numeric fields are numeric

            df_map_attributes["Residual Risk"] = pd.to_numeric(
                df_map_attributes["Residual Risk"],
                errors="coerce"
            )

            df_map_attributes["JFMP Year"] = pd.to_numeric(
                df_map_attributes["JFMP Year"],
                errors="coerce"
            )

            # Keep one attribute record per treatment name

            df_map_attributes = df_map_attributes.drop_duplicates(
                subset=["NAME_JOIN"]
            )

            # Join the Excel attributes onto the shapefile

            map_gdf = build_map_gdf(
                gdf,
                df
            )


            # -------------------------------------------------
            # MAP FILTERS
            # -------------------------------------------------

            map_filter_col1, map_filter_col2 = st.columns(2)

            with map_filter_col1:

                map_district_options = sorted(
                    map_gdf["district"]
                    .dropna()
                    .unique()
                    .tolist()
                )

                selected_map_districts = st.multiselect(
                    "Map District",
                    options=map_district_options,
                    default=map_district_options,
                    key="map_district_filter"
                )

            with map_filter_col2:

                map_year_options = sorted(
                    map_gdf["JFMP Year"]
                    .dropna()
                    .unique()
                    .tolist()
                )

                selected_map_years = st.multiselect(
                    "Map JFMP Year",
                    options=map_year_options,
                    default=map_year_options,
                    key="map_year_filter"
                )

            map_symbology = st.selectbox(
                "Map symbology",
                options=[
                    "Residual Risk",
                    "JFMP Year"
                ],
                index=0,
                key="map_symbology_selector"
            )

            map_display_mode = st.radio(
                "Map display",
                [
                    "Filtered burns",
                    "Selected burns"
                ],
                horizontal=True,
                key="map_display_mode",
                on_change=clear_chart_map_focus
            )

            # -------------------------------------------------
            # CLEAR GRAPH FOCUS
            # -------------------------------------------------

            if st.session_state.get("map_focus_burn"):

                st.success(
                    f"Map focused on: "
                    f"{st.session_state['map_focus_burn']}"
                )

                if st.button(
                    "Clear chart selection",
                    key="clear_map_focus"
                ):

                    clear_chart_map_focus()
                    st.rerun()

            

            # -------------------------------------------------
            # APPLY MAP FILTERS
            # -------------------------------------------------

            map_plot = map_gdf[
                map_gdf["district"].isin(
                    selected_map_districts
                )
            ].copy()

            map_plot = map_plot[
                map_plot["JFMP Year"].isin(
                    selected_map_years
                )
            ].copy()

            # -------------------------------------------------
            # FOCUS MAP ON BURN CLICKED IN A CHART
            # -------------------------------------------------

            # If Selected burns mode is active,
            # further restrict the map using the
            # main burn-selection widget

            if map_display_mode == "Selected burns":

                selected_map_burns = st.session_state.get(
                    "burn_selection",
                    []
                )

                map_plot = map_plot[
                    map_plot["Treatment Name"].isin(
                        selected_map_burns
                    )
                ].copy()

            # A burn clicked in either chart
            # takes temporary priority

            clicked_burn = st.session_state.get(
                "map_focus_burn"
            )

            if clicked_burn:

                clicked_burn_map = map_gdf[
                    map_gdf["Treatment Name"] == clicked_burn
                ].copy()

                if not clicked_burn_map.empty:

                    map_plot = clicked_burn_map

            # Reset the index so Plotly polygon IDs match cleanly

            map_plot = map_plot.reset_index(drop=True)

            # Risk classes
            def classify_rr(rr):

                if rr >= 1.65:
                    return "EXTREME"

                elif rr >= 1.0:
                    return "VERY HIGH"

                elif rr >= 0.3:
                    return "HIGH"

                else:
                    return "MODERATE"


            map_plot["RR Class"] = (
                map_plot["Residual Risk"]
                .apply(classify_rr)
            )

            # -------------------------------------------------
            # CREATE MAP
            # -------------------------------------------------

            if map_plot.empty:

                st.warning(
                    "No burns match the selected map filters."
                )

            else:

                # Use the filtered polygon extent to centre the map
                # -------------------------------------------------
                # AUTO CENTRE AND AUTO ZOOM
                # -------------------------------------------------

                min_lon, min_lat, max_lon, max_lat = (
                    map_plot.total_bounds
                )

                map_center = {
                    "lat": (min_lat + max_lat) / 2,
                    "lon": (min_lon + max_lon) / 2
                }

                extent_width = max_lon - min_lon
                extent_height = max_lat - min_lat

                extent = max(
                    extent_width,
                    extent_height
                )

                # Zoom based on spatial extent

                if extent < 0.01:
                    map_zoom = 14

                elif extent < 0.02:
                    map_zoom = 13

                elif extent < 0.05:
                    map_zoom = 12

                elif extent < 0.10:
                    map_zoom = 11

                elif extent < 0.25:
                    map_zoom = 10

                elif extent < 0.50:
                    map_zoom = 9

                elif extent < 1.00:
                    map_zoom = 8

                else:
                    map_zoom = 7

                # ---------------------------------------------
                # RESIDUAL RISK SYMBOLOGY
                # ---------------------------------------------

                if map_symbology == "Residual Risk":

                    fig_map = px.choropleth_map(
                        map_plot,
                        geojson=map_plot.__geo_interface__,
                        locations=map_plot.index,
                        color="RR Class",

                        color_discrete_map={
                            "EXTREME": "#d73027",      # Red
                            "VERY HIGH": "#fc8d59",    # Orange
                            "HIGH": "#fee08b",         # Yellow
                            "MODERATE": "#91cf60",     # Green
                            "NEGLIGABLE": "#4575b4"    # Blue
                        },

                        hover_name="Treatment Name",
                        hover_data={
                            "district": True,
                            "JFMP Year": True,
                            "Treatment Type": True,
                            "Residual Risk": ":.3f"
                        },
                        center=map_center,
                        zoom=map_zoom,
                        opacity=0.75,
                        height=550,
                        labels={
                            "Residual Risk": "Risk reduction",
                            "district": "District",
                            "JFMP Year": "JFMP Year",
                            "Treatment Type": "Treatment Type"
                        }
                    )

                # ---------------------------------------------
                # JFMP YEAR SYMBOLOGY
                # ---------------------------------------------

                else:

                    # Convert the year to text so Plotly treats
                    # the years as categories, not a continuous scale

                    map_plot["JFMP Year Display"] = (
                        map_plot["JFMP Year"]
                        .astype(int)
                        .astype(str)
                    )

                    fig_map = px.choropleth_map(
                        map_plot,
                        geojson=map_plot.__geo_interface__,
                        locations=map_plot.index,
                        color="JFMP Year Display",
                        color_discrete_map={
                            "2027": "#1f77b4",
                            "2028": "#ff7f0e",
                            "2029": "#2ca02c"
                        },
                        category_orders={
                            "JFMP Year Display": [
                                "2027",
                                "2028",
                                "2029"
                            ]
                        },
                        hover_name="Treatment Name",
                        hover_data={
                            "district": True,
                            "JFMP Year": True,
                            "Treatment Type": True,
                            "Residual Risk": ":.3f",
                            "JFMP Year Display": False
                        },
                        center=map_center,
                        zoom=map_zoom,
                        opacity=0.75,
                        height=550,
                        labels={
                            "JFMP Year Display": "JFMP Year",
                            "Residual Risk": "Risk reduction",
                            "district": "District",
                            "Treatment Type": "Treatment Type"
                        }
                    )

                # -------------------------------------------------
                # MAP APPEARANCE
                # -------------------------------------------------

                fig_map.update_traces(
                    marker_line_width=0.1,
                    marker_line_color="#222222"
                )

                fig_map.update_layout(
                    map_style="open-street-map",
                    paper_bgcolor=CARD,
                    font=dict(color=TEXT),
                    margin=dict(
                        l=0,
                        r=0,
                        t=10,
                        b=0
                    ),
                    coloraxis_colorbar=dict(
                        title="Risk"
                    )
                )

                st.plotly_chart(
                    fig_map,
                    use_container_width=True
                )

        except Exception as e:

            st.error(
                f"Map failed to load: {e}"
            )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    # =========================
    # RIGHT PANEL
    # =========================

    with col_right:

        # ---- Selection ----

        # =========================
        # FILTERS
        # =========================

        treatment_types = sorted(
            df["Treatment Type"].dropna().unique()
        )

        selected_treatment_types = st.multiselect(
            "Treatment Type",
            options=treatment_types,
            default=treatment_types
        )

        jfmp_years = sorted(
            df["JFMP Year"].dropna().unique()
        )

        selected_jfmp_years = st.multiselect(
            "JFMP Year",
            options=jfmp_years,
            default=jfmp_years
        )

        districts = sorted(
            df["district"].dropna().unique()
        )

        selected_districts = st.multiselect(
            "district",
            options=districts,
            default=districts
        )

        # Apply filters

        filtered_df = df[
            df["district"].isin(selected_districts)
        ].copy()

        filtered_df = filtered_df[
            filtered_df["Treatment Type"].isin(
                selected_treatment_types
            )
        ].copy()

        filtered_df = filtered_df[
            filtered_df["JFMP Year"].isin(
                selected_jfmp_years
            )
        ].copy()


        st.markdown(
            """
            **Filters first, then selects burns.**

            District, Treatment Type and JFMP Year filters determine which treatments are available for selection below.

            Defaults to top 10 burns that meet filter criteria.
            """
        )

        burn_list = filtered_df["Treatment Name"].tolist()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("Top 10"):
                st.session_state["burn_selection"] = burn_list[:10]

        with col2:
            if st.button("Top 15"):
                st.session_state["burn_selection"] = burn_list[:15]

        with col3:
            if st.button("Top 20"):
                st.session_state["burn_selection"] = burn_list[:20]

        with col4:
            if st.button("All"):
                st.session_state["burn_selection"] = burn_list

        # First load
        if "burn_selection" not in st.session_state:
            st.session_state["burn_selection"] = burn_list[:10]

        # Remove burns that are no longer available after filtering
        st.session_state["burn_selection"] = [
            burn
            for burn in st.session_state["burn_selection"]
            if burn in burn_list
        ]

        selected = st.multiselect(
            "Select burns",
            burn_list,
            key="burn_selection"
        )

        view = filtered_df[
            filtered_df["Treatment Name"].isin(selected)
        ].copy()

        view = view.sort_values(
            by="Residual Risk",
            ascending=False
        )

        # cumulative
        view["cumulative"] = view["Residual Risk"].cumsum()

        # ✅ CALCULATE KPI EARLY
        total_selected = view["Residual Risk"].sum()

        # Total risk reduction across the ENTIRE 3-year JFMP
        total_all = df["Residual Risk"].sum()

        pct = (
            (total_selected / total_all) * 100
            if total_all != 0
            else 0
        )

        # =========================
        # TOP: RISK CHART
        # =========================

        fig = go.Figure()

        # Individual treatment bars

        if SHOW_INDIVIDUAL:

            fig.add_trace(
                go.Bar(
                    x=view["Treatment Name"],
                    y=view["Residual Risk"],
                    name="Individual",
                    marker_color=PRIMARY,

                    customdata=view[
                        "Treatment Name"
                    ],

                    hovertemplate=(
                        "<b>%{customdata}</b><br>"
                        "Risk reduction: %{y:.3f}"
                        "<extra></extra>"
                    )
                )
            )

        # Cumulative risk-reduction line

        if SHOW_CUMULATIVE:

            fig.add_trace(
                go.Scatter(
                    x=view["Treatment Name"],
                    y=view["cumulative"],
                    mode="lines+markers",
                    name="Cumulative",
                    line=dict(
                        color=ACCENT,
                        width=4
                    ),

                    customdata=view[
                        "Treatment Name"
                    ],

                    hovertemplate=(
                        "<b>%{customdata}</b><br>"
                        "Cumulative: %{y:.3f}"
                        "<extra></extra>"
                    )
                )
            )

        fig.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            font=dict(color=TEXT),

            margin=dict(
                l=10,
                r=10,
                t=40,
                b=10
            ),

            xaxis_tickangle=-45,

            clickmode="event+select"
        )

        bar_chart_key = (
            f"burn_priority_bar_chart_"
            f"{st.session_state['chart_reset_version']}"
        )

        st.session_state["active_bar_chart_key"] = bar_chart_key

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=bar_chart_key,
            on_select=focus_map_from_bar,
            selection_mode="points"
        )

        st.markdown("### Key Insight")
        st.markdown(
            f"Selected {len(view)} burns contribute **{pct:.1f}%** of total risk reduction in the three year JFMP.",
        )

        # =========================
        # KPI
        # =========================

        # =====================================================
        # CUMULATIVE ESTIMATED RESIDUAL RISK BY JFMP YEAR
        # =====================================================

        # The JFMP Year values used in the treatment workbook
        JFMP_YEARS = [
            2027,
            2028,
            2029
        ]

        estimated_rr_results = {}

        # Tracks selected risk reduction carried forward
        # from all preceding JFMP years
        cumulative_selected_reduction = 0.0

        # Tracks the previous year's full-program reduction
        # so that we can calculate the additional reduction
        # introduced by each new year of the JFMP
        previous_full_program_reduction = 0.0


        for season in JFMP_YEARS:

            # =================================================
            # FIND ALL AND SELECTED TREATMENTS FOR THIS YEAR
            # =================================================

            all_year_treatments = df[
                pd.to_numeric(
                    df["JFMP Year"],
                    errors="coerce"
                ) == season
            ].copy()

            selected_year_treatments = view[
                pd.to_numeric(
                    view["JFMP Year"],
                    errors="coerce"
                ) == season
            ].copy()

            # Ensure Residual Risk contribution is numeric

            all_year_treatments["Residual Risk"] = pd.to_numeric(
                all_year_treatments["Residual Risk"],
                errors="coerce"
            ).fillna(0)

            selected_year_treatments["Residual Risk"] = pd.to_numeric(
                selected_year_treatments["Residual Risk"],
                errors="coerce"
            ).fillna(0)

            # Total treatment contribution available in this year

            total_year_risk_reduction = (
                all_year_treatments["Residual Risk"].sum()
            )

            # Contribution represented by the selected treatments

            selected_year_risk_reduction = (
                selected_year_treatments["Residual Risk"].sum()
            )

            # Proportion of this year's program selected

            if total_year_risk_reduction != 0:

                selected_year_proportion = (
                    selected_year_risk_reduction
                    / total_year_risk_reduction
                )

            else:

                selected_year_proportion = 0.0

            # Prevent unexpected data issues producing a proportion
            # below 0% or above 100%

            selected_year_proportion = max(
                0.0,
                min(1.0, selected_year_proportion)
            )

            # =================================================
            # GET THE MODELLING RESULTS FOR THIS SEASON
            # =================================================

            rr_projection_row = rr_mg[
                pd.to_numeric(
                    rr_mg["Season"],
                    errors="coerce"
                ) == season
            ]

            if not rr_projection_row.empty:

                rr_with_jfmp = float(
                    rr_projection_row[
                        "Projected Residual Risk with JFMP"
                    ].iloc[0]
                )

                rr_without_jfmp = float(
                    rr_projection_row[
                        "Projected Residual Risk without JFMP"
                    ].iloc[0]
                )

                # Total cumulative benefit of the complete JFMP
                # by this point in time

                full_program_reduction = (
                    rr_without_jfmp
                    - rr_with_jfmp
                )

                # Calculate only the NEW benefit introduced
                # by treatments scheduled for this JFMP year

                incremental_year_reduction = (
                    full_program_reduction
                    - previous_full_program_reduction
                )

                # Apply the selected proportion of this year's
                # incremental benefit

                selected_incremental_reduction = (
                    incremental_year_reduction
                    * selected_year_proportion
                )

                # Carry all selected benefits from earlier years forward

                cumulative_selected_reduction += (
                    selected_incremental_reduction
                )

                # Estimate residual risk using all selected treatments
                # delivered up to and including this year

                estimated_rr = (
                    rr_without_jfmp
                    - cumulative_selected_reduction
                )

                estimated_rr_results[season] = {
                    "estimated_rr": estimated_rr,
                    "year_proportion": selected_year_proportion,
                    "year_selected_reduction": selected_incremental_reduction,
                    "cumulative_selected_reduction": cumulative_selected_reduction,
                    "rr_with_jfmp": rr_with_jfmp,
                    "rr_without_jfmp": rr_without_jfmp
                }

                # Remember the complete-program reduction at this point,
                # ready to calculate the following year's added benefit

                previous_full_program_reduction = (
                    full_program_reduction
                )

            else:

                estimated_rr_results[season] = {
                    "estimated_rr": None,
                    "year_proportion": selected_year_proportion,
                    "year_selected_reduction": 0.0,
                    "cumulative_selected_reduction": cumulative_selected_reduction,
                    "rr_with_jfmp": None,
                    "rr_without_jfmp": None
                }


        st.markdown(
            """
            *The actual RR value of a subset of burns is impossible to measure without scenario-specific modelling.*

            *This is an indicative estimate of residual risk if ONLY the selected burns are delivered; assuming treatments contribute proportionally to the modelled annual residual-risk reduction, with treatment benefits carried forward into subsequent years.*
            """
        )


        # =====================================================
        # DISPLAY ESTIMATED RR METRICS
        # =====================================================


        
        rr_col_2027, rr_col_2028, rr_col_2029 = st.columns(3)

        with rr_col_2027:

            result_2027 = estimated_rr_results[2027]

            if result_2027["estimated_rr"] is not None:

                st.metric(
                    "Estimated RR 2027",
                    f'{result_2027["estimated_rr"]:.1f}%',
                    help=(
                        f'Selected treatments represent '
                        f'{result_2027["year_proportion"]:.1%} '
                        f'of total Year 1 risk reduction.'
                    )
                )

            else:

                st.metric(
                    "Estimated RR 2027",
                    "No data"
                )


        with rr_col_2028:

            result_2028 = estimated_rr_results[2028]

            if result_2028["estimated_rr"] is not None:

                st.metric(
                    "Estimated RR 2028",
                    f'{result_2028["estimated_rr"]:.1f}%',
                    help=(
                        f'Selected treatments represent '
                        f'{result_2028["year_proportion"]:.1%} '
                        f'of total Year 2 risk reduction.'
                    )
                )

            else:

                st.metric(
                    "Estimated RR 2028",
                    "No data"
                )


        with rr_col_2029:

            result_2029 = estimated_rr_results[2029]

            if result_2029["estimated_rr"] is not None:

                st.metric(
                    "Estimated RR 2029",
                    f'{result_2029["estimated_rr"]:.1f}%',
                    help=(
                        f'Selected treatments represent '
                        f'{result_2029["year_proportion"]:.1%} '
                        f'of total Year 3 risk reduction.'
                    )
                )

            else:

                st.metric(
                    "Estimated RR 2029",
                    "No data"
                )



       

        # =========================
        # CLICKABLE DOUGHNUT
        # =========================

        # Create a clean sequential dataset so the clicked segment number
        # always matches the correct treatment.

        donut_view = view[
            [
                "Treatment Name",
                "Residual Risk"
            ]
        ].copy()

        donut_view["Residual Risk"] = pd.to_numeric(
            donut_view["Residual Risk"],
            errors="coerce"
        ).fillna(0)

        donut_view = donut_view[
            donut_view["Residual Risk"] != 0
        ].reset_index(drop=True)

        # Convert Pandas Series to ordinary Python lists.
        # This prevents the custom component incorrectly treating
        # each treatment as having an equal value.

        donut_labels = donut_view[
            "Treatment Name"
        ].tolist()

        donut_values = donut_view[
            "Residual Risk"
        ].abs().tolist()

        # Explicit colours prevent the custom component from
        # rendering every doughnut segment in the same colour.

        donut_colours = px.colors.qualitative.Safe

        donut_segment_colours = [
            donut_colours[i % len(donut_colours)]
            for i in range(len(donut_view))
        ]

        donut = go.Figure(
            data=[
                go.Pie(
                    labels=donut_labels,
                    values=donut_values,
                    customdata=donut_labels,
                    hole=0.6,

                    marker=dict(
                        colors=donut_segment_colours,
                        line=dict(
                            color=CARD,
                            width=1
                        )
                    ),

                    textinfo="percent",

                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Risk contribution: %{value:.3f}<br>"
                        "Share of selected risk: %{percent}"
                        "<extra></extra>"
                    ),

                    sort=False
                )
            ]
        )

        donut.update_layout(
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            font=dict(color=TEXT),

            margin=dict(
                l=10,
                r=10,
                t=40,
                b=10
            ),

            legend_itemclick=False,
            legend_itemdoubleclick=False
        )

        # Capture genuine doughnut-segment clicks.

        donut_clicked_points = plotly_events(
            donut,
            click_event=True,
            select_event=False,
            hover_event=False,
            override_height=500,
            key=(
                f"burn_priority_donut_click_"
                f"{st.session_state['chart_reset_version']}"
            )
        )

        if donut_clicked_points:
            
            clicked_point_number = donut_clicked_points[0].get(
                "pointNumber"
            )

            if clicked_point_number is not None:

                clicked_point_number = int(
                    clicked_point_number
                )

                if 0 <= clicked_point_number < len(donut_view):

                    clicked_burn = donut_view.iloc[
                        clicked_point_number
                    ]["Treatment Name"]

                    st.session_state[
                        "map_focus_burn"
                    ] = clicked_burn

                    # Consume the doughnut click by forcing both
                    # interactive charts to receive fresh widget keys.
                    # The selected burn remains stored for the map,
                    # but the old doughnut event cannot replay.

                    st.session_state[
                        "chart_reset_version"
                    ] += 1

                    st.rerun()



# ==========================================================
# TAB 2 - RESIDUAL RISK OUTCOMES
# ==========================================================

with tab2:

    st.markdown(
        '<div class="title">Murray Goldfields Residual Risk Outcomes</div>',
        unsafe_allow_html=True
    )

    top_left, top_right = st.columns([1, 1])

    # =====================================================
    # TOP LEFT - NARRATIVE
    # =====================================================

    with top_left:

        st.subheader("Overview")

        try:

            with open(
                RR_MG_NARRATIVE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                st.markdown(f.read())

        except:

            st.warning(
                "Residual Risk narrative file not found."
            )

    # =====================================================
    # TOP RIGHT - SPEEDOMETERS
    # =====================================================

    with top_right:

        # Use Murray Goldfields worksheet

        projection_rows = rr_mg[
            rr_mg[
                [
                    "Projected Residual Risk with JFMP",
                    "Projected Residual Risk without JFMP"
                ]
            ].notna().any(axis=1)
        ].copy()

        season_options = projection_rows["Season"].tolist()[1:]
        selected_season = st.selectbox(
            "Projection Season",
            season_options,
            index=0
        )

        selected_projection = projection_rows[
            projection_rows["Season"] == selected_season
        ].iloc[0]

        with_jfmp_value = selected_projection[
            "Projected Residual Risk with JFMP"
        ]

        without_jfmp_value = selected_projection[
            "Projected Residual Risk without JFMP"
        ]

        gauge1, gauge2 = st.columns(2)

        # =========================
        # GAUGE COLOURS AND TARGET
        # =========================

        TARGET_RISK = 75.0
        BELOW_TARGET_COLOUR = "#2ca02c"   # Green
        AT_OR_ABOVE_TARGET_COLOUR = "#e63946"   # Red

        with_jfmp_colour = (
            BELOW_TARGET_COLOUR
            if with_jfmp_value < TARGET_RISK
            else AT_OR_ABOVE_TARGET_COLOUR
        )

        without_jfmp_colour = (
            BELOW_TARGET_COLOUR
            if without_jfmp_value < TARGET_RISK
            else AT_OR_ABOVE_TARGET_COLOUR
        )

        gauge1, gauge2 = st.columns(2)

        with gauge1:

            fig1 = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=with_jfmp_value,
                    number={
                        "suffix": "%",
                        "valueformat": ".1f",
                        "font": {
                            "color": with_jfmp_colour
                        }
                    },
                    title={
                        "text": (
                            "With JFMP"
                            "<br><span style='font-size:14px'>"
                            "Target: 75%</span>"
                        )
                    },
                    gauge={
                        "axis": {
                            "range": [0, 100],
                            "ticksuffix": "%"
                        },
                        "bar": {
                            "color": with_jfmp_colour,
                            "thickness": 0.75
                        },
                        "steps": [
                            {
                                "range": [0, TARGET_RISK],
                                "color": "#e8f5e9"
                            },
                            {
                                "range": [TARGET_RISK, 100],
                                "color": "#fdeaea"
                            }
                        ],
                        "threshold": {
                            "line": {
                                "color": "#f39c12",
                                "width": 5
                            },
                            "thickness": 0.85,
                            "value": TARGET_RISK
                        }
                    }
                )
            )

            fig1.update_layout(
                height=300,
                paper_bgcolor=CARD,
                font=dict(color=TEXT),
                margin=dict(l=15, r=15, t=70, b=15)
            )

            st.plotly_chart(
                fig1,
                use_container_width=True
            )

        with gauge2:

            fig2 = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=without_jfmp_value,
                    number={
                        "suffix": "%",
                        "valueformat": ".1f",
                        "font": {
                            "color": without_jfmp_colour
                        }
                    },
                    title={
                        "text": (
                            "Without JFMP"
                            "<br><span style='font-size:14px'>"
                            "Target: 75%</span>"
                        )
                    },
                    gauge={
                        "axis": {
                            "range": [0, 100],
                            "ticksuffix": "%"
                        },
                        "bar": {
                            "color": without_jfmp_colour,
                            "thickness": 0.75
                        },
                        "steps": [
                            {
                                "range": [0, TARGET_RISK],
                                "color": "#e8f5e9"
                            },
                            {
                                "range": [TARGET_RISK, 100],
                                "color": "#fdeaea"
                            }
                        ],
                        "threshold": {
                            "line": {
                                "color": "#f39c12",
                                "width": 5
                            },
                            "thickness": 0.85,
                            "value": TARGET_RISK
                        }
                    }
                )
            )

            fig2.update_layout(
                height=300,
                paper_bgcolor=CARD,
                font=dict(color=TEXT),
                margin=dict(l=15, r=15, t=70, b=15)
            )

            st.plotly_chart(
                fig2,
                use_container_width=True
            )

    # =====================================================
    # BOTTOM ROW
    # =====================================================

    graph_col, locality_col = st.columns([2, 1])

    # =====================================================
    # HERO GRAPH - RR OT PROFILE
    # =====================================================

    with graph_col:

        fig_rr = go.Figure()

        fig_rr.add_trace(
            go.Scatter(
                x=rr_mg_plot["Season"],
                y=rr_mg_plot["Historical Residual Risk"],
                mode="lines",
                name="Historical Residual Risk",
                line=dict(
                    color="#156082",
                    width=3
                ),
                connectgaps=False
            )
        )

        fig_rr.add_trace(
            go.Scatter(
                x=rr_mg_plot["Season"],
                y=rr_mg_plot["Risk Target"],
                mode="lines",
                name="Risk Target",
                line=dict(
                    color="#e97132",
                    width=3
                ),
                connectgaps=False
            )
        )

        fig_rr.add_trace(
            go.Scatter(
                x=rr_mg_plot["Season"],
                y=rr_mg_plot["Projected Residual Risk with JFMP"],
                mode="lines+markers",
                name="Projected Residual Risk with JFMP",
                line=dict(
                    color="#196b24",
                    width=4
                ),
                marker=dict(size=6),
                connectgaps=False
            )
        )

        fig_rr.add_trace(
            go.Scatter(
                x=rr_mg_plot["Season"],
                y=rr_mg_plot["Projected Residual Risk without JFMP"],
                mode="lines+markers",
                name="Projected Residual Risk without JFMP",
                line=dict(
                    color="#0f9ed5",
                    width=4
                ),
                marker=dict(size=6),
                connectgaps=False
            )
        )

        fig_rr.update_layout(
            title={
                "text": (
                    "Murray Goldfields<br>"
                    "<sup>Residual Risk: Historic, Long-term Goal, "
                    "and JFMP Projection</sup>"
                ),
                "x": 0.5,
                "xanchor": "center"
            },
            xaxis=dict(
                title="Season",
                type="category"
            ),
            yaxis=dict(
                title="Residual Risk (%)",
                range=[0, 100],
                ticksuffix="%"
            ),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5
            ),
            paper_bgcolor=CARD,
            plot_bgcolor=CARD,
            font=dict(color=TEXT),
            margin=dict(
                l=60,
                r=30,
                t=90,
                b=110
            ),
            height=550
        )

        st.plotly_chart(
            fig_rr,
            use_container_width=True
        )

        # =====================================================
        # LOCALITY BENEFITS
        # =====================================================

        with locality_col:

            # Sort all eligible localities from highest to lowest benefit
            locality_options_df = locality_loss.sort_values(
                by="Difference",
                ascending=False
            ).copy()

            # Dropdown order also runs from highest to lowest benefit
            locality_options = locality_options_df["Locality"].tolist()

            # Default selection is the top 10 localities
            default_localities = locality_options[:10]

            selected_localities = st.multiselect(
                "Select localities",
                options=locality_options,
                default=default_localities
            )

            # Keep only the localities selected in the dropdown
            locality_plot = locality_options_df[
                locality_options_df["Locality"].isin(selected_localities)
            ].copy()

            # Sort ascending so the highest-value bar appears at the top
            locality_plot = locality_plot.sort_values(
                by="Difference",
                ascending=True
            )

            fig_locality = go.Figure()

            fig_locality.add_trace(
                go.Bar(
                    x=locality_plot["Difference"],
                    y=locality_plot["Locality"],
                    orientation="h",
                    name="Difference",
                    marker_color=PRIMARY,
                    hovertemplate=(
                        "<b>%{y}</b><br>"
                        "Difference: %{x:,.2f}"
                        "<extra></extra>"
                    )
                )
            )

            fig_locality.update_layout(
                title={
                    "text": "Localities Most Protected by the JFMP",
                    "x": 0.5,
                    "xanchor": "center"
                },
                xaxis=dict(
                    title="Difference"
                ),
                yaxis=dict(
                    title=None,
                    automargin=True
                ),
                paper_bgcolor=CARD,
                plot_bgcolor=CARD,
                font=dict(color=TEXT),
                showlegend=False,
                margin=dict(
                    l=20,
                    r=20,
                    t=70,
                    b=50
                ),
                height=550
            )

            st.plotly_chart(
                fig_locality,
                use_container_width=True
            )

# ==========================================================
# TAB 3 - MALLEE RESIDUAL RISK OUTCOMES
# ==========================================================

with tab3:

    st.markdown(
        '<div class="title">Mallee Residual Risk Outcomes</div>',
        unsafe_allow_html=True
    )

    top_left_mal, top_right_mal = st.columns([1, 1])

    # =====================================================
    # TOP LEFT - MALLEE NARRATIVE
    # =====================================================

    with top_left_mal:

        st.subheader("Overview")

        try:

            with open(
                RR_MAL_NARRATIVE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                st.markdown(f.read())

        except Exception as e:

            st.warning(
                f"Mallee Residual Risk narrative file not found: {e}"
            )

    # =====================================================
    # TOP RIGHT - MALLEE SPEEDOMETERS
    # =====================================================

    with top_right_mal:

        # Use Mallee worksheet projection data

        projection_rows_mal_tab = rr_mal[
            rr_mal[
                [
                    "Projected Residual Risk with JFMP",
                    "Projected Residual Risk without JFMP"
                ]
            ].notna().any(axis=1)
        ].copy()

        # Remove the first projection value because it represents current risk

        season_options_mal = (
            projection_rows_mal_tab["Season"]
            .tolist()[1:]
        )

        
        selected_season_mal = st.selectbox(
            "Projection Season",
            season_options_mal,
            index=0,
            key="mallee_projection_season"
        )

        selected_projection_mal = projection_rows_mal_tab[
            projection_rows_mal_tab["Season"] == selected_season_mal
        ].iloc[0]

        with_jfmp_value_mal = selected_projection_mal[
            "Projected Residual Risk with JFMP"
        ]

        without_jfmp_value_mal = selected_projection_mal[
            "Projected Residual Risk without JFMP"
        ]

        # =========================
        # GAUGE COLOURS AND TARGET
        # =========================

        TARGET_RISK_MAL = 90.0

        BELOW_TARGET_COLOUR_MAL = "#2ca02c"
        AT_OR_ABOVE_TARGET_COLOUR_MAL = "#e63946"

        with_jfmp_colour_mal = (
            BELOW_TARGET_COLOUR_MAL
            if with_jfmp_value_mal < TARGET_RISK_MAL
            else AT_OR_ABOVE_TARGET_COLOUR_MAL
        )

        without_jfmp_colour_mal = (
            BELOW_TARGET_COLOUR_MAL
            if without_jfmp_value_mal < TARGET_RISK_MAL
            else AT_OR_ABOVE_TARGET_COLOUR_MAL
        )

        gauge1_mal, gauge2_mal = st.columns(2)

        # =========================
        # WITH JFMP GAUGE
        # =========================

        with gauge1_mal:

            fig1_mal = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=with_jfmp_value_mal,

                    number={
                        "suffix": "%",
                        "valueformat": ".1f",
                        "font": {
                            "color": with_jfmp_colour_mal
                        }
                    },

                    title={
                        "text": (
                            "With JFMP"
                            "<br><span style='font-size:14px'>"
                            "Target: 75%</span>"
                        )
                    },

                    gauge={
                        "axis": {
                            "range": [0, 100],
                            "ticksuffix": "%"
                        },

                        "bar": {
                            "color": with_jfmp_colour_mal,
                            "thickness": 0.75
                        },

                        "steps": [
                            {
                                "range": [0, TARGET_RISK_MAL],
                                "color": "#e8f5e9"
                            },
                            {
                                "range": [TARGET_RISK_MAL, 100],
                                "color": "#fdeaea"
                            }
                        ],

                        "threshold": {
                            "line": {
                                "color": "#f39c12",
                                "width": 5
                            },
                            "thickness": 0.85,
                            "value": TARGET_RISK_MAL
                        }
                    }
                )
            )

            fig1_mal.update_layout(
                height=300,
                paper_bgcolor=CARD,
                font=dict(color=TEXT),
                margin=dict(
                    l=15,
                    r=15,
                    t=70,
                    b=15
                )
            )

            st.plotly_chart(
                fig1_mal,
                use_container_width=True
            )

        # =========================
        # WITHOUT JFMP GAUGE
        # =========================

        with gauge2_mal:

            fig2_mal = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=without_jfmp_value_mal,

                    number={
                        "suffix": "%",
                        "valueformat": ".1f",
                        "font": {
                            "color": without_jfmp_colour_mal
                        }
                    },

                    title={
                        "text": (
                            "Without JFMP"
                            "<br><span style='font-size:14px'>"
                            "Target: 75%</span>"
                        )
                    },

                    gauge={
                        "axis": {
                            "range": [0, 100],
                            "ticksuffix": "%"
                        },

                        "bar": {
                            "color": without_jfmp_colour_mal,
                            "thickness": 0.75
                        },

                        "steps": [
                            {
                                "range": [0, TARGET_RISK_MAL],
                                "color": "#e8f5e9"
                            },
                            {
                                "range": [TARGET_RISK_MAL, 100],
                                "color": "#fdeaea"
                            }
                        ],

                        "threshold": {
                            "line": {
                                "color": "#f39c12",
                                "width": 5
                            },
                            "thickness": 0.85,
                            "value": TARGET_RISK_MAL
                        }
                    }
                )
            )

            fig2_mal.update_layout(
                height=300,
                paper_bgcolor=CARD,
                font=dict(color=TEXT),
                margin=dict(
                    l=15,
                    r=15,
                    t=70,
                    b=15
                )
            )

            st.plotly_chart(
                fig2_mal,
                use_container_width=True
            )

    # =====================================================
    # BOTTOM ROW
    # =====================================================

    graph_col_mal, locality_col_mal = st.columns([2, 1])

    # =====================================================
    # MALLEE HERO GRAPH - RESIDUAL RISK PROFILE
    # =====================================================

    with graph_col_mal:

        fig_rr_mal = go.Figure()

        # Historical Residual Risk

        fig_rr_mal.add_trace(
            go.Scatter(
                x=rr_mal_plot["Season"],
                y=rr_mal_plot["Historical Residual Risk"],
                mode="lines",
                name="Historical Residual Risk",

                line=dict(
                    color="#156082",
                    width=3
                ),

                connectgaps=False
            )
        )

        # Risk Target

        fig_rr_mal.add_trace(
            go.Scatter(
                x=rr_mal_plot["Season"],
                y=rr_mal_plot["Risk Target"],
                mode="lines",
                name="Risk Target",

                line=dict(
                    color="#e97132",
                    width=3
                ),

                connectgaps=False
            )
        )

        # Projected Residual Risk with JFMP

        fig_rr_mal.add_trace(
            go.Scatter(
                x=rr_mal_plot["Season"],
                y=rr_mal_plot[
                    "Projected Residual Risk with JFMP"
                ],
                mode="lines+markers",
                name="Projected Residual Risk with JFMP",

                line=dict(
                    color="#196b24",
                    width=4
                ),

                marker=dict(
                    size=6
                ),

                connectgaps=False
            )
        )

        # Projected Residual Risk without JFMP

        fig_rr_mal.add_trace(
            go.Scatter(
                x=rr_mal_plot["Season"],
                y=rr_mal_plot[
                    "Projected Residual Risk without JFMP"
                ],
                mode="lines+markers",
                name="Projected Residual Risk without JFMP",

                line=dict(
                    color="#0f9ed5",
                    width=4
                ),

                marker=dict(
                    size=6
                ),

                connectgaps=False
            )
        )

        fig_rr_mal.update_layout(

            title={
                "text": (
                    "Mallee<br>"
                    "<sup>Residual Risk: Historic, Long-term Goal, "
                    "and JFMP Projection</sup>"
                ),
                "x": 0.5,
                "xanchor": "center"
            },

            xaxis=dict(
                title="Season",
                type="category"
            ),

            yaxis=dict(
                title="Residual Risk (%)",
                range=[0, 100],
                ticksuffix="%"
            ),

            hovermode="x unified",

            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.18,
                xanchor="center",
                x=0.5
            ),

            paper_bgcolor=CARD,
            plot_bgcolor=CARD,

            font=dict(
                color=TEXT
            ),

            margin=dict(
                l=60,
                r=30,
                t=90,
                b=110
            ),

            height=550
        )

        st.plotly_chart(
            fig_rr_mal,
            use_container_width=True
        )

    # =====================================================
    # MALLEE LOCALITY BENEFITS
    # =====================================================

    with locality_col_mal:

        # Sort eligible Mallee localities from highest to lowest benefit

        locality_options_df_mal = locality_loss_mal.sort_values(
            by="Difference",
            ascending=False
        ).copy()

        # Dropdown order runs from highest to lowest benefit

        locality_options_mal = (
            locality_options_df_mal["Locality"]
            .tolist()
        )

        # Default selection is the top 10 Mallee localities

        default_localities_mal = locality_options_mal[:10]

        selected_localities_mal = st.multiselect(
            "Select localities",
            options=locality_options_mal,
            default=default_localities_mal,
            key="mallee_locality_selection"
        )

        # Keep only selected Mallee localities

        locality_plot_mal = locality_options_df_mal[
            locality_options_df_mal["Locality"].isin(
                selected_localities_mal
            )
        ].copy()

        # Sort ascending so highest-value bar appears at top

        locality_plot_mal = locality_plot_mal.sort_values(
            by="Difference",
            ascending=True
        )

        fig_locality_mal = go.Figure()

        fig_locality_mal.add_trace(
            go.Bar(
                x=locality_plot_mal["Difference"],
                y=locality_plot_mal["Locality"],
                orientation="h",
                name="Difference",
                marker_color=PRIMARY,

                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Difference: %{x:,.2f}"
                    "<extra></extra>"
                )
            )
        )

        fig_locality_mal.update_layout(

            title={
                "text": "Mallee Localities Most Protected by the JFMP",
                "x": 0.5,
                "xanchor": "center"
            },

            xaxis=dict(
                title="Difference"
            ),

            yaxis=dict(
                title=None,
                automargin=True
            ),

            paper_bgcolor=CARD,
            plot_bgcolor=CARD,

            font=dict(
                color=TEXT
            ),

            showlegend=False,

            margin=dict(
                l=20,
                r=20,
                t=70,
                b=50
            ),

            height=550
        )

        st.plotly_chart(
            fig_locality_mal,
            use_container_width=True
        )

# ==========================================================
# TAB 4 - SPRING_PRIORITIES
# ==========================================================

with tab4:

    st.markdown(
        '<div class="title">Spring Burn Summary</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([2,5])

    with col1:

        st.subheader("Spring Priorities")
        
        st.markdown(
            f"""
            <div style="
                background-color:#e8f4fd;
                color:#0f4c81;
                padding:20px;
                border-radius:10px;
                font-size:18px;
                line-height:1.6;
                border-left:5px solid #1f77b4;
            ">
            {spring_narrative}
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown("## 🔥 Priority Burns")

        st.markdown(
        'Note: Fire Invesitigation and training burns have been omitted from this assessment')

        # Split the TXT content at each Markdown level-2 heading
        burn_sections = re.split(
            r"(?=^##\s+)",
            spring_priorities,
            flags=re.MULTILINE
        )

        # Remove blank sections
        burn_sections = [
            section.strip()
            for section in burn_sections
            if section.strip()
        ]

        priority_col1, priority_col2 = st.columns(2)

        for index, section in enumerate(burn_sections):

            target_column = (
                priority_col1
                if index % 2 == 0
                else priority_col2
            )

            with target_column:
                with st.container(border=True):
                    st.markdown(section)

st.sidebar.caption(
    f"Render time: {time.time() - start_time:.2f} sec"
)

