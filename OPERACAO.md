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

## Consulta web local

O navegador só consulta; cadastro, edição, remoção e a consulta online ao NVD
continuam na CLI. O frontend começa com dados fictícios já incluídos na imagem.
Na raiz do projeto:

```powershell
docker compose -f docker/compose.yaml up -d --build frontend
docker compose -f docker/compose.yaml logs --tail 50 frontend
```

Abra <http://127.0.0.1:8000>. Para encerrar somente o frontend:

```powershell
docker compose -f docker/compose.yaml stop frontend
```

Para executar sem Docker, com Python 3.11 ou superior:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONDONTWRITEBYTECODE = '1'
.\.venv\Scripts\waitress-serve.exe --listen=127.0.0.1:8000 --call app_web:create_app
```

Encerre com Ctrl+C. O Waitress serve a aplicação sem habilitar o depurador do
Flask. Sem `INVENTARIO_ARQUIVO`, lê `exemplos/inventario_web.json` e identifica
a demonstração na tela. Para consultar outra base persistida, defina antes de
iniciar o servidor (comece com uma cópia fictícia):

```powershell
$env:INVENTARIO_ARQUIVO = 'C:\caminho\ficticio\inventario.json'
```

Essa variável pertence ao processo do servidor; o navegador não escolhe o
arquivo. Reinicie o servidor para trocar o caminho. A base é relida em cada
consulta. Arquivo ausente ou inválido mostra inventário indisponível, sem
recuperação nem backup automático; `[]` válido mostra nenhum ativo cadastrado.
Uma falha somente no risco preserva a listagem e os detalhes.

No Docker, para uma base diferente, monte a pasta que a contém como somente
leitura e aponte `INVENTARIO_ARQUIVO` para o caminho dentro do contêiner. Monte
a pasta inteira para que o manifesto de migração, se existir, também possa ser
consultado. O Compose padrão não monta a base real e não precisa dessa mudança.
Ao voltar ao exemplo local padrão, remova a variável do terminal:

```powershell
Remove-Item Env:INVENTARIO_ARQUIVO -ErrorAction SilentlyContinue
```

A interface não possui autenticação; mantenha a porta em `127.0.0.1`.
Exposição em rede e implantação na faculdade exigem uma etapa própria.

Para validar os estados com bases temporárias fictícias:

```powershell
.\.venv\Scripts\python.exe -B -m unittest tests.test_app_web -v
.\.venv\Scripts\python.exe -B -m unittest discover -v
docker compose -f docker/compose.yaml run --rm -T inventario python -B -m unittest discover -v
```
