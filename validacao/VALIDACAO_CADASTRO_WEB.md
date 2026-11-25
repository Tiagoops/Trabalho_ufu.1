# Validação do cadastro web - 25/11/2026

## Entrega

Incremento sobre `a3800fef972a459373840a7d3e19fb6bc0ee53bf`.
A interface mantém botões e formulários. Foram implementados o botão Cadastrar
ativo, o formulário de cinco campos, Salvar ativo e Cancelar. A página usa HTML
renderizado pelo Flask, sem terminal embutido nem novas dependências.

O cadastro válido usa `Ativo.criar` e `BancoDeDados.adicionar`, preservando POO,
validações, trava cooperante, detecção de snapshot desatualizado, rollback e
substituição atômica da persistência existente. A mensagem de sucesso só é
emitida após a gravação confirmada. O novo ativo começa sem vínculos.

`BancoDeDados(..., recuperar=False)` recusa base inválida, ausente, inacessível
ou com migração pendente sem criar backup. A CLI mantém a recuperação padrão.
Consultas e abertura/cancelamento do formulário continuam sem escrita.

## Testes automatizados

- Windows / Python 3.11.15: 200 testes, sem falhas; 199 aprovados e um caso de
  link simbólico pulado pelo teste existente por limitação do ambiente.
- Linux / Python 3.12.12, imagem independente com apenas os testes montados:
  200 testes aprovados, sem skips.
- Compose habitual, serviço inventario: 200 testes aprovados.
- 14 testes novos em tests/test_cadastro_web.py, aprovados também isoladamente
  no Windows e no Linux após a revisão final.

Cobertura dos novos testes: cadastro e reconstrução da classe Notebook;
campos inválidos com valores preservados; ID e hostname repetidos; proteção
contra envio sem token válido ou de outra sessão; token não ASCII recusado;
modo de consulta e exemplo versionado protegidos contra gravação; GET e
cancelamento sem escrita; base inválida/ausente/migração pendente sem backup;
falha no replace sem sucesso falso; conflito com outro escritor sem perder o
cadastro concorrente; escape de HTML; inicialização sem sobrescrever a base.

Uma mutação controlada removeu o bloqueio do modo leitura. O teste correspondente
falhou com 200 em vez de 403. O código original foi restaurado e os 14 testes
passaram nos dois sistemas. A revisão também corrigiu um token não ASCII que
inicialmente gerava erro 500; agora retorna 400 sem gravar.

## Navegador real

Edge 158.0.4370.33, perfil isolado, dados fictícios, em http://127.0.0.1:8000.

- Botão Cadastrar ativo abre o formulário com os oito tipos da enumeração.
- Cancelar após preencher os campos conserva a contagem de quatro ativos.
- ID 10 repetido é recusado com HTTP 400; campos permanecem para correção.
- Cadastrado o exemplo ID 9001, hostname demo-notebook-web, tipo Notebook.
- Responsável Pessoa fictícia; setor Laboratório fictício.
- A listagem passou de quatro para cinco ativos e confirmou a gravação.
- Recarregar a página manteve o novo ativo.
- Formulário verificado em 320, 768, 1024 e 1440 pixels sem transbordamento.
- Estrutura acessível e capturas de desktop/celular inspecionadas.
- Nenhum erro JavaScript, requisição interrompida ou aviso inesperado no console.
  O HTTP 400 da duplicidade foi intencional.

A tela de cadastro foi aberta também no navegador do aplicativo para o usuário.
As capturas e o roteiro local de navegador ficam fora do repositório. Os testes
automatizados e este registro fazem parte da entrega clonável.

## Docker e persistência

Imagem final trabalho-ufu:local e trabalho-ufu:cadastro-candidato:
`sha256:79f5646c9b24b6f5e16717e60daa8992b184adc485dedd9b1dcd09ab92081bff`.
A anterior permanece em trabalho-ufu:frontend-a3800fe.

O serviço frontend roda como 65534:65534, com filesystem somente leitura e um
volume gravável em /dados. A porta continua publicada apenas em loopback.
O volume docker_frontend_dados guarda inventario.json e a trava cooperante.
A inicialização exclusiva copia o exemplo apenas quando o arquivo não existe.
Um arquivo existente, inclusive inválido, não é substituído na inicialização.

Após o cadastro pelo navegador, o contêiner foi recriado com --force-recreate.
A assinatura SHA-256 do JSON permaneceu idêntica. O ativo 9001 foi recarregado
como Notebook e a contagem permaneceu em cinco. O arquivo de exemplos versionado
foi comparado ao conteúdo do commit anterior e permaneceu inalterado.

## Limites e pendências

Este incremento entrega cadastro de ativos e consulta. Edição, remoção e as
outras operações do menu continuam na CLI para os próximos incrementos.
A base fictícia do frontend é separada de ativos_db.txt da CLI.

Não há autenticação, exposição em rede, implantação na faculdade ou teste de
24 horas. A chave temporária do processo invalida formulários abertos antes de
um reinício; recarregue-os. A primeira cópia do exemplo pode ficar incompleta
se o processo for interrompido, mas essa base inválida é preservada e bloqueia
cadastros; não há recuperação automática. As falhas intermitentes anteriores
de gravação no Windows não foram diagnosticadas neste incremento. Não há push.

Referências: https://flask.palletsprojects.com/en/stable/web-security/ e
https://docs.docker.com/engine/storage/volumes/ .
