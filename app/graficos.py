"""Gráficos Plotly do app: mapa do Brasil por partido e barras de cadeiras por partido."""

import pandas as pd
import plotly.graph_objects as go

from dados import centroides, geojson_ufs

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


def cor_partido(sigla: str) -> str:
    return CORES_PARTIDO.get(sigla, COR_OUTROS)


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
