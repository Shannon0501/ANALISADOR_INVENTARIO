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
    df = pd.read_excel(
        arquivo,
        sheet_name=0,
        engine="openpyxl"
    )

    colunas_necessarias = [
        "Filiais",
        "Embalagem",
        "classification",
        "Qtd Ap",
        "Qtd Teórico",
        "Diferença",
        "Custo Total da diferença"
    ]

    faltantes = [col for col in colunas_necessarias if col not in df.columns]

    if faltantes:
        st.error(f"Colunas ausentes no arquivo: {faltantes}")
        st.stop()

    df = df[colunas_necessarias].copy()

    for col in ["Qtd Ap", "Qtd Teórico", "Diferença", "Custo Total da diferença"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Filiais"] = df["Filiais"].astype(str).str.strip()

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

# =========================
# Lista de filiais
# =========================

lista_filiais = [
    "ABAETETUBA 1",
    "CAPANEMA 1",
    "CASTANHAL 1",
    "CAMETA",
    "CAPITAO POCO",
    "SANTA ISABEL",
    "ABAETETUBA 2",
    "CASTANHAL 2",
    "BARCARENA 1",
    "QUATRO BOCAS",
    "CASTANHAL 3",
    "ITAITUBA 1",
    "ITAITUBA 2",
    "CASTANHAL 4",
    "CASTANHAL 5",
    "MAE DO RIO",
    "CAPANEMA 2",
    "PORTEL",
    "BENEVIDES"
]

# =========================
# Menu lateral
# =========================

st.sidebar.header("Filtros")

filial_selecionada = st.sidebar.selectbox(
    "Filial",
    options=lista_filiais
)
)

data_inventario = st.sidebar.date_input(
    "Data do Inventário"
)

arquivo_excel = st.sidebar.file_uploader(
    "Upload do arquivo Excel",
    type=["xlsx"]
)

# =========================
# Aplicação
# =========================

if arquivo_excel is None:
    st.info("Faça o upload do arquivo Excel para iniciar a análise.")
    st.stop()

df = carregar_aba_principal(arquivo_excel)

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
# Gráfico por classification
# =========================

st.subheader("Custo Total da Diferença por Classificação")

df_grafico = (
    df_filtrado
    .groupby("classification", as_index=False)["Custo Total da diferença"]
    .sum()
    .sort_values("Custo Total da diferença")
)

fig = px.bar(
    df_grafico,
    x="classification",
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
