"""Lê os CSVs do TSE em data/raw e monta o banco SQLite data/brasil.db.

Uso:
    python scripts/montar_banco.py

O banco é recriado do zero a cada execução. Os anos processados são os que constam
em data/raw/fontes.json (gerado por baixar_dados.py).

Modelo (eixos: ano e estado):
    fonte         um registro por CSV lido (arquivo, URL do zip, sha256, data do download)
    uf            estados, com nome e região
    candidatura   um registro por candidato por turno, com a linha exata do CSV de origem
    votacao_uf    votos nominais somados por candidato, turno e UF (a partir de município/zona)
"""

import json
import sqlite3
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"
REGISTRO = PASTA_RAW / "fontes.json"
BANCO = RAIZ / "data" / "brasil.db"

# Escopo do MVP: presidente, governador, senador e deputado federal
CARGOS = {1: "Presidente", 3: "Governador", 5: "Senador", 6: "Deputado Federal"}

# Situações de fim de turno que significam eleito (variam conforme o ano)
SITUACOES_ELEITO = {"ELEITO", "ELEITO POR QP", "ELEITO POR MÉDIA", "MÉDIA"}

UFS = [
    ("AC", "Acre", "Norte"), ("AL", "Alagoas", "Nordeste"), ("AP", "Amapá", "Norte"),
    ("AM", "Amazonas", "Norte"), ("BA", "Bahia", "Nordeste"), ("CE", "Ceará", "Nordeste"),
    ("DF", "Distrito Federal", "Centro-Oeste"), ("ES", "Espírito Santo", "Sudeste"),
    ("GO", "Goiás", "Centro-Oeste"), ("MA", "Maranhão", "Nordeste"),
    ("MT", "Mato Grosso", "Centro-Oeste"), ("MS", "Mato Grosso do Sul", "Centro-Oeste"),
    ("MG", "Minas Gerais", "Sudeste"), ("PA", "Pará", "Norte"), ("PB", "Paraíba", "Nordeste"),
    ("PR", "Paraná", "Sul"), ("PE", "Pernambuco", "Nordeste"), ("PI", "Piauí", "Nordeste"),
    ("RJ", "Rio de Janeiro", "Sudeste"), ("RN", "Rio Grande do Norte", "Nordeste"),
    ("RS", "Rio Grande do Sul", "Sul"), ("RO", "Rondônia", "Norte"), ("RR", "Roraima", "Norte"),
    ("SC", "Santa Catarina", "Sul"), ("SP", "São Paulo", "Sudeste"), ("SE", "Sergipe", "Nordeste"),
    ("TO", "Tocantins", "Norte"),
    # Abrangências que não são estados, mas aparecem nos arquivos
    ("BR", "Brasil", None), ("ZZ", "Exterior", None), ("VT", "Voto em trânsito", None),
]

