"""Formatação e blocos de interface reutilizados pelas seções."""

import pandas as pd
import streamlit as st


def fmt_int(n) -> str:
    return "—" if pd.isna(n) else f"{int(n):,}".replace(",", ".")


def fmt_pct(p) -> str:
    return "—" if pd.isna(p) else f"{p * 100:.1f}%".replace(".", ",")


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
