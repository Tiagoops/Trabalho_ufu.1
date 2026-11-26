# Validação de telas pequenas — 26/11/2026

Revisão sobre da65bfb. O commit que contém este relatório identifica a entrega.
Escopo: Chrome real em viewport 320×800 e 768×1024, com dados fictícios.
É validação dos casos descritos, não certificação universal de dispositivos,
navegadores ou acessibilidade. Não houve alteração de regras Python ou JSON.

## Defeito reproduzido e correção necessária

Na página `/ativos/10`, em 320 px, a largura útil era 305 px e o documento
chegava a 350 px. O botão “Cadastrar vulnerabilidade” saía do painel porque
o título e a ação estavam em linha flex sem quebra.

A única alteração funcional foi acrescentar `flex-wrap: wrap` à regra existente
`.titulo-secao` de `static/inventario.css`. O mesmo caso passou com documento
305 px, sem elemento fora da largura. Não foi usado overflow hidden para
esconder conteúdo. Os demais lugares que usam a regra também foram conferidos.

## Casos executados no navegador

| Tela / estado | 320 px | 768 px |
|---|---|---|
| Visão geral com cinco ativos fictícios | Aprovado | Aprovado |
| Lista e controles de busca de ativos | Aprovado | Aprovado |
| Cadastro de ativo | Aprovado; formulário preenchido e salvo | Layout aprovado |
| Detalhes de ativo | Aprovado após correção | Aprovado |
| Edição de ativo | Aprovado | Aprovado |
| Confirmação de remoção de ativo | Aprovado, sem confirmar exclusão | Aprovado, sem confirmar exclusão |
| Lista de vulnerabilidades | Aprovado | Aprovado |
| Avaliação por vetor e critérios CVSS 4.0 | Aprovado | Aprovado |
| Tela após submeter Avaliar e revisar | Layout aprovado, sem confirmar associação | Layout aprovado, sem confirmar associação |
| Lista de dependências | Aprovado | Aprovado |
| Cadastro e edição de dependência | Aprovado | Aprovado |
| Confirmação de remoção de dependência | Aprovado, sem confirmar exclusão | Aprovado, sem confirmar exclusão |
| Riscos, ranking e matriz A expandida | Aprovado | Aprovado |
| Página Importar JSON | Layout aprovado | Layout aprovado |
| Ajuda CVSS | Aprovado | Aprovado |
| Sessão encerrada | Aprovado | Aprovado |

São 16 rotas, com estados adicionais no formulário de vulnerabilidade e riscos.
As medições consolidadas estão em `evidencias_telas_pequenas_2026-11-26/medicoes_navegador.json`.
Com barra vertical, a largura útil foi 305/753 px; na tela curta de sessão,
320/768 px. Em todos esses casos finais, scrollWidth=clientWidth.

Botões e campos ficaram dentro da página; navegação quebrou em linhas. Capturas
representativas foram inspecionadas na sessão, incluindo topo e fim do formulário
CVSS. Tabelas largas mantiveram rolagem interna, sem ampliar a página. Em 320 px,
o gesto de rolagem da ferramenta deslocou a tabela cerca de 345 px enquanto
a página manteve scrollLeft=0, expondo as colunas de risco.

O cadastro do ativo 9501 foi feito de verdade pelo formulário em 320 px, com
sucesso. Sair encerrou a sessão; Entrar novamente recarregou cinco ativos
fictícios. As prévias e páginas de remoção foram examinadas sem confirmar mudanças.

## Ambiente e limites da evidência

O ensaio usou dois contêineres exclusivos, portas loopback 52258/52259 e uma
pasta fictícia, sem montar a base real. O segundo contêiner serviu o CSS corrigido
por montagem somente leitura. A imagem candidata final tem o mesmo CSS:
`sha256:03036fab9716560ccbb02fbe00963654b2d0c2853083af407e85ae709c765be7`.
SHA256 do CSS: `723f26a543298bfd1fd5bc3a2dd7aa984ca4345714d30391652d9877925f6602`.

A ferramenta teve uma interrupção durante uma sequência; os casos afetados
foram observados novamente antes de serem aprovados. Após concluir os casos,
o controle Windows perdeu acesso ao cursor; a restauração final da dimensão
temporária não pôde ser confirmada. Não foi feita tentativa de contornar a
restrição do Windows. Isso não representa erro da aplicação.

Este registro conserva as medições; não inclui arquivos de screenshot. Não
foram testados dispositivos físicos, gestos touch, outros navegadores, zoom
200% ou uma auditoria WCAG completa. O seletor nativo de upload e o envio por
esse diálogo continuam pendentes; somente o layout da página foi aprovado.
NVD ao vivo e download CSV não foram repetidos nesta rodada.

## Testes e preservação

As suítes completas foram executadas novamente após a correção: Windows,
280 executados (279 aprovados, 1 omitido), em 33,734 s; Linux independente,
280 executados (278 aprovados, 2 omitidos), em 16,361 s. Nenhuma falha ou erro
final. As omissões são de plataforma. A suíte Linux usa a imagem candidata,
rede desabilitada, raiz somente leitura e dados temporários fictícios.

A base da apresentação permaneceu idêntica, SHA256
`8fb968248a95733c06dfe5c938901cac25790ec5454f51ff7c9830a33b736763`.
O Dockerfile da raiz e `tatus --short` permanecem fora do commit. A atualização
da imagem habitual foi concluída: início, metadados, ativo 70 e risco responderam
HTTP 200; o CSS servido coincidiu com o arquivo validado. O launcher reconheceu
a mesma base, com sete ativos preservados e risco 70=(0;7,35). Registro em
`evidencias_telas_pequenas_2026-11-26/previa_habitual.json`. A imagem anterior
foi preservada em `trabalho-ufu:antes-telas-0b8b900`. Os contêineres fictícios
foram parados, com os dados de ensaio preservados.

Não houve implantação docente, execução de 24h, apresentação oral nem push.
Os relatórios anteriores permanecem como histórico de suas respectivas rodadas.
