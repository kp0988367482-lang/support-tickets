import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="GHG Emissions Dashboard", layout="wide")

st.title("🌍 GHG Emissions Dashboard")
st.write("Upload your emission data (CSV) or use the sample dataset below.")

# --- CSV 업로드 ---
uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])
if uploaded_file:
    df_raw = pd.read_csv(uploaded_file)
else:
    try:
        df_raw = pd.read_csv("emissions_data.csv")
        st.info("Using bundled sample: emissions_data.csv")
    except FileNotFoundError:
        st.error("No file uploaded and sample not found. Please upload your CSV file.")
        st.stop()

# --- 데이터 확인 ---
st.subheader("📊 Raw Data Preview")
st.dataframe(df_raw.head())

# --- 데이터 전처리 ---
if "Emission (tCO2e)" not in df_raw.columns:
    st.warning("⚠️ CSV 파일에 'Emission (tCO2e)' 컬럼이 포함되어야 합니다.")
    st.stop()

# --- 국가별 총 배출량 ---
country_sum = df_raw.groupby("Country")["Emission (tCO2e)"].sum().reset_index()

fig_country = px.bar(
    country_sum,
    x="Country",
    y="Emission (tCO2e)",
    title="🌎 Total GHG Emissions by Country",
    color="Emission (tCO2e)",
    color_continuous_scale="YlOrRd",
)
st.plotly_chart(fig_country, use_container_width=True)

# --- 연도별 추세 ---
if "Year" in df_raw.columns:
    yearly = df_raw.groupby("Year")["Emission (tCO2e)"].sum().reset_index()
    fig_year = px.line(
        yearly, x="Year", y="Emission (tCO2e)", markers=True, title="📈 Yearly Emission Trends"
    )
    st.plotly_chart(fig_year, use_container_width=True)

# --- Scope별 비율 ---
if "Scope" in df_raw.columns:
    scope_sum = df_raw.groupby("Scope")["Emission (tCO2e)"].sum().reset_index()
    fig_scope = px.pie(
        scope_sum,
        names="Scope",
        values="Emission (tCO2e)",
        title="♻️ Emission by Scope (1, 2, 3)",
    )
    st.plotly_chart(fig_scope, use_container_width=True)

st.success("✅ Dashboard loaded successfully!")
