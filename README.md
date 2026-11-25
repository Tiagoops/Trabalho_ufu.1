# Inventário UFU — análise matemática de risco

Aplicação acadêmica de terminal para cadastrar ativos, ocorrências de vulnerabilidades e dependências direcionadas. Calcula risco direto e propagado, com persistência JSON e recuperação após falhas de gravação.

A implementação com CVSS, catálogo CVE local e análise matemática de riscos foi publicada na branch `main`, commit `0ef166b`, em 22/11/2026. Esta versão inclui a correção do empacotamento Docker e as instruções de execução local, demonstração e Compose. Não há interface das formigas nesta versão.

## Instalação e execução

Requisitos locais: Python **3.11 ou superior** e NumPy **2.3.5** e cvss **3.6**, fixados em `requirements.txt`. O contêiner usa Python 3.12.12.

Execute os comandos a partir da raiz do projeto. No PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Linux/macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Para abrir quatro ativos de teste sem usar sua base real:

```powershell
.\.venv\Scripts\python.exe main.py --demo
```

No Linux/macOS, use `.venv/bin/python main.py --demo`.

O modo `--demo` usa uma base temporária e descarta suas alterações ao sair. Ativos, dependências e medições são fictícios; os três CVEs e seus vetores têm fontes públicas verificadas. Não instala versões vulneráveis nem realiza varredura ou exploração.

A base padrão é `ativos_db.txt`, ao lado de `banco_dados.py`, independentemente do diretório usado para executar o programa. Importar módulos ou abrir e sair do menu não cria a base. A API `BancoDeDados(caminho)` aceita outro arquivo. O CSV usa o diretório de execução ou o caminho escolhido.

### Docker

É necessário ter o engine Docker em execução. Na raiz do projeto, construa e execute a imagem independente, sem bind mount ou volume:

```bash
docker build -f docker/Dockerfile -t trabalho-ufu:demo-check .
docker run --rm -it trabalho-ufu:demo-check python main.py --demo
```

O menu aparece no terminal; `0` encerra. A imagem instala as dependências fixadas, inclui `catalogo_cvss.py`, `matematica/` e `exemplos/`, e não inclui a base real. A base de `--demo` é temporária. Sem `--demo`, a base padrão fica em `/app/ativos_db.txt`; sem volume, os dados do contêiner são perdidos quando ele é removido por `--rm`.

Valide o Compose separadamente, também com dados fictícios:

```bash
docker compose -f docker/compose.yaml run --build --rm inventario python main.py --demo
```

O Compose monta a pasta do projeto em `/app`, sobrepondo o conteúdo da imagem. Esse teste não comprova que a imagem independente está completa. Com `--demo`, a base fica em um diretório temporário do contêiner e é descartada ao sair. Exportações CSV para `/app` persistem na pasta montada, inclusive no modo de demonstração.

Para usar a base persistente pelo Compose:

```bash
docker compose -f docker/compose.yaml run --build --rm inventario
```

Nesse modo, `/app/ativos_db.txt`, seus backups e os CSV exportados para `/app` ficam na pasta do projeto no computador. Use **um escritor por base**, incluindo execuções locais e contêineres. Não foram alterados os volumes nem o modo de operação do Compose.

Repositório: https://github.com/Tiagoops/Trabalho_ufu.1. Clonar a branch `main` obtém a versão publicada; alterações locais posteriores só estarão disponíveis após publicação autorizada. Estes comandos são instruções de execução, não evidência de build, implantação ou funcionamento por 24 horas.

## Menu

| Opção | Operação |
|---|---|
| 1–4 | Cadastrar, consultar, atualizar e remover ativos |
| 5–6 | Cadastrar e consultar vulnerabilidades |
| 7 | Listar ativos |
| 8–9 | Atualizar e remover vulnerabilidades |
| 10 | Exportar CSV, com severidade numérica e sem status |
| 11 | Calcular dependências pelos serviços, medir indisponibilidade, editar ou remover |
| 12 | Exibir matrizes/vetores, ranking ou risco individual |
| 13 | Importar biblioteca JSON, com prévia e validação do lote |
| 14 | Consultar orientações específicas da classe do ativo |
| 0 | Encerrar |

