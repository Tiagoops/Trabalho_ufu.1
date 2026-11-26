# Matriz de evidências — revisão de 26/11/2026

Checkout oficial: C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT
Código validado: correções de IDs/migração e quebra de títulos em telas pequenas; 280 testes por ambiente. O commit que contém esta matriz identifica a entrega; rodadas anteriores preservadas no histórico.
Repositório: https://github.com/Tiagoops/Trabalho_ufu.1
Referência remota conferida antes desta etapa: bd1eacd, publicado com autorização específica. As novas alterações exigem novo push autorizado; não presumir que já estão no GitHub.

Fonte acadêmica: Trabalho_2.pdf, Tabela 1 e seção 5. Pesos 20/20/45/15 são do
atendimento aos requisitos, não percentuais diretos da nota final. O enunciado
exige demonstração do programa em cinco minutos; slides são apoio solicitado
no cartão S5_19 e pelo autor. IA não substitui o domínio oral do aluno.

| Requisito / atividade | Estado atual | Evidência verificável | Limite / próxima ação |
|---|---|---|---|
| POO e objetos individuais — 20% | Implementado e testado | modelos.py: fábrica, subclasses, orientacoes_tratamento e recarga; tests/test_modelagem_oo.py; tests/test_integracao_poo_integridade.py | Ensaio oral do aluno ainda necessário |
| Lista JSON de objetos — 20% | Implementado e testado | banco_dados.py: consultar_retrato e salvar; to_dict/from_dict; testes de rollback, identidade e concorrência | Retentativas limitadas, conflito e rollback validados; permissão permanente continua sendo erro |
| Contêiner e 24h no servidor — 45% | Configuração local comprovada; implantação e 24h abertas | docker/compose.servidor.yaml, healthcheck, volume nomeado e persistência após recriar; 280 testes por ambiente; VALIDACAO_ETAPAS_1_4.md | Aguardando endereço, acesso e identificação docente; teste local não comprova servidor nem 24h |
| Risco próprio/efetivo — 15% | Implementado e testado | servico_risco.py e matematica/risco.py; M, v, A, b=Mv, solve, rho, condição e resíduo; oráculo manual | Índice não é probabilidade nem percentual; não inventar fatores para demonstrar POO |
| Frontend, opções 0–14 | Layout validado no Chrome em 320/768 px nos casos registrados | 16 rotas nas duas larguras; cadastro fictício, critérios/prévia CVSS, expansão e rolagem de tabelas, Sair/Entrar; VALIDACAO_TELAS_PEQUENAS.md | Upload nativo ainda não concluído; dispositivos físicos e outros navegadores não testados |
| Importação JSON | HTTP/testes e layout 320/768 px aprovados; upload nativo pendente | Prévia sem escrita e rejeições cobertas; página de importação medida no navegador | A validação de layout não certifica a seleção e envio pelo diálogo nativo |
| CSV | Download Chrome aprovado na rodada anterior | relatorio_ensaio.csv com duas ocorrências fictícias; link de exportação na navegação responsiva | Download não repetido nesta rodada de layout |
| NVD pela nova interface | Fluxo HTTP real aprovado | CVE-2021-44228 consultada na API; prévia preserva a base; confirmação explícita; nota 10.0 e referência recarregadas em ativo fictício 9903 | CVE encontrada não prova falha em equipamento real |
| Estados da base e sessão | Aprovados por HTTP / testes | JSON inválido → 503 sem novos arquivos; [] → 200 com mensagem vazia; falha só no risco preserva ativos em HTTP 200 (validacao_risco_http.json); Sair e Entrar novamente aprovados | Sair encerra sessão, não o servidor; não apaga dados |
| Windows WinError 5 | Recuperação do inventário e migração validada | Retry compartilhado; teste antigo distingue fase da falha; controles transitório, permanente, conflito e handle nativo; tests/test_migracao_windows.py | Processo externo histórico não identificado; permissão permanente segue sendo erro |
| Bases CLI/web | Unificadas e conferidas | dados/inventario.json; dois serviços usam /dados; seletor encaminha CLI ao frontend ativo; sete registros idênticos ao backup | Volume antigo preservado; não há mesclagem automática nem garantia entre escritores Windows/Linux simultâneos |
| Identidade antes do reuso web | Corrigida e validada | GET /metadados, protocolo 1; caminho canônico identificado sem expô-lo; porta e montagem Docker conferidas; bases distintas com bytes iguais recusadas por HTTP real | Instância antiga sem metadados precisa ser reiniciada; protocolo não é autenticação |
| Honeypot no cadastro | Implementado e validado | Campo website oculto por CSS; preenchimento retorna 400 antes de abrir a base; vazio/ausente mantém cadastro; tests/test_cadastro_web.py | Proteção complementar: não detecta bots que deixam o campo vazio |
| IDs de ocorrência em links | Corrigido | Validação compartilhada recusa segmentos de caminho/controles antes de importar; IDs válidos preservados; tests/test_ids_ocorrencias_web.py | Não renomeia dados automaticamente; base incompatível exige correção explícita |
| S3_09 — material de estudo | Localização esclarecida pelo autor; não é documento exigido na apresentação | Autor informou material no caderno; PDF, página 3, seção 5.B dispensa documento adicional; VALIDACAO_ETAPAS_5_6.md | Caderno não inspecionado; não certifica exercícios nem avaliação diária |
| Branches / merges / PR / CI | Conferência atual concluída; evidências da sprint não encontradas | Checkout não shallow: 25 commits antes da revisão, 0 merges; API pública: 1 main, 0 PRs e 0 workflows, sem paginação; conferencia_academica.json | S3_08 é estudo/avaliação diária; não fabricar histórico nem confundir com requisito extra da Tabela 1 |
| S5_19 — apresentação | Material existente e ensaio funcional registrado | Slides/roteiro anteriores e VALIDACAO_ETAPAS_1_4.md, tópico 3 | Ensaio oral de 5 minutos e revisão por colega dependem do aluno; ensaio funcional não os substitui |
| Acesso do docente / prazo | Acesso público anônimo confirmado | API GitHub HTTP 200 sem credencial, private=false, main=bd1eacd; prazo 27/11/2026; conferência das etapas 5–6 | Novos commits ainda dependem de push autorizado; rede do docente não testada |

