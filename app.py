import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import io

# ─── Config ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Auditoria de Faltas",
    page_icon="📦",
    layout="wide",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    .block-container { padding-top: 1.5rem; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a3d);
        border: 1px solid #2e3555;
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        text-align: center;
    }
    .metric-value { font-size: 2rem; font-weight: 700; color: #ff4b4b; }
    .metric-label { font-size: 0.8rem; color: #aab0c6; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; }
    .metric-value-green { font-size: 2rem; font-weight: 700; color: #00c896; }
    .metric-value-blue  { font-size: 2rem; font-weight: 700; color: #4e8ef7; }
    .stDownloadButton button {
        background: linear-gradient(90deg, #4e8ef7, #7b5ef7);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ─── Header ──────────────────────────────────────────────────────────────────
st.title("📦 Auditoria de Faltas — Top 10 SKUs")
st.markdown("---")

# ─── Sidebar: upload + filtros ────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configurações")
    arquivo = st.file_uploader("Upload do Excel de auditoria", type=["xlsx", "xls"])

    nome_filial = st.text_input("Nome da Filial", placeholder="Ex: Castanhal, Belém, Barcarena...")
    data_ref = st.date_input("Data da auditoria", value=date.today())

    st.markdown("---")
    st.caption("Colunas esperadas: `Un. Neg.`, `Embalagem`, `Dif`, `Est. Ap.`, `Est. Te.`, `Custo Total`")

# ─── Leitura do arquivo ───────────────────────────────────────────────────────
if arquivo is None:
    st.info("👈 Faça upload de um arquivo Excel para começar.")
    st.stop()

@st.cache_data(show_spinner="Lendo arquivo...")
def carregar_excel(conteudo: bytes) -> pd.DataFrame:
    df = pd.read_excel(io.BytesIO(conteudo), header=1)

    # Renomear para nomes seguros
    rename = {
        "Un. Neg.": "filial",
        "Embalagem": "sku",
        "Classificação 2° Nível": "categoria",
        "Dif": "diferenca",
        "Est. Ap.": "est_ap",
        "Est. Te.": "est_te",
        "Custo Total": "custo_total",
    }
    df = df.rename(columns={k: v for k, v in rename.items() if k in df.columns})

    # Garantir tipos
    for col in ["diferenca", "est_ap", "est_te", "custo_total"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "filial" in df.columns:
        df["filial"] = df["filial"].astype(str).str.strip()

    return df

conteudo = arquivo.read()
df_raw = carregar_excel(conteudo)

# ─── Validação de colunas ────────────────────────────────────────────────────
colunas_necessarias = {"filial", "sku", "diferenca", "est_ap", "custo_total"}
faltando = colunas_necessarias - set(df_raw.columns)
if faltando:
    st.error(f"❌ Colunas não encontradas no arquivo: `{faltando}`\n\nColunas presentes: `{list(df_raw.columns)}`")
    st.stop()

# ─── Nome da filial informado manualmente ────────────────────────────────────
df = df_raw.copy()
filial_selecionada = nome_filial.strip() if nome_filial.strip() else "Não informada"

if df.empty:
    st.warning("O arquivo não contém dados.")
    st.stop()

# ─── Métricas gerais ──────────────────────────────────────────────────────────
total_skus   = len(df)
skus_falta   = df[df["diferenca"] < 0]
skus_sobra   = df[df["diferenca"] > 0]
perda_total  = skus_falta["custo_total"].sum()
sobra_total  = skus_sobra["custo_total"].sum()
qtd_faltas   = len(skus_falta)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value-blue">{total_skus:,}</div>
        <div class="metric-label">Total de SKUs</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{qtd_faltas:,}</div>
        <div class="metric-label">SKUs com Falta</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value-green">{len(skus_sobra):,}</div>
        <div class="metric-label">SKUs com Sobra</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">R$ {abs(perda_total):,.2f}</div>
        <div class="metric-label">Perda (R$)</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value-green">R$ {sobra_total:,.2f}</div>
        <div class="metric-label">Sobra (R$)</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─── Top 10 faltas ────────────────────────────────────────────────────────────
top10 = (
    skus_falta
    .sort_values("diferenca")      # mais negativo = maior falta
    .head(10)
    .copy()
)
top10["falta_abs"]   = top10["diferenca"].abs()
top10["custo_abs"]   = top10["custo_total"].abs()
top10["sku_short"]   = top10["sku"].str[:40] + top10["sku"].apply(lambda x: "…" if len(x) > 40 else "")

# ─── Layout: gráfico + tabela ─────────────────────────────────────────────────
col_graf, col_tab = st.columns([3, 2], gap="large")

with col_graf:
    st.subheader(f"📉 Top 10 SKUs com mais faltas — Filial {filial_selecionada} | {data_ref.strftime('%d/%m/%Y')}")

    fig = go.Figure()

    # Barras de quantidade de falta
    fig.add_trace(go.Bar(
        y=top10["sku_short"][::-1],
        x=top10["falta_abs"][::-1],
        orientation="h",
        name="Qtd. Falta",
        marker=dict(
            color=top10["falta_abs"][::-1],
            colorscale=[[0, "#ff8c8c"], [1, "#cc0000"]],
            showscale=False,
        ),
        text=top10["falta_abs"][::-1].apply(lambda v: f"{v:,.0f} un"),
        textposition="outside",
        textfont=dict(color="white", size=12),
        customdata=top10[["custo_abs", "est_ap"]][::-1].values,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Qtd. Falta: %{x:,.0f} un<br>"
            "Impacto financeiro: R$ %{customdata[0]:,.2f}<br>"
            "Est. Apontado: %{customdata[1]:,.0f}<extra></extra>"
        ),
    ))

    fig.update_layout(
        height=480,
        margin=dict(l=20, r=100, t=20, b=20),
        plot_bgcolor="#0f1117",
        paper_bgcolor="#0f1117",
        font=dict(color="white", family="Inter, sans-serif"),
        xaxis=dict(
            title="Quantidade de Falta (unidades)",
            gridcolor="#2e3555",
            tickfont=dict(color="#aab0c6"),
        ),
        yaxis=dict(
            gridcolor="#2e3555",
            tickfont=dict(color="white", size=11),
        ),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

with col_tab:
    st.subheader("🗂️ Detalhamento")

    tabela = top10[["sku", "diferenca", "est_ap", "est_te", "custo_abs"]].copy()
    tabela.columns = ["SKU", "Diferença", "Est. Ap.", "Est. Te.", "Impacto R$"]
    tabela = tabela.reset_index(drop=True)
    tabela.index += 1

    st.dataframe(
        tabela.style
            .format({
                "Diferença": "{:,.0f}",
                "Est. Ap.": "{:,.0f}",
                "Est. Te.": "{:,.0f}",
                "Impacto R$": "R$ {:,.2f}",
            })
            .map(lambda v: "color: #ff4b4b;" if isinstance(v, (int, float)) and v < 0 else "", subset=["Diferença"])
            .set_properties(**{"background-color": "#1e2130", "color": "white"}),
        use_container_width=True,
        height=430,
    )

# ─── Gráfico de impacto financeiro ───────────────────────────────────────────
st.markdown("---")
st.subheader("💰 Impacto Financeiro — Top 10 faltas")

fig2 = px.bar(
    top10.sort_values("custo_abs"),
    x="custo_abs",
    y="sku_short",
    orientation="h",
    text=top10.sort_values("custo_abs")["custo_abs"].apply(lambda v: f"R$ {v:,.2f}"),
    color="custo_abs",
    color_continuous_scale=["#ff8c8c", "#8b0000"],
    labels={"custo_abs": "Impacto (R$)", "sku_short": "SKU"},
)
fig2.update_traces(textposition="outside", textfont=dict(color="white", size=11))
fig2.update_layout(
    height=420,
    margin=dict(l=20, r=120, t=10, b=20),
    plot_bgcolor="#0f1117",
    paper_bgcolor="#0f1117",
    font=dict(color="white"),
    coloraxis_showscale=False,
    xaxis=dict(gridcolor="#2e3555", tickprefix="R$ ", tickfont=dict(color="#aab0c6")),
    yaxis=dict(gridcolor="#2e3555", tickfont=dict(color="white", size=11)),
)
st.plotly_chart(fig2, use_container_width=True)

# ─── Export ──────────────────────────────────────────────────────────────────
st.markdown("---")
col_dl1, col_dl2, _ = st.columns([1, 1, 3])

with col_dl1:
    csv_bytes = top10[["sku", "diferenca", "est_ap", "est_te", "custo_total"]].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Exportar Top 10 (CSV)",
        data=csv_bytes,
        file_name=f"top10_faltas_filial{filial_selecionada}_{data_ref}.csv",
        mime="text/csv",
    )

with col_dl2:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        top10[["sku", "diferenca", "est_ap", "est_te", "custo_total"]].to_excel(writer, index=False, sheet_name="Top10 Faltas")
        df.to_excel(writer, index=False, sheet_name="Dados Completos")
    st.download_button(
        "⬇️ Exportar Relatório (Excel)",
        data=buf.getvalue(),
        file_name=f"auditoria_filial{filial_selecionada}_{data_ref}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
