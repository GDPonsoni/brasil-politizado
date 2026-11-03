"""Formatação, glossário e blocos de interface reutilizados pelas seções."""

import re

import pandas as pd
import streamlit as st

# Textos de ajuda mostrados ao passar o mouse (ícone "?" dos widgets, cabeçalhos de tabela e métricas)
GLOSSARIO = {
    "turno": "Presidente e governador precisam de mais da metade dos votos válidos. Se ninguém "
             "chega lá no 1º turno, os dois mais votados disputam o 2º turno.",
    "votos_nominais": "Votos dados diretamente a um candidato, digitando o número dele. Não incluem "
                      "votos só no partido (legenda), brancos ou nulos.",
    "pct_nominais": "Votos do candidato divididos pelo total de votos nominais do cargo naquele estado e turno.",
    "situacao": "Situação final publicada pelo TSE, já considerando decisões posteriores à eleição "
                "(por exemplo, cassações).",
    "media": "MÉDIA (ou ELEITO POR MÉDIA): eleito pelas sobras, as vagas que restam depois da divisão "
             "pelo quociente partidário. ELEITO POR QP: eleito pelas vagas que o partido conquistou direto.",
    "calculado": "Quando o TSE não informa o resultado de um turno, o mais votado no arquivo de votação "
                 "é marcado como eleito, com a situação \"calculado pela votação\".",
    "coligacao": "Aliança de partidos que concorreu junta. Nas eleições para deputado, as coligações "
                 "foram proibidas a partir de 2020.",
    "fonte": "Arquivo CSV do TSE (dentro do zip baixado do Portal de Dados Abertos) de onde o registro foi lido.",
    "linha": "Número da linha nesse CSV (a linha 1 é o cabeçalho). Fica vazio quando o dado foi calculado pela votação.",
    "senado": "O Senado tem 81 cadeiras, 3 por estado. A cada eleição a renovação alterna entre 2 vagas "
              "por estado (2/3 do Senado) e 1 vaga (1/3).",
    "camara": "A Câmara tem 513 deputados federais, distribuídos entre os estados de acordo com a "
              "população (mínimo de 8 e máximo de 70 por estado).",
    "mais_votado_uf": "Candidato com mais votos nominais em cada estado. Não é necessariamente quem venceu no país.",
    "partidos_representados": "Quantos partidos diferentes têm pelo menos um eleito no recorte escolhido.",
}


PARTICULAS = {"da", "de", "do", "das", "dos", "e", "di", "du"}
# Siglas que aparecem em nomes de urna e devem ficar em maiúsculas
SIGLAS_EM_NOMES = {"ACM", "JHC", "II", "III"}


def nome_proprio(texto) -> str:
    """'TIÃO VIANA' -> 'Tião Viana'; 'LULA DA SILVA' -> 'Lula da Silva'; mantém siglas conhecidas."""
    if not isinstance(texto, str):
        return texto
    palavras = []
    for i, palavra in enumerate(texto.split()):
        if palavra.upper() in SIGLAS_EM_NOMES:
            palavras.append(palavra.upper())
        elif i > 0 and palavra.lower() in PARTICULAS:
            palavras.append(palavra.lower())
        else:
            # capitaliza também depois de apóstrofo e hífen: D'ÁVILA -> D'Ávila, SANTA-RITA -> Santa-Rita
            palavras.append(re.sub(r"(^|['’-])(\w)", lambda m: m.group(1) + m.group(2).upper(), palavra.lower()))
    return " ".join(palavras)


def eh_celular() -> bool:
    """Detecção simples pelo navegador, usada só para ajustar alturas de gráficos."""
    return "Mobi" in (st.context.headers.get("User-Agent") or "")


def ajuda(*chaves: str) -> str:
    return "\n\n".join(GLOSSARIO[c] for c in chaves)


def fmt_int(n) -> str:
    return "—" if pd.isna(n) else f"{int(n):,}".replace(",", ".")


def fmt_pct(p) -> str:
    return "—" if pd.isna(p) else f"{p * 100:.1f}%".replace(".", ",")


def _texto_hover(linha: pd.Series) -> str:
    votos = f"{fmt_int(linha['votos'])} votos · {fmt_pct(linha['pct'])} dos nominais"
    if "turno" in linha and pd.notna(linha["turno"]):
        votos += f" · {int(linha['turno'])}º turno"
    if pd.notna(linha.get("linha_fonte")):
        fonte = f"{linha['fonte_arquivo']}, linha {int(linha['linha_fonte'])}"
    else:
        fonte = f"{linha['fonte_arquivo']} (soma de município/zona)"
    return (
        f"<b>{linha['estado']}</b><br>"
        f"{linha['nome_exibicao']} · <b>{linha['sg_partido']}</b><br>"
        f"<span style='font-size:11px;opacity:.75'>{linha['partido_exibicao']}</span><br>"
        f"{votos}<br>"
        f"<span style='font-size:10px;opacity:.6'>Nome no TSE: {linha['nome']}<br>Fonte: {fonte}</span>"
    )


def hover_candidatos(df: pd.DataFrame) -> list[str]:
    """Texto do tooltip do mapa: estado, candidato, partido, votos, turno e fonte, igual em todos os mapas."""
    return [_texto_hover(linha) for _, linha in df.iterrows()]


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
            column_config={
                "Arquivo": st.column_config.TextColumn("Arquivo", help=ajuda("fonte")),
                "URL": st.column_config.LinkColumn("Download (zip)", display_text="cdn.tse.jus.br ↗",
                                                   help="Link do arquivo original no Portal de Dados Abertos do TSE"),
            },
        )
