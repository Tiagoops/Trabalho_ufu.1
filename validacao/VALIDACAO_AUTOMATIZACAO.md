> Documento histórico. Para os comandos atuais, consulte o [README](../README.md). As evidências originais estão em `historico/`.

# Validação da automatização e exemplos CVE — 18/11/2026

## Resultado

Implementadas as três capacidades solicitadas: importação de biblioteca JSON; cálculo de severidades Base CVSS; cálculo de pesos por participação de serviços. A observação de indisponibilidade entre ativos foi mantida separadamente, conforme a escolha do usuário. Risco próprio e efetivo continuam sendo calculados pelas matrizes.

A versão continua somente local, sem commit ou push. A biblioteca real do usuário ainda não foi enviada; o formato de referência é uma lista JSON documentada no README. Não foram alterados os ativos reais.

## O que mudou

- `avaliacao.py`: cálculo Base CVSS 3.1/4.0 pela biblioteca cvss 3.6; critérios de serviços e observações de falha.
- `modelos.py`: preserva vetor/fonte da severidade, critérios e medições junto aos pesos; recusa divergência entre resultados e entradas técnicas.
- `banco_dados.py`: gravação conjunta dos critérios e pesos, limpeza de avaliações quando relações/ativos são removidos, rollback com referências a registros imutáveis preservadas.
- `biblioteca.py`: prévia e validação integral da biblioteca; calcula notas/pesos ausentes com os critérios; aceita avaliações externas com fonte; recusa colisões em vez de sobrescrever; insere o lote em uma gravação.
- `main.py`: cadastro e edição sem notas prontas; questionário técnico ou vetor CVSS; quantidades de serviços e tempos; opção13 de importação; `--demo` em base temporária. Termos risco próprio/direto e efetivo/propagado explicitados.
- Dockerfile e requirements: incluem novos módulos, exemplos e cvss==3.6.
- README: execução, formato, conceitos, fontes e limitações atualizados.

## Critérios aprovados e seus limites

O peso Aij é `servicos_fornecidos / total_servicos`. O total deve ser consistente para o mesmo ativo e cada serviço tem igual importância. Não há inferência automática de serviços redundantes, sobrepostos ou com criticidade desigual. Para mudar o total em diversos vínculos, remova/refaça as relações afetadas com o mesmo denominador.

A dependência integral de 100% resulta em 1 e é recusada porque o modelo anterior exige Aij<1. Não há ajuste artificial para 0,99. A estabilidade global rho(A)<1 continua obrigatória no cálculo de risco.

A indisponibilidade observada é `100 * minutos_indisponiveis / minutos_da_falha`. É uma observação registrada com fonte, não previsão, probabilidade ou comprovação causal. Não multiplica os pesos do modelo. Medição ausente continua desconhecida; não vira zero.

CVSS Base é calculado a partir das características fornecidas ou de vetores publicados; não é uma nota inferida do nome do equipamento. CVEs devem ser compatíveis com componente, versão e contexto. Registros anteriores sem critérios são preservados e identificados como anteriores, não recalculados por suposição.

## Exemplos reais de CVE em ativos fictícios

A fonte indicada pelo usuário foi https://www.cvefind.com/pt/cve.html. Foram usados três exemplos curados, confirmados na API NVD em 18/11/2026, sem copiar a lista inteira nem depender de login/API do CVE Find. Descrições foram resumidas. Vetores, fonte da avaliação, links, data de consulta e nota publicada estão em `exemplos/referencias_cve.json`.

| Ativo fictício | Componente hipotético | CVE | Nota Base recalculada |
|---|---|---|---|
| 10 aplicação | Apache Log4j Core 2.14.1 | CVE-2021-44228, Log4Shell | 10,0 |
| 20 servidor TLS | OpenSSL 1.0.1f | CVE-2014-0160, Heartbleed | 7,5 |
| 30 transferência | MOVEit Transfer 2023.0.0 (15.0.0) | CVE-2023-34362 | 9,8 |
| 40 estação | Nenhuma ocorrência cadastrada no cenário | Não presumir ausência de outras falhas | 0 próprio |

Fontes primárias:

- https://nvd.nist.gov/vuln/detail/CVE-2021-44228
- https://nvd.nist.gov/vuln/detail/CVE-2014-0160
- https://nvd.nist.gov/vuln/detail/CVE-2023-34362
- Endpoints oficiais `https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=...` registrados no arquivo de referências.
- OpenSSL confirma 1.0.1f afetado: https://openssl-library.org/news/secadv/20140407.txt.

