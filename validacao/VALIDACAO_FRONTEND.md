# Validação do frontend de consulta - 25/11/2026

## Escopo e versão

Base: commit `030cd59cd5390383de7b937e1bd44e444ab40ec6` no checkout oficial.
Este registro acompanha o commit que acrescenta as três etapas do frontend.
Não houve push, implantação na faculdade ou teste de 24 horas.

Implementação: Flask 3.1.3 com templates escapados e Waitress 3.0.2. Nenhum
arquivo do núcleo de POO, persistência, catálogo, NVD ou matemática foi alterado.
O exemplo web é o retrato persistido do lote fictício original, com teste de
correspondência. Nenhuma base real foi utilizada nas verificações.

## Etapa 1 - Consulta de ativos e riscos

A página lista quatro ativos, três vulnerabilidades e quatro dependências.
Mostra responsáveis, setores, tipos, ocorrências, vetores CVSS, fontes e pesos.

| ID | Risco próprio | Risco efetivo |
|---|---:|---:|
| 10 | 10,00 | 16,92 |
| 20 | 7,50 | 12,40 |
| 30 | 9,80 | 9,80 |
| 40 | 0,00 | 4,23 |

A leitura usa `BancoDeDados.consultar_ativos`; o cálculo usa `analisar_ativos`
sobre a mesma lista. A requisição não usa o construtor de recuperação.

## Etapa 2 - Estados e proteção da base

13 testes novos em `tests/test_app_web.py`, todos aprovados:

- Ativos, riscos por linha e detalhes, com consultas repetidas.
- Instabilidade matemática real: ativos e ocorrências continuam visíveis.
- Erro inesperado de cálculo: mensagem genérica, sem detalhes internos na página.
- JSON inválido, vazio em bytes, estrutura inválida e UTF-8 inválido: HTTP 503.
- Base ausente, diretório, permissão negada simulada e migração pendente: HTTP 503.
- `[]` válido: HTTP 200 e nenhum ativo cadastrado, sem chamar o cálculo.
- Escape de HTML vindo do JSON e cabeçalhos de proteção/cache.
- Métodos de escrita recusados e arquivos fora do diretório estático inacessíveis.
- Caminho fixado no servidor, domínio HTTP validado e releitura ao atualizar.
- Exemplo persistido equivalente ao lote fictício original.

As consultas são verificadas por comparação de nomes e bytes dos arquivos.
Os testes também impedem o construtor do banco, salvar, a trava de escrita e
`mkstemp`, para detectar tentativas de criação de backup/trava/temporário.
Não se trata apenas de verificar se um arquivo temporário sobrou ao final.

A distinção entre vazio e indisponível foi submetida a uma mutação controlada:
trocar `ativos is None` por `not ativos` fez o teste de base vazia falhar com
503 em vez de 200. O código original foi restaurado e os 13 testes passaram.

## Etapa 3 - Docker, Compose e navegador

- Windows, Python 3.11.15: 186 testes, sem falhas; 185 aprovados e um teste de
  link simbólico pulado pelo próprio teste porque o ambiente não permite criá-lo.
- Linux, Python 3.12.12 na imagem independente: 186 testes aprovados, sem skips.
  Apenas `/app/tests` foi montado como somente leitura; o código e os exemplos
  executados pertencem à imagem, sem montagem da raiz do checkout.
- Compose habitual: 186 testes aprovados na CLI via `run --rm -T inventario`.
- `docker compose -f docker/compose.yaml config --quiet`: aprovado.
- `frontend`: usuário `65534:65534`, filesystem somente leitura, nenhum volume,
  Waitress na porta 8000, publicada somente em `127.0.0.1:8000`.
- Imagem anterior preservada em `trabalho-ufu:030cd59` (`1f949157d0fe`).
- Imagem final `trabalho-ufu:local` e `trabalho-ufu:frontend-candidato`:
  `sha256:f365c46c34fada36a32c1a9c739ca773ab833622bb55e6dd9223695a46b8f71e`.

Navegador real: Edge 158.0.4370.33, perfil temporário e dados fictícios.
Verificados detalhes por mouse e teclado, atualização da consulta, ordem do
foco, estrutura acessível, ausência de erros/avisos no console e de requisições
com falha na consulta válida. Larguras verificadas: 320, 768, 1024 e 1440 pixels.
A página não transborda horizontalmente; a tabela possui rolagem própria.
Capturas de desktop e celular foram inspecionadas visualmente.

Os quatro estados também foram abertos pelo navegador em um servidor Waitress
temporário com base fictícia isolada: ativos com risco (200), ativos com risco
indisponível (200), inventário indisponível (503) e inventário válido vazio (200).
Os nomes e bytes dos arquivos foram preservados após cada navegação. O servidor
temporário foi encerrado. A demonstração do Compose permanece disponível.
As capturas e os scripts dessa verificação local ficam fora do repositório;
este relatório e os testes automatizados fazem parte da entrega clonável.

## Dependências e limites

Metadados públicos do PyPI consultados para as versões instaladas de Flask,
Waitress, Blinker, Click, ItsDangerous, Jinja2, MarkupSafe e Werkzeug: nenhum
alerta listado no campo `vulnerabilities`. Isso é uma consulta aos alertas
conhecidos do registro, não uma auditoria exaustiva de segurança.

Não foram validados leitor de tela real, outros navegadores/dispositivos,
exposição em rede, autenticação, carga de produção ou funcionamento por 24 horas.
O frontend não tem CRUD, nem consulta automática ao NVD. A exigência complementar
de CRUD web permanece pendente de confirmação com o docente. As falhas
intermitentes anteriores de gravação no Windows não foram diagnosticadas aqui.
