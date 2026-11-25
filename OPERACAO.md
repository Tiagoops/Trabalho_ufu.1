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
