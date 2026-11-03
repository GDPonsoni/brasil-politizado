# Brasil Politizado

Web app de transparência política brasileira, navegável por **ano** e **região**.

O MVP mostra a foto eleitoral histórica a partir dos dados abertos do TSE: presidente,
governadores por estado e eleitos para Câmara e Senado. Todo dado exibido indica de onde veio.

## Como rodar (100% local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/baixar_dados.py   # baixa os arquivos do TSE para data/raw
python scripts/montar_banco.py   # trata os CSVs e gera data/brasil.db
streamlit run app/app.py         # abre a interface
```

Os dados brutos e o banco **não** vão para o Git; qualquer pessoa os recria com os scripts acima.

## Estrutura

```
docs/      requisitos e guia do projeto
scripts/   coleta (baixar_dados.py) e carga (montar_banco.py)
app/       interface Streamlit
data/      raw/ (CSVs do TSE) e brasil.db (gerados localmente)
```

## Fonte dos dados

[Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/).