ESQUEMA = """
CREATE TABLE fonte (
    id          INTEGER PRIMARY KEY,
    arquivo     TEXT NOT NULL UNIQUE,  -- caminho do CSV dentro de data/raw
    zip         TEXT NOT NULL,
    conjunto    TEXT NOT NULL,
    descricao   TEXT,
    ano         INTEGER NOT NULL,
    url         TEXT NOT NULL,         -- URL do zip no Portal de Dados Abertos do TSE
    baixado_em  TEXT,
    sha256_zip  TEXT
);

CREATE TABLE uf (
    sigla   TEXT PRIMARY KEY,
    nome    TEXT NOT NULL,
    regiao  TEXT
);

CREATE TABLE candidatura (
    id                    INTEGER PRIMARY KEY,
    ano                   INTEGER NOT NULL,
    turno                 INTEGER NOT NULL,
    cd_cargo              INTEGER NOT NULL,
    cargo                 TEXT NOT NULL,
    sg_uf                 TEXT NOT NULL REFERENCES uf(sigla),
    sq_candidato          TEXT NOT NULL,
    nr_candidato          TEXT,
    nome                  TEXT,
    nome_urna             TEXT,
    nr_partido            TEXT,
    sg_partido            TEXT,
    nm_partido            TEXT,
    coligacao             TEXT,
    composicao_coligacao  TEXT,
    situacao_candidatura  TEXT,
    situacao_turno        TEXT,
    eleito                INTEGER NOT NULL,
    fonte_id              INTEGER NOT NULL REFERENCES fonte(id),
    linha_fonte           INTEGER NOT NULL  -- linha no CSV (1 = cabeçalho)
);
CREATE INDEX ix_candidatura_eixos ON candidatura (ano, cd_cargo, sg_uf);
CREATE INDEX ix_candidatura_sq ON candidatura (sq_candidato);

CREATE TABLE votacao_uf (
    ano           INTEGER NOT NULL,
    turno         INTEGER NOT NULL,
    cd_cargo      INTEGER NOT NULL,
    sg_uf         TEXT NOT NULL REFERENCES uf(sigla),
    sq_candidato  TEXT NOT NULL,
    votos         INTEGER NOT NULL,
    fonte_id      INTEGER NOT NULL REFERENCES fonte(id),
    PRIMARY KEY (ano, turno, cd_cargo, sg_uf, sq_candidato)
);
"""

COLS_CAND = [
    "ANO_ELEICAO", "NR_TURNO", "CD_CARGO", "SG_UF", "SQ_CANDIDATO", "NR_CANDIDATO",
    "NM_CANDIDATO", "NM_URNA_CANDIDATO", "NR_PARTIDO", "SG_PARTIDO", "NM_PARTIDO",
    "NM_COLIGACAO", "DS_COMPOSICAO_COLIGACAO", "DS_SITUACAO_CANDIDATURA", "DS_SIT_TOT_TURNO",
]
COLS_VOTOS = ["ANO_ELEICAO", "NR_TURNO", "CD_CARGO", "SG_UF", "SQ_CANDIDATO", "QT_VOTOS_NOMINAIS"]


def ler_csv_tse(caminho: Path, colunas: list[str], **kwargs):
    return pd.read_csv(caminho, sep=";", encoding="latin1", dtype=str, usecols=colunas, **kwargs)


def csvs_do_zip(info: dict) -> list[str]:
    """CSVs por UF (e BR). O arquivo _BRASIL é a consolidação dos demais e é ignorado."""
    return [a for a in info["arquivos"] if a.endswith(".csv") and not a.endswith("_BRASIL.csv")]


def registrar_fonte(con: sqlite3.Connection, zip_nome: str, info: dict, csv: str) -> int:
    cur = con.execute(
        "INSERT INTO fonte (arquivo, zip, conjunto, descricao, ano, url, baixado_em, sha256_zip)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (f"{Path(zip_nome).stem}/{csv}", zip_nome, info["conjunto"], info.get("descricao"),
         info["ano"], info["url"], info.get("baixado_em"), info.get("sha256")),
    )
    return cur.lastrowid


