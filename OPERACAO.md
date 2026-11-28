# Operação do Inventário de Ativos

Use uma versão identificada pelo commit do Git. Para conferir o código recebido:

```powershell
git clone https://github.com/Tiagoops/Trabalho_ufu.1.git
cd Trabalho_ufu.1
git rev-parse HEAD
docker compose -f docker/compose.yaml run --build --rm inventario python main.py --demo
```

A demonstração usa uma base fictícia temporária. Confirme que o menu abre e use
a opção 0 para sair. Para operar o inventário, execute da raiz do repositório:

```powershell
docker compose -f docker/compose.yaml run --build --rm inventario
```

O Compose monta o código em `/app` no serviço de terminal e monta `dados/`
em `/dados` nos dois serviços. Ambos usam `dados/inventario.json` do computador,
junto aos backups e ao eventual manifesto de migração.
Restrinja o acesso a essa pasta e use um escritor por base. Feche a aplicação
antes de alternar entre Windows e Docker sobre a mesma pasta.

## Escolha da interface ao iniciar

Na pasta do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -B main.py
```

Antes de abrir a base, escolha **1 - Acessar interface gráfica** ou
**2 - Continuar no terminal**. A interface gráfica abre o navegador padrão
quando possível. Uma prévia já aberta só é reutilizada depois da conferência de sua base pelo
endpoint `/metadados`. Bases diferentes, mesmo contendo JSON idêntico, são
recusadas. Uma instância antiga sem metadados também deve ser encerrada antes
de iniciar esta versão. Se for necessário iniciar um servidor novo, o terminal informa
o endereço; mantenha-o aberto e use Ctrl+C para encerrar esse servidor.
Fechar apenas a aba do navegador não encerra o processo.

Use `main.py --terminal` para entrar diretamente na CLI. `main.py --demo`
continua abrindo diretamente a demonstração temporária da CLI.

Dentro de um contêiner, o navegador fica no computador anfitrião. Para o
seletor iniciar a prévia acessível pelo computador, publique a porta:

```powershell
docker compose -f docker/compose.yaml run --rm -p 127.0.0.1:2229:2229 inventario
```

Escolha 1 e abra <http://127.0.0.1:2229>. Não execute esse comando com a porta
já publicada pelo serviço frontend. Para manter o serviço frontend aberto,
use o seletor Python local, que o reconhece e reaproveita. Para operar apenas
pela CLI, o comando habitual sem `-p` continua válido: escolha 2.

A CLI e a interface usam `dados/inventario.json`. Com o frontend Docker ativo,
a opção 2 e `main.py --terminal` executam a CLI nesse mesmo contêiner; não
criam outra base no Windows. Sem o frontend Docker ativo, os dois iniciadores
nativos usam o mesmo arquivo do computador. O caminho aparece no terminal.

## Backup e restauração

1. Encerre a CLI, os contêineres do projeto e qualquer migração. Copie
   `dados/inventario.json`, os arquivos `dados/inventario.json.*.bak` e o eventual
   `dados/inventario.json.migracao.json` para uma pasta fora do repositório, com data e
   acesso restrito. Inclua o commit da versão que gravou os dados.
2. Antes de substituir uma base ativa, guarde uma cópia dela. Para verificar a
   restauração, use uma segunda cópia do repositório na versão identificada e
   coloque nela a base do backup. Abra o Compose nessa cópia e confira ativos,
   ocorrências, dependências e uma consulta de risco. Verifique o aviso no
   terminal caso os dados não sejam válidos.
3. Com as instâncias encerradas e a cópia de restauração validada, coloque o
   arquivo aprovado na pasta ativa e abra novamente. Se existir uma migração
   pendente, preserve os arquivos juntos e siga a seção de migração do README no
   ambiente e caminho registrados. O arquivo de trava `.lock` é operacional e
   fica fora da cópia de restauração.

## Atualizar o catálogo

A atualização é manual e offline. Prepare um lote no formato de
[referencias_cve.json](exemplos/referencias_cve.json), com uma lista
`registros` e um objeto completo por CVE. Para cada entrada nova ou revista:

- Confira o identificador, produto, descrição resumida e classificações nas
  referências oficiais. Registre a URL NVD, quem atribuiu cada CWE e a data da
  consulta. Preserve a origem, a data, a nota e o vetor da avaliação CVSS.
- Revise apenas CVEs com evidência de inclusão ou alteração. O carregador
  compara nota e vetor, e a revisão humana confere os dados com os boletins.
- Informe o caminho de um lote já preparado. O comando sem `--saida` mostra
  inclusões e campos alterados, sem gravar. A repetição de um identificador no
  próprio lote é recusada. Uma CVE existente recebe o registro completo do
  lote, incluindo a remoção de campos omitidos. CVEs ausentes do lote são
  preservadas.

```powershell
python -B -m catalogo_cvss lote.json
python -B -m catalogo_cvss lote.json --saida catalogo-candidato.json
git diff --no-index -- exemplos/referencias_cve.json catalogo-candidato.json
```

Execute esses comandos no ambiente Python com as dependências do projeto.
A saída exige um arquivo novo. O Git retorna código 1 quando encontra diferenças.
Aprovação é uma etapa manual: depois de revisar o diff, substitua o catálogo
em uma cópia de teste, execute a suíte e abra a busca. Publique a mudança pelo
Git após a revisão e reconstrua a imagem se distribuir o aplicativo em Docker.

## Suporte e limites

Em caso de erro, registre commit ou ID da imagem, sistema operacional,
comando, resultado esperado e mensagem de erro. Use um exemplo fictício e
retire nomes de ativos, credenciais e caminhos sensíveis do material enviado.
Falhas de gravação pedem conferência de permissões, espaço disponível e outras
instâncias antes de repetir a operação. Um JSON inválido bloqueia a gravação.

A cobertura da trava foi verificada para processos cooperantes no mesmo
sistema operacional. O catálogo auxilia a avaliação humana de aplicabilidade.
Backup, operação em servidor, atualização automática e prazos de suporte
dependem do ambiente e do acordo de entrega.

## Gestão web local

Na raiz do projeto:

```powershell
docker compose -f docker/compose.yaml up -d --build frontend
```

Abra <http://127.0.0.1:2229>, clique **Cadastrar ativo**, preencha os cinco campos
e clique **Salvar ativo**. Use apenas dados fictícios nesta demonstração. O ID
precisa ser inteiro positivo e único; hostname também deve ser único. O novo
ativo pode receber vulnerabilidades iniciais ao marcar a opção de rascunho.
Nesse caso, confirme o ativo ao concluir as ocorrências. Sem essa opção, ele
começa sem vulnerabilidades. Dependências são cadastradas depois, na tela
própria. Cancelar volta ao inventário sem alterar a base.

A montagem de `dados/` guarda `/dados/inventario.json` e a trava de escrita.
Uma base nova é inicializada com `[]`; reinícios e recriações preservam o
arquivo existente, inclusive se estiver inválido. Os dois serviços usam a
mesma base. Não remova `dados/`: ela contém os cadastros. Para parar o servidor:

```powershell
docker compose -f docker/compose.yaml stop frontend
```

Execução local sem Docker, com Python 3.11 ou superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B iniciar_web.py
```

