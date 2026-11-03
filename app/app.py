"""Brasil Politizado — interface Streamlit.

Uso:
    streamlit run app/app.py
"""

from pathlib import Path

import pandas as pd
import streamlit as st

from dados import (BANCO, DEP_FEDERAL, GOVERNADOR, PRESIDENTE, SENADOR, consulta, eleitos,
                   presidente_por_uf, resultado_presidente)
from graficos import CONFIG_PLOTLY, barras_partido, mapa_partidos, tema
from ui import (ajuda, bloco_fontes, eh_celular, fmt_int, fmt_pct, hover_candidatos, resumo_mais_votados,
                resumo_partidos)

st.set_page_config(page_title="Brasil Politizado", page_icon=":material/how_to_vote:", layout="wide")

ESTILO = Path(__file__).resolve().parent / "estilo.css"


def aplicar_estilo() -> None:
    """Carrega app/estilo.css (só aparência e animação), com as cores do tema ativo."""
    t = tema()
    variaveis = f":root {{ --bp-primaria: {t['primaria']}; --bp-sombra: {t['sombra']}; }}"
    st.html(f"<style>{variaveis}\n{ESTILO.read_text(encoding='utf-8')}</style>")


# Colunas comuns às tabelas, com o texto que aparece ao passar o mouse no cabeçalho
COL_FONTE = {
    "fonte_arquivo": st.column_config.TextColumn("Arquivo de origem", help=ajuda("fonte")),
    "linha_fonte": st.column_config.NumberColumn("Linha", format="%d", help=ajuda("linha")),
}
COL_VOTOS = st.column_config.NumberColumn("Votos", format="localized", help=ajuda("votos_nominais"))
COL_SITUACAO = st.column_config.TextColumn("Situação", help=ajuda("situacao", "media", "calculado"))
COL_PARTIDO = st.column_config.TextColumn("Partido", help="Sigla do partido pelo qual o candidato concorreu.")


def col_nome(titulo: str):
    return st.column_config.TextColumn(titulo, help="Nome usado na urna. O TSE registra em maiúsculas; "
                                       "aqui aparece em caixa normal para facilitar a leitura.")


def aviso_sem_dados(o_que: str, ano: int) -> None:
    st.info(f"O banco não tem dados de {o_que} para {ano}. Baixe essa eleição com "
            f"`python scripts/baixar_dados.py --anos {ano}` e monte o banco de novo.", icon=":material/info:")


def nomes_partidos(df: pd.DataFrame) -> dict[str, str]:
    return dict(zip(df["sg_partido"], df["partido_exibicao"]))


# ---------------------------------------------------------------- mapa clicável e raio-x do estado

def estados() -> dict[str, str]:
    ufs = consulta("SELECT sigla, nome FROM uf WHERE regiao IS NOT NULL ORDER BY nome")
    return dict(zip(ufs["sigla"], ufs["nome"]))


def ao_clicar_no_mapa(chave: str) -> None:
    """Callback do clique no mapa: escolhe o estado no seletor do Raio-X (e na URL)."""
    pontos = st.session_state[chave]["selection"]["points"]
    if not pontos:
        return
    uf = pontos[0].get("location") or pontos[0].get("customdata")
    if uf in estados():
        st.session_state["uf"] = uf
        st.toast(f"Raio-X de {estados()[uf]} logo abaixo do mapa", icon=":material/location_on:")


def mapa_clicavel(df: pd.DataFrame, chave: str) -> None:
    fig = mapa_partidos(df, hover_candidatos(df), altura=420 if eh_celular() else 560,
                        destaque=st.session_state.get("uf"))
    st.plotly_chart(fig, width="stretch", config=CONFIG_PLOTLY, key=chave,
                    on_select=lambda: ao_clicar_no_mapa(chave), selection_mode="points")


def cartao(chave: str, titulo: str, ajuda_titulo: str | None = None):
    # a key vira a classe st-key-cartao-<chave>, usada pelo estilo.css para o efeito de hover
    caixa = st.container(border=True, key=f"cartao-{chave}")
    caixa.caption(titulo, help=ajuda_titulo)
    return caixa


