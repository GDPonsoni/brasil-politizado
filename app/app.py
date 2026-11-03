"""Brasil Politizado — interface Streamlit.

Uso:
    streamlit run app/app.py
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "brasil.db"
GEOJSON = Path(__file__).resolve().parent / "assets" / "ufs.geojson"

PRESIDENTE, GOVERNADOR, SENADOR, DEP_FEDERAL = 1, 3, 5, 6

# Cores fixas por partido (a cor acompanha o partido em qualquer ano). No mapa só cabem
# 4 cores distinguíveis entre si, inclusive para daltônicos; os demais partidos ficam em
# cinza e todo estado leva a sigla do partido escrita, para nunca depender só da cor.
CORES_PARTIDO = {"PT": "#e34948", "PSDB": "#2a78d6", "PMDB": "#008300", "MDB": "#008300", "PSB": "#eda100"}
COR_OUTROS = "#c9c7bf"

# Estados pequenos demais para caber o rótulo: posição (lon, lat) do rótulo, no mar
ROTULOS_FORA = {
    "RN": (-33.5, -4.6), "PB": (-33.5, -6.6), "PE": (-33.5, -8.6), "AL": (-33.5, -10.6),
    "SE": (-33.5, -12.6), "ES": (-37.5, -20.6), "RJ": (-40.5, -24.6), "DF": (-46.0, -14.0),
}
COR_BARRA = "#0F766E"
COR_TEXTO = "#1F2933"
COR_TEXTO_SECUNDARIO = "#52514e"

st.set_page_config(page_title="Brasil Politizado", page_icon="🗳️", layout="wide")


# ---------------------------------------------------------------- dados

@st.cache_resource
def conexao() -> sqlite3.Connection:
    return sqlite3.connect(f"file:{BANCO}?mode=ro", uri=True, check_same_thread=False)


@st.cache_data
def consulta(sql: str, params: tuple = ()) -> pd.DataFrame:
    # escalares numpy (ex.: int64 vindo de um DataFrame) iriam para o SQLite como BLOB e não casariam
    params = tuple(p.item() if hasattr(p, "item") else p for p in params)
    return pd.read_sql_query(sql, conexao(), params=params)


@st.cache_data
def geojson_ufs() -> dict:
    return json.loads(GEOJSON.read_text(encoding="utf-8"))


@st.cache_data
def centroides() -> pd.DataFrame:
    """Centro aproximado do maior polígono de cada UF, para posicionar os rótulos."""
    linhas = []
    for f in geojson_ufs()["features"]:
        geom = f["geometry"]
        poligonos = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        anel = max((p[0] for p in poligonos), key=len)
        a = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(anel, anel[1:]):
            cruz = x0 * y1 - x1 * y0
            a += cruz
            cx += (x0 + x1) * cruz
            cy += (y0 + y1) * cruz
        linhas.append({"sg_uf": f["id"], "lon": cx / (3 * a), "lat": cy / (3 * a)})
    return pd.DataFrame(linhas)


SQL_ELEITOS = """
SELECT c.sg_uf, u.nome AS estado, u.regiao, c.turno, c.nome_urna, c.nome, c.nr_candidato,
       c.sg_partido, c.nm_partido, c.coligacao, c.composicao_coligacao, c.situacao_turno,
       v.votos, tot.total,
       f.arquivo AS fonte_arquivo, c.linha_fonte, f.url AS fonte_url,
       fv.arquivo AS fonte_votos_arquivo, fv.url AS fonte_votos_url
