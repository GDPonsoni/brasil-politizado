# Brasil Politizado — Guia de Início (Setup + Prompts)

> Passo a passo pronto para sentar no computador e começar direto. Siga de cima para baixo: pré-requisitos, criar a pasta, rodar o Claude Code, e os prompts numerados para colar em ordem.

## 1. Pré-requisitos (instalar uma vez)

- Python 3.11 ou mais novo.
- Git.
- Claude Code (CLI da Anthropic), instalado e logado.
- Um editor, VS Code de preferência.
- Conta no GitHub (repositório será privado).

## 2. Criar a pasta e o repositório

No terminal, na pasta onde você guarda seus projetos:

```
mkdir brasil-politizado
cd brasil-politizado
git init
```

Crie também, pelo site do GitHub, um repositório PRIVADO chamado brasil-politizado e guarde a URL dele — você vai conectar depois (o próprio Claude Code pode te ajudar com isso).

## 3. Estrutura de pastas (alvo)

Você não precisa criar tudo à mão — o Claude Code monta no primeiro prompt. Esta é a estrutura que a gente quer chegar:

```
brasil-politizado/
├── CLAUDE.md            (regras do projeto para a IA)
├── README.md
├── requirements.txt     (dependências Python)
├── .gitignore
├── docs/
│   └── requisitos.md    (o documento de requisitos que já fizemos)
├── data/
│   ├── raw/             (CSVs crus do TSE — NÃO vão para o Git)
│   └── brasil.db        (banco SQLite — NÃO vai para o Git)
├── scripts/
│   ├── baixar_dados.py  (baixa os arquivos do TSE)
│   └── montar_banco.py  (trata os CSVs e popula o SQLite)
└── app/
    └── app.py           (interface Streamlit)
```

## 4. Onde rodar o Claude Code

Abra o terminal, entre na pasta do projeto (`cd brasil-politizado`) e rode `claude`. Ele trabalha direto nos arquivos dessa pasta — não precisa conectar nada. Deixe a pasta aberta no VS Code ao lado para ir vendo os arquivos surgirem.

## 5. Antes de começar: colocar os dois arquivos de contexto

Antes do primeiro prompt, coloque na pasta:

1. O documento de requisitos exportado em markdown, salvo como `docs/requisitos.md`.
2. O `CLAUDE.md` na raiz (conteúdo pronto na seção 7 abaixo).

Assim a IA já começa com todo o contexto e o escopo travado.

## 6. Prompts para enviar (em ordem)

Mande um de cada vez. Só avance quando o anterior estiver funcionando. Leia a resposta antes de aprovar — principalmente o prompt 2, que é um plano, não é código.

### Prompt 1 — Dar o contexto

```
Leia os arquivos docs/requisitos.md e CLAUDE.md por completo. Eles descrevem um projeto de transparência política chamado Brasil Politizado. Me confirme, em resumo, qual é o escopo do MVP e quais tecnologias vamos usar, para eu ter certeza de que você entendeu. Ainda não escreva código.
```

### Prompt 2 — Pedir o plano (aprovar antes de codar)

```
Monte um plano de implementação só do MVP, em etapas pequenas e na ordem em que devemos fazer. Para cada etapa diga o que será feito e qual arquivo será criado ou alterado. Não escreva código ainda — quero aprovar o plano primeiro.
```

### Prompt 3 — Estrutura do projeto

```
Crie a estrutura inicial do projeto conforme o plano: as pastas, o .gitignore (ignorando data/raw, o arquivo .db e segredos), o requirements.txt com as dependências (incluindo streamlit, pandas e requests) e um README.md curto. Ainda sem baixar dados.
```

### Prompt 4 — Baixar os dados do TSE

```
Vamos começar pela coleta. Escreva o script scripts/baixar_dados.py que baixa, do Portal de Dados Abertos do TSE, os resultados de UMA eleição para testarmos — a eleição de 2010. Baixe para data/raw. Mostre no terminal o que foi baixado e de qual URL, para termos rastreabilidade da fonte.
```

### Prompt 5 — Montar o banco

```
Agora escreva scripts/montar_banco.py que lê os CSVs de data/raw, trata os dados e popula um banco SQLite em data/brasil.db. Modele as tabelas pensando no eixo tempo (ano) e região (estado). Em cada registro, guarde também de qual arquivo de origem ele veio, para rastreabilidade. Me explique o modelo de tabelas antes de rodar.
```

### Prompt 6 — Primeira tela

```
Agora a interface. Crie app/app.py com Streamlit: um seletor de ano no topo e um mapa do Brasil colorido por partido do governador eleito naquele ano, lendo de data/brasil.db. Capricho na usabilidade e no visual — layout limpo, agradável e responsivo é a prioridade número um. Em cada dado mostrado, deixe acessível a fonte de onde ele veio.
```

### Prompt 7 — Primeiro commit

```
Vamos versionar. Me ajude a fazer o primeiro commit e a conectar com o repositório privado do GitHub (vou te passar a URL). Confirme que data/raw e o .db estão no .gitignore antes de commitar.
```

## 7. Conteúdo do CLAUDE.md (copie para a raiz do projeto)

```
# Brasil Politizado — Regras do projeto

## O que é
Web app de transparência política brasileira, navegável por ano e região. Detalhes completos em docs/requisitos.md.

## Escopo ATUAL (não ultrapassar)
Apenas o MVP: foto eleitoral histórica a partir dos dados do TSE (presidente, governadores por estado, eleitos para Câmara e Senado, plano de governo do presidente). Uma fonte só: TSE.
NÃO implementar as fases 2, 3 ou futuras (composição ao longo do mandato, finanças, indicadores, classificação por pauta). Se achar que algo dessas fases é necessário, pergunte antes.

## Tecnologias (não trocar sem avisar)
- Python em tudo.
- SQLite como banco (arquivo único, sem servidor).
- Streamlit na interface (sem front-end separado, sem HTML/JS à mão).

## Prioridades inegociáveis
1. Usabilidade e visual vêm primeiro: interface agradável, bonita, fácil e responsiva.
2. Rastreabilidade: todo dado exibido mostra de onde veio (fonte, arquivo, lugar).
3. Rodar 100% local por enquanto; nada de hospedagem.

## Método de trabalho
Vibe coding: eu guio e aprovo, você implementa. Sempre proponha um plano antes de gerar código em etapas novas. Faça mudanças em passos pequenos e me explique as decisões em português.

## Regras de dados
- Dados brutos do TSE e o arquivo .db nunca vão para o Git (ficam no .gitignore).
- Scripts que baixam os dados vão para o Git.
```
