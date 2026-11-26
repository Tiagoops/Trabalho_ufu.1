> Registro histórico: a configuração de bases deste documento foi substituída
> em 26/11/2026. CLI e web agora compartilham `dados/inventario.json`.
> Resultados atuais: [VALIDACAO_BASE_UNICA.md](VALIDACAO_BASE_UNICA.md).

# Paridade da interface gráfica — 25/11/2026

## Escopo entregue

As três etapas cobrem o menu 0–14 sem mudar o modelo matemático:

1. Ativos e sessão: busca por ID, hostname exato e trecho, detalhes, edição,
   remoção confirmada com limpeza dos vínculos, orientações polimórficas e Sair.
2. Vulnerabilidades: cadastro, edição e remoção por ID estável; questionário
   CVSS 4.0, vetor Base 3.1/4.0, catálogo local e consulta NVD por ID de CVE.
   Referências exigem confirmação de aplicabilidade. Cadastro inicial pode
   reunir várias ocorrências em rascunho, gravando tudo somente ao concluir.
3. Dependências por critérios, tempos observados, risco individual e ranking,
   M/v/A/b/x e diagnóstico numérico, relatório CSV e importação JSON confirmada.

A navegação mantém botões e formulários, layout branco/laranja e campos de
inteiros em texto com teclado numérico, sem controles de aumentar/diminuir.
O CSV e a importação compartilham lógica com o terminal. Não foram adicionadas
dependências Python. `interface_web/` organiza rotas por responsabilidade.

## Verificações executadas

- 238 testes na imagem Linux independente, montando somente `tests/` para leitura.
  O código da aplicação veio dos COPY de `docker/Dockerfile`, sem montagem de /app.
- Windows: 238 testes executados com TEMP/TMP em uma pasta isolada no workspace;
  237 passaram e 1 verificação de symlink foi ignorada pela limitação do ambiente.
- No TEMP padrão do Windows ocorreram duas falhas WinError 5 em os.replace,
  em testes distintos de persistência já existentes. O primeiro caso passou
  isoladamente. A causa externa continua sem confirmação; não foram incluídas
  tentativas silenciosas nem enfraquecidos rollback e exceções. O método salvar
  não foi alterado nesta entrega.
- Testes HTTP cobrem busca, CRUD, todos os modos CVSS, rascunho inicial, NVD
  simulado com/sem vetor e falha de rede, confirmação, token alterado, formulário
  desatualizado, CSV com fórmula, importação inválida/duplicada/grande, gravação
  interrompida e sessão encerrada. Somente dados fictícios.
- Consultas são verificadas sem construtor gravável e sem novos arquivos.
  Base inválida é inventário indisponível (503); base vazia válida tem mensagem
  própria. Falha só no risco mantém os ativos disponíveis (200).
- Revisão de segurança: CSRF nas mutações, escape HTML, cabeçalhos existentes,
  modo somente consulta, upload limitado a 1 MiB sem arquivo intermediário,
  prévias assinadas com expiração de 15 min e vínculo à sessão/revisão da base.
- Prova de sensibilidade: a inversão temporária da condição de confirmação
  fez o teste de remoção falhar. O arquivo original foi restaurado e verificado.
- Compose habitual: 238 testes passaram, 12 rotas HTTP responderam 200, imagem
  `trabalho-ufu:local` atualizada. Base preservada byte a byte, SHA-256
  `D9E004114441419BB6422BBE40E878AD05240E47110EE1421EE3ED9258511649`.
  Imagem anterior: `trabalho-ufu:antes-gestao-06df68770d21`.
- Navegador no Compose habitual: Sair exibiu Sessão encerrada; Entrar novamente
  retornou à visão geral com os seis registros preexistentes. Screenshot final
  salvo fora do Git no diretório de evidências local.
- Navegador real, contêiner isolado: cadastro do ativo fictício 9902, avaliação
  por vetor (9,8), associação após prévia, dependência 1/4 e risco individual
  direto 9,8 / propagado 12,25. Verificação visual da página e da navegação.
  O upload pela automação do navegador travou; esse fluxo foi validado por HTTP,
  não considerado concluído visualmente nessa tentativa.

## Operação e limites

Sair encerra a sessão do navegador; não apaga dados e não encerra o servidor.
Entrar novamente cria uma nova sessão de formulários. Ctrl+C ou Compose stop
encerra o servidor. Não há autenticação: a configuração continua em loopback.
As bases de CLI, iniciador local e Compose permanecem separadas por padrão;
nenhum dado foi migrado ou mesclado automaticamente.

A base do Compose habitual foi copiada para evidência local fora do Git antes da
recriação. A imagem anterior foi preservada para reversão. O hash dos dados foi
conferido após atualizar o contêiner. Não foram usados os cadastros habituais
nos testes de remoção/importação. A implantação na faculdade e o teste de
24 horas continuam para outra etapa. Nenhum push está autorizado nesta entrega.

Referências: [Flask Blueprints](https://flask.palletsprojects.com/en/stable/blueprints/),
[segurança Flask](https://flask.palletsprojects.com/en/stable/web-security/),
[uploads Flask](https://flask.palletsprojects.com/en/stable/patterns/fileuploads/),
[assinaturas com prazo](https://itsdangerous.palletsprojects.com/en/stable/timed/).

## Revisão de 26/11/2026

O diagnóstico avançou: substituições mínimas fora da aplicação reproduziram
WinError 5 / STATUS_ACCESS_DENIED em TEMP e no workspace. Um handle de leitura
do destino sem FILE_SHARE_DELETE reproduziu o mesmo erro; fechá-lo permitiu
a substituição. Esse controle demonstra uma condição, mas não identifica o
processo das recusas espontâneas. Não houve alteração em salvar nem retry.
Veja [DIAGNOSTICO_WINDOWS.md](DIAGNOSTICO_WINDOWS.md).

A suíte Windows atual passou em TEMP padrão: 238 executados, 237 aprovados e
1 symlink ignorado. A falha intermitente não foi considerada resolvida por isso.
Importação com prévia, download CSV, sessão, quatro estados de inventário/risco
e consulta NVD real pela rota web foram verificados por HTTP em contêiner
fictício separado. CVE-2021-44228 resultou em 10,0, com vetor NIST e confirmação
antes da associação. O seletor de arquivos da automação voltou a travar;
inspeção visual final e telas pequenas continuam parciais.

Foram preparados seis slides com notas, roteiro de 300 segundos, perguntas
para treino e gravação real de terminal Docker sem rede (44,27 s, 66 eventos,
saída 0). O ensaio oral do aluno e a revisão por colega continuam pendentes.
A matriz atual está em [MATRIZ_EVIDENCIAS.md](MATRIZ_EVIDENCIAS.md).
A revisão automática bloqueou o push por exigir autorização específica;
nenhuma publicação nova foi confirmada nesta revisão. Servidor e 24h seguem adiados.
