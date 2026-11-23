> Documento histórico. Para os comandos atuais, consulte o [README](../README.md). As evidências originais estão em `historico/`.

> Registro histórico da validação de16/11/2026. A automatização posterior está documentada em [VALIDACAO_AUTOMATIZACAO.md](VALIDACAO_AUTOMATIZACAO.md).

# Validação da refatoração matemática — 16/11/2026

## Resultado e escopo

A implementação local foi concluída sobre o repositório publicado, conforme a escolha do usuário. Commit de origem: `ae020f215a81b95ca46aedf84d355c045b784d3b`. O remoto main foi consultado em 16/11/2026 e continua nesse commit. Não foram feitos commit, push ou publicação. A versão local com registros humanos e formigas não foi alterada nem incorporada.

## Diagnóstico que antecedeu a implementação

Foram examinados os sete arquivos Python da versão publicada (cinco módulos de aplicação e dois de testes), sua documentação e configuração Docker. O inventário já tinha CRUD de ativos e vulnerabilidades, índices por ID/hostname, serialização em lista JSON, temporários exclusivos, fsync, substituição atômica, backups e rollback de referências em memória. Os 65 testes originais passaram antes da alteração.

Não havia dependências ponderadas, matrizes nem cálculo de risco. Severidade e status eram enums usados no cadastro, edição, formatação, CSV e snapshot de recuperação. Na versão escolhida, retirar status não interrompe um fluxo indispensável de registros estruturados: esses registros pertencem à outra entrega local. A consequência intencional é deixar de acompanhar tratamento por status e retirar essa coluna do CSV.

Também foi identificado que a exportação CSV poderia sobrescrever a própria base. A criação agora é exclusiva, com regressão específica para esse caso.

O Sauron foi examinado na cópia de referência do commit `1850e8465fba43c49ae19e074eeea05775f7f6ba`, incluindo domínio, montagem das matrizes, estabilidade, solução e testes matemáticos. Seu filtro de status na incidência não atende ao pedido atual e não foi incorporado. Não foi importado seu código nem sua pilha Django/SciPy. A referência fornece a formulação conceitual, não resultados de testes executados no Sauron.

## Entrega por requisito

| Solicitação | Entrega/evidência |
|---|---|
| Severidade float de 0 a 10 | Validação no modelo, JSON, CLI e testes; rejeita bool, texto, NaN, infinitos e valores fora da faixa |
| Remover classificação antiga | Enums e rótulos retirados; nomes antigos aparecem somente na detecção/testes de migração |
| Retirar status sem afetar o cálculo | Modelo, menu, serialização e CSV atualizados; cálculo baseado apenas em incidência, severidade e dependências |
| Preservar ativos na migração | Cópia do JSON original; altera somente listas de vulnerabilidades; testes com campos adicionais e IDs não consecutivos |
| Backup e confirmação antes da exclusão | Backup byte a byte verificado, SHA-256, prévia por ativo e confirmação interativa específica |
| Migração única | Manifesto de preparação/conclusão; segunda execução preserva novas vulnerabilidades |
| Retomar após falha | Validação dos hashes original/novo; falha entre base e manifesto bloqueia aplicação até retomada |
| Dependências direcionadas | Cadastro, edição, remoção e listagem; pesos finitos em [0,1), diagonal zero, destinos existentes |
| Remover ativo referenciado | Limpa relações de entrada e saída na mesma gravação; rollback testado nos quatro pontos de falha |
| Arquitetura modular | Domínio, persistência, migração, serviço, motor matemático e CLI separados |
| Matriz M binária | Validação estrita e montagem automática por ID de ocorrência |
| b=Mv | Cálculo e testes com múltiplas ocorrências e valores agregados acima de 10 |
| (I-A)x=b | numpy.linalg.solve; nenhuma inversa explícita |
| Estabilidade | Autovalores, rho<1, ciclos estáveis, instáveis e fronteira numérica |
| Correspondência entre IDs e posições | Ordens explícitas, IDs não consecutivos, persistência e empate no ranking testados |
| Interface completa | Matrizes M/A, vetor v, resultados b/x, risco individual e ranking |
| Compatibilidade | CRUD, buscas, exportação, cancelamentos, persistência e falhas continuam cobertos |
| Documentação e Docker | README reescrito; NumPy instalado na imagem; módulos novos incluídos |

## Cenários conferidos antes de implementar

