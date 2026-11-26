# Diagnóstico da substituição de arquivos no Windows — 26/11/2026

## Conclusão comprovada

O WinError 5 foi reproduzido em um programa mínimo, sem Flask, NumPy ou classes
do inventário. A sequência é criar temporário exclusivo, escrever JSON fictício,
flush/fsync, fechar o arquivo e chamar os.replace. O Windows negou algumas
substituições com NTSTATUS `0xC0000022` (`STATUS_ACCESS_DENIED`).

| Experimento | Substituições | Recusas |
|---|---:|---:|
| TEMP padrão, Python 3.11.15 | 1200 | 3 |
| Workspace OneDrive, mesmo Python | 1200 | 54 |
| Suíte atual, TEMP padrão | 238 testes / 256 substituições | 0 erros e 0 falhas |

A suíte passou com 237 aprovações e 1
teste de symlink ignorado. Isso não apaga as recusas do experimento mínimo e
não certifica o desaparecimento da falha. As contagens de stress são observações
desta execução, não probabilidades de falha em produção.

## Controle que reproduz a condição

Foi mantido aberto um handle de leitura do destino com FILE_SHARE_READ |
FILE_SHARE_WRITE, sem FILE_SHARE_DELETE. os.replace retornou o mesmo WinError 5
e o mesmo NTSTATUS. O JSON anterior ficou intacto. Depois de fechar o handle,
a substituição do arquivo fictício foi bem-sucedida.

Isso demonstra uma condição capaz de gerar o erro. **Não demonstra que esse
handle foi a causa de cada recusa espontânea**, nem identifica o processo que
estaria abrindo o arquivo. Origem e destino tinham atributo 32 (archive), sem
read-only; as sondagens de acesso DELETE posteriores à falha conseguiram abrir
os dois arquivos. Essas sondagens verificam o instante posterior, não o instante
exato da recusa.

## O que continua sem comprovação

O processo, filtro ou evento responsável pelas recusas espontâneas ainda não
foi capturado. OneDrive, Defender e indexador em execução não provam causalidade.
`fltmc filters` retornou acesso negado (0x80070005); não houve elevação administrativa,
desativação de proteção, alteração de ACL nem inclusão de exceção no antivírus.
Uma captura de I/O/Process Monitor, com privilégio adequado e filtro restrito à
pasta fictícia exclusiva, é o próximo passo para correlacionar abertura e rename.

## Decisão sobre o código

O método salvar não foi alterado. Não foi adicionado retry silencioso, remoção
prévia do JSON nem escrita direta sobre a base. Os testes de rollback e os
erros de gravação permanecem ativos. Até a captura conclusiva, o relatório
deve tratar o mecanismo como hipótese demonstrada por controle e a autoria da
interferência como pendência. A execução Linux em Docker é uma alternativa
operacional já testada, não uma correção da causa no Windows.

## Fontes e registros

- Microsoft: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-erref/596a1078-e883-4972-9bbc-49e60bebca55
- Microsoft: https://learn.microsoft.com/en-us/windows/win32/fileio/moving-and-replacing-files
- Microsoft: https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fscc/1d2673a8-8fb9-4868-920a-775ccaa30cf8
- Registros brutos e script: outputs/revisao_final_2026-11-26/ (workspace local).
- Resumo versionado: evidencias_2026-11-26/resumo.json.