Sem variáveis, usa `dados/inventario.json`, a mesma base da CLI e do Compose.
Se não existir, o iniciador web cria uma lista vazia. A pasta fica fora do Git
e do contexto de construção Docker; os dados não entram na imagem.
O servidor local continua usando Waitress, na porta 2229 em loopback. Encerre
com Ctrl+C. Não execute junto com outro servidor na mesma porta.

`INVENTARIO_ARQUIVO` define o caminho no servidor. `iniciar_web.py` habilita o
cadastro nesse caminho e inicializa um arquivo ausente com uma lista vazia;
nunca sobrescreve um arquivo existente. Para apenas consultar, sem inicializar
nem habilitar o cadastro, mantenha o comando anterior:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:2229 --call app_web:create_app
```

A fábrica usa `INVENTARIO_CADASTRO=1` para habilitar cadastro em uma base
configurada; o exemplo versionado é sempre protegido contra gravação.
O navegador não escolhe caminhos. As consultas continuam sem escrita. Falha
na base mostra inventário indisponível; `[]` válido significa nenhum ativo;
falha só no cálculo mantém os ativos. Falha ao salvar mostra erro sem sucesso.

Formulários abertos antes de um reinício devem ser recarregados, pois o token
de proteção usa uma sessão assinada com chave temporária do processo. Não há
autenticação; mantenha a porta em `127.0.0.1`. A implantação na faculdade e o
controle de acesso em rede ficam para outra etapa.

O formulário **Cadastrar ativo** tem um campo de texto `website`, oculto por
CSS, fora da navegação por teclado e com autocomplete desativado. Qualquer valor
recebido nesse campo, inclusive espaços ou uma ocorrência repetida preenchida,
retorna HTTP 400 com mensagem genérica antes de abrir o banco ou criar rascunho.
Campo vazio ou ausente mantém o fluxo normal. O valor nunca é persistido.
É uma proteção complementar para bots que preenchem campos indiscriminadamente;
não substitui CSRF e não detecta bots que deixam o campo vazio. Outros formulários
não receberam esse campo.

Verificações com arquivos temporários fictícios:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.test_cadastro_web tests.test_app_web -v
.\.venv\Scripts\python.exe -B -m unittest discover -q
$ensaioUfu = Join-Path $env:TEMP ("ufu_validacao_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $ensaioUfu | Out-Null
docker compose -f docker/compose.yaml run --rm -T --volume "${PWD}:/app:ro" --volume "${ensaioUfu}:/dados" inventario python -B -m unittest discover -q
```