FROM candidatura c
JOIN uf u ON u.sigla = c.sg_uf
JOIN fonte f ON f.id = c.fonte_id
LEFT JOIN (
    SELECT ano, turno, cd_cargo, sq_candidato, SUM(votos) AS votos, MIN(fonte_id) AS fonte_id
    FROM votacao_uf GROUP BY ano, turno, cd_cargo, sq_candidato
) v ON v.ano = c.ano AND v.turno = c.turno AND v.cd_cargo = c.cd_cargo AND v.sq_candidato = c.sq_candidato
LEFT JOIN (
    SELECT vu.ano, vu.turno, vu.cd_cargo, cc.sg_uf, SUM(vu.votos) AS total
    FROM votacao_uf vu
    JOIN candidatura cc ON cc.sq_candidato = vu.sq_candidato AND cc.turno = vu.turno
    GROUP BY vu.ano, vu.turno, vu.cd_cargo, cc.sg_uf
) tot ON tot.ano = c.ano AND tot.turno = c.turno AND tot.cd_cargo = c.cd_cargo AND tot.sg_uf = c.sg_uf
LEFT JOIN fonte fv ON fv.id = v.fonte_id
WHERE c.ano = ? AND c.cd_cargo = ? AND c.eleito = 1
ORDER BY c.sg_uf, c.nome_urna
"""


def eleitos(ano: int, cargo: int) -> pd.DataFrame:
    df = consulta(SQL_ELEITOS, (ano, cargo))
    df["pct"] = df["votos"] / df["total"]
    return df


def resultado_presidente(ano: int) -> pd.DataFrame:
    return consulta(
        """
        SELECT c.turno, c.nome_urna, c.sg_partido, c.situacao_turno, SUM(v.votos) AS votos,
               f.arquivo AS fonte_arquivo, c.linha_fonte, f.url AS fonte_url
        FROM candidatura c
        JOIN fonte f ON f.id = c.fonte_id
        JOIN votacao_uf v ON v.sq_candidato = c.sq_candidato AND v.turno = c.turno AND v.cd_cargo = c.cd_cargo
        WHERE c.ano = ? AND c.cd_cargo = 1
        GROUP BY c.turno, c.sq_candidato
        ORDER BY c.turno, votos DESC
        """,
        (ano,),
    )


def presidente_por_uf(ano: int, turno: int) -> pd.DataFrame:
    """Candidato mais votado em cada UF no turno escolhido."""
    df = consulta(
        """
        SELECT v.sg_uf, u.nome AS estado, c.nome_urna, c.sg_partido, v.votos,
               SUM(v.votos) OVER (PARTITION BY v.sg_uf) AS total,
               f.arquivo AS fonte_arquivo, f.url AS fonte_url
        FROM votacao_uf v
        JOIN uf u ON u.sigla = v.sg_uf
        JOIN fonte f ON f.id = v.fonte_id
        JOIN candidatura c ON c.sq_candidato = v.sq_candidato AND c.turno = v.turno AND c.cd_cargo = v.cd_cargo
        WHERE v.ano = ? AND v.turno = ? AND v.cd_cargo = 1 AND u.regiao IS NOT NULL
        """,
        (ano, turno),
    )
    df["pct"] = df["votos"] / df["total"]
    return df.sort_values("votos", ascending=False).drop_duplicates("sg_uf").sort_values("sg_uf")


# ---------------------------------------------------------------- formatação

def fmt_int(n) -> str:
    return "—" if pd.isna(n) else f"{int(n):,}".replace(",", ".")


def fmt_pct(p) -> str:
    return "—" if pd.isna(p) else f"{p * 100:.1f}%".replace(".", ",")


def cor_partido(sigla: str) -> str:
    return CORES_PARTIDO.get(sigla, COR_OUTROS)


def bloco_fontes(df: pd.DataFrame, colunas=(("fonte_arquivo", "fonte_url"),), nota: str = "") -> None:
    """Expander com os arquivos do TSE de onde vieram os dados exibidos logo acima."""
    pares = pd.concat(
        [df[[a, u]].set_axis(["Arquivo", "URL"], axis=1) for a, u in colunas if a in df]
    ).dropna().drop_duplicates()
    with st.expander(f"📄 Fonte dos dados ({len(pares)} arquivo{'s' if len(pares) != 1 else ''} do TSE)"):
        if nota:
            st.caption(nota)
        st.dataframe(
            pares.sort_values("Arquivo"),
            hide_index=True,
            width="stretch",
            column_config={"URL": st.column_config.LinkColumn("Download (zip)", display_text="cdn.tse.jus.br ↗")},
        )


# ---------------------------------------------------------------- gráficos

def mapa_partidos(df: pd.DataFrame, hover: list[str]) -> go.Figure:
    """Mapa do Brasil colorido pelo partido, com a sigla do partido escrita em cada UF."""
    df = df.merge(centroides(), on="sg_uf")
    df["cor"] = df["sg_partido"].map(cor_partido)
    df["hover"] = hover

    fig = go.Figure()
    # um traço por cor, para a legenda listar os partidos coloridos + "outros", sempre na mesma ordem
    ordem_cores = list(dict.fromkeys([*CORES_PARTIDO.values(), COR_OUTROS]))
    for cor in ordem_cores:
        grupo = df[df["cor"] == cor]
        if grupo.empty:
            continue
        destacados = sorted(set(grupo["sg_partido"]) & set(CORES_PARTIDO))
        nome = " / ".join(destacados) if cor != COR_OUTROS else "Outros partidos"
        fig.add_trace(go.Choropleth(
            geojson=geojson_ufs(), locations=grupo["sg_uf"], z=[1] * len(grupo),
            colorscale=[[0, cor], [1, cor]], showscale=False,
            marker_line_color="#FAFAF7", marker_line_width=1.5,
            name=nome, showlegend=True,
            customdata=grupo["hover"], hovertemplate="%{customdata}<extra></extra>",
        ))
    # estados grandes: rótulo no centro; pequenos: rótulo no mar, ligado por uma linha-guia
    no_lugar = df[~df["sg_uf"].isin(ROTULOS_FORA)]
    fig.add_trace(go.Scattergeo(
        lon=no_lugar["lon"], lat=no_lugar["lat"], mode="text", showlegend=False, hoverinfo="skip",
        text=no_lugar["sg_uf"] + "<br><b>" + no_lugar["sg_partido"] + "</b>",
        textfont=dict(size=10, color=COR_TEXTO),
    ))
    fora = df[df["sg_uf"].isin(ROTULOS_FORA)]
    for _, uf in fora.iterrows():
        lon, lat = ROTULOS_FORA[uf["sg_uf"]]
        fig.add_trace(go.Scattergeo(
            lon=[uf["lon"], lon], lat=[uf["lat"], lat], mode="lines", showlegend=False, hoverinfo="skip",
            line=dict(width=1, color=COR_TEXTO_SECUNDARIO),
        ))
    fig.add_trace(go.Scattergeo(
        lon=[ROTULOS_FORA[u][0] for u in fora["sg_uf"]], lat=[ROTULOS_FORA[u][1] for u in fora["sg_uf"]],
        mode="text", textposition="middle right", showlegend=False, hoverinfo="skip",
        text=" " + fora["sg_uf"] + " <b>" + fora["sg_partido"] + "</b>",
        textfont=dict(size=10, color=COR_TEXTO),
    ))
    # área fixa (e não fitbounds) para os rótulos no mar não serem cortados
    fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                    lonaxis_range=[-74.5, -26], lataxis_range=[-34, 5.5])
    fig.update_layout(
        height=560, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(color=COR_TEXTO_SECUNDARIO)),
        hoverlabel=dict(bgcolor="white", font_color=COR_TEXTO, bordercolor="#d6d4cc"),
        dragmode=False,
    )
    return fig


def barras_partido(contagem: pd.Series, rotulo: str) -> go.Figure:
    """Barras horizontais de cadeiras por partido (uma série só: uma cor só)."""
    contagem = contagem.sort_values()
    fig = go.Figure(go.Bar(
        x=contagem.values, y=contagem.index, orientation="h",
        marker=dict(color=COR_BARRA, cornerradius=4), width=0.7,
        text=contagem.values, textposition="outside", cliponaxis=False,
        textfont=dict(color=COR_TEXTO_SECUNDARIO, size=11),
        hovertemplate="<b>%{y}</b><br>%{x} " + rotulo + "<extra></extra>",
    ))
    fig.update_layout(
        height=max(260, 22 * len(contagem) + 40), margin=dict(l=0, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(tickfont=dict(color=COR_TEXTO, size=12)),
        bargap=0.25, dragmode=False,
    )
    return fig


CONFIG_PLOTLY = {"displayModeBar": False, "scrollZoom": False}


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