Não foram instalados componentes vulneráveis, realizadas varreduras ou aplicadas essas ocorrências ao inventário real. A demonstração contém os vetores e contagens, sem preencher notas/pesos no JSON de entrada; a importação calcula os valores.

## Conferência matemática independente

Linhas/colunas dos ativos: 10,20,30,40. Colunas de M: Heartbleed, Log4Shell, MOVEit, ordenadas pelos IDs das ocorrências.

```text
M = [[0,1,0],
     [1,0,0],
     [0,0,1],
     [0,0,0]]
v = [7.5,10,9.8]
A = [[0,0.4,0.2,0],
     [0,0,0.5,0],
     [0,0,0,0],
     [0.25,0,0,0]]
b = [10,7.5,9.8,0]
x = [16.92,12.4,9.8,4.23]
```

Substituição com frações exatas conferida:
x30=9,8; x20=7,5+0,5×9,8=12,4; x10=10+0,4×12,4+0,2×9,8=16,92; x40=0,25×16,92=4,23. Resíduo exato zero. Um ativo sem ocorrência cadastrada pode receber risco por dependências.

A falha fictícia do ativo 20 dura 120 min; o ativo 10 fica indisponível 30 min, produzindo 25% observados. O peso dessa relação continua 2/5=0,4.

## Validações realizadas

- **Windows:134 testes aprovados**, Python 3.11.15, NumPy 2.3.5 e cvss 3.6; suíte final 10,731 s.
- **Docker Linux:134 testes aprovados**, Python 3.12.12, NumPy 2.3.5 e cvss 3.6; suíte 5,787 s.
- Os 110 testes anteriores foram mantidos/adaptados; 24 testes novos cobrem critérios, CVSS, importação, falhas, medições, casos inválidos e isolamento da demonstração.
- A imagem foi construída e executou `--demo` sem montagem de pasta real; exibiu os CVEs, os pesos, a indisponibilidade e os riscos esperados.
- Execução isolada da CLI em outro diretório preservou bases sentinelas e usou os exemplos empacotados.
- Importação com colisão ou erro não sobrescreve nem insere parcialmente; falhas de tempfile/json/fsync/replace restauram o estado.
- Notas/pesos divergentes, booleanos, vetores incompletos/duplicados e tempos inválidos foram recusados.
- `git diff --check` sem erros de whitespace.

Os tempos são observações dessas execuções, não benchmark comparável. Os testes não acessam rede nem alteram bases reais. As consultas NVD ocorreram somente na preparação das referências.

Imagem: `trabalho-ufu:local`.
ID: `sha256:8d27420b631cfcb7d6f9c2d8c70e97adba884503c12651c6b68072ddd7977222`.

## Evidências e preservação

- `historico/RESULTADO_TESTES_AUTOMATIZACAO.txt`: suíte Windows completa.
- `historico/RESULTADO_TESTES_DOCKER_AUTOMATIZACAO.txt`: suíte Docker completa.
- `historico/DEMONSTRACAO_AUTOMATIZACAO.txt`: execução real pelo menu.
- `historico/DEMONSTRACAO_DOCKER_AUTOMATIZACAO.txt`: imagem sem pasta montada.
- `exemplos/ativos_teste.json`: biblioteca de exemplo.
- `exemplos/referencias_cve.json`: fontes e vetores verificados.

O arquivo real `ativos_db.txt` continua com o mesmo hash da interrupção, sem edição ou recálculo dos cadastros:
`43660c162b65925e40172dd26e857c4e823a088a3d701cb1ea34be11b7ed3189`.
Backup anterior: `outputs/backup_automatico_2026-11-18/ativos_db.011821478545.bak`.
Snapshot dos fontes anteriores também foi preservado nessa pasta.

## O que não foi realizado

Não houve publicação, implantação na faculdade ou comprovação de 24 horas. Não há sincronização em tempo real com CVE Find/NVD, descoberta automática de vulnerabilidades ou integração de uma biblioteca externa ainda não fornecida. A hierarquia de equipamentos/formigas não foi ampliada neste escopo. O modelo continua sendo um índice acadêmico, não probabilidade nem CVSS agregado.

A biblioteca cvss é uma dependência instalada LGPLv3+; sua implementação não foi copiada. Referências: https://pypi.org/project/cvss/, https://github.com/RedHatProductSecurity/cvss e https://www.first.org/cvss/v4.0/specification-document.
