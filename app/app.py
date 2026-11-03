"""Brasil Politizado — interface Streamlit.

Uso:
    streamlit run app/app.py
"""

import pandas as pd
import streamlit as st

from dados import (BANCO, DEP_FEDERAL, GOVERNADOR, PRESIDENTE, SENADOR, consulta, eleitos,
                   presidente_por_uf, resultado_presidente)
from graficos import CONFIG_PLOTLY, barras_partido, mapa_partidos
from ui import ajuda, bloco_fontes, fmt_int, fmt_pct, hover_candidatos

st.set_page_config(page_title="Brasil Politizado", page_icon="🗳️", layout="wide")


# Colunas comuns às tabelas, com o texto que aparece ao passar o mouse no cabeçalho
COL_FONTE = {
    "fonte_arquivo": st.column_config.TextColumn("Arquivo de origem", help=ajuda("fonte")),
    "linha_fonte": st.column_config.NumberColumn("Linha", format="%d", help=ajuda("linha")),
}
COL_VOTOS = st.column_config.NumberColumn("Votos", format="localized", help=ajuda("votos_nominais"))
COL_SITUACAO = st.column_config.TextColumn("Situação", help=ajuda("situacao", "media", "calculado"))
COL_PARTIDO = st.column_config.TextColumn("Partido", help="Sigla do partido pelo qual o candidato concorreu.")


def aviso_sem_dados(o_que: str, ano: int) -> None:
    st.info(f"O banco não tem dados de {o_que} para {ano}. Baixe essa eleição com "
            f"`python scripts/baixar_dados.py --anos {ano}` e monte o banco de novo.", icon=":material/info:")


def nomes_partidos(df: pd.DataFrame) -> dict[str, str]:
    return dict(zip(df["sg_partido"], df["nm_partido"]))


# ---------------------------------------------------------------- seções

