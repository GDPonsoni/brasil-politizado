"""Gráficos Plotly do app: mapa do Brasil por partido e barras de cadeiras por partido."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dados import centroides, geojson_ufs

# Cores por tema. A cor acompanha o partido em qualquer ano. No mapa só cabem 4 cores
# distinguíveis entre si (validadas para daltonismo, todos os pares, em cada tema); os demais
# partidos ficam em cinza e todo estado leva a sigla do partido escrita, para nunca depender só
# da cor. O tema escuro tem tons próprios, não é uma inversão do claro: o vermelho do PT é mais
# fechado para não se confundir com o amarelo do PSB sobre fundo escuro.
TEMAS = {
    "light": {
        "partidos": {"PT": "#e34948", "PSDB": "#2a78d6", "PMDB": "#008300", "MDB": "#008300", "PSB": "#eda100"},
        "outros": "#c9c7bf", "barra": "#0F766E", "fundo": "#FAFAF7",
        "texto": "#1F2933", "texto_secundario": "#52514e",
        "hover_fundo": "#ffffff", "hover_borda": "#d6d4cc",
    },
    "dark": {
        "partidos": {"PT": "#cf3f4f", "PSDB": "#3987e5", "PMDB": "#008300", "MDB": "#008300", "PSB": "#c98500"},
        "outros": "#5c5a55", "barra": "#2BB3A3", "fundo": "#1a1a19",
        "texto": "#ECEDEA", "texto_secundario": "#c3c2b7",
        "hover_fundo": "#262624", "hover_borda": "#3a3a37",
    },
}

# Estados pequenos demais para caber o rótulo: posição (lon, lat) do rótulo, no mar
ROTULOS_FORA = {
    "RN": (-33.5, -4.6), "PB": (-33.5, -6.6), "PE": (-33.5, -8.6), "AL": (-33.5, -10.6),
    "SE": (-33.5, -12.6), "ES": (-37.5, -20.6), "RJ": (-40.5, -24.6), "DF": (-46.0, -14.0),
}

CONFIG_PLOTLY = {"displayModeBar": False, "scrollZoom": False}


def tema() -> dict:
    """Paleta do tema ativo no navegador (claro ou escuro)."""
    return TEMAS.get(st.context.theme.type or "light", TEMAS["light"])


def _luminancia(cor: str) -> float:
    canais = [int(cor[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    """Razão de contraste WCAG entre duas cores (1 a 21)."""
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def texto_sobre(fundo: str) -> str:
    """Preto ou branco, o que tiver mais contraste com o preenchimento do estado. Com as cores
    de partido dos dois temas, o pior caso fica em 4,69:1 (acima do mínimo AA de 4,5:1)."""
    return "#000000" if contraste("#000000", fundo) >= contraste("#ffffff", fundo) else "#ffffff"


def _hoverlabel(t: dict) -> dict:
    return dict(bgcolor=t["hover_fundo"], font_color=t["texto"], bordercolor=t["hover_borda"], align="left")


def mapa_partidos(df: pd.DataFrame, hover: list[str], altura: int = 560, destaque: str | None = None) -> go.Figure:
    """Mapa do Brasil colorido pelo partido, com a sigla do partido escrita em cada UF.

    `destaque` é a sigla de uma UF a contornar (o estado escolhido no Raio-X)."""
    t = tema()
    df = df.merge(centroides(), on="sg_uf")
    df["cor"] = df["sg_partido"].map(lambda p: t["partidos"].get(p, t["outros"]))
    df["hover"] = hover

    fig = go.Figure()
    # um traço por cor, para a legenda listar os partidos coloridos + "outros", sempre na mesma ordem
    ordem_cores = list(dict.fromkeys([*t["partidos"].values(), t["outros"]]))
    for cor in ordem_cores:
        grupo = df[df["cor"] == cor]
        if grupo.empty:
            continue
        destacados = sorted(set(grupo["sg_partido"]) & set(t["partidos"]))
        nome = " / ".join(destacados) if cor != t["outros"] else "Outros partidos"
        fig.add_trace(go.Choropleth(
            geojson=geojson_ufs(), locations=grupo["sg_uf"], z=[1] * len(grupo),
            colorscale=[[0, cor], [1, cor]], showscale=False,
            marker_line_color=t["fundo"], marker_line_width=1.5,
            name=nome, showlegend=True,
            # ao clicar, o Plotly esmaeceria os outros estados; mantemos todos visíveis
            selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)),
            # customdata leva a sigla da UF, usada para identificar o estado clicado
            text=grupo["hover"], customdata=grupo["sg_uf"], hovertemplate="%{text}<extra></extra>",
        ))
    if destaque in set(df["sg_uf"]):
        fig.add_trace(go.Choropleth(
            geojson=geojson_ufs(), locations=[destaque], z=[1], showscale=False, showlegend=False,
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], hoverinfo="skip",
            marker_line_color=t["texto"], marker_line_width=3,
        ))
    # estados grandes: rótulo no centro, na cor de maior contraste com o preenchimento;
    # pequenos: rótulo no mar, ligado por uma linha-guia
    no_lugar = df[~df["sg_uf"].isin(ROTULOS_FORA)]
    fig.add_trace(go.Scattergeo(
        lon=no_lugar["lon"], lat=no_lugar["lat"], mode="text", showlegend=False, hoverinfo="skip",
        text=no_lugar["sg_uf"] + "<br><b>" + no_lugar["sg_partido"] + "</b>",
        textfont=dict(size=11, color=no_lugar["cor"].map(texto_sobre).tolist()),
    ))
    fora = df[df["sg_uf"].isin(ROTULOS_FORA)]
    for _, uf in fora.iterrows():
        lon, lat = ROTULOS_FORA[uf["sg_uf"]]
        fig.add_trace(go.Scattergeo(
            lon=[uf["lon"], lon], lat=[uf["lat"], lat], mode="lines", showlegend=False, hoverinfo="skip",
            line=dict(width=1, color=t["texto_secundario"]),
        ))
    fig.add_trace(go.Scattergeo(
        lon=[ROTULOS_FORA[u][0] for u in fora["sg_uf"]], lat=[ROTULOS_FORA[u][1] for u in fora["sg_uf"]],
        mode="text", textposition="middle right", showlegend=False, hoverinfo="skip",
        text=" " + fora["sg_uf"] + " <b>" + fora["sg_partido"] + "</b>",
        textfont=dict(size=11, color=t["texto"]),
    ))
    # área fixa (e não fitbounds) para os rótulos no mar não serem cortados
    fig.update_geos(visible=False, bgcolor="rgba(0,0,0,0)", projection_type="mercator",
                    lonaxis_range=[-74.5, -26], lataxis_range=[-34, 5.5])
    fig.update_layout(
        height=altura, margin=dict(l=0, r=0, t=30, b=0), paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1, x=0, bgcolor="rgba(0,0,0,0)",
                    font=dict(color=t["texto_secundario"])),
        hoverlabel=_hoverlabel(t), dragmode=False,
    )
    return fig


def barras_partido(contagem: pd.Series, rotulo: tuple[str, str], nomes: dict[str, str] | None = None) -> go.Figure:
    """Barras horizontais de cadeiras por partido (uma série só: uma cor só).

    `rotulo` é (singular, plural), ex.: ("governador", "governadores"); `nomes` mapeia
    sigla -> nome completo do partido, mostrado no tooltip."""
    t = tema()
    contagem = contagem.sort_values()
    nomes = nomes or {}
    total = contagem.sum()
    hover = [
        f"<b>{sigla}</b><br><span style='font-size:11px;opacity:.75'>{nomes.get(sigla, '')}</span><br>"
        f"{n} {rotulo[0] if n == 1 else rotulo[1]} · " + f"{n / total * 100:.1f}".replace(".", ",") + "% do total"
        for sigla, n in contagem.items()
    ]
    fig = go.Figure(go.Bar(
        x=contagem.values, y=contagem.index, orientation="h",
        marker=dict(color=t["barra"], cornerradius=4), width=0.7,
        text=contagem.values, textposition="outside", cliponaxis=False,
        textfont=dict(color=t["texto_secundario"], size=11),
        customdata=hover, hovertemplate="%{customdata}<extra></extra>",
    ))
    fig.update_layout(
        height=max(260, 22 * len(contagem) + 40), margin=dict(l=0, r=30, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(tickfont=dict(color=t["texto"], size=12)),
        bargap=0.25, dragmode=False, hoverlabel=_hoverlabel(t),
    )
    return fig
