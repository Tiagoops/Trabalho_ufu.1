# Correção Windows e base compartilhada — 26/11/2026

Escopo autorizado: recuperar gravações transitórias, unificar as bases usadas
pela CLI e pela interface e manter a apresentação somente neste computador.
Código aplicado sobre `ee855b7`; esta correção e suas evidências formam um commit
local. Não houve push, implantação na faculdade nem ensaio de 24 horas.

## Gravação e limites

`BancoDeDados.salvar` conserva temporário exclusivo, flush/fsync, substituição
atômica e rollback. Somente PermissionError do Windows com código 5, 32 ou 33
recebe até seis tentativas. Os cinco intervalos são 10/30/80/200/500 ms: 820 ms
acumulados de espera programada, além do tempo de I/O e do agendamento do SO.
Cada tentativa recuperável gera aviso; o mesmo temporário é reutilizado.

Após a espera, a assinatura dos bytes atuais é conferida novamente. Uma mudança
externa encerra a operação como conflito. Não há remoção prévia do original,
escrita direta sobre ele, alteração de ACL ou desativação de proteção. Erro
permanente continua sendo erro, sem anunciar sucesso e com rollback em memória.
O processo/filtro responsável pelas recusas espontâneas não foi identificado.
O diagnóstico anterior está preservado em DIAGNOSTICO_WINDOWS.md.

| Ensaio com dados fictícios | Resultado |
|---|---|
| Windows TEMP, 2.000 gravações | 6 bloqueios recuperados; 0 falhas finais; JSON relido; 0 temporários restantes |
| Windows workspace OneDrive, 2.000 gravações | 12 bloqueios recuperados; 0 falhas finais; JSON relido; 0 temporários restantes |
| Linux Docker, bind no Windows, 500 gravações | 0 falhas finais |
| Handle nativo Windows sem FILE_SHARE_DELETE | Bloqueio reproduzido; liberação durante a espera permite salvar |
| Negativa persistente simulada | Seis tentativas; exceção mantida; JSON e memória anteriores preservados |
| Alteração externa durante espera | Conflito recusado; alteração externa não sobrescrita |

São medições desta execução, não garantia de zero falhas futuras. A proteção
de concorrência continua sendo entre processos cooperantes no mesmo SO.

## Uma base para as interfaces

O caminho padrão é `dados/inventario.json`, relativo à raiz do projeto,
independentemente do diretório de onde o Python é executado. `configuracao.py`
centraliza essa decisão sem escrever arquivos. `INVENTARIO_ARQUIVO` continua
permitindo configurar explicitamente outro caminho.

No Compose, ambos os serviços montam `../dados` em `/dados` e usam
`/dados/inventario.json`. Com o frontend Docker ativo, a opção 2 do seletor local
e `main.py --terminal` executam a CLI no mesmo contêiner. Assim, os escritores
compartilham o mecanismo Linux de trava; a falha dessa ponte não abre outra base
silenciosamente. Sem frontend Docker ativo, os iniciadores nativos compartilham
o caminho do computador. Não force escritores Windows e Linux simultâneos com
uma configuração explícita de caminho.

Uma instalação nova começa com `[]`, não copia exemplos sobre cadastros. Bases
existentes, inclusive inválidas, não são substituídas na inicialização. As
consultas continuam sem criar backup, trava ou temporário. `--demo` mantém seu
cenário fictício temporário. A pasta `dados/` está fora do Git e da imagem.

Na conferência anterior à migração, `ativos_db.txt` e
`dados_web/inventario.json` não existiam neste checkout. A base ativa estava no
volume `docker_frontend_dados`. Com o serviço parado, seus bytes foram copiados
para a base compartilhada e validados; não foi necessária mesclagem. O volume
antigo foi preservado como cópia anterior, sem sincronização posterior.
Os sete IDs preservados são 10, 20, 30, 40, 70, 88 e 9001.

SHA-256 antes/depois:
`8fb968248a95733c06dfe5c938901cac25790ec5454f51ff7c9830a33b736763`.
Backups e o registro intermediário do incidente abaixo permanecem fora do Git,
no workspace local `outputs/correcao_local_2026-11-26/`.

## Incidente de isolamento durante a validação

Uma primeira execução da suíte pelo Compose herdou `INVENTARIO_ARQUIVO` da base
operacional em subprocessos de `TestExecucaoIsolada`. Dois registros fictícios,
IDs 1 e 2, foram inseridos inadvertidamente; três testes falharam ao procurar os
arquivos em suas pastas temporárias. Isso foi uma falha da validação.

O frontend foi parado e a base de nove registros foi guardada. Os sete registros
originais foram comparados integralmente com o backup; somente os dois registros
comprovadamente criados pelos testes foram removidos. O arquivo final voltou a
ser idêntico, byte a byte, ao backup de sete registros e ao SHA acima.

A fixture agora remove essa variável dos subprocessos isolados. O comando de
ensaio documentado também substitui `/dados` por uma pasta fictícia exclusiva e
monta `/app` somente para leitura. A repetição passou com 250 casos, sem alteração
da base operacional. Não usar o volume da apresentação como área de testes.

## Suítes, HTTP e imagem

| Ambiente | Executados | Aprovados | Ignorados | Falhas/erros |
|---|---:|---:|---:|---:|
| Windows Python 3.11, TEMP padrão | 250 | 249 | 1 symlink | 0 |
| Imagem Linux independente, somente tests/ montado | 250 | 249 | 1 controle nativo Windows | 0 |
| Compose com /dados fictício exclusivo e /app somente leitura | 250 | 249 | 1 controle nativo Windows | 0 |

São os mesmos casos em plataformas distintas, não 750 testes únicos.
A condição nova de elegibilidade da retentativa foi invertida propositalmente:
o teste de bloqueio transitório falhou. O arquivo foi restaurado exatamente e
a suíte Windows voltou a passar. Nenhuma verificação foi removida para aprovar.

O fluxo HTTP real no Waitress nativo Windows, com base fictícia exclusiva e
porta loopback temporária, validou cadastro de dois ativos, severidades 9.8/7.5,
dependência 0.25, risco efetivo 11.675, edição refletida na CLI, remoção com limpeza
de vínculos, CSV e Sair/Entrar. O servidor de ensaio foi encerrado.

No serviço habitual, nove consultas HTTP responderam 200, incluindo os ativos
70 e 88, cadastro, importação e riscos. O risco próprio do ativo 70 é 0 e o efetivo
é 7.35, recebido pela dependência 30 com peso 0.75. Essas consultas não alteraram
os bytes nem o conteúdo do diretório. O terminal iniciado no host também encontrou
o ativo 70 pela ponte Docker sem criar os antigos arquivos de base.

Imagem habitual: `trabalho-ufu:local`, ID
`sha256:90b8258a15694c2b52a19f84f80ce31da9a31202b71b82ee7482015c0539e766`.
Imagem anterior preservada: `trabalho-ufu:antes-base-unica-9ecd038c1be6`.
O frontend monta somente dados, usa usuário sem privilégios e raiz somente leitura.
A publicação no host é exclusivamente `127.0.0.1:8000`; o bind interno do contêiner
em 0.0.0.0 não publica a aplicação na rede do computador.

Os arquivos em `evidencias_base_unica_2026-11-26/` guardam saídas das suítes,
resumos HTTP, stress, conferência final e a mutação rejeitada. Os scripts de
ensaio e backups estão na pasta local indicada acima. O layout e os templates
não foram alterados nesta correção; não houve nova certificação visual de upload
ou telas pequenas. Acesso remoto, implantação docente, 24h, ensaio oral e push
continuam pendentes conforme a matriz.