O ensaio Compose substitui `/dados` por uma pasta fictícia exclusiva e monta
`/app` somente para leitura. Nunca execute testes com a base da apresentação.

A navegação reúne **Ativos**, **Vulnerabilidades**, **Dependências**, **Riscos**,
**Importar JSON**, **Exportar CSV** e **Sair**. Os detalhes do ativo trazem suas
orientações por tipo. As ações de remoção exigem confirmação e mostram os efeitos.
Use a busca de Ativos para ID, hostname exato ou trecho do nome.

Na avaliação de vulnerabilidade, escolha o modo e clique **Usar modo** para
mostrar seus campos. Depois, use **Avaliar e revisar**, confira a prévia e
confirme a associação. Catálogo e NVD exigem marcar a aplicabilidade ao ativo.
O NVD recebe somente o ID público da CVE. A consulta não faz varredura.

Na importação, selecione uma lista JSON UTF-8 de até 1 MiB. **Validar e revisar
lote** não grava nada. A confirmação adiciona o lote em uma única gravação;
IDs e hostnames repetidos são recusados. O upload não é salvo como arquivo.
A prévia é assinada e vale por até 15 minutos. Se a base mudar, reabra a operação.

**Exportar CSV** baixa o relatório no navegador. O servidor não cria uma cópia
local. Campos com fórmulas ou controles de linha são recusados antes do download.

**Sair** encerra a sessão do navegador, invalida seus formulários e mostra
**Entrar novamente**. O servidor permanece disponível. Para encerrá-lo, use
Ctrl+C no terminal ou `docker compose -f docker/compose.yaml stop frontend`.

As interfaces compartilham `dados/inventario.json`. `INVENTARIO_ARQUIVO`
continua permitindo uma escolha explícita de caminho. Não use essa variável
para executar escritores Windows e Linux simultaneamente na mesma base. O
seletor padrão encaminha o terminal ao contêiner ativo para evitar essa mistura.
Bases legadas e o volume antigo permanecem preservados; não há mesclagem
automática. Use `--demo` para um cenário fictício temporário separado.

## Gravação no Windows

Bloqueios temporários na substituição do JSON recebem até seis tentativas,
com espera total máxima programada de 820 ms. Cada bloqueio recuperável gera
aviso no log. Antes de tentar novamente, a assinatura da base é conferida;
uma alteração externa exige reabrir o inventário. Se a permissão continuar
negada, a operação termina com erro e rollback. O arquivo anterior não é
removido previamente. Isso trata bloqueios transitórios; não concede permissões
a quem não as possui e não identifica o processo externo responsável.

## Identidade e saúde da interface

`GET /metadados` responde JSON com `aplicacao`, `protocolo` (1), `base_id` e
`inventario_disponivel`. O ID é a assinatura do caminho canônico, não dos dados;
não muda ao cadastrar ativos e não expõe o caminho no HTTP. O endpoint só lê e
valida a base: HTTP 200 quando disponível, HTTP 503 quando ausente/inválida. Não
cria arquivo, backup ou trava, e continua acessível após Sair. Não calcula risco.

