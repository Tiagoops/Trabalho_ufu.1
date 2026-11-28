# Execução superior a 24 horas no Docker da UFU

Conferência de 27/11/2026, horário de Brasília (UTC-03:00).

## Resultado e origem da evidência

A saída do terminal SSH fornecida pelo autor mostra o contêiner
`7f68bae94287` em execução por mais de 24 horas, com zero reinícios,
estado `running` e saúde `healthy`. A consulta final a `/metadados`
retornou HTTP 200 e `inventario_disponivel: true`.

Os comandos foram executados pelo autor no servidor e a saída foi enviada
na conversa para análise e registro. Este arquivo transcreve os trechos
relevantes dessa saída; não é uma coleta SSH realizada pelo assistente.
Não contém senha, chave privada nem conteúdo do inventário.

| Informação | Valor observado |
|---|---|
| Servidor / usuário SSH | `10.0.99.150` / `12621CBS229` |
| Contêiner | `trab02_2026_2_12621cbs229-frontend-1` |
| ID | `7f68bae94287` |
| Tag de imagem exibida | `trabalho-ufu:7340771-servidor` |
| Início UTC, informado pelo Docker | `2026-11-27T01:13:57.207726693Z` |
| Início em Brasília | 26/11/2026 às 22:13:57,207726693 |
| Horário do servidor na conferência | `2026-11-27T22:19:02-03:00` |
| Intervalo até esse horário | 86.704 segundos completos: **24h05min04s**, arredondado para baixo |
| Reinícios / estado / saúde | `0` / `running` / `healthy` |
| Data da resposta HTTP final | `Sat, 28 Nov 2026 01:19:29 GMT` = 27/11 às 22:19:29 em Brasília |
| Publicação observada | `0.0.0.0:2229->2229/tcp` |

O marco de 24 horas ocorreu em 27/11/2026 às 22:13:57,207726693 em
Brasília, antes da conferência. A checagem anterior enviada na mesma conversa
também mostrava o mesmo ID, o mesmo `StartedAt`, zero reinícios e saúde
`healthy`; a resposta HTTP anterior era de 27/11 às 22:59:53 GMT
(19:59:53 em Brasília).

## Transcrição da conferência final

```text
$ date --iso-8601=seconds
2026-11-27T22:19:02-03:00

$ sudo docker ps -a --filter "name=229"
CONTAINER ID   IMAGE                         COMMAND                  CREATED        STATUS                  PORTS                    NAMES
7f68bae94287   trabalho-ufu:7340771-servidor  "python -B iniciar_w…"   24 hours ago   Up 24 hours (healthy)   0.0.0.0:2229->2229/tcp   trab02_2026_2_12621cbs229-frontend-1

$ sudo docker inspect --format 'Inicio={{.State.StartedAt}} | Reinicios={{.RestartCount}} | Estado={{.State.Status}} | Saude={{.State.Health.Status}}' 7f68bae94287
Inicio=2026-11-27T01:13:57.207726693Z | Reinicios=0 | Estado=running | Saude=healthy

$ curl --max-time 10 --fail-with-body -i http://127.0.0.1:2229/metadados
HTTP/1.1 200 OK
Cache-Control: no-store
Content-Length: 150
Content-Security-Policy: default-src 'none'; style-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'; form-action 'self'
Content-Type: application/json
Date: Sat, 28 Nov 2026 01:19:29 GMT
Referrer-Policy: no-referrer
Server: waitress
Vary: Cookie
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-Inventario-App: inventario-ti

{"aplicacao":"inventario-ti","base_id":"21ad442013ced1f224c8884ca89f5850abbadf0438a2e4cc27d1e858950d56c4","inventario_disponivel":true,"protocolo":1}
```

## Alcance da conclusão

- O registro documenta mais de 24 horas de execução do contêiner segundo o
  relógio do servidor e os campos do Docker, com resposta funcional do endpoint
  de metadados no final. A indicação arredondada `Up 24 hours` não foi usada
  sozinha: a duração foi calculada com `StartedAt` e `date`.
- `healthy`, zero reinícios e HTTP 200 pontual não certificam disponibilidade
  HTTP ininterrupta durante todo o intervalo. O relatório final do monitor
  de 24 horas e suas amostras não foram fornecidos nem analisados nesta etapa.
- A imagem foi identificada pela tag exibida. Seu digest e a igualdade dos
  arquivos da implantação com o checkout não foram conferidos nesta etapa.
- Cadastro, alteração, exclusão, cálculo de risco, carga e acesso HTTP pelo IP
  externo não foram retestados nesta conferência. O endpoint valida a leitura
  da base, sem demonstrar todas as funções do projeto.
- A publicação observada usa todas as interfaces IPv4, diferente do loopback
  do Compose versionado. Firewall e controles de rede não foram auditados.

Este registro altera somente documentação. Não foi executado build, reinício,
recriação, atualização de imagem nem alteração da base no servidor. A publicação
do commit no repositório remoto é uma etapa separada.