## Modelo demonstrável

IDs (10,20,30,40): b=(10;7,5;9,8;0), x=(16,92;12,40;9,80;4,23).
x30=9,8; x20=7,5+0,5*9,8; x10=10+0,4*12,40+0,2*9,8;
x40=0+0,25*16,92. O peso 0,25 é participação de serviços; a indisponibilidade
observada é separada e não multiplica esse peso. Um cadastro vazio de ocorrências
e dependências pode ter risco zero, sem comprovar segurança do equipamento.

## Verificações e rastreabilidade

- Suítes atuais: 280 executados no Windows (279 aprovados, 1 omitido) e Linux
  independente (278 aprovados, 2 omitidos), sem erros/falhas finais. Relatório
  VALIDACAO_ETAPAS_1_4.md. Histórico da rodada anterior: 271 executados, 270
  aprovados e 1 ignorado por plataforma em cada ambiente. Logs e HTTP
  real em evidencias_json_status_2026-11-26/. A primeira execução Windows teve
  uma falha em teste antigo de retomada de migração; passou nas 15 repetições
  isoladas e na suíte final. Causa exata não capturada; testes não enfraquecidos. A rodada anterior de 250 casos em Compose
  isolado permanece identificada em VALIDACAO_BASE_UNICA.md.
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

26/11/2026, correção de identidade: endpoint de metadados sem escrita e validação
obrigatória antes do reuso. Comprovada a mesma base Windows/Docker por publicação
e bind; rejeitada outra base com JSON idêntico. Honeypot da etapa anterior incluído.
O item 1 da auditoria foi corrigido; os itens 2–4 permanecem pendentes. Não há
comprovação de 24 horas nem implantação docente concluída nesta etapa.

26/11/2026, itens 2 e 4 da auditoria: validação JSON integral no modelo compartilhado,
incluindo campos extras, números finitos e UTF-8; erros de inicialização propagados
com código 1 nas duas entradas. HTTP real recusou cinco lotes inválidos sem gravar,
exibiu 503 para bases inválidas e preservou acentos/emojis no lote válido. Teste
Docker sem permissão terminou com status 1. A intermitência de migração Windows foi
registrada sem alegar causa confirmada ou solução por repetição. O item 3 continua
pendente. Implantação docente e 24 horas permanecem sem comprovação.

26/11/2026, etapas 1–4: IDs inseguros recusados, migração com retry compartilhado
e teste de falha fortalecido. Ensaio Chrome registrado no tópico 3 do relatório;
CSV aprovado, upload visual bloqueado pela extensão. Compose de servidor passou
localmente com volume fictício e recriação persistente; implantação depende dos
dados de acesso solicitados. A causa externa histórica e as 24h não foram comprovadas.

26/11/2026, etapas 5–6: autor informou o S3_09 no caderno; PDF 5.B dispensa
documento adicional na apresentação. Acesso público anônimo e histórico Git
reconferidos; sem PR/workflow encontrado. O controle do navegador encerrou a
tentativa visual por não identificar a URL Windows com segurança. Upload e
telas pequenas continuam parciais; 10 testes existentes passaram. Ver
VALIDACAO_ETAPAS_5_6.md. Não há mudança de código, push ou implantação.

26/11/2026, telas pequenas: reproduzido overflow de 350 px em largura útil
de 305 px no detalhe do ativo. Uma propriedade flex-wrap no título corrigiu
o vazamento; 16 rotas passaram em 320/768 px, com tabelas rolando dentro de
seus contêineres. Suítes de 280 testes Windows/Linux aprovadas com omissões
de plataforma. Registro em VALIDACAO_TELAS_PEQUENAS.md. Upload nativo,
implantação docente, 24h e ensaio oral permanecem pendentes.