- M=[[1,1],[0,1]], v=[4,7], A=0: b=x=[11,7].
- Cadeia com b=[4,6,8], pesos 0.2 e 0.5: x=[6,10,8].
- Ciclo com b=[4,2], pesos 0.5 e 0.25: x=[40/7,24/7]; rho=sqrt(0.125).
- Três ativos, peso 0.6 em toda ligação entre ativos distintos: rho=1.2. I-A é invertível, mas a propagação é inválida e deve ser recusada.
- Grafo acíclico com soma de linha 1.6: pode ser estável; x=[8,5,5] para b=[0,5,5].

Os cinco resultados foram substituídos nas equações com aritmética racional, com resíduo exato zero. A implementação também tem testes numéricos desses cenários, além dos casos vazios e inválidos.

## Testes realizados

| Ambiente | Resultado |
|---|---|
| Base publicada antes da mudança | 65 testes aprovados |
| Base local avançada, somente auditoria anterior | 103 testes aprovados; não é a base escolhida para esta implementação |
| Windows, Python 3.11.15, NumPy 2.3.5 | **110 testes aprovados**; execução final da suíte: 15.857 s |
| Docker Linux, Python 3.12.12, NumPy 2.3.5 | **110 testes aprovados**; execução da suíte: 5.388 s |
| Imagem sem pasta montada | Menu, consulta de inventário vazio e saída aprovados |
| CLI completa com dados fictícios | Cadastro de três ativos e vulnerabilidades, duas dependências, matrizes, ranking e consulta individual aprovados |
| Reinício da CLI | Mesmos resultados lidos do JSON; consultas não alteraram o arquivo |
| Revisão do diff | git diff --check sem erros de whitespace |

As durações são observações destas execuções, não um benchmark comparável entre ambientes. Os 65 testes anteriores foram mantidos e adaptados; 45 foram acrescentados. Nenhum teste foi removido para obter aprovação.

Arquivos de evidência:

- `historico/RESULTADO_TESTES_RISCO.txt`: saída completa dos testes Windows.
- `historico/RESULTADO_TESTES_DOCKER_RISCO.txt`: saída completa dos testes Docker.
- `historico/DEMONSTRACAO_RISCO.txt`: execução real da CLI e nova leitura após reinício.
- `historico/DEMONSTRACAO_IMAGEM_DOCKER.txt`: inicialização da imagem isolada.

Imagem construída: `trabalho-ufu:local`.
Identificador: `sha256:3ea5f19e5a2ff7a262240b39f0c7e9a3d6bb506028bf9c4d7c7dc017ea7a5a10`.

## Dados reais e migração

As seguintes bases foram localizadas em 12/11 e revalidadas em 16/11; todas contêm exatamente `[]`, com 2 bytes:

1. `C:\Users\Nitro\OneDrive\Documentos\UFU\trabalho ufu\trabalho2.py\.vscode\ativos_db.txt`.
2. `outputs/etapas_2_3_visual_2026-11-06/antes/ativos_db.txt`.
3. `outputs/etapas_2_3_visual_2026-11-06/depois/ativos_db.txt`.

SHA-256 comum: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.

Nenhuma dessas bases foi modificada, migrada ou excluída. Não há base real no checkout refatorado. Backups e exclusões usados na validação ocorreram somente em arquivos temporários fictícios. Não foi necessário solicitar uma exclusão real porque nenhum registro antigo foi localizado. Se outra base aparecer, é necessário conferir a prévia, o backup e obter a confirmação específica antes de aplicá-la.

## Limitações e pendências externas

- A refatoração ainda não está no GitHub, por solicitação do usuário; clonar o remoto continua obtendo a versão anterior.
- A implantação na faculdade e operação contínua por 24 horas não foram realizadas ou comprovadas.
- Uma única instância deve escrever na base. Não há coordenação entre processos nem garantia de durabilidade contra queda de energia.
- Migração pendente exige o mesmo ambiente/caminho da preparação e preservação do manifesto/backup. Feche as outras instâncias antes de migrar.
- Matrizes densas atendem ao escopo acadêmico. Não foram medidos capacidade ou desempenho para inventários grandes.
- m representa ocorrências cadastradas, não um catálogo global de CVEs compartilhadas. Duplicar uma ocorrência soma sua severidade novamente.
- Pesos e severidades são informados por pessoas. O índice não foi calibrado como probabilidade, CVSS ou prejuízo.
- Casos muito próximos de rho=1 ou sem precisão numérica útil são recusados; isso é proteção computacional, não classificação de risco.

## Como apresentar

Abra o projeto local, instale as dependências conforme o README e execute `main.py`, ou use `docker compose -f docker/compose.yaml run --build --rm inventario` nesta pasta. As opções novas são **11** (dependências) e **12** (matrizes e riscos). Para conferir o exemplo sem cadastrar dados, leia `historico/DEMONSTRACAO_RISCO.txt`.
