# Matriz de evidências — revisão de 26/11/2026

Checkout oficial: C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT
Código validado: correção de gravação/base única sobre ee855b7 (26/11/2026); veja VALIDACAO_BASE_UNICA.md e o commit que contém esta revisão.
Repositório: https://github.com/Tiagoops/Trabalho_ufu.1
Última conferência remota: main em 030cd59; frontend e correções estão em commits locais. Não houve push nesta correção. A tentativa anterior foi bloqueada pela revisão automática por exigir autorização específica do autor.

Fonte acadêmica: Trabalho_2.pdf, Tabela 1 e seção 5. Pesos 20/20/45/15 são do
atendimento aos requisitos, não percentuais diretos da nota final. O enunciado
exige demonstração do programa em cinco minutos; slides são apoio solicitado
no cartão S5_19 e pelo autor. IA não substitui o domínio oral do aluno.

| Requisito / atividade | Estado atual | Evidência verificável | Limite / próxima ação |
|---|---|---|---|
| POO e objetos individuais — 20% | Implementado e testado | modelos.py: fábrica, subclasses, orientacoes_tratamento e recarga; tests/test_modelagem_oo.py; tests/test_integracao_poo_integridade.py | Ensaio oral do aluno ainda necessário |
| Lista JSON de objetos — 20% | Implementado e testado | banco_dados.py: consultar_retrato e salvar; to_dict/from_dict; testes de rollback, identidade e concorrência | Retentativas limitadas, conflito e rollback validados; permissão permanente continua sendo erro |
| Contêiner e 24h no servidor — 45% | Parte local comprovada; requisito integral aberto | docker/Dockerfile, docker/compose.yaml; 250 testes em cada ambiente Linux e Compose isolado; VALIDACAO_BASE_UNICA.md | Implantação docente e 24h não executadas; permanecem adiadas |
| Risco próprio/efetivo — 15% | Implementado e testado | servico_risco.py e matematica/risco.py; M, v, A, b=Mv, solve, rho, condição e resíduo; oráculo manual | Índice não é probabilidade nem percentual; não inventar fatores para demonstrar POO |
| Frontend, opções 0–14 | Implementado | interface_web/, templates/, app_web.py; CRUD, CVSS, dependências, riscos, JSON, CSV e Sair | Inspeção visual final e telas pequenas continuam parciais devido à automação do navegador |
| Importação JSON | HTTP real aprovado | validacao_http.json: prévia não grava; confirmação adiciona lote fictício; cancelamento/duplicidade também cobertos pela suíte | Upload visual não concluído; não confundir HTTP aprovado com inspeção do seletor |
| CSV | Download HTTP aprovado | Content-Disposition attachment; 4 ocorrências ordenadas; nenhum arquivo criado no servidor; CSV fictício preservado | Clique/download no navegador e layout pequeno não certificados nesta rodada |
| NVD pela nova interface | Fluxo HTTP real aprovado | CVE-2021-44228 consultada na API; prévia preserva a base; confirmação explícita; nota 10.0 e referência recarregadas em ativo fictício 9903 | CVE encontrada não prova falha em equipamento real |
| Estados da base e sessão | Aprovados por HTTP / testes | JSON inválido → 503 sem novos arquivos; [] → 200 com mensagem vazia; falha só no risco preserva ativos em HTTP 200 (validacao_risco_http.json); Sair e Entrar novamente aprovados | Sair encerra sessão, não o servidor; não apaga dados |
| Windows WinError 5 | Recuperação transitória implementada e validada | 4.000 gravações fictícias, 18 bloqueios recuperados e 0 falhas finais; teste com handle nativo; rollback persistente e conflito cobertos | Processo externo ainda não identificado; erros permanentes não são mascarados |
| Bases CLI/web | Unificadas e conferidas | dados/inventario.json; dois serviços usam /dados; seletor encaminha CLI ao frontend ativo; sete registros idênticos ao backup | Volume antigo preservado; não há mesclagem automática nem garantia entre escritores Windows/Linux simultâneos |
| S3_09 — relatório original | Não localizado nas fontes consultadas | Página Notion e duas exportações Trello descrevem relatório e checklist concluído; o cartão não possui anexos nas duas exportações; busca dirigida por nomes em Downloads/Documentos sem resultado | Localizar arquivo original/recibo com o aluno. Não recriar retroativamente como evidência histórica |
| Branches / merges | Conferência concluída; comprovação acadêmica não localizada | Na auditoria anterior: histórico completo (não shallow), 20 commits, 0 merges; API GitHub: 1 branch main e 0 PRs | Branches apagadas ou atividades externas não podem ser descartadas; não inventar histórico |
| S5_19 — apresentação | Material produzido nesta revisão | 6 slides PowerPoint com notas e roteiro de 300s; perguntas/respostas; gravação real de terminal Docker offline (44.27s) | Ensaio oral e revisão por colega dependem do aluno. A gravação não é sua apresentação oral |
| Acesso do docente / prazo | Acesso público comprovado; versão nova requer publicação | API GitHub sem credencial: private=false, visibility=public, main; prazo do enunciado 27/11/2026 | Não certifica a rede ou o login do docente; conferir SHA remoto após push |

