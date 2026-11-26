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

O Compose monta essa pasta em `/app`. Os dados ficam em `ativos_db.txt` na
pasta do computador, junto aos backups e ao eventual manifesto de migração.
Restrinja o acesso a essa pasta e use um escritor por base. Feche a aplicação
antes de alternar entre Windows e Docker sobre a mesma pasta.

## Escolha da interface ao iniciar

Na pasta do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -B main.py
```

Antes de abrir a base, escolha **1 - Acessar interface gráfica** ou
**2 - Continuar no terminal**. A interface gráfica abre o navegador padrão
quando possível. Uma prévia do inventário que já esteja na porta 8000 é
reutilizada. Se for necessário iniciar um servidor novo, o terminal informa
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

A prévia nova usa `dados_web/inventario.json` com dados fictícios, sem tocar
em `ativos_db.txt`. No Compose, essa pasta persiste na montagem do projeto.
O frontend dedicado conserva o volume separado `frontend_dados`. Reutilizar
um servidor já aberto conserva a base que aquele servidor já utiliza.

## Backup e restauração

1. Encerre a CLI, os contêineres do projeto e qualquer migração. Copie
   `ativos_db.txt`, os arquivos `ativos_db.txt.*.bak` e o eventual
   `ativos_db.txt.migracao.json` para uma pasta fora do repositório, com data e
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

O volume `frontend_dados` guarda `/dados/inventario.json` e a trava de escrita.
A primeira inicialização copia o exemplo fictício versionado; reinícios e
recriações do contêiner preservam a base existente, inclusive se estiver
inválida. O exemplo versionado e `ativos_db.txt` da CLI não são sobrescritos.
Remover o volume elimina os cadastros da demonstração. Para parar sem removê-lo:

```powershell
docker compose -f docker/compose.yaml stop frontend
```

Execução local sem Docker, com Python 3.11 ou superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B iniciar_web.py
```

Sem variáveis, cria uma base demonstrativa em `dados_web/inventario.json` apenas
na primeira inicialização. Essa pasta fica fora do Git e do contexto Docker.
O servidor local continua usando Waitress, na porta 8000 em loopback. Encerre
com Ctrl+C. Não execute junto com outro servidor na mesma porta.

`INVENTARIO_ARQUIVO` define o caminho no servidor. `iniciar_web.py` habilita o
cadastro nesse caminho e inicializa um arquivo ausente com dados fictícios;
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

Verificações com arquivos temporários fictícios:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.test_cadastro_web tests.test_app_web -v
.\.venv\Scripts\python.exe -B -m unittest discover -q
docker compose -f docker/compose.yaml run --rm -T inventario python -B -m unittest discover -q
```

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

As bases da CLI, do iniciador local e do serviço frontend são separadas por
padrão. A interface opera exclusivamente em `INVENTARIO_ARQUIVO`; não migra nem
mescla bases automaticamente. Para compartilhar uma base, o operador precisa
configurar explicitamente o mesmo caminho/volume e respeitar os bloqueios da
persistência. Use dados fictícios nesta demonstração.