O iniciador exige protocolo e identidade compatíveis. Para reconhecer o mesmo
arquivo Windows/Docker, confere a publicação loopback na porta usada e a montagem
bind informadas pelo Docker. Não presume que quaisquer arquivos em `/dados` sejam
a mesma base. Docker indisponível ou montagem não comprovada impede essa equivalência.
Esse protocolo evita confusão entre instâncias; não é um mecanismo de autenticação.

A verificação de saúde é pontual. Ela não comprova execução contínua por 24 horas
nem substitui a implantação no servidor disponibilizado pelo docente.

## Validação do documento e códigos de saída

O inventário aceita somente documentos regraváveis como JSON com números finitos
e texto UTF-8 válido, incluindo campos extras e suas chaves. NaN, Infinity e
sequências Unicode isoladas são recusados na validação compartilhada dos ativos.
Acentos, emojis e campos extras válidos são preservados. Consultar uma base inválida
retorna inventário indisponível (HTTP 503), sem backup, trava ou temporário; uma
importação inválida retorna HTTP 400 antes da prévia e mantém a base anterior.
A recuperação explícita da CLI conserva a política anterior de backup e bloqueio.

`iniciar_web.py` retorna 1 quando não consegue iniciar o servidor, por exemplo
por falha de bind ou permissão. Uma instância incompatível também retorna 1.
Encerramento normal, Ctrl+C tratado e reuso de uma instância identificada retornam 0.
O seletor de `main.py` propaga esses códigos. No PowerShell, confira `$LASTEXITCODE`
após o processo terminar. O mesmo status é devolvido ao Docker e aos scripts.

A rodada de 271 testes está em `validacao/evidencias_json_status_2026-11-26/`.
Ela registra uma falha inicial intermitente de um teste antigo de retomada de
migração Windows, as verificações posteriores e o limite de causa não confirmada.

## IDs importados e migração — revisão de 26/11/2026

IDs de ocorrências não podem conter `/`, `\`, controles ou ser `.`/`..`.
Registros com ID incompatível são recusados antes da prévia de importação;
uma base incompatível fica indisponível. IDs válidos são preservados, sem
renomeação automática. Corrija dados antigos explicitamente em cópia com backup.

A migração também reutiliza as seis tentativas limitadas de substituição no
Windows e verifica se o arquivo mudou antes de repetir. Recusa permanente ou
conflito continuam sendo erro. A CLI apresenta status 1 sem traceback para esses
conflitos. Diagnóstico e resultados atuais: validacao/VALIDACAO_ETAPAS_1_4.md.

## Servidor do docente — operação e registro de 24 horas

Em 27/11/2026, a saída SSH fornecida pelo autor confirmou mais de 24 horas
de execução no servidor da UFU, zero reinícios, saúde `healthy` e HTTP 200
com inventário disponível. Evidências e limites em
[VALIDACAO_24H_UFU.md](validacao/VALIDACAO_24H_UFU.md). Os comandos abaixo
são um modelo de implantação; a conferência não executou build nem reinício.

Use `docker/compose.servidor.yaml` em checkout separado e limpo da versão
publicada e validada. Antes, confira a instalação que já existe, contêineres,
volumes, porta e faça cópia recuperável dos dados. Não substitua outra entrega
nem apague volumes. O Compose habitual `docker/compose.yaml` permanece local.

O acompanhamento S5_20 informa projeto `trab02_2026_2_MATRICULA` e porta externa
2000 + os três últimos dígitos da matrícula. Confirme com o docente; nenhum valor
real foi preenchido. Em Bash, substitua os três valores abaixo pelos confirmados:

```bash
export UFU_PROJETO='trab02_2026_2_MATRICULA'
export UFU_PORTA='PORTA_CONFIRMADA'
export UFU_IMAGEM='trabalho-ufu:COMMIT_VALIDADO'
docker compose -f docker/compose.servidor.yaml config --quiet
docker compose -f docker/compose.servidor.yaml build frontend
docker compose -f docker/compose.servidor.yaml up -d --wait --wait-timeout 60
docker compose -f docker/compose.servidor.yaml ps
docker compose -f docker/compose.servidor.yaml logs --tail 100 frontend
curl --fail "http://127.0.0.1:${UFU_PORTA}/metadados"
```

O serviço inicia diretamente a web e permanece ativo sem menu/TTY. Cria base
vazia somente se ausente; `/dados` usa volume nomeado do projeto, com usuário
65534, e sobrevive à recriação. O volume antigo de outra configuração não é
importado automaticamente. Para copiar dados, valide uma cópia e combine a
origem/destino antes de alterar o volume. Não execute `down -v`.

O modelo versionado publica a porta somente no loopback do servidor.
Na instalação da UFU observada em 27/11, a saída do Docker mostra
`0.0.0.0:2229->2229/tcp`; essa diferença operacional está registrada no relatório.
Para uma instalação em loopback, na apresentação remota,
um túnel SSH permite abrir `http://127.0.0.1:2229` no computador local:

