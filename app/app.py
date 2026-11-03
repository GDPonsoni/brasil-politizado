"""Brasil Politizado — interface Streamlit.

Uso:
    streamlit run app/app.py
"""

import pandas as pd
import streamlit as st

from dados import (BANCO, DEP_FEDERAL, GOVERNADOR, PRESIDENTE, SENADOR, consulta, eleitos,
                   presidente_por_uf, resultado_presidente)
from graficos import CONFIG_PLOTLY, barras_partido, mapa_partidos
from ui import bloco_fontes, fmt_int, fmt_pct

st.set_page_config(page_title="Brasil Politizado", page_icon="🗳️", layout="wide")


# ---------------------------------------------------------------- seções

def secao_presidente(ano: int) -> None:
    res = resultado_presidente(ano)
    if res.empty:
        st.info("Sem dados de presidente para este ano.")
        return
    ultimo_turno = int(res["turno"].max())
    eleito = eleitos(ano, PRESIDENTE).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Presidente eleito", eleito["nome_urna"].title(), eleito["sg_partido"], delta_color="off", delta_arrow="off")
    final = res[res["turno"] == ultimo_turno]
    c2.metric(f"Votos no {ultimo_turno}º turno", fmt_int(eleito["votos"]),
              fmt_pct(eleito["votos"] / final["votos"].sum()) + " dos votos nominais", delta_color="off", delta_arrow="off")
    c3.metric("Turnos", int(ultimo_turno))

    turno = st.segmented_control(
        "Turno", options=sorted(int(t) for t in res["turno"].unique()), default=ultimo_turno,
        format_func=lambda t: f"{t}º turno", key=f"turno_pres_{ano}",
    ) or ultimo_turno

    col_mapa, col_tab = st.columns([3, 2], gap="large")
    with col_mapa:
        st.markdown(f"**Mais votado em cada estado — {turno}º turno**")
        por_uf = presidente_por_uf(ano, turno)
        hover = (
            "<b>" + por_uf["estado"] + "</b><br>" + por_uf["nome_urna"] + " (" + por_uf["sg_partido"] + ")<br>"
            + por_uf["votos"].map(fmt_int) + " votos · " + por_uf["pct"].map(fmt_pct)
        ).tolist()
        st.plotly_chart(mapa_partidos(por_uf, hover), width="stretch", config=CONFIG_PLOTLY)
    with col_tab:
        st.markdown(f"**Resultado nacional — {turno}º turno**")
        t = res[res["turno"] == turno].copy()
        t["pct"] = t["votos"] / t["votos"].sum()
        st.dataframe(
            t[["nome_urna", "sg_partido", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
            hide_index=True, width="stretch",
            column_config={
                "nome_urna": "Candidato", "sg_partido": "Partido",
                "votos": st.column_config.NumberColumn("Votos", format="localized"),
                "pct": st.column_config.ProgressColumn("% nominais", format="percent", min_value=0, max_value=1),
                "situacao_turno": "Situação", "fonte_arquivo": "Arquivo de origem", "linha_fonte": "Linha",
            },
        )
    bloco_fontes(
        pd.concat([res, por_uf]),
        nota="Candidatos: consulta_cand. Votos: votacao_candidato_munzona, somados de município/zona para estado. "
             "Votos no exterior (ZZ) e em trânsito (VT) entram no total nacional, mas não no mapa.",
    )


def secao_governadores(ano: int) -> None:
    gov = eleitos(ano, GOVERNADOR)
    if gov.empty:
        st.info("Sem dados de governadores para este ano.")
        return

    col_mapa, col_resumo = st.columns([3, 2], gap="large")
    with col_mapa:
        st.markdown("**Partido do governador eleito em cada estado**")
        hover = (
            "<b>" + gov["estado"] + "</b><br>" + gov["nome_urna"] + " (" + gov["sg_partido"] + ")<br>"
            + "Eleito no " + gov["turno"].astype(str) + "º turno · " + gov["votos"].map(fmt_int) + " votos ("
            + gov["pct"].map(fmt_pct) + ")<br><span style='font-size:11px'>Fonte: " + gov["fonte_arquivo"]
            + ", linha " + gov["linha_fonte"].astype(str) + "</span>"
        ).tolist()
        st.plotly_chart(mapa_partidos(gov, hover), width="stretch", config=CONFIG_PLOTLY)
    with col_resumo:
        st.markdown("**Governadores por partido**")
        st.plotly_chart(barras_partido(gov["sg_partido"].value_counts(), "governadores"),
                        width="stretch", config=CONFIG_PLOTLY)
        segundo = int((gov["turno"] == 2).sum())
        st.caption(f"{len(gov) - segundo} estados decidiram no 1º turno e {segundo} no 2º turno.")

    st.markdown("**Detalhe por estado**")
    st.dataframe(
        gov[["sg_uf", "estado", "regiao", "nome_urna", "sg_partido", "coligacao", "turno", "votos", "pct",
             "fonte_arquivo", "linha_fonte"]],
        hide_index=True, width="stretch",
        column_config={
            "sg_uf": "UF", "estado": "Estado", "regiao": "Região", "nome_urna": "Governador",
            "sg_partido": "Partido", "coligacao": "Coligação", "turno": "Turno",
            "votos": st.column_config.NumberColumn("Votos", format="localized"),
            "pct": st.column_config.NumberColumn("% nominais", format="percent"),
            "fonte_arquivo": "Arquivo de origem", "linha_fonte": "Linha",
        },
    )
    bloco_fontes(gov, colunas=(("fonte_arquivo", "fonte_url"), ("fonte_votos_arquivo", "fonte_votos_url")))


def secao_legislativo(ano: int, cargo: int, rotulo: str) -> None:
    df = eleitos(ano, cargo)
    if df.empty:
        st.info(f"Sem dados de {rotulo} para este ano.")
        return

    regioes = ["Todas"] + sorted(df["regiao"].dropna().unique())
    f1, f2 = st.columns(2)
    regiao = f1.selectbox("Região", regioes, key=f"regiao_{cargo}_{ano}")
    if regiao != "Todas":
        df = df[df["regiao"] == regiao]
    ufs = ["Todos"] + sorted(df["estado"].unique())
    estado = f2.selectbox("Estado", ufs, key=f"uf_{cargo}_{ano}")
    if estado != "Todos":
        df = df[df["estado"] == estado]

    m1, m2 = st.columns(2)
    m1.metric(f"{rotulo.capitalize()} eleitos", len(df))
    m2.metric("Partidos representados", df["sg_partido"].nunique())

    col_graf, col_tab = st.columns([2, 3], gap="large")
    with col_graf:
        st.markdown("**Cadeiras por partido**")
        st.plotly_chart(barras_partido(df["sg_partido"].value_counts(), rotulo), width="stretch", config=CONFIG_PLOTLY)
    with col_tab:
        busca = st.text_input("Buscar por nome ou partido", key=f"busca_{cargo}_{ano}", placeholder="ex.: Tiririca, PSOL")
        tabela = df
        if busca:
            alvo = busca.upper()
            tabela = df[df["nome_urna"].str.contains(alvo, regex=False) | df["nome"].str.contains(alvo, regex=False)
                        | (df["sg_partido"].str.upper() == alvo)]
        st.dataframe(
            tabela.sort_values("votos", ascending=False)[
                ["nome_urna", "sg_partido", "sg_uf", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
            hide_index=True, width="stretch", height=480,
            column_config={
                "nome_urna": "Nome na urna", "sg_partido": "Partido", "sg_uf": "UF",
                "votos": st.column_config.NumberColumn("Votos", format="localized"),
                "pct": st.column_config.NumberColumn("% do estado", format="percent",
                                                     help="Votos nominais do candidato sobre o total de votos nominais do cargo no estado"),
                "situacao_turno": st.column_config.TextColumn("Situação", help="MÉDIA = eleito pelas sobras (média)"),
                "fonte_arquivo": "Arquivo de origem", "linha_fonte": "Linha",
            },
        )
    bloco_fontes(df, colunas=(("fonte_arquivo", "fonte_url"), ("fonte_votos_arquivo", "fonte_votos_url")))


def secao_sobre() -> None:
    st.markdown(
        """
        **De onde vêm os dados.** Tudo o que aparece aqui vem do
        [Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/). Cada tabela mostra o
        arquivo CSV e a linha de onde o registro saiu, e cada seção tem um bloco *Fonte dos dados*
        com o link do arquivo original. O contorno dos estados no mapa vem da
        [API de malhas do IBGE](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3).

        **Como os números foram calculados.** Os votos são os *votos nominais* (no candidato),
        somados a partir dos arquivos por município e zona eleitoral. Percentuais são sobre o total
        de votos nominais do cargo naquele estado e turno.

        **Situação dos candidatos.** É a situação final publicada pelo TSE, já com decisões
        posteriores à eleição (por exemplo, cassações). Por isso alguns totais podem diferir da
        apuração da noite da eleição. Eleições suplementares não entram.

        **Quando o TSE não informa quem foi eleito.** Em 2006 o arquivo de candidatos não traz o
        2º turno de presidente. Nesses casos o eleito é o mais votado no arquivo de votação, e a
        situação aparece como *calculado pela votação*, com o arquivo de votação como fonte.
        """
    )
    st.markdown("**Arquivos carregados no banco**")
    st.dataframe(
        consulta("SELECT ano, conjunto, arquivo, baixado_em, sha256_zip, url FROM fonte ORDER BY ano, conjunto, arquivo"),
        hide_index=True, width="stretch",
        column_config={
            "ano": st.column_config.NumberColumn("Ano", format="%d"), "conjunto": "Conjunto",
            "arquivo": "Arquivo", "baixado_em": "Baixado em", "sha256_zip": "SHA-256 do zip",
            "url": st.column_config.LinkColumn("Download (zip)", display_text="cdn.tse.jus.br ↗"),
        },
    )


# ---------------------------------------------------------------- página

def main() -> None:
    if not BANCO.exists():
        st.title("Brasil Politizado")
        st.warning("O banco ainda não foi gerado. Rode no terminal:")
        st.code("python scripts/baixar_dados.py\npython scripts/montar_banco.py", language="bash")
        st.stop()

    anos = consulta("SELECT DISTINCT ano FROM candidatura ORDER BY ano")["ano"].tolist()

    topo, seletor = st.columns([3, 2], vertical_alignment="bottom")
    with topo:
        st.title("Brasil Politizado")
        st.caption("A foto eleitoral do Brasil, ano a ano e estado a estado. Dados oficiais do TSE.")
    with seletor:
        ano = st.segmented_control("Ano da eleição", anos, default=anos[-1], key="ano") or anos[-1]

    # Navegação que executa só a seção escolhida (st.tabs renderiza todas de uma vez, o que deixa
    # a página lenta e faz mapas simultâneos do Plotly às vezes não desenharem)
    secoes = {
        "🏛️ Presidente": lambda: secao_presidente(ano),
        "🗺️ Governadores": lambda: secao_governadores(ano),
        "⚖️ Senado": lambda: secao_legislativo(ano, SENADOR, "senadores"),
        "👥 Câmara dos Deputados": lambda: secao_legislativo(ano, DEP_FEDERAL, "deputados federais"),
        "ℹ️ Sobre os dados": secao_sobre,
    }
    escolha = st.segmented_control("Seção", list(secoes), default="🏛️ Presidente", key="secao",
                                   label_visibility="collapsed") or "🏛️ Presidente"
    st.divider()
    secoes[escolha]()


main()
