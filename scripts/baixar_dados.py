"""Baixa arquivos do Portal de Dados Abertos do TSE para data/raw.

Uso:
    python scripts/baixar_dados.py               # eleição de 2010
    python scripts/baixar_dados.py --anos 2010 2014
    python scripts/baixar_dados.py --sem-votos   # pula o arquivo grande de votação

Cada download é registrado em data/raw/fontes.json (URL, arquivo, data, tamanho, sha256),
para que todo dado do banco possa ser rastreado até a origem.
"""

import argparse
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RAW = RAIZ / "data" / "raw"
REGISTRO = PASTA_RAW / "fontes.json"

BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele"

# nome do conjunto (também é a pasta no CDN) -> descrição
CONJUNTOS = {
    "consulta_cand": "Candidatos (inclui situação de eleito por turno)",
    "votacao_candidato_munzona": "Votação nominal por candidato, município e zona",
}


def url_do_conjunto(conjunto: str, ano: int) -> str:
    return f"{BASE_URL}/{conjunto}/{conjunto}_{ano}.zip"


def sha256(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def baixar(url: str, destino: Path) -> None:
    with requests.get(url, stream=True, timeout=60) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        baixado = 0
        temporario = destino.with_suffix(".part")
        with temporario.open("wb") as f:
            for bloco in resp.iter_content(chunk_size=1 << 20):
                f.write(bloco)
                baixado += len(bloco)
                if total:
                    print(f"\r    {baixado / 1e6:6.1f} / {total / 1e6:.1f} MB", end="", flush=True)
        print()
        temporario.rename(destino)


def extrair(zip_path: Path, pasta: Path) -> list[str]:
    pasta.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(pasta)
        return sorted(n for n in z.namelist() if not n.endswith("/"))


def carregar_registro() -> dict:
    if REGISTRO.exists():
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    return {}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--anos", type=int, nargs="+", default=[2010])
    parser.add_argument("--sem-votos", action="store_true", help="não baixa votacao_candidato_munzona")
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se o zip já existir")
    args = parser.parse_args()

    PASTA_RAW.mkdir(parents=True, exist_ok=True)
    registro = carregar_registro()

    conjuntos = [c for c in CONJUNTOS if not (args.sem_votos and c == "votacao_candidato_munzona")]
    for ano in args.anos:
        for conjunto in conjuntos:
            url = url_do_conjunto(conjunto, ano)
            zip_path = PASTA_RAW / f"{conjunto}_{ano}.zip"
            print(f"[{ano}] {CONJUNTOS[conjunto]}")
            print(f"    fonte: {url}")

            if zip_path.exists() and not args.forcar:
                print(f"    já existe: {zip_path.relative_to(RAIZ)} (use --forcar para baixar de novo)")
            else:
                baixar(url, zip_path)

            pasta_extraida = PASTA_RAW / f"{conjunto}_{ano}"
            arquivos = extrair(zip_path, pasta_extraida)
            print(f"    extraído em {pasta_extraida.relative_to(RAIZ)}/ ({len(arquivos)} arquivos)")

            registro[zip_path.name] = {
                "conjunto": conjunto,
                "descricao": CONJUNTOS[conjunto],
                "ano": ano,
                "url": url,
                "baixado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "tamanho_bytes": zip_path.stat().st_size,
                "sha256": sha256(zip_path),
                "arquivos": arquivos,
            }

    REGISTRO.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRegistro de fontes salvo em {REGISTRO.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
