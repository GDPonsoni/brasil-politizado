"""Acesso ao banco SQLite (somente leitura) e consultas usadas pelo app."""

import json
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "brasil.db"
GEOJSON = Path(__file__).resolve().parent / "assets" / "ufs.geojson"

PRESIDENTE, GOVERNADOR, SENADOR, DEP_FEDERAL = 1, 3, 5, 6


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
    JOIN candidatura cc ON cc.ano = vu.ano AND cc.sq_candidato = vu.sq_candidato AND cc.turno = vu.turno
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
        JOIN votacao_uf v ON v.ano = c.ano AND v.sq_candidato = c.sq_candidato AND v.turno = c.turno AND v.cd_cargo = c.cd_cargo
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
        JOIN candidatura c ON c.ano = v.ano AND c.sq_candidato = v.sq_candidato AND c.turno = v.turno AND c.cd_cargo = v.cd_cargo
        WHERE v.ano = ? AND v.turno = ? AND v.cd_cargo = 1 AND u.regiao IS NOT NULL
        """,
        (ano, turno),
    )
    df["pct"] = df["votos"] / df["total"]
    return df.sort_values("votos", ascending=False).drop_duplicates("sg_uf").sort_values("sg_uf")
