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

# ====================================
# MAPEAMENTO DAS FILIAIS
# ====================================

MAPA_FILIAIS = {
    1: "ABAETETUBA 1",
    2: "CAPANEMA 1",
    3: "CASTANHAL 1",
    4: "CAMETA",
    5: "CAPITAO POCO",
    6: "SANTA ISABEL",
    7: "ABAETETUBA 2",
    8: "CASTANHAL 2",
    9: "BARCARENA 1",
    10: "QUATRO BOCAS",
    11: "CASTANHAL 3",
    12: "ITAITUBA 1",
    13: "ITAITUBA 2",
    14: "CASTANHAL 4",
    15: "CASTANHAL 5",
    16: "MAE DO RIO",
    17: "CAPANEMA 2",
    18: "PORTEL",
    19: "BENEVIDES",
    22: "BENEVIDES"
}

LISTA_FILIAIS = list(MAPA_FILIAIS.values())

st.title("Análise de Inventário")


# ====================================
# LEITURA DO EXCEL
# ====================================

def carregar_aba_principal(arquivo):

    df = pd.read_excel(
        arquivo,
        sheet_name=0,
        header=1,
        engine="openpyxl"
    )

    df = df.rename(columns={
        "Un. Neg.": "CodigoFilial",
        "Embalagem": "Embalagem",
        "Classificação 2° Nível": "classification",
        "Est. Ap.": "Qtd Ap",
        "Est. Te.": "Qtd Teórico",
        "Dif": "Diferença",
        "Custo Total": "Custo Total da diferença"
    })

    colunas_necessarias = [
        "CodigoFilial",
        "Embalagem",
        "classification",
        "Qtd Ap",
        "Qtd Teórico",
        "Diferença",
        "Custo Total da diferença"
    ]

    faltantes = [c for c in colunas_necessarias if c not in df.columns]

    if faltantes:
        st.error(f"Colunas ausentes: {faltantes}")
        st.write(df.columns.tolist())
        st.stop()

    df = df[colunas_necessarias].copy()

    # =============================
    # Trata código filial
    # =============================

    df["CodigoFilial"] = pd.to_numeric(
        df["CodigoFilial"],
        errors="coerce"
    ).fillna(0).astype(int)

    df["Filiais"] = df["CodigoFilial"].map(MAPA_FILIAIS)

    # =============================
    # Trata numéricos
    # =============================

    colunas_numericas = [
        "Qtd Ap",
        "Qtd Teórico",
        "Diferença",
        "Custo Total da diferença"
    ]

    for col in colunas_numericas:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


# ====================================
# SALVAR HISTÓRICO
# ====================================

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
        "Quantidade de SKUs Zerados": (
            df_filtrado["Qtd Ap"] == 0
        ).sum(),
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


# ====================================
# SIDEBAR
# ====================================

st.sidebar.header("Filtros")

filial_selecionada = st.sidebar.selectbox(
    "Filial",
    LISTA_FILIAIS
)

data_inventario = st.sidebar.date_input(
    "Data do Inventário"
)

arquivo_excel = st.sidebar.file_uploader(
    "Upload Excel",
    type=["xlsx"]
)

# ====================================
# PROCESSAMENTO
# ====================================

if arquivo_excel is None:
    st.info("Faça upload do arquivo Excel.")
    st.stop()

df = carregar_aba_principal(arquivo_excel)

df_filtrado = df[
    df["Filiais"] == filial_selecionada
].copy()

if df_filtrado.empty:

    st.warning("Nenhum dado encontrado.")

    st.write("Códigos encontrados:")
    st.write(df["CodigoFilial"].unique())

    st.write("Filiais mapeadas:")
    st.write(df["Filiais"].unique())

    st.stop()

# ====================================
# CARDS
# ====================================

valor_faltas = df_filtrado.loc[
    df_filtrado["Custo Total da diferença"] < 0,
    "Custo Total da diferença"
].sum()

valor_sobras = df_filtrado.loc[
    df_filtrado["Custo Total da diferença"] > 0,
    "Custo Total da diferença"
].sum()

skus_zerados = (
    df_filtrado["Qtd Ap"] == 0
).sum()

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
    "SKUs Zerados",
    int(skus_zerados)
)

st.divider()

# ====================================
# GRÁFICO
# ====================================

st.subheader(
    "Custo Total da Diferença por Classificação"
)

df_grafico = (
    df_filtrado
    .groupby(
        "classification",
        as_index=False
    )["Custo Total da diferença"]
    .sum()
)

fig = px.bar(
    df_grafico,
    x="classification",
    y="Custo Total da diferença",
    text_auto=".2s"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

# ====================================
# TOP 10 PREJUÍZO
# ====================================

st.subheader(
    "Top 10 SKUs com Maior Prejuízo"
)

top_10 = (
    df_filtrado[
        df_filtrado["Custo Total da diferença"] < 0
    ]
    .sort_values(
        "Custo Total da diferença"
    )
    .head(10)
)

st.dataframe(
    top_10,
    use_container_width=True
)

# ====================================
# HISTÓRICO
# ====================================

st.divider()

if st.button("Salvar no Histórico"):

    salvar_historico(
        df_filtrado,
        filial_selecionada,
        data_inventario
    )

    st.success("Histórico salvo com sucesso.")

if os.path.exists(HISTORICO_CSV):

    st.subheader("Histórico Salvo")

    historico = pd.read_csv(HISTORICO_CSV)

    st.dataframe(
        historico,
        use_container_width=True
    )
