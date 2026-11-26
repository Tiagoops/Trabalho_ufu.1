# Etapas 1 a 4 — 26/11/2026

Base da revisão: bd1eacd. O commit que contém este relatório identifica o código
entregue. Este relatório separa testes locais, ensaio funcional e implantação.

## 1. IDs de vulnerabilidade usados em links — corrigido

IDs importados como `../outra`, `a/b`, `a\b`, `.`/`..` e caracteres de controle
podiam produzir links de edição/remoção incompatíveis com as rotas. A validação
agora ocorre em `Vulnerabilidade.from_dict`, antes de aceitar a base ou prévia.
Não há renomeação automática de registros. UUID, acentos, espaços, `legado:1`,
`falha.v2` e `id%2Ftexto` mantêm identidade e links funcionais.

Teste de regressão: `tests/test_ids_ocorrencias_web.py`. A importação inválida
retorna 400 sem prévia nem alteração de arquivos. Uma base já contendo ID
incompatível fica indisponível e exige correção explícita, em cópia com backup.

## 2. Falha intermitente de migração Windows — mecanismo reproduzido e protegido

Nas 60 repetições instrumentadas anteriores à mudança não houve recusa espontânea.
Um WinError 5 controlado na primeira troca da base reproduziu a assinatura da
falha antiga: o teste aceitava qualquer OSError e confundia essa fase com a falha
de confirmação do manifesto que pretendia provocar. Agora exige a mensagem dessa
falha específica; todas as verificações de conteúdo, backup e retomada continuam.

A migração passa a reutilizar a mesma troca atômica do inventário: até seis
tentativas para erros Windows 5/32/33, espera total programada de 820 ms e nova
conferência de conteúdo antes de repetir. Mantém temporário exclusivo, fsync,
limpeza e erro em recusa permanente. Conflitos são apresentados pela CLI com
status 1. Não houve mudança de ACL, exceção de antivírus ou exclusão prévia da base.

Foram aprovados controles de recusa transitória, permanente, alteração externa,
retomada e handle nativo sem compartilhamento de exclusão liberado durante a
espera. O mesmo controle que antes fazia o teste falhar passou após a correção.
O processo/filtro responsável pela ocorrência histórica espontânea NÃO foi
identificado. Recuperação comprovada não significa causa externa eliminada.

## 3. Resultado do ensaio funcional

Ambiente independente: imagem `trabalho-ufu:ids-migracao-candidato`, ID
`sha256:4393f1bd64e80fa784ea2967877c6b820a0738796f09a6a42620587320eaf1c9`.
Chrome acessando contêiner somente em loopback, porta fictícia 52255, com pasta
de dados exclusiva. Nenhuma operação do ensaio usou a base da apresentação.

| Ação executada no navegador | Resultado observado |
|---|---|
| Base válida vazia | “Nenhum ativo cadastrado”, contadores zerados |
| Cadastro 701 Notebook e 702 Servidor | Mensagens de sucesso, dois ativos recarregados, orientações específicas das classes |
| Cadastro de duas vulnerabilidades por vetor | Prévia sem gravação, notas 9,80 e 7,50; associação somente após confirmar |
| Dependência 701 → 702, 1 serviço de 4 | Peso 0,25 salvo e direção exibida corretamente |
| Cálculo | b=(9,8;7,5), x=(11,675;7,5), rho=0 e resíduo=0; bate com 9,8+0,25×7,5 |
| Edição de ativo e ocorrência | Hostname/descrição alterados; UUID, vetor, nota e dependência preservados |
| Exportar CSV | Clique baixou duas ocorrências, ordenadas 9,8 e 7,5; conteúdo conferido no arquivo |
| Remover ocorrência 701 | Exigiu confirmação; b701=0 e x701=1,875 após recálculo |
| Remover fornecedor 702 | Exibiu o dependente afetado, removeu vínculos e ocorrência; restou 701 com risco zero |
| Busca por trecho | Encontrou somente `demo-ensaio-701-editado` |
| Sair / Entrar novamente | Mostrou sessão encerrada e recarregou dados preservados |
| Importar JSON pelo seletor | BLOQUEADO: extensão Chrome sem acesso a URLs de arquivos; não certificado visualmente |

