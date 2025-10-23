import os
from datetime import date
import pandas as pd
import altair as alt
import streamlit as st

st.set_page_config(page_title="GHG Calculator & Dashboard", layout="wide")
st.title("🌍 GHG Calculator & Dashboard (Scopes 1/2/3 + unit conversions)")

DATA_PATH = "emissions_activity_data.csv"   # 활동자료 + 계산결과 저장 파일

# ------------------------ Defaults ------------------------
# AR6 100-yr GWP (원하면 사이드바에서 수정 가능)
DEFAULT_GWP = {"CO2": 1.0, "CH4": 27.2, "N2O": 273.0}

# 배출계수(예시). 단위 = kg gas / activity-unit
# 필요 시 사이드바에서 수정 가능. (한국 값으로 대체 가능)
DEFAULT_EF = pd.DataFrame([
    # category, unit, scope, ef_co2, ef_ch4, ef_n2o
    ["electricity_grid", "kWh",        2, 0.5,      0.0,     0.0],      # 0.5 kgCO2/kWh (예시)
    ["diesel_stationary", "L",         1, 2.68,     0.0001,  0.00008],  # 연소(고정) 예시
    ["lng_stationary",    "Nm3",       1, 2.0,      0.00005, 0.00003],
    ["waste_mixed",       "kg",        3, 0.7,      0.0,     0.0],      # 처리/위탁 배출
    ["water",             "m3",        3, 0.34,     0.0,     0.0],      # 상수도(예시)
], columns=["Category", "Unit", "Scope", "EF_CO2", "EF_CH4", "EF_N2O"])

# ------------------------ Helpers ------------------------
def load_data() -> pd.DataFrame:
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
    else:
        df = pd.DataFrame(columns=[
            "Date","Year","Region","Facility","Scope","Category","Activity","Unit",
            "EF_CO2","EF_CH4","EF_N2O","GWP_CO2","GWP_CH4","GWP_N2O",
            "CO2e_kg","Note"
        ])
    return df

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False)

def compute_co2e(activity, ef_co2, ef_ch4, ef_n2o, gwp):
    # activity * (EF_CO2*1 + EF_CH4*GWP_CH4 + EF_N2O*GWP_N2O)
    return float(activity) * (
        float(ef_co2)*gwp["CO2"] + float(ef_ch4)*gwp["CH4"] + float(ef_n2o)*gwp["N2O"]
    )

# ------------------------ Sidebar: parameters ------------------------
st.sidebar.header("⚙️ Parameters")

# GWP editable
st.sidebar.subheader("GWP (AR6, 100-yr)")
gwp = {}
for gas in ["CO2","CH4","N2O"]:
    gwp[gas] = st.sidebar.number_input(f"{gas}", value=float(DEFAULT_GWP[gas]))

# EF editable
st.sidebar.subheader("Emission factors (kg gas / unit)")
ef_table = st.sidebar.data_editor(
    DEFAULT_EF.copy(),
    hide_index=True,
    num_rows="dynamic",
    use_container_width=True
)

# Optional CSV upload (활동자료 일괄 업로드)
st.sidebar.subheader("Upload activity CSV (optional)")
st.sidebar.caption("Columns: Date,Region,Facility,Category,Activity,Unit,Scope,Note")
up = st.sidebar.file_uploader("CSV", type=["csv"])

# ------------------------ Data load/init ------------------------
df = load_data()

if up:
    new = pd.read_csv(up)
    # infer year
    if "Year" not in new.columns:
        new["Year"] = pd.to_datetime(new["Date"]).dt.year
    # match EFs by Category (merge)
    merged = new.merge(ef_table, on=["Category","Unit","Scope"], how="left")
    for col in ["EF_CO2","EF_CH4","EF_N2O"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    merged["GWP_CO2"] = gwp["CO2"]; merged["GWP_CH4"] = gwp["CH4"]; merged["GWP_N2O"] = gwp["N2O"]
    merged["CO2e_kg"] = merged.apply(
        lambda r: compute_co2e(r["Activity"], r["EF_CO2"], r["EF_CH4"], r["EF_N2O"],
                               {"CO2":r["GWP_CO2"], "CH4":r["GWP_CH4"], "N2O":r["GWP_N2O"]}),
        axis=1
    )
    keep_cols = ["Date","Year","Region","Facility","Scope","Category","Activity","Unit",
                 "EF_CO2","EF_CH4","EF_N2O","GWP_CO2","GWP_CH4","GWP_N2O","CO2e_kg","Note"]
    df = pd.concat([df, merged[keep_cols]], ignore_index=True)
    save_data(df)
    st.success(f"Uploaded {len(new)} records and calculated CO₂e.")

# ------------------------ Tabbed UI ------------------------
tab_calc, tab_dash, tab_table = st.tabs(["📝 Record activity", "📊 Dashboard", "📄 Raw data"])

with tab_calc:
    st.subheader("Add a single activity record")

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        d = st.date_input("Date", value=date.today())
        region = st.text_input("Region", value="Yongin")
        facility = st.text_input("Facility", value="Gomae")
    with c2:
        scope = st.selectbox("Scope", [1,2,3])
        category = st.selectbox("Category", ef_table["Category"].unique().tolist())
        note = st.text_input("Note", "")
    with c3:
        # EF auto-fill by selected category/scope
        ef_row = ef_table[ef_table["Category"]==category].iloc[0]
        unit = st.text_input("Unit", value=str(ef_row["Unit"]))
        ef_co2 = st.number_input("EF_CO2 (kg/unit)", value=float(ef_row["EF_CO2"]), min_value=0.0)
    with c4:
        ef_ch4 = st.number_input("EF_CH4 (kg/unit)", value=float(ef_row["EF_CH4"]), min_value=0.0, format="%.8f")
        ef_n2o = st.number_input("EF_N2O (kg/unit)", value=float(ef_row["EF_N2O"]), min_value=0.0, format="%.8f")

    activity = st.number_input("Activity amount", min_value=0.0, value=0.0)
    calc = compute_co2e(activity, ef_co2, ef_ch4, ef_n2o, gwp)
    st.info(f"👉 Calculated **CO₂e** = **{calc:,.3f} kg** for this record.")

    if st.button("➕ Save record"):
        row = {
            "Date": d.isoformat(),
            "Year": d.year,
            "Region": region,
            "Facility": facility,
            "Scope": scope,
            "Category": category,
            "Activity": activity,
            "Unit": unit,
            "EF_CO2": ef_co2,
            "EF_CH4": ef_ch4,
            "EF_N2O": ef_n2o,
            "GWP_CO2": gwp["CO2"],
            "GWP_CH4": gwp["CH4"],
            "GWP_N2O": gwp["N2O"],
            "CO2e_kg": calc,
            "Note": note
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        save_data(df)
        st.success("Saved ✅")

with tab_dash:
