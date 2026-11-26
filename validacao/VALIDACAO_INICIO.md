> Registro histórico: a configuração de bases deste documento foi substituída
> em 26/11/2026. CLI e web agora compartilham `dados/inventario.json`.
> Resultados atuais: [VALIDACAO_BASE_UNICA.md](VALIDACAO_BASE_UNICA.md).

# Validação da escolha inicial de interface - 25/11/2026

Base deste incremento: ea1603f062239846601e96fcccb1fae3ffaaf6ef.
A entrega reúne três alterações autorizadas: remoção das setas do ID, visual
inspirado na referência com remoção de Trabalho 2 e escolha da interface.

## Comportamento

Sem argumentos, python main.py oferece antes de abrir a base:

1 - Acessar interface gráfica (navegador)
2 - Continuar no terminal

A opção 1 chama o iniciador web. Um servidor identificado do inventário já
aberto em 127.0.0.1:8000 é reutilizado, inclusive quando responde HTTP 503.
A identificação usa o cabeçalho X-Inventario-App; não é autenticação.
Uma porta usada por outro serviço não provoca inicialização de base nem
abertura de outro servidor. Se estiver livre, o Waitress reserva a porta,
a base fictícia é preparada sem sobrescrever arquivo existente e a abertura
do navegador é solicitada em uma thread separada. O terminal mantém o servidor
em execução. Ctrl+C o encerra; fechar apenas a aba não encerra o processo.

A opção 2 chama o menu existente. --terminal entra nele diretamente e --demo
mantém a demonstração temporária diretamente na CLI, preservando os scripts.
Cancelamento da escolha inicial não abre o banco. Os testes de execução
isolada foram ajustados para --terminal, preservando todas as verificações.

## Resultados

- 12 testes novos em tests/test_inicio.py: escolhas, entrada inválida,
  EOF/Ctrl+C, reaproveitamento, porta de outro serviço, conexão recusada,
  ordem de inicialização, falha no bind, falha na base, ausência de navegador,
  comportamento no Docker e identificação da aplicação mesmo em HTTP 503.
- Windows / Python 3.11.15: 212 testes sem falhas; 211 aprovados e um caso de
  link simbólico pulado pelo teste existente por limitação do ambiente.
- Linux / Python 3.12.12: 212 testes aprovados na imagem independente. Apenas
  os testes foram montados; código, templates e exemplos vieram da imagem.
- Compose habitual: 212 testes aprovados.
- Mutação controlada retirou o ramo de reaproveitamento; o teste correspondente
  falhou. O arquivo original foi restaurado e os 12 testes passaram novamente.

## Comandos completos e servidor real

A imagem independente foi iniciada pelo seu comando padrão com entrada 2 e 0.
O seletor apareceu, abriu o menu completo até a opção 14 e saiu normalmente.

Uma segunda execução isolada recebeu a escolha 1, com base fictícia em /tmp.
A porta do contêiner foi publicada dinamicamente apenas em loopback. O teste
HTTP confirmou o servidor, sua identificação e os quatro ativos fictícios.
Nova chamada ao iniciador reaproveitou o processo sem alterar o JSON. A base
fictícia foi então tornada inválida propositalmente; o servidor respondeu 503
e o iniciador ainda o reconheceu, sem sobrescrever o arquivo nem criar backup.
O contêiner descartável de teste foi encerrado ao concluir.

Após atualizar o frontend habitual, a escolha 1 também foi executada pelo
Python local contra esse servidor real. O pedido de abertura do navegador
foi interceptado por um substituto de teste para não abrir uma janela do sistema.
Não foi criada uma segunda pasta de dados. A assinatura SHA-256 da base do
frontend permaneceu idêntica antes e depois da atualização do contêiner.

A chamada à biblioteca webbrowser e seus casos de falha foram testados com
substitutos. Não se afirma que uma janela do navegador padrão do Windows foi
aberta durante essa validação. No Docker, o programa imprime o endereço para
abertura no computador anfitrião, sem tentar iniciar navegador no contêiner.

## Imagem e operação

Imagem trabalho-ufu:local e trabalho-ufu:inicio-candidato:
sha256:06df68770d21d108fe1faa10f9515696f9fdecb306625e460af5e5076a3d3832.
Imagem anterior preservada em trabalho-ufu:antes-inicio-aacf192149dd.

Para usar a escolha gráfica dentro do Compose, é necessário publicar a porta
na chamada run: -p 127.0.0.1:8000:8000. Sem esse parâmetro, a CLI continua
funcionando, mas a porta web do contêiner não é publicada. Não publicar a mesma
porta de um serviço frontend já em execução. O seletor Python local consegue
reaproveitar esse serviço existente.

A prévia nova usa dados_web/inventario.json por padrão; o frontend dedicado
mantém seu volume frontend_dados. Não há sincronização entre essas bases e a
base real da CLI. O caminho configurado por INVENTARIO_ARQUIVO é respeitado.

As alterações visuais anteriores permanecem limitadas aos templates e ao CSS.
Os 27 testes de cadastro/consulta passaram após sua implementação; os textos e
recursos foram conferidos por HTTP. Não houve nova inspeção visual automática
neste incremento. O ID permanece sem setas e Trabalho 2 não aparece nas telas.

Não houve push, implantação na faculdade, teste de 24 horas nem novo teste real
do NVD. As demais operações ainda não levadas ao navegador permanecem na CLI.
