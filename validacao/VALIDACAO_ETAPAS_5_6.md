# Etapas 5 e 6 — conferência de 26/11/2026

Código conferido: `0b8b900`. Esta rodada altera documentação e evidências;
não altera o programa, dependências, imagem ou base da apresentação.

## Etapa 6 — evidências acadêmicas conferidas

### Material S3_09

O autor informou nesta conversa que possui a matéria no caderno e que não
precisa apresentar esse material ao professor. A localização foi esclarecida;
a busca por um relatório digital deixa de ser pendência da apresentação.
O conteúdo do caderno não foi inspecionado nem certificado como exercício resolvido.

O enunciado `Trabalho_2.pdf`, página 3, seção 5.B, foi relido: a apresentação
exige o código-fonte no repositório, em execução no computador; não exige
documento adicional. SHA256 do PDF:
`aa99c9ab175005c05b4487046a5d1058981fd7a93fa3be6cee0b41b52b255685`.

O acompanhamento [S3_09](https://app.notion.com/p/4155b20a63e681909a4efa6bc8e365ad)
registra estudo de transformações, núcleo/imagem e cenário de três equipamentos.
É evidência do planejamento/checklist histórico, não auditoria do caderno.
A avaliação de trabalhos diários permanece distinta da entrega do programa.

### Git, branches, PRs e CI

Conferência somente de leitura do checkout oficial, sem criar histórico:
25 commits alcançáveis antes deste commit documental, 0 commits de merge,
histórico não shallow e branch local main. Referências e amostra do histórico
estão em `evidencias_etapas_5_6_2026-11-26/conferencia_academica.json`.

A API pública do GitHub respondeu HTTP 200, sem token/cookie, para repositório,
branches, PRs e workflows: repositório público, uma branch main em bd1eacd,
0 PRs abertos/fechados e 0 workflows. As respostas não indicaram página seguinte.
Não havia workflow local. Branches apagadas ou atividades em outros repositórios
não podem ser descartadas por essa conferência.

O cartão [S3_08](https://app.notion.com/p/4155b20a63e681bca115f53112a70a13)
prevê PR, revisão e CI como estudo/entregável da sprint. Essas evidências não
foram encontradas. Não foram criadas retroativamente nem marcadas como feitas.
Isso não acrescenta requisito à Tabela 1 do programa; a avaliação diária do
tutor continua independente, conforme o enunciado.

### Acesso ao código

[Repositório público](https://github.com/Tiagoops/Trabalho_ufu.1) confirmado sem
autenticação. Não é necessário conceder convite para ler código público.
A conferência não testa a rede/dispositivo do docente. A main pública consultada
continua em bd1eacd; 0b8b900 e este commit documental dependem de push autorizado.
O prazo registrado no enunciado é 27/11/2026. Não houve push nesta etapa.

## Etapa 5 — validação visual ainda parcial

Foi criada instância exclusiva `ufu-ensaio-final-20261126`, somente em loopback
na porta fictícia 52257, com JSON vazio em pasta de ensaio exclusiva. A página
Importar JSON abriu no Chrome e exibiu o seletor e o botão de validar o lote.

A tentativa anterior do seletor automatizado falhara por ausência de acesso a
URLs de arquivos na extensão. Nesta rodada tentou-se o seletor nativo, sem
mudar permissões. Ao selecionar a janela do Chrome, o controle de computador
encerrou a sessão porque não conseguiu identificar com segurança a URL no
Windows. Não houve nova tentativa de contornar esse bloqueio.

Consequência: upload visual e medições de layout em telas pequenas NÃO foram
concluídos. O bloqueio é da ferramenta de controle; não demonstra falha da
aplicação. A revisão estática confirmou meta viewport, media queries de 650/1000
px, quebra da navegação e rolagem de tabelas. Isso não comprova aparência nem
ausência de cortes em 320/768 px. Não foram produzidas capturas de validação.

Complemento automatizado, sem alegação de ensaio visual: 10 testes existentes
de transferências e IDs passaram em 0,945 s, com bases fictícias. Cobrem prévia,
confirmação, documento inválido, duplicidade, token adulterado, IDs incompatíveis,
CSV, dependências, risco e consulta sem efeitos de escrita. O HTTP real da
rodada anterior continua em `evidencias_etapas_1_4_2026-11-26/importacao_http.json`.

Para concluir esta etapa falta repetir a seleção de um lote fictício válido e
um inválido no navegador e observar início/formulários/tabelas em larguras
320 e 768 px, quando o controle do navegador estiver disponível. Nenhuma
alteração de segurança do Chrome foi feita.

## Preservação e pendências

Os sete ativos da apresentação permaneceram idênticos, SHA256
`8fb968248a95733c06dfe5c938901cac25790ec5454f51ff7c9830a33b736763`.
O contêiner de ensaio foi parado após a conferência; seus dados foram preservados.
O Dockerfile da raiz e `tatus --short` ficam fora do commit.

A conferência da etapa 6 foi realizada, com os limites acima. A etapa 5 continua
parcial. Push autorizado, implantação docente, 24h e ensaio oral de cinco minutos
continuam pendentes. Não foi repetida a suíte completa: não houve mudança de código.