```bash
ssh -N -L 2229:127.0.0.1:PORTA_CONFIRMADA USUARIO@HOST
```

Não há autenticação de usuários na aplicação. A publicação em loopback
do modelo versionado não abre acesso público; a instalação observada na UFU
publica em todas as interfaces IPv4. Firewall e controles de rede não foram
auditados nesta conferência.

No modelo versionado, o healthcheck consulta identidade e validade da base
e não há reinício automático. A política de reinício da instalação observada
não foi conferida nesta etapa. Antes/depois do período exigido, registre UTC,
commit, imagem, `StartedAt`, `RestartCount`, estado de saúde, logs e operações
funcionais com dados fictícios. Reinício interrompe a evidência de execução
contínua; saúde pontual não comprova disponibilidade HTTP durante 24h.
A conferência de 27/11 registrou mais de 24 horas de execução pelo `StartedAt`
e pelo relógio do servidor; o relatório do monitor não foi analisado nesta etapa.

Para interromper somente este projeto, use `docker compose -f
docker/compose.servidor.yaml stop frontend`. Para rollback, preserve o volume e
use a tag anterior já existente com `up -d --no-build --wait`; confira antes a
compatibilidade dos dados e a cópia recuperável. Nunca sobrescreva uma tag de
versão usada como evidência.

Validação local: projeto fictício isolado, cadastro HTTP, volume gravável, raiz
somente leitura, healthcheck e JSON idêntico após recriar. A implantação real
foi observada por saída SSH do autor em `10.0.99.150`, com usuário
`12621CBS229`, porta 2229 e contêiner `7f68bae94287`. Consulte o relatório
de 27/11 para os horários e o estado, sem confundir esse registro com os ensaios locais.

## Inicialização Docker e porta 2229 — revisão de 26/11/2026

A imagem passa a iniciar `python -B iniciar_web.py` por padrão, sem stdin/TTY.
`INVENTARIO_HOST=0.0.0.0` vale dentro do contêiner; o Compose publica somente
`127.0.0.1:2229:2229`. O iniciador nativo também usa 2229 e valida a identidade
da base antes de reutilizar a instância. Healthcheck e descoberta Docker foram
alinhados à mesma porta. Não há publicação na rede por esta configuração.

```powershell
Set-Location -LiteralPath 'C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT'
docker compose -f docker/compose.yaml up -d --build frontend
docker compose -f docker/compose.yaml ps
Start-Process 'http://127.0.0.1:2229'
```

`docker compose run --rm inventario` continua sendo o serviço interativo, com
comando explícito para `main.py`. Para usar o terminal do frontend já ativo:

```powershell
docker compose -f docker/compose.yaml exec frontend python -B main.py --terminal
```

“Como deseja iniciar?” seguido de “Inicialização cancelada” ocorria ao executar
o CMD antigo `python main.py` sem uma entrada de terminal. Não era uma falha de
leitura do JSON nem prova de que o serviço frontend ativo havia parado.

No Docker Desktop, crie novamente os contêineres antigos, que guardam o comando
da imagem anterior. Para conservar os sete registros habituais, prefira o Compose
acima ou aponte a montagem para a mesma pasta `dados`. A imagem não contém a
base real; sem montagem persistente, o cadastro fica apenas no contêiner.

No Compose de servidor, `UFU_PORTA` continua explícita. A porta informada pelo
autor nesta revisão é 2229; endereço, acesso e identificação do servidor ainda
precisam ser confirmados. Túnel SSH exige porta local livre: se já houver uma
interface local na 2229, encerre essa interface antes de usar o mesmo endereço
para um túnel. Esta revisão não comprova implantação docente nem 24 horas.