def secao_presidente(ano: int) -> None:
    res = resultado_presidente(ano)
    if res.empty:
        aviso_sem_dados("presidente", ano)
        return
    ultimo_turno = int(res["turno"].max())
    eleito = eleitos(ano, PRESIDENTE).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Presidente eleito", eleito["nome_urna"].title(), eleito["sg_partido"],
              delta_color="off", delta_arrow="off",
              help=f"{eleito['nome']} — {eleito['nm_partido']}")
    final = res[res["turno"] == ultimo_turno]
    c2.metric(f"Votos no {ultimo_turno}º turno", fmt_int(eleito["votos"]),
              fmt_pct(eleito["votos"] / final["votos"].sum()) + " dos votos nominais",
              delta_color="off", delta_arrow="off", help=ajuda("votos_nominais", "pct_nominais"))
    c3.metric("Turnos", int(ultimo_turno), help=ajuda("turno"))

    turno = st.segmented_control(
        "Turno", options=sorted(int(t) for t in res["turno"].unique()), default=ultimo_turno,
        format_func=lambda t: f"{t}º turno", key=f"turno_pres_{ano}", help=ajuda("turno"),
    ) or ultimo_turno

    col_mapa, col_tab = st.columns([3, 2], gap="large")
    with col_mapa:
        st.markdown(f"**Mais votado em cada estado — {turno}º turno**", help=ajuda("mais_votado_uf"))
        por_uf = presidente_por_uf(ano, turno)
        st.plotly_chart(mapa_partidos(por_uf, hover_candidatos(por_uf)), width="stretch", config=CONFIG_PLOTLY)
    with col_tab:
        st.markdown(f"**Resultado nacional — {turno}º turno**")
        t = res[res["turno"] == turno].copy()
        t["pct"] = t["votos"] / t["votos"].sum()
        st.dataframe(
            t[["nome_urna", "sg_partido", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
            hide_index=True, width="stretch",
            column_config={
                "nome_urna": st.column_config.TextColumn("Candidato", help="Nome usado na urna."),
                "sg_partido": COL_PARTIDO, "votos": COL_VOTOS,
                "pct": st.column_config.ProgressColumn("% nominais", format="percent", min_value=0, max_value=1,
                                                       help=ajuda("pct_nominais")),
                "situacao_turno": COL_SITUACAO, **COL_FONTE,
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
        aviso_sem_dados("governadores", ano)
        return

    col_mapa, col_resumo = st.columns([3, 2], gap="large")
    with col_mapa:
        st.markdown("**Partido do governador eleito em cada estado**",
                    help="Passe o mouse sobre um estado para ver o governador, os votos e a fonte.")
        st.plotly_chart(mapa_partidos(gov, hover_candidatos(gov)), width="stretch", config=CONFIG_PLOTLY)
    with col_resumo:
        st.markdown("**Governadores por partido**")
        st.plotly_chart(barras_partido(gov["sg_partido"].value_counts(), ("governador", "governadores"), nomes_partidos(gov)),
                        width="stretch", config=CONFIG_PLOTLY)
        segundo = int((gov["turno"] == 2).sum())
        st.caption(f"{len(gov) - segundo} estados decidiram no 1º turno e {segundo} no 2º turno.",
                   help=ajuda("turno"))

    st.markdown("**Detalhe por estado**")
    st.dataframe(
        gov[["sg_uf", "estado", "regiao", "nome_urna", "sg_partido", "coligacao", "turno", "votos", "pct",
             "fonte_arquivo", "linha_fonte"]],
        hide_index=True, width="stretch",
        column_config={
            "sg_uf": "UF", "estado": "Estado", "regiao": "Região",
            "nome_urna": st.column_config.TextColumn("Governador", help="Nome usado na urna."),
            "sg_partido": COL_PARTIDO,
            "coligacao": st.column_config.TextColumn("Coligação", help=ajuda("coligacao")),
            "turno": st.column_config.NumberColumn("Turno", help=ajuda("turno")),
            "votos": COL_VOTOS,
            "pct": st.column_config.NumberColumn("% nominais", format="percent", help=ajuda("pct_nominais")),
            **COL_FONTE,
        },
    )
    bloco_fontes(gov, colunas=(("fonte_arquivo", "fonte_url"), ("fonte_votos_arquivo", "fonte_votos_url")))


def secao_legislativo(ano: int, cargo: int, rotulo: tuple[str, str]) -> None:
    """`rotulo` é (singular, plural) do cargo, ex.: ("senador", "senadores")."""
    df = eleitos(ano, cargo)
    if df.empty:
        aviso_sem_dados(rotulo[1], ano)
        return
    nomes = nomes_partidos(df)
    sobre_casa = ajuda("senado" if cargo == SENADOR else "camara")

    regioes = ["Todas"] + sorted(df["regiao"].dropna().unique())
    f1, f2 = st.columns(2)
    regiao = f1.selectbox("Região", regioes, key=f"regiao_{cargo}_{ano}",
                          help="Filtra os eleitos pela região do estado.")
    if regiao != "Todas":
        df = df[df["regiao"] == regiao]
    ufs = ["Todos"] + sorted(df["estado"].unique())
    estado = f2.selectbox("Estado", ufs, key=f"uf_{cargo}_{ano}", help="Filtra os eleitos de um estado.")
    if estado != "Todos":
        df = df[df["estado"] == estado]

    m1, m2 = st.columns(2)
    m1.metric(f"{rotulo[1].capitalize()} eleitos", len(df), help=sobre_casa)
    m2.metric("Partidos representados", df["sg_partido"].nunique(), help=ajuda("partidos_representados"))

    col_graf, col_tab = st.columns([2, 3], gap="large")
    with col_graf:
        st.markdown("**Cadeiras por partido**", help="Passe o mouse sobre uma barra para ver o nome do partido.")
        st.plotly_chart(barras_partido(df["sg_partido"].value_counts(), rotulo, nomes),
                        width="stretch", config=CONFIG_PLOTLY)
    with col_tab:
        busca = st.text_input("Buscar por nome ou partido", key=f"busca_{cargo}_{ano}", placeholder="ex.: Tiririca, PSOL",
                              help="Procura no nome de urna, no nome completo ou na sigla do partido.")
        tabela = df
        if busca:
            alvo = busca.strip().upper()
            tabela = df[df["nome_urna"].str.contains(alvo, regex=False) | df["nome"].str.contains(alvo, regex=False)
                        | (df["sg_partido"].str.upper() == alvo)]
            st.caption(f"{len(tabela)} de {len(df)} eleitos correspondem à busca.")
        if tabela.empty:
            st.info(f"Nenhum eleito encontrado para “{busca.strip()}” neste recorte. Tente parte do nome, "
                    "a sigla do partido ou limpar os filtros de região e estado.", icon=":material/search_off:")
        else:
            st.dataframe(
                tabela.sort_values("votos", ascending=False)[
                    ["nome_urna", "sg_partido", "sg_uf", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
                hide_index=True, width="stretch", height=480,
                column_config={
                    "nome_urna": st.column_config.TextColumn("Nome na urna", help="Nome usado na urna."),
                    "sg_partido": COL_PARTIDO, "sg_uf": "UF", "votos": COL_VOTOS,
                    "pct": st.column_config.NumberColumn("% do estado", format="percent", help=ajuda("pct_nominais")),
                    "situacao_turno": COL_SITUACAO, **COL_FONTE,
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
            "arquivo": st.column_config.TextColumn("Arquivo", help=ajuda("fonte")),
            "baixado_em": "Baixado em",
            "sha256_zip": st.column_config.TextColumn(
                "SHA-256 do zip", help="Impressão digital do arquivo baixado. Se o TSE trocar o arquivo, ela muda."),
            "url": st.column_config.LinkColumn("Download (zip)", display_text="cdn.tse.jus.br ↗"),
        },
    )


# ---------------------------------------------------------------- página

def main() -> None:
    if not BANCO.exists():
        st.title("Brasil Politizado")
        st.info("O banco de dados ainda não foi gerado. São dois passos no terminal, na pasta do projeto: "
                "o primeiro baixa os arquivos do TSE e o segundo monta o banco (cerca de 2 minutos por eleição "
                "com votação).", icon=":material/database:")
        st.code("python scripts/baixar_dados.py\npython scripts/montar_banco.py", language="bash")
        st.caption("Depois, recarregue esta página.")
        st.stop()

    anos = consulta("SELECT DISTINCT ano FROM candidatura ORDER BY ano")["ano"].tolist()

    topo, seletor = st.columns([3, 2], vertical_alignment="bottom")
    with topo:
        st.title("Brasil Politizado")
        st.caption("A foto eleitoral do Brasil, ano a ano e estado a estado. Dados oficiais do TSE.")
    with seletor:
        ano = st.segmented_control("Ano da eleição", anos, default=anos[-1], key="ano",
                                   help="Eleições gerais: presidente, governadores, Senado e Câmara.") or anos[-1]

    # Navegação que executa só a seção escolhida (st.tabs renderiza todas de uma vez, o que deixa
    # a página lenta e faz mapas simultâneos do Plotly às vezes não desenharem)
    secoes = {
        "🏛️ Presidente": lambda: secao_presidente(ano),
        "🗺️ Governadores": lambda: secao_governadores(ano),
        "⚖️ Senado": lambda: secao_legislativo(ano, SENADOR, ("senador", "senadores")),
        "👥 Câmara dos Deputados": lambda: secao_legislativo(ano, DEP_FEDERAL, ("deputado federal", "deputados federais")),
        "ℹ️ Sobre os dados": secao_sobre,
    }
    escolha = st.segmented_control("Seção", list(secoes), default="🏛️ Presidente", key="secao",
                                   label_visibility="collapsed") or "🏛️ Presidente"
    st.divider()
    secoes[escolha]()


main()