Complemento HTTP real, separado do resultado visual: lote com ID inseguro retornou
400 sem modificar arquivos; lote válido gerou prévia sem escrita; confirmação
adicionou 703 com ID `legado:703` preservado e edição HTTP 200. Não substitui o
teste do seletor nativo. O upload não foi habilitado por alteração de permissões.

Ocorreram timeouts do controle do Chrome; a tela foi relida antes de continuar.
O console registrou uma mensagem de canal assíncrono fechado na página de upload.
A aplicação não carrega scripts JavaScript; isso é compatível com interferência
de extensão, sem atribuição conclusiva. Nenhum travamento da aplicação foi
observado nos fluxos concluídos. Telas pequenas, NVD ao vivo e ensaio oral
cronometrado do aluno não foram repetidos nesta rodada. Este ensaio é funcional,
não uma certificação da apresentação oral de cinco minutos.

## 4. Implantação no servidor — configuração pronta; acesso pendente

`docker/compose.servidor.yaml` exige projeto, imagem versionada e porta explícitos.
Usa o iniciador web contínuo, volume nomeado, usuário 65534, raiz somente leitura,
publicação loopback e healthcheck de `/metadados`. Não altera o Compose habitual.
Sem reinício automático: uma queda permanece visível; healthcheck sozinho não
reinicia o processo e não comprova 24 horas.

Validação local em projeto `ufu-validacao-servidor-20261126`, porta fictícia
52256: cadastro HTTP 704, dono/gravação do volume, recriação do contêiner com JSON
idêntico, raiz protegida e healthcheck aprovado. O primeiro verificador consultou
cedo demais após recriar; foi corrigido para aguardar `compose up --wait` e passou.
O teste não foi implantado no servidor docente e não executou 24 horas.

Faltam endereço, método de acesso, matrícula/identificador, porta e localização
da versão enviada. Foram solicitados sem senha/chave privada. O acompanhamento
S5_20 informa `trab02_2026_2_MATRICULA` e porta 2000 + três últimos dígitos, ainda
sujeitos à confirmação no servidor do docente. Ver instruções em OPERACAO.md.

## Verificação e preservação

- Windows: 280 executados, 279 aprovados, 1 omitido por plataforma, 41,526 s.
- Linux independente: 280 executados, 278 aprovados, 2 omitidos por plataforma,
  22,931 s; rede desabilitada, raiz somente leitura e dados fictícios.
- Dois controles de mutação (validação de ID e condição de retry) fizeram os
  respectivos testes falharem; fontes restauradas antes das suítes finais.
- Base operacional permaneceu idêntica, SHA256
  `8fb968248a95733c06dfe5c938901cac25790ec5454f51ff7c9830a33b736763`.
- Evidências resumidas e logs: `evidencias_etapas_1_4_2026-11-26/`.
- Prévia habitual atualizada para a imagem validada; HTTP 200 em início, metadados,
  ativo 70 e seu risco. Launcher reconheceu a mesma base; sete ativos preservados,
  b70=0 e x70=7,35. Retorno disponível em
  `trabalho-ufu:antes-ids-migracao-bd1eacd`. Ver `previa_habitual.json`.
- Contêineres fictícios foram parados após o ensaio; dados e volume preservados.
- `Dockerfile` da raiz e `tatus --short` permanecem fora do commit.

Não há garantia de ausência de todo defeito, de recuperação de permissão
permanente, de escritores Windows/Linux simultâneos ou de durabilidade sob
queda de energia. Implantação e 24h continuam requisitos acadêmicos abertos.
