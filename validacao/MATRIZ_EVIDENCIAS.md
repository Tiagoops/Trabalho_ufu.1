# Matriz de evidências — revisão de 26/11/2026

Checkout oficial: C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT
Código da aplicação validado: 2e1195e10e2a5a9133a5b1192e09ccd28ed8e5e8
Repositório: https://github.com/Tiagoops/Trabalho_ufu.1
A main remota está em 030cd59; o código do frontend 2e1195e está salvo localmente. A publicação foi bloqueada pela revisão automática por exigir autorização específica para push; permanece pronta para essa autorização.

Fonte acadêmica: Trabalho_2.pdf, Tabela 1 e seção 5. Pesos 20/20/45/15 são do
atendimento aos requisitos, não percentuais diretos da nota final. O enunciado
exige demonstração do programa em cinco minutos; slides são apoio solicitado
no cartão S5_19 e pelo autor. IA não substitui o domínio oral do aluno.

| Requisito / atividade | Estado atual | Evidência verificável | Limite / próxima ação |
|---|---|---|---|
| POO e objetos individuais — 20% | Implementado e testado | modelos.py: fábrica, subclasses, orientacoes_tratamento e recarga; tests/test_modelagem_oo.py; tests/test_integracao_poo_integridade.py | Ensaio oral do aluno ainda necessário |
| Lista JSON de objetos — 20% | Implementado e testado | banco_dados.py: consultar_retrato e salvar; to_dict/from_dict; testes de rollback, identidade e concorrência | WinError 5 intermitente reproduzido fora do domínio; autoria ainda indeterminada |
| Contêiner e 24h no servidor — 45% | Parte local comprovada; requisito integral aberto | docker/Dockerfile, docker/compose.yaml; 238 testes Linux e Compose na entrega de código 2e1195e | Implantação docente e 24h não executadas; permanecem adiadas |
| Risco próprio/efetivo — 15% | Implementado e testado | servico_risco.py e matematica/risco.py; M, v, A, b=Mv, solve, rho, condição e resíduo; oráculo manual | Índice não é probabilidade nem percentual; não inventar fatores para demonstrar POO |
| Frontend, opções 0–14 | Implementado | interface_web/, templates/, app_web.py; CRUD, CVSS, dependências, riscos, JSON, CSV e Sair | Inspeção visual final e telas pequenas continuam parciais devido à automação do navegador |
| Importação JSON | HTTP real aprovado | validacao_http.json: prévia não grava; confirmação adiciona lote fictício; cancelamento/duplicidade também cobertos pela suíte | Upload visual não concluído; não confundir HTTP aprovado com inspeção do seletor |
| CSV | Download HTTP aprovado | Content-Disposition attachment; 4 ocorrências ordenadas; nenhum arquivo criado no servidor; CSV fictício preservado | Clique/download no navegador e layout pequeno não certificados nesta rodada |
| NVD pela nova interface | Fluxo HTTP real aprovado | CVE-2021-44228 consultada na API; prévia preserva a base; confirmação explícita; nota 10.0 e referência recarregadas em ativo fictício 9903 | CVE encontrada não prova falha em equipamento real |
| Estados da base e sessão | Aprovados por HTTP / testes | JSON inválido → 503 sem novos arquivos; [] → 200 com mensagem vazia; falha só no risco preserva ativos em HTTP 200 (validacao_risco_http.json); Sair e Entrar novamente aprovados | Sair encerra sessão, não o servidor; não apaga dados |
| Windows WinError 5 | Investigação avançou; causa final aberta | Script mínimo: 3/1200 recusas em TEMP e 54/1200 no workspace; controle de handle reproduz o código | Capturar processo/I/O com privilégio adequado; sem atribuir a antivírus ou OneDrive por suposição |
| S3_09 — relatório original | Não localizado nas fontes consultadas | Página Notion e duas exportações Trello descrevem relatório e checklist concluído; o cartão não possui anexos nas duas exportações; busca dirigida por nomes em Downloads/Documentos sem resultado | Localizar arquivo original/recibo com o aluno. Não recriar retroativamente como evidência histórica |
| Branches / merges | Conferência concluída; comprovação acadêmica não localizada | Histórico Git completo (não shallow), 20 commits, 0 merges; API GitHub: 1 branch main e 0 PRs | Branches apagadas ou atividades externas não podem ser descartadas; não inventar histórico |
| S5_19 — apresentação | Material produzido nesta revisão | 6 slides PowerPoint com notas e roteiro de 300s; perguntas/respostas; gravação real de terminal Docker offline (44.27s) | Ensaio oral e revisão por colega dependem do aluno. A gravação não é sua apresentação oral |
| Acesso do docente / prazo | Acesso público comprovado; versão nova requer publicação | API GitHub sem credencial: private=false, visibility=public, main; prazo do enunciado 27/11/2026 | Não certifica a rede ou o login do docente; conferir SHA remoto após push |

## Modelo demonstrável

IDs (10,20,30,40): b=(10;7,5;9,8;0), x=(16,92;12,40;9,80;4,23).
x30=9,8; x20=7,5+0,5*9,8; x10=10+0,4*12,40+0,2*9,8;
x40=0+0,25*16,92. O peso 0,25 é participação de serviços; a indisponibilidade
observada é separada e não multiplica esse peso. Um cadastro vazio de ocorrências
e dependências pode ter risco zero, sem comprovar segurança do equipamento.

## Verificações e rastreabilidade

- Suíte Windows atual: 238 executados, 237 aprovados,
  1 symlink ignorado, 0 erros e 0 falhas; TEMP padrão.
- As suítes de 238 casos Linux/Compose da entrega 2e1195e permanecem
  identificadas em VALIDACAO_GESTAO_WEB.md. Repetições não são casos únicos novos.
- A gravação foi executada de verdade em imagem independente, --network none,
  --read-only e /tmp temporário; verificou recarga e o oráculo manual com asserts.
- Dados das validações são fictícios em contêiner separado, porta 8001. A base
  habitual da porta 8000 não foi usada para importação/remoção nem alterada.
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
