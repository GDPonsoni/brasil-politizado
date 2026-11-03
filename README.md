# Brasil Politizado

Web app de transparência política brasileira, navegável por **ano** e **região**.

O MVP mostra a foto eleitoral histórica a partir dos dados abertos do TSE: presidente,
governadores por estado e eleitos para Câmara e Senado. Todo dado exibido indica de onde veio.

## Como rodar (100% local)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/baixar_dados.py                    # baixa 2010 (padrão) para data/raw
python scripts/baixar_dados.py --anos 2018 2022   # ou outros anos de eleição geral
python scripts/montar_banco.py                    # trata os CSVs e gera data/brasil.db
streamlit run app/app.py                          # abre a interface
```

Os dados brutos e o banco **não** vão para o Git; qualquer pessoa os recria com os scripts acima.
Use `--sem-votos` no download para pular o arquivo grande de votação (o app mostra os eleitos,
mas sem contagem de votos).

## O que o app mostra

- **Presidente:** eleito, resultado nacional por turno e mapa do mais votado em cada estado.
- **Governadores:** mapa colorido pelo partido do governador eleito, contagem por partido e detalhe por estado.
- **Senado e Câmara:** eleitos com filtro por região e estado, cadeiras por partido e busca por nome.
- **Sobre os dados:** todos os arquivos carregados, com URL, data do download e SHA-256.

Rastreabilidade: cada registro do banco guarda o CSV e a **linha** de onde saiu (`candidatura.fonte_id`
e `candidatura.linha_fonte`), e o app mostra isso nas tabelas e no bloco *Fonte dos dados* de cada seção.

## Modelo do banco (`data/brasil.db`)

| Tabela | Conteúdo |
|---|---|
| `fonte` | um registro por CSV lido: arquivo, zip, URL, data do download, SHA-256 |
| `uf` | estados com nome e região (mais BR, ZZ = exterior, VT = voto em trânsito) |
| `candidatura` | candidato por turno: cargo, UF, partido, coligação, situação, se foi eleito, fonte e linha |
| `votacao_uf` | votos nominais por candidato, turno e UF, somados a partir de município/zona |

Escopo atual: presidente, governador, senador e deputado federal. Os arquivos `_BRASIL.csv`
do TSE são consolidações dos arquivos por UF e são ignorados para não duplicar registros.

### Regras de tratamento

- **Só eleições gerais:** eleições suplementares que vêm no mesmo arquivo (ex.: governador do AM em 2017,
  dentro do arquivo de 2014) são descartadas.
- **Situação final:** vale a situação publicada pelo TSE, já com cassações e decisões posteriores.
  Ex.: em 2018 o Senado tem 53 eleitos, porque a vaga de MT foi cassada.
- **Eleito calculado:** quando o TSE não traz um turno no arquivo de candidatos (2º turno de presidente
  em 2006), a candidatura é criada a partir da votação, o mais votado é marcado como eleito e a
  situação fica "calculado pela votação", com o arquivo de votação como fonte.
- **Eleito só no último turno:** se o arquivo marca o mesmo candidato como eleito em dois turnos, vale o último.

## Volume de dados

Medido com as eleições gerais de 2002 a 2022 (6 eleições):

| Item | Tamanho |
|---|---|
| zips baixados do TSE (`data/raw`) | ~1,8 GB |
| mesmos arquivos, se extraídos | ~28 GB (por isso os CSVs são lidos direto do zip) |
| banco final (`data/brasil.db`) | ~13 MB |
| tempo para montar o banco | ~2,5 min |

O peso está nos dados **brutos** (votação por município e zona). O banco que o app usa guarda os votos
já somados por estado e é pequeno.

## Estrutura

```
docs/      requisitos e guia do projeto
scripts/   coleta (baixar_dados.py) e carga (montar_banco.py)
app/       interface Streamlit
data/      raw/ (CSVs do TSE) e brasil.db (gerados localmente)
```

## Fonte dos dados

[Portal de Dados Abertos do TSE](https://dadosabertos.tse.jus.br/).
