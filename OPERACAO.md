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
docker compose -f docker/compose.yaml run --rm -p 127.0.0.1:8000:8000 inventario
```

Escolha 1 e abra <http://127.0.0.1:8000>. Não execute esse comando com a porta
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

Abra <http://127.0.0.1:8000>, clique **Cadastrar ativo**, preencha os cinco campos
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
O servidor local continua usando Waitress, na porta 8000 em loopback. Encerre
com Ctrl+C. Não execute junto com outro servidor na mesma porta.

`INVENTARIO_ARQUIVO` define o caminho no servidor. `iniciar_web.py` habilita o
cadastro nesse caminho e inicializa um arquivo ausente com uma lista vazia;
nunca sobrescreve um arquivo existente. Para apenas consultar, sem inicializar
nem habilitar o cadastro, mantenha o comando anterior:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --call app_web:create_app
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