A CLI não pede mais notas de severidade ou pesos prontos. Você responde características técnicas CVSS (ou informa um vetor publicado) e quantidades de serviços. Os valores são calculados. Tempos de falha aceitam ponto ou vírgula decimal. A API continua lendo números anteriores para compatibilidade, sem inventar critérios ausentes.

Cadastro, edição e remoção preservam as buscas por ID e hostname. O hostname é único sem distinguir maiúsculas. A remoção de um ativo também remove relações que apontam para ele; sua confirmação informa essa consequência.

## Dados e arquitetura

```text
main.py                 menu, validação da entrada e apresentação
modelos.py              Ativo e Vulnerabilidade; critérios e validação numérica
avaliacao.py            cálculo CVSS, participação de serviços e indisponibilidade
biblioteca.py           prévia, validação e importação atômica
catalogo_cvss.py         leitura, busca e validação do catálogo CVE local
exemplos/               ativos fictícios com CVEs reais e fontes verificadas
tipos.py                somente o Enum TipoAtivo
cores.py                utilitário ANSI genérico
banco_dados.py          CRUD, índices, integridade e escrita atômica
migracao.py             prévia, backup, confirmação e retomada
servico_risco.py         correspondência entre IDs e posições das matrizes
matematica/risco.py      validação matemática e solução do sistema
tests/                  unittest: regressão, matemática, CLI e falhas
docker/                 Dockerfile e configuração Compose
validacao/              relatórios e evidências históricas
```

O JSON continua sendo uma **lista de ativos**. Cada ativo guarda `id_ativo`, `hostname`, `responsavel`, `setor`, `tipo`, `vulnerabilidades` e `dependencias`. Outros campos existentes no ativo são preservados.

Exemplo de registro persistido de um ativo que depende do ativo 40 (o destino também precisa estar cadastrado). Na biblioteca de entrada, nota e peso podem ser omitidos quando existem vetor e critérios:

```json
{
  "id_ativo": 10,
  "hostname": "aplicacao",
  "responsavel": "Ana",
  "setor": "TI",
  "tipo": "APLICACAO_WEB",
  "vulnerabilidades": [
    {
      "id_vulnerabilidade": "ocorrencia-1",
      "descricao": "CVE-2021-44228 - cenario de exemplo Log4j Core 2.14.1",
      "categoria": "Software",
      "severidade": 10.0,
      "vetor_cvss": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
      "fonte_severidade": "https://nvd.nist.gov/vuln/detail/CVE-2021-44228"
    }
  ],
  "dependencias": {
    "40": 0.4
  },
  "avaliacoes_dependencias": {
    "40": {
      "total_servicos": 5,
      "servicos_fornecidos": 2
    }
  }
}
```

Os IDs das dependências são inteiros na memória e chaves textuais canônicas no JSON. Não há autodependências ou destinos inexistentes. Peso zero é permitido e não transmite risco.

Cada vulnerabilidade cadastrada é uma **ocorrência em um ativo**, com ID próprio e estável. Duas ocorrências com a mesma descrição continuam distintas. O catálogo CVE local é uma referência para consulta e seleção de vetores; o número `m` continua representando ocorrências cadastradas nos ativos. O motor matemático também aceita incidência compartilhada em matrizes fornecidas diretamente.

Os status de tratamento foram removidos do modelo, do menu e do CSV. O inventário passa a representar as ocorrências atualmente cadastradas. Uma ocorrência deixa de contribuir ao ser removida; a remoção exige confirmação e não conserva um histórico de correção. Nenhum status filtra o cálculo.

## Automatização das entradas

### Severidade calculada

No cadastro/edição, escolha responder as onze métricas Base CVSS 4.0 ou colar um vetor Base CVSS 3.1/4.0. A biblioteca `cvss==3.6` calcula a nota; vetor e resultado são persistidos juntos e divergências são recusadas. Dados incompletos, métricas extras/duplicadas ou valores inválidos não recebem nota presumida.

