import os
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Análise de Inventário",
    layout="wide"
)

HISTORICO_CSV = "historico_inventario.csv"

st.title("Análise de Inventário")

# =========================
# Funções auxiliares
# =========================

def carregar_aba_principal(arquivo):
    """
    Lê a primeira aba do Excel e trata arquivos cujo cabeçalho real esteja na primeira linha.
    """
    df_raw = pd.read_excel(arquivo, sheet_name=0, header=None)

    # Detecta linha de cabeçalho procurando "Embalagem"
    header_row = None
    for i in range(min(10, len(df_raw))):
        valores = df_raw.iloc[i].astype(str).str.lower().tolist()
        if any("embalagem" in v for v in valores):
            header_row = i
            break

    if header_row is not None:
        df = pd.read_excel(arquivo, sheet_name=0, header=header_row)
    else:
        df = pd.read_excel(arquivo, sheet_name=0)

    df.columns = [str(c).strip() for c in df.columns]
    return df


def padronizar_colunas(df):
    """
    Padroniza nomes vindos do modelo anexado ou do layout informado.
    """
    mapa = {}

    for col in df.columns:
        c = col.strip().lower()

        if c in ["filiais", "filial", "un. neg.", "un neg", "unidade"]:
            mapa[col] = "Filiais"

        elif c in ["embalagem", "produto", "sku"]:
            mapa[col] = "Embalagem"

        elif "classificação" in c or "classificacao" in c:
            mapa[col] = "classificação"

        elif c in ["qtd ap", "est. ap.", "estoque apurado"]:
            mapa[col] = "Qtd Ap"

        elif c in ["qtd teórico", "qtd teorico", "est. te.", "estoque teórico", "estoque teorico"]:
            mapa[col] = "Qtd Teórico"

        elif c in ["diferença", "diferenca", "dif"]:
            mapa[col] = "Diferença"

        elif "custo total" in c:
            mapa[col] = "Custo Total da diferença"

    df = df.rename(columns=mapa)

    colunas_necessarias = [
        "Filiais",
        "Embalagem",
        "classificação",
        "Qtd Ap",
        "Qtd Teórico",
        "Diferença",
        "Custo Total da diferença"
    ]

    faltantes = [c for c in colunas_necessarias if c not in df.columns]

    if faltantes:
        st.error(f"Colunas ausentes no arquivo: {faltantes}")
        st.stop()

    df = df[colunas_necessarias].copy()

    for col in ["Qtd Ap", "Qtd Teórico", "Diferença", "Custo Total da diferença"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Filiais"] = pd.to_numeric(df["Filiais"], errors="coerce")
    df = df.dropna(subset=["Filiais"])
    df["Filiais"] = df["Filiais"].astype(int)

    return df


def salvar_historico(df_filtrado, filial, data_inventario):
    resumo = {
        "Data Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Filial": filial,
        "Data Inventário": data_inventario.strftime("%Y-%m-%d"),
        "Valor Total de Faltas": df_filtrado.loc[
            df_filtrado["Custo Total da diferença"] < 0,
            "Custo Total da diferença"
        ].sum(),
        "Valor Total de Sobras": df_filtrado.loc[
            df_filtrado["Custo Total da diferença"] > 0,
            "Custo Total da diferença"
        ].sum(),
        "Quantidade de SKUs Zerados": (df_filtrado["Qtd Ap"] == 0).sum(),
        "Quantidade de Itens": len(df_filtrado)
    }

    historico = pd.DataFrame([resumo])

    if os.path.exists(HISTORICO_CSV):
        historico.to_csv(
            HISTORICO_CSV,
            mode="a",
            index=False,
            header=False,
            encoding="utf-8-sig"
        )
    else:
        historico.to_csv(
            HISTORICO_CSV,
            index=False,
            encoding="utf-8-sig"
        )


# =========================
# Menu lateral
# =========================

st.sidebar.header("Filtros")

filial_selecionada = st.sidebar.selectbox(
    "Filial",
    options=list(range(1, 21))
)

data_inventario = st.sidebar.date_input(
    "Data do Inventário"
)

arquivo_excel = st.sidebar.file_uploader(
    "Upload do arquivo Excel",
    type=["xlsx", "xls"]
)

# =========================
# Aplicação
# =========================

if arquivo_excel is None:
    st.info("Faça o upload do arquivo Excel para iniciar a análise.")
    st.stop()

df = carregar_aba_principal(arquivo_excel)
df = padronizar_colunas(df)

df_filtrado = df[df["Filiais"] == filial_selecionada].copy()

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para a filial selecionada.")
    st.stop()

# =========================
# Cards de resumo
# =========================

valor_faltas = df_filtrado.loc[
    df_filtrado["Custo Total da diferença"] < 0,
    "Custo Total da diferença"
].sum()

valor_sobras = df_filtrado.loc[
    df_filtrado["Custo Total da diferença"] > 0,
    "Custo Total da diferença"
].sum()

skus_zerados = (df_filtrado["Qtd Ap"] == 0).sum()

col1, col2, col3 = st.columns(3)

col1.metric(
    "Valor Total de Faltas",
    f"R$ {valor_faltas:,.2f}"
)

col2.metric(
    "Valor Total de Sobras",
    f"R$ {valor_sobras:,.2f}"
)

col3.metric(
    "Quantidade de SKUs Zerados",
    int(skus_zerados)
)

st.divider()

# =========================
# Gráfico por classificação
# =========================

st.subheader("Custo Total da Diferença por Classificação")

df_grafico = (
    df_filtrado
    .groupby("classificação", as_index=False)["Custo Total da diferença"]
    .sum()
    .sort_values("Custo Total da diferença")
)

fig = px.bar(
    df_grafico,
    x="classificação",
    y="Custo Total da diferença",
    text_auto=".2s",
    title="Custo Total da Diferença por Classificação"
)

fig.update_layout(
    xaxis_title="Classificação",
    yaxis_title="Custo Total da Diferença",
    xaxis_tickangle=-45
)

st.plotly_chart(fig, use_container_width=True)

# =========================
# Top 10 prejuízos
# =========================

st.subheader("Top 10 SKUs com Maior Prejuízo")

top_10_prejuizo = (
    df_filtrado[df_filtrado["Custo Total da diferença"] < 0]
    .sort_values("Custo Total da diferença")
    .head(10)
)

st.dataframe(
    top_10_prejuizo,
    use_container_width=True
)

# =========================
# Histórico
# =========================

st.divider()

if st.button("Salvar no Histórico"):
    salvar_historico(df_filtrado, filial_selecionada, data_inventario)
    st.success("Dados salvos no histórico com sucesso.")

if os.path.exists(HISTORICO_CSV):
    st.subheader("Histórico Salvo")
    historico = pd.read_csv(HISTORICO_CSV)
    st.dataframe(historico, use_container_width=True)
