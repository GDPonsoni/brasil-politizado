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

## Convenções
- Commits seguem Conventional Commits (feat, fix, docs, chore, refactor...), mensagens em português.