O questionário mostra **CAMPO** e **O QUE INFORMAR** para cada métrica, com o significado das letras aceitas. `N` significa nenhum, não desconhecido. As explicações seguem a [especificação CVSS 4.0 da FIRST](https://www.first.org/cvss/v4.0/specification-document). Ao concluir, mostra o vetor, a severidade calculada e sua relação com `v`. A opção **11** explica os critérios de serviços/indisponibilidade; em **12 → 1**, cada matriz/vetor traz **CAMPO**, **O QUE INFORMAR** e **O QUE CALCULAR**, junto dos valores obtidos. As fórmulas e os dados existentes permanecem iguais.

A captura [DEMONSTRACAO_GUIA_CVSS.txt](validacao/historico/DEMONSTRACAO_GUIA_CVSS.txt) mostra o questionário preenchido com um cenário técnico fictício e a consulta das matrizes da demonstração temporária. Registro histórico da verificação desta apresentação em 18/11/2026: **134 testes locais aprovados**, severidade de referência **9,9** e risco efetivo dos exemplos **[16,92; 12,4; 9,8; 4,23]**, sem alteração da base real. A imagem Docker não foi reconstruída nem testada novamente nesta alteração; o serviço estava desligado.

O valor é uma avaliação Base derivada das características fornecidas, não certificação do equipamento nem detecção automática de vulnerabilidades. CVSS Base mede severidade; o risco do inventário continua sendo calculado pelas matrizes. A CLI informa quando existem cadastros anteriores sem vetor/fonte. Eles são preservados, e sua reavaliação exige dados técnicos; não são apagados nem convertidos automaticamente.

### Peso calculado e medida de indisponibilidade

O critério escolhido é:

`A[i,j] = serviços fornecidos por j / total de serviços necessários a i`.

Os serviços têm igual importância nessa contagem. O total deve ser consistente entre as dependências avaliadas do mesmo ativo. Para alterar esse total em vários vínculos, remova e refaça as relações afetadas com o novo denominador. O modelo não identifica automaticamente serviços sobrepostos, redundância ou criticidade desigual.

Exemplo: 2 serviços fornecidos, entre 5 necessários, produzem peso **0,4**. Se todos os serviços forem fornecidos pelo mesmo ativo, o resultado seria 1: o sistema recusa essa dependência integral porque o requisito matemático exige `Aij < 1`; não a transforma silenciosamente em 0,99.

Separadamente, podem ser registrados duração da falha do fornecedor, tempo indisponível do dependente e fonte da observação. O sistema calcula:

`indisponibilidade observada (%) = 100 × tempo indisponível / duração da falha`.

Uma falha de 120 minutos com 30 minutos de indisponibilidade gera **25% observados**. Isso não altera o peso 0,4 e não é previsão, probabilidade ou comprovação de causalidade. Ausência de medição aparece como “não medida”, nunca como zero. Tempos inválidos ou fora da janela da falha são recusados.

### Importar a biblioteca

A opção **13** recebe o caminho de uma lista JSON de ativos. Valida o lote e mostra uma prévia; a inclusão só ocorre após a confirmação no menu. IDs, hostnames ou ocorrências em conflito recusam o lote inteiro, sem sobrescrever registros. A gravação é única e usa o rollback da base.

- Vulnerabilidade com `vetor_cvss`: a nota é calculada; uma nota também fornecida precisa conferir.
- Vulnerabilidade com nota publicada: exige `severidade` numérica e `fonte_severidade` identificada; é importação de uma avaliação externa, não um cálculo novo.
- Dependência com `avaliacoes_dependencias`: os pesos são derivados das contagens de serviços; pesos explícitos também precisam conferir.
- Dependências numéricas já conhecidas podem ser importadas sem inventar critérios de origem. Sua procedência deve ser conferida pelo usuário.

Use `exemplos/ativos_teste.json` como formato de referência. O arquivo contém vetores e critérios, sem notas nem pesos preenchidos. A biblioteca real ainda será fornecida pelo usuário; adaptadores para outros formatos não foram presumidos. A importação não consulta o CVE Find/NVD em tempo real e não associa um CVE a todos os ativos de um mesmo tipo.

## Exemplos de CVEs e ativos fictícios

Referência inicial: [CVE Find](https://www.cvefind.com/pt/cve.html). Vetores e notas foram conferidos na API oficial NVD em **18/11/2026** e guardados em `exemplos/referencias_cve.json`.

| Ativo fictício | Componente do cenário | CVE de exemplo | CVSS Base 3.1 calculado |
|---|---|---|---|
| 10 — aplicação | Apache Log4j Core 2.14.1 | [CVE-2021-44228 / Log4Shell](https://nvd.nist.gov/vuln/detail/CVE-2021-44228) | 10,0 |
| 20 — servidor TLS | OpenSSL 1.0.1f | [CVE-2014-0160 / Heartbleed](https://nvd.nist.gov/vuln/detail/CVE-2014-0160) | 7,5 |
| 30 — transferência | MOVEit Transfer 2023.0.0 (15.0.0) | [CVE-2023-34362](https://nvd.nist.gov/vuln/detail/CVE-2023-34362) | 9,8 |
| 40 — estação | Sem vulnerabilidade cadastrada no cenário | Não presumir ausência de outras falhas | 0 próprio |

Os componentes/versionamentos são hipóteses do exemplo; não foram encontrados nos seus equipamentos. Não é necessário instalar software vulnerável para executar a demonstração.

Dependências de teste: 10→20=2/5, 10→30=1/5, 20→30=1/2 e 40→10=1/4. Na ordem dos ativos 10,20,30,40:

- Risco próprio: **b=[10; 7,5; 9,8; 0]**.
- Risco efetivo: **x=[16,92; 12,4; 9,8; 4,23]**.
- No vínculo 10→20, a medição fictícia de 30/120 minutos produz 25% de indisponibilidade observada, separada do peso 0,4.

Conferência manual: x30=9,8; x20=7,5+0,5×9,8=12,4; x10=10+0,4×12,4+0,2×9,8=16,92; x40=0,25×16,92=4,23. A estação tem risco próprio zero e recebe risco pelas dependências.

Os IDs das ocorrências são ordenados; Heartbleed vem antes de Log4Shell nas colunas. Por isso M não é necessariamente uma identidade: a correspondência dos IDs é exibida no menu **12**, junto às matrizes. A demonstração abre também no Docker:

```bash
docker compose -f docker/compose.yaml run --build --rm inventario python main.py --demo
```

## Modelo matemático

- `M`: matriz binária `n × m`, relacionando ativos e ocorrências.
- `v`: vetor de severidades, com cada valor entre 0 e 10.
- `A`: matriz `n × n`; `A[i,j]` indica quanto o ativo **i depende de j**. Cada peso está em `[0,1)` e a diagonal é zero.
- `b = M @ v`: risco direto, soma das severidades incidentes.
- `(I - A) @ x = b`: risco propagado.

O sistema usa `numpy.linalg.solve(I - A, b)`. Não calcula a inversa. A estabilidade exige `rho(A) < 1`, calculada pelos autovalores; invertibilidade, sozinha, não basta. Ciclos estáveis são aceitos. Um conjunto de dependências instável pode ser cadastrado e editado, mas o cálculo é bloqueado até sua correção. A soma de uma linha menor que 1 não é uma restrição adicional obrigatória.

Na consulta, a ordem dos IDs é mostrada junto às matrizes. Ativos são ordenados pelo ID e ocorrências pelo ID estável; posições de listas nunca são tratadas como IDs. O ranking usa risco propagado decrescente e ID crescente nos empates.

O risco é um **índice matemático**, pode ultrapassar 10 e não representa probabilidade, percentual, CVSS ou prejuízo financeiro. Não foram criadas faixas de risco agregado. Os pesos agora são calculados pela participação dos serviços descrita abaixo.

### Demonstração automática do modelo e da recarga

Na raiz do projeto, execute `python -B -m exemplos.demonstrar_modelo` com as dependências instaladas.
O programa cria uma base temporária, importa o cenário existente e abre outra instância do banco.
Confere os dados recarregados, M, v, A, b, x e os riscos individuais, sem usar a base real.
Mostra IDs de linhas e colunas, os diagnósticos numéricos e a conferência manual independente.
O JSON guarda entradas; os riscos são recalculados em memória. A base temporária é removida ao sair.

Para os ativos `[10,20,30,40]`, as ocorrências são ordenadas por ID: Heartbleed, Log4Shell e MOVEit.
Logo, `v=[7.5,10,9.8]` e `M=[[0,1,0],[1,0,0],[0,0,1],[0,0,0]]`; M não é identidade.
As dependências são 10→20 (0,4), 10→30 (0,2), 20→30 (0,5) e 40→10 (0,25).
A seta significa “depende de”; a influência do risco percorre do fornecedor para o dependente.
Manual: x30=9,8; x20=7,5+0,5×9,8=12,40; x10=10+0,4×12,40+0,2×9,8=16,92;
x40=0+0,25×16,92=4,23. O ativo 40 tem risco próprio zero e recebe risco pelo vínculo com 10.
O peso 0,4 é 2/5 dos serviços; os 25% observados são 30/120 minutos, sem multiplicar o peso.
As comparações desse cenário pequeno usam rtol=atol=1e-12, sem arredondar entradas ou cálculos.
Risco efetivo é um índice que pode ultrapassar 10, não porcentagem, probabilidade ou CVSS agregado.

### Exemplos verificáveis

| Cenário | Entrada | Resultado esperado |
|---|---|---|
| Sem dependências | M=[[1,1],[0,1]], v=[4,7], A=0 | b=x=[11,7] |
| Cadeia A→B→C | b=[4,6,8], A→B=0.2, B→C=0.5 | x=[6,10,8] |
| Ciclo estável | b=[4,2], A→B=0.5, B→A=0.25 | x=[40/7,24/7], rho=sqrt(0.125) |
| Invertível, mas instável | 3 ativos, todos os pesos entre ativos distintos=0.6 | rho=1.2: cálculo recusado |
| Soma de linha >1, grafo acíclico | b=[0,5,5], A→B=A→C=0.8 | x=[8,5,5], rho=0 |
| Sem ativos | M e A com forma (0,0), v vazio | b e x vazios |
| Ativos sem vulnerabilidades | M com forma (n,0), v vazio, A estável | b e x nulos |

Na cadeia, xC=8; xB=6+0.5×8=10; xA=4+0.2×10=6. No ciclo, xA=4+0.5xB e xB=2+0.25xA, resultando em xA=40/7 e xB=24/7. Os resultados foram conferidos com aritmética exata antes da implementação.

### Precisão e limites

São validados dimensões, números reais finitos, M binária, pesos e diagonal de A. A interface mostra raio espectral, número de condição e resíduo relativo, antes de arredondar os resultados para exibição.

A margem `16 × eps(float64) × n` ao redor de rho=1 evita aprovar um caso que o arredondamento não distingue da fronteira. É uma proteção numérica conservadora, não uma faixa de risco. Sistemas com `cond(I-A) × eps >= 1` são recusados porque a precisão disponível não assegura dígitos úteis. O resíduo é escalonado para evitar estouro; seu limite é `64 × eps × max(n,m,1)`.

As matrizes são densas: memória O(n²+nm) e solução/autovalores com custo cúbico no número de ativos. O foco é o inventário acadêmico; não foram medidos limites para redes grandes. Pesos e severidades são calculados a partir de dados técnicos informados ou importados; a qualidade desses dados ainda depende da avaliação humana. Nomes de ativos não determinam automaticamente vulnerabilidades. Duplicar uma ocorrência aumenta o risco direto; descrições iguais não são deduplicadas automaticamente.

## Migração sem conversão de severidades

**Feche outras instâncias do inventário antes de migrar.** A migração usa a mesma trava de gravação do inventário. Um formato antigo bloqueia gravações, sem converter enumerações nem tratar a base como inventário novo. A migração é separada da inicialização normal.

Primeiro, prepare a prévia:

```powershell
.\.venv\Scripts\python.exe migracao.py "CAMINHO\ativos_db.txt"
```

Este comando cria uma cópia `.migracao.*.bak`, verifica os bytes e informa SHA-256, caminho do backup, IDs/hostnames dos ativos e quantidade de vulnerabilidades afetadas. Não altera a base. O manifesto `.migracao.json` registra o plano e bloqueia gravações enquanto a preparação estiver pendente.

Somente após conferir backup e impacto:

```powershell
.\.venv\Scripts\python.exe migracao.py "CAMINHO\ativos_db.txt" --aplicar
```

O programa exige digitar `EXCLUIR` seguido do identificador mostrado na prévia. A confirmação genérica `sim` não autoriza a operação. São removidas somente as listas antigas de vulnerabilidades; os demais campos dos ativos e as dependências são preservados. Não há conversão automática das classificações antigas.

O SHA-256 da base e o backup são revalidados antes de substituir o arquivo. Uma base alterada após a prévia ou um backup diferente bloqueia a operação. Bases numéricas ou mistas não são limpas automaticamente. Se não houver vulnerabilidades, o procedimento informa que a migração é desnecessária.

Para cancelar a preparação, preservando base e backup:

```powershell
.\.venv\Scripts\python.exe migracao.py "CAMINHO\ativos_db.txt" --cancelar
```

Se houver falha entre a substituição da base e a confirmação do manifesto, execute novamente com `--aplicar` no **mesmo ambiente e caminho**. O hash identifica o arquivo já migrado e conclui o registro sem repetir a exclusão. Não apague o manifesto: o estado concluído protege os novos cadastros de uma segunda limpeza. Depois da migração, reabra o inventário. Preserve base, backup e manifesto juntos; uma migração pendente não é transportável entre caminhos Windows e Docker sem revisar os caminhos registrados.

**Dados reais:** não foi aplicada exclusão em bases do usuário. O cadastro atual do usuário já contém dados e foi preservado, com backup antes da automatização. As bases que estavam vazias em 12/11/2026 são apenas uma referência histórica.

## Persistência e recuperação

A gravação usa temporário exclusivo no mesmo diretório, `flush`, `fsync` e `os.replace`. Falhas antes da substituição restauram objetos, listas, dicionários e índices ao último sucesso, preservando referências em memória. Campos adicionais dos ativos também sobrevivem à leitura/gravação.

Arquivo inválido bloqueia gravações mesmo quando o backup é criado com sucesso. Revise e corrija o arquivo explicitamente e reabra o inventário; não há restauração nem limpeza automática. Se o backup falhar, o original também permanece protegido. Formato antigo e migração pendente continuam bloqueados até o procedimento explícito de migração.

Gravações do inventário e da migração usam trava do sistema operacional no arquivo adjacente `.lock`, liberada ao finalizar a operação ou o processo. O arquivo permanece e não deve ser apagado enquanto houver instâncias abertas. Uma instância desatualizada recusa gravação se os bytes da base mudaram: reabra o inventário para ler a versão atual. A proteção cobre processos cooperantes no mesmo sistema operacional; não foi certificada entre o host Windows e o Linux do Docker sobre a mesma pasta, nem em sistemas de arquivos remotos. Não execute escritores nesses ambientes simultaneamente. Não há garantia contra queda de energia ou serviço de servidor por 24 horas validado. O relatório CSV usa criação exclusiva: não sobrescreve arquivos existentes nem a base, e recusa campos com fórmulas/controles de linha.

## Testes

No PowerShell:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -v
```

Linux ou contêiner com os testes montados pelo Compose (a imagem independente não inclui a suíte):

```bash
python -B -m unittest discover -v
docker compose -f docker/compose.yaml run --rm -T inventario python -B -m unittest discover -v
```

A suíte usa arquivos temporários e dados fictícios. Os 65 testes anteriores foram mantidos e adaptados às mudanças intencionais: severidade numérica, retirada de status, coluna CSV e Python mínimo. Os testes adicionais cobrem validação matemática, ciclos, mapeamento de IDs, CRUD de dependências, rollback, confirmação, backups e retomada da migração. [VALIDACAO_RISCO.md](validacao/VALIDACAO_RISCO.md) preserva os resultados de 16/11. [VALIDACAO_AUTOMATIZACAO.md](validacao/VALIDACAO_AUTOMATIZACAO.md) também contém registros históricos e exemplos CVE; esses documentos não substituem uma nova execução da suíte nem validam a imagem atual.

Os arquivos em `validacao/historico/` preservam saídas e manifestos das versões anteriores. Os caminhos e hashes desses manifestos descrevem o estado original; não são prova de integridade da organização atual.

## Referências

Documentação oficial: [numpy.linalg.solve](https://numpy.org/doc/stable/reference/generated/numpy.linalg.solve.html) e [numpy.linalg.eigvals](https://numpy.org/doc/stable/reference/generated/numpy.linalg.eigvals.html).

Dependência de avaliação: [cvss 3.6](https://pypi.org/project/cvss/), projeto Red Hat Product Security, licença LGPLv3+. Usada como biblioteca instalada; sua implementação não foi copiada para o projeto.


### Classes concretas e demonstração de POO

Cadastro, importação e leitura JSON usam `Ativo.criar`, selecionando a classe
pela categoria persistida, sem deduzi-la pelo hostname. `Notebook` especializa
`EstacaoTrabalho`; `AplicacaoWeb` e `SistemaBancoDados` especializam `Software`.
A opção 14 chama `orientacoes_tratamento()` e mostra o comportamento específico.
São orientações de revisão; não executam correções nem alteram o risco calculado.

Atualizar um ativo pela CLI substitui seu objeto pela classe correta, preservando
ID, ocorrências, dependências, avaliações e campos extras. Quem usa a API deve
consultar novamente `buscar_por_id` após `atualizar_ativo`; referências antigas
não acompanham a substituição. Se a gravação falhar, o objeto anterior é restaurado.

### Estado da entrega local

A implantação no servidor e a comprovação de 24 horas estão adiadas por decisão
do autor enquanto o frontend é desenvolvido. Isso não equivale ao atendimento
do requisito de hospedagem do enunciado. A demonstração usa somente a CLI.
As falhas intermitentes Windows em `os.replace` seguem sem causa identificada;
não há retry automático nem garantia de que uma execução local vá completá-las.


Para instalar, manter o catálogo e recuperar o inventário, consulte o
[guia de operação](OPERACAO.md).

### Rastreabilidade da seleção no catálogo CVE

Na avaliação de vulnerabilidade, a opção 3 permite buscar no catálogo local por
CVE, produto, versão de exemplo, descrição ou código CWE completo, como `CWE-89`.
A descrição é um resumo da fonte NVD. A consulta mostra os códigos CWE e quem
forneceu cada classificação, além do endereço da referência. Os três registros
foram consultados para descrição e CWE em 25/11/2026. O catálogo é lido offline.

Selecionar e confirmar uma CVE na biblioteca local grava na ocorrência o campo
opcional `cve`, o vetor e a URL NVD em `fonte_severidade`. O ID da ocorrência
continua independente: a mesma CVE pode estar associada a diferentes ativos.
A consulta mostra tanto o vetor quanto a fonte. A recarga JSON e a importação
de ativos preservam esses metadados; registros antigos sem `cve` continuam válidos
e não recebem associação presumida pela descrição ou pelo vetor.

Na edição, escolher outra CVE substitui sua referência. Uma avaliação manual
remove a associação anterior à CVE e sua fonte; editar somente descrição ou
categoria mantém os metadados. Cancelar a edição preserva o registro inteiro.
São recusadas CVEs malformadas e fontes NVD que não correspondam ao identificador.
O formato do CSV permanece o mesmo. Não há varredura nem sincronização online;
a confirmação humana da aplicabilidade ao ativo continua necessária.