def raio_x_estado(ano: int) -> None:
    """Resumo de um estado: governador, senadores, bancada na Câmara e presidente mais votado."""
    nomes = estados()
    st.markdown("#### Raio-X do estado")
    # index só na primeira vez: depois o valor vem do session_state (clique no mapa ou URL)
    inicial = {} if "uf" in st.session_state else {"index": None}
    uf = st.selectbox(
        "Estado", list(nomes), format_func=lambda s: f"{nomes[s]} ({s})", **inicial,
        placeholder="Clique em um estado no mapa ou escolha aqui", key="uf",
        persist_state="session", label_visibility="collapsed",
        help="Mostra quem foi eleito neste estado em todos os cargos.",
    )
    if uf:
        st.query_params["uf"] = uf
    else:
        st.query_params.pop("uf", None)
    if uf is None:
        st.caption("Dica: clique em qualquer estado do mapa para ver o resumo dele aqui.")
        return

    gov = eleitos(ano, GOVERNADOR).query("sg_uf == @uf")
    sen = eleitos(ano, SENADOR).query("sg_uf == @uf")
    dep = eleitos(ano, DEP_FEDERAL).query("sg_uf == @uf")
    res = resultado_presidente(ano)
    turno = int(res["turno"].max()) if not res.empty else None
    pres = presidente_por_uf(ano, turno).query("sg_uf == @uf") if turno else pd.DataFrame()

    c1, c2, c3, c4 = st.columns(4)
    with c1, cartao("governador", "Governador eleito"):
        for _, g in gov.iterrows():
            st.markdown(f"**{g['nome_exibicao']}** · {g['sg_partido']}")
            st.caption(f"{fmt_pct(g['pct'])} dos votos nominais · {int(g['turno'])}º turno")
    with c2, cartao("senado", f"Senado · {len(sen)} vaga{'s' if len(sen) != 1 else ''} nesta eleição", ajuda("senado")):
        for _, s in sen.sort_values("votos", ascending=False).iterrows():
            st.markdown(f"**{s['nome_exibicao']}** · {s['sg_partido']}")
    with c3, cartao("camara", f"Câmara · {len(dep)} deputados federais", ajuda("camara")):
        bancadas = dep["sg_partido"].value_counts()
        st.markdown(" · ".join(f"**{p}** {n}" for p, n in bancadas.head(6).items()))
        if len(bancadas) > 6:
            st.caption(f"e mais {len(bancadas) - 6} partidos")
    with c4, cartao("presidente", f"Presidente · mais votado aqui no {turno}º turno", ajuda("mais_votado_uf")):
        for _, p in pres.iterrows():
            st.markdown(f"**{p['nome_exibicao']}** · {p['sg_partido']}")
            st.caption(f"{fmt_pct(p['pct'])} dos votos nominais no estado")
    bloco_fontes(pd.concat([gov, sen, dep, pres]),
                 colunas=(("fonte_arquivo", "fonte_url"), ("fonte_votos_arquivo", "fonte_votos_url")))


# ---------------------------------------------------------------- seções