## Modelo demonstrável

IDs (10,20,30,40): b=(10;7,5;9,8;0), x=(16,92;12,40;9,80;4,23).
x30=9,8; x20=7,5+0,5*9,8; x10=10+0,4*12,40+0,2*9,8;
x40=0+0,25*16,92. O peso 0,25 é participação de serviços; a indisponibilidade
observada é separada e não multiplica esse peso. Um cadastro vazio de ocorrências
e dependências pode ter risco zero, sem comprovar segurança do equipamento.

## Verificações e rastreabilidade

- Suítes atuais: 250 executados, 249 aprovados e 1 ignorado por plataforma em
  cada execução Windows, Linux independente e Compose isolado; 0 erros/falhas.
- Stress Windows: 4.000 gravações, 18 bloqueios recuperados, 0 falhas finais.
  Bind Linux/Windows: 500 gravações, 0 falhas finais. Não são garantias futuras.
- HTTP nativo Windows: cadastro, edição, CVSS, dependência, risco, remoção, CSV e
  Sair/Entrar aprovados em base fictícia. Consultas habituais 70/88/riscos: HTTP 200.
- Evidências atuais: VALIDACAO_BASE_UNICA.md e evidencias_base_unica_2026-11-26/.
  Os resultados anteriores de 238 casos permanecem como histórico.
- A gravação foi executada de verdade em imagem independente, --network none,
  --read-only e /tmp temporário; verificou recarga e o oráculo manual com asserts.
- Na rodada anterior os dados de validação ficaram em contêiner fictício, porta
  8001. Nesta correção houve um incidente de isolamento em subprocessos da suíte:
  dois registros fictícios foram inseridos na base habitual. Foram removidos após
  comparação integral dos sete originais; o arquivo voltou a ser idêntico ao backup.
  A fixture e o comando Compose foram corrigidos; repetição isolada passou.
  Detalhes e SHA antes/depois em VALIDACAO_BASE_UNICA.md.
- Versões anteriores da matriz e guia foram preservadas no diretório desta revisão.
- Referências de acompanhamento: Notion 4155b20a63e6818a99e4f5f5fee55483;
  S3_09 https://app.notion.com/p/4155b20a63e681909a4efa6bc8e365ad;
  S5_19 https://trello.com/c/kWoLA4RP. O acompanhamento histórico não equivale
  à validação atual. Nenhum checklist do aluno foi marcado como aprendido.

## Registro de revisão

26/11/2026: substituída a fotografia de 9a75a89/155 testes por esta conferência
do código 2e1195e/238 casos. Frontend e NVD atualizados; registradas recusas
Windows reproduzíveis e limites visuais, sem apagar o histórico nem declarar
implantação/24h como feitas.

26/11/2026, correção posterior: base única compartilhada, tratamento limitado
para bloqueios Windows e operação somente em loopback. Matriz atualizada com
250 casos por ambiente, incidentes e limites, preservando os registros históricos.