def carregar_candidaturas(con: sqlite3.Connection, caminho: Path, fonte_id: int) -> int:
    df = ler_csv_tse(caminho, COLS_CAND)
    df["linha_fonte"] = df.index + 2  # +1 do cabeçalho, +1 porque a contagem começa em 1
    df["CD_CARGO"] = df["CD_CARGO"].astype(int)
    df = df[df["CD_CARGO"].isin(CARGOS)]
    if df.empty:
        return 0

    saida = pd.DataFrame({
        "ano": df["ANO_ELEICAO"].astype(int),
        "turno": df["NR_TURNO"].astype(int),
        "cd_cargo": df["CD_CARGO"],
        "cargo": df["CD_CARGO"].map(CARGOS),
        "sg_uf": df["SG_UF"],
        "sq_candidato": df["SQ_CANDIDATO"],
        "nr_candidato": df["NR_CANDIDATO"],
        "nome": df["NM_CANDIDATO"],
        "nome_urna": df["NM_URNA_CANDIDATO"],
        "nr_partido": df["NR_PARTIDO"],
        "sg_partido": df["SG_PARTIDO"],
        "nm_partido": df["NM_PARTIDO"],
        "coligacao": df["NM_COLIGACAO"].replace("#NULO#", None),
        "composicao_coligacao": df["DS_COMPOSICAO_COLIGACAO"],
        "situacao_candidatura": df["DS_SITUACAO_CANDIDATURA"],
        "situacao_turno": df["DS_SIT_TOT_TURNO"],
        "eleito": df["DS_SIT_TOT_TURNO"].isin(SITUACOES_ELEITO).astype(int),
        "fonte_id": fonte_id,
        "linha_fonte": df["linha_fonte"],
    })
    saida.to_sql("candidatura", con, if_exists="append", index=False)
    return len(saida)


def carregar_votacao(con: sqlite3.Connection, caminho: Path, fonte_id: int) -> int:
    """Soma os votos de município/zona por candidato, turno e UF, lendo em blocos."""
    parciais = []
    for bloco in ler_csv_tse(caminho, COLS_VOTOS, chunksize=500_000):
        bloco["CD_CARGO"] = bloco["CD_CARGO"].astype(int)
        bloco = bloco[bloco["CD_CARGO"].isin(CARGOS)]
        bloco["QT_VOTOS_NOMINAIS"] = bloco["QT_VOTOS_NOMINAIS"].astype(int)
        parciais.append(
            bloco.groupby(["ANO_ELEICAO", "NR_TURNO", "CD_CARGO", "SG_UF", "SQ_CANDIDATO"])
            ["QT_VOTOS_NOMINAIS"].sum()
        )
    if not parciais:
        return 0

    total = pd.concat(parciais).groupby(level=[0, 1, 2, 3, 4]).sum().reset_index()
    total.columns = ["ano", "turno", "cd_cargo", "sg_uf", "sq_candidato", "votos"]
    total["ano"] = total["ano"].astype(int)
    total["turno"] = total["turno"].astype(int)
    total["fonte_id"] = fonte_id
    total.to_sql("votacao_uf", con, if_exists="append", index=False)
    return len(total)


CARREGADORES = {
    "consulta_cand": carregar_candidaturas,
    "votacao_candidato_munzona": carregar_votacao,
}


def main() -> None:
    if not REGISTRO.exists():
        raise SystemExit("data/raw/fontes.json não encontrado. Rode antes: python scripts/baixar_dados.py")
    registro = json.loads(REGISTRO.read_text(encoding="utf-8"))

    BANCO.unlink(missing_ok=True)
    con = sqlite3.connect(BANCO)
    con.executescript(ESQUEMA)
    con.executemany("INSERT INTO uf VALUES (?, ?, ?)", UFS)

    for zip_nome, info in sorted(registro.items()):
        carregar = CARREGADORES.get(info["conjunto"])
        if carregar is None:
            continue
        pasta = PASTA_RAW / Path(zip_nome).stem
        print(f"[{info['ano']}] {info['conjunto']}")
        total = 0
        for csv in csvs_do_zip(info):
            fonte_id = registrar_fonte(con, zip_nome, info, csv)
            total += carregar(con, pasta / csv, fonte_id)
        print(f"    {total} registros")

    con.commit()
    resumo = con.execute(
        "SELECT ano, cargo, COUNT(*), SUM(eleito) FROM candidatura GROUP BY ano, cd_cargo ORDER BY ano, cd_cargo"
    ).fetchall()
    print("\nResumo (ano, cargo, candidaturas, eleitos):")
    for linha in resumo:
        print("   ", *linha)
    con.close()
    print(f"\nBanco gerado em {BANCO.relative_to(RAIZ)} ({BANCO.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