def secao_presidente(ano: int) -> None:
    res = resultado_presidente(ano)
    if res.empty:
        aviso_sem_dados("presidente", ano)
        return
    ultimo_turno = int(res["turno"].max())
    eleito = eleitos(ano, PRESIDENTE).iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Presidente eleito", eleito["nome_exibicao"], eleito["sg_partido"],
              delta_color="off", delta_arrow="off",
              help=f"{eleito['nome']} — {eleito['partido_exibicao']}")
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
        mapa_clicavel(por_uf, f"mapa_presidente_{ano}_{turno}")
        st.caption(resumo_mais_votados(por_uf, turno))
    with col_tab:
        st.markdown(f"**Resultado nacional — {turno}º turno**")
        t = res[res["turno"] == turno].copy()
        t["pct"] = t["votos"] / t["votos"].sum()
        st.dataframe(
            t[["nome_exibicao", "sg_partido", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
            hide_index=True, width="stretch",
            column_config={
                "nome_exibicao": col_nome("Candidato"),
                "sg_partido": COL_PARTIDO, "votos": COL_VOTOS,
                "pct": st.column_config.ProgressColumn("% nominais", format="percent", min_value=0, max_value=1,
                                                       help=ajuda("pct_nominais")),
                "situacao_turno": COL_SITUACAO, **COL_FONTE,
            },
        )
    raio_x_estado(ano)
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
        mapa_clicavel(gov, f"mapa_governadores_{ano}")
        st.caption(resumo_partidos(gov["sg_partido"].value_counts(), ("governador", "governadores"), ano))
    with col_resumo:
        st.markdown("**Governadores por partido**")
        st.plotly_chart(barras_partido(gov["sg_partido"].value_counts(), ("governador", "governadores"), nomes_partidos(gov)),
                        width="stretch", config=CONFIG_PLOTLY)
        segundo = int((gov["turno"] == 2).sum())
        st.caption(f"{len(gov) - segundo} estados decidiram no 1º turno e {segundo} no 2º turno.",
                   help=ajuda("turno"))

    raio_x_estado(ano)

    st.markdown("**Todos os governadores eleitos**")
    st.dataframe(
        gov[["sg_uf", "estado", "regiao", "nome_exibicao", "sg_partido", "coligacao", "turno", "votos", "pct",
             "fonte_arquivo", "linha_fonte"]],
        hide_index=True, width="stretch",
        column_config={
            "sg_uf": "UF", "estado": "Estado", "regiao": "Região",
            "nome_exibicao": col_nome("Governador"),
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
        recorte = f" ({estado})" if estado != "Todos" else (f" (região {regiao})" if regiao != "Todas" else "")
        st.caption(resumo_partidos(df["sg_partido"].value_counts(), rotulo, ano, recorte))
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
                    ["nome_exibicao", "sg_partido", "sg_uf", "votos", "pct", "situacao_turno", "fonte_arquivo", "linha_fonte"]],
                hide_index=True, width="stretch", height=480,
                column_config={
                    "nome_exibicao": col_nome("Nome na urna"),
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
    aplicar_estilo()
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
        # Ano, seção e estado ficam na URL (?ano=2018&secao=governadores&uf=BA), para dar para
        # compartilhar o link de uma tela específica. O ano usa o bind nativo; seção e estado são
        # sincronizados à mão porque o bind grava o rótulo formatado, e não o valor curto.
        ano = st.segmented_control("Ano da eleição", anos, default=anos[-1], key="ano", required=True,
                                   bind="query-params",
                                   help="Eleições gerais: presidente, governadores, Senado e Câmara.")

    # Navegação que executa só a seção escolhida (st.tabs renderiza todas de uma vez, o que deixa
    # a página lenta e faz mapas simultâneos do Plotly às vezes não desenharem)
    secoes = {
        "presidente": (":material/account_balance: Presidente", lambda: secao_presidente(ano)),
        "governadores": (":material/map: Governadores", lambda: secao_governadores(ano)),
        "senado": (":material/event_seat: Senado",
                   lambda: secao_legislativo(ano, SENADOR, ("senador", "senadores"))),
        "camara": (":material/groups: Câmara dos Deputados",
                   lambda: secao_legislativo(ano, DEP_FEDERAL, ("deputado federal", "deputados federais"))),
        "sobre": (":material/info: Sobre os dados", secao_sobre),
    }
    if "secao" not in st.session_state:
        da_url = st.query_params.get("secao")
        st.session_state["secao"] = da_url if da_url in secoes else "presidente"
    if "uf" not in st.session_state and (st.query_params.get("uf") or "").upper() in estados():
        st.session_state["uf"] = st.query_params["uf"].upper()

    escolha = st.segmented_control("Seção", list(secoes), format_func=lambda s: secoes[s][0], key="secao",
                                   required=True, label_visibility="collapsed")
    st.query_params["secao"] = escolha
    if escolha not in ("presidente", "governadores"):
        st.query_params.pop("uf", None)
    st.divider()
    secoes[escolha][1]()


main()
