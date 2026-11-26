# Inicialização Docker e porta 2229 — 26/11/2026

Revisão sobre 402f859. O commit que contém este relatório identifica a entrega.
Porta solicitada pelo autor: 2229. Mantido acesso somente em loopback.

## Causa confirmada

Os contêineres iniciados pelo autor executavam o CMD antigo `python main.py`,
sem stdin interativo, publicação de porta ou montagem de dados. O seletor de
interface recebia EOF e encerrava com “Inicialização cancelada”, código 0.
O frontend Compose, que tinha comando explícito `iniciar_web.py`, permanecia
ativo. O cancelamento não demonstrava falha da base ou do cálculo de risco.

O cenário foi reproduzido com a imagem anterior e dados fictícios: o teste
esperava servidor persistente e encontrou o menu seguido de cancelamento.

## Correção e preservação dos modos de uso

- `docker/Dockerfile`: CMD passa a `python -B iniciar_web.py`; define endereço
  de escuta dentro do contêiner e caminho `/dados/inventario.json` por ambiente.
- Porta interna, EXPOSE, publicação local, iniciador nativo, URL de abertura,
  descoberta de identidade Docker e healthcheck passam a usar 2229.
- `docker/compose.yaml`: frontend publica `127.0.0.1:2229:2229`; o serviço
  `inventario` tem comando explícito para `main.py`, preservando o menu interativo.
- `docker/compose.servidor.yaml`: mantém projeto, imagem e porta externa
  explicitamente exigidos; o destino interno e healthcheck usam 2229.
- O seletor continua em `python main.py`; `--terminal` continua direto no menu.
  Nenhuma classe, fórmula, política de confirmação ou dado cadastrado foi alterado.

A imagem não contém a base real. Contêiner independente exige montagem em
`/dados` para persistência; o Compose habitual continua montando a pasta original.
Contêiner antigo guarda o CMD e a imagem usados na sua criação: atualizar uma
tag não reconfigura um contêiner que já existe. É necessário recriá-lo.

## Verificações realizadas

| Verificação | Resultado |
|---|---|
| Teste novo de porta antes da mudança | Falhou: tentou 8000 em vez de 2229, reproduzindo a regressão |
| Casos focados de início, identidade e status | 28 testes aprovados |
| Suíte Windows | 282 executados, 281 aprovados e 1 omitido por plataforma; 30,194 s |
| Suíte Linux independente | 282 executados, 280 aprovados e 2 omitidos por plataforma; 17,401 s |
| CMD real da imagem sem stdin/TTY | Servidor permaneceu ativo, HTTP 200 |
| Cadastro HTTP fictício 9907 | Gravado e recarregado |
| CLI explícita no contêiner web | `main.py --terminal`, saída 0, mesma base fictícia |
| Reinício do contêiner de ensaio | HTTP 200 e JSON fictício idêntico |
| Configuração dos dois Composes | Resolvida e conferida, com porta e healthcheck alinhados |
| Frontend habitual após substituir | HTTP 200 em início, metadados, ativo 70 e seu risco |
| Reuso pelo iniciador nativo | Reconheceu a mesma base na porta 2229, sem criar outro servidor |

O primeiro verificador de reinício continuou consultando a porta efêmera antiga:
Docker atribuiu outra porta após reiniciar. O teste foi corrigido para reinspecionar
a publicação e passou. Na rodada final, a porta fictícia mudou de 57457 para
57496; a aplicação seguiu usando 2229 internamente. A publicação habitual é fixa,
2229. A falha anterior do verificador foi preservada nas evidências.

Imagem final: `sha256:5e8c3b402d1520c7704528bf0eff21433661db23ddc307dc75e715e8f1e1ecb1`.
Imagem anterior preservada: `trabalho-ufu:antes-inicio-2229-402f859`.
O frontend habitual publica somente `127.0.0.1:2229`; não publica mais 8000.

Os sete ativos habituais foram preservados, SHA256 da base:
`8fb968248a95733c06dfe5c938901cac25790ec5454f51ff7c9830a33b736763`.
Ativo 70: risco próprio 0 e propagado 7,35. Os contêineres de smoke foram
removidos e os diretórios temporários fictícios, limpos; as evidências permanecem.

Registros e teste reproduzível em `evidencias_inicio_docker_2229_2026-11-26/`.
O Dockerfile da raiz e `tatus --short` permanecem fora do commit.

## Operação atual

```powershell
Set-Location -LiteralPath 'C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT'
docker compose -f docker/compose.yaml up -d --build frontend
Start-Process 'http://127.0.0.1:2229'
```

Para terminal com a mesma base do frontend:

```powershell
docker compose -f docker/compose.yaml exec frontend python -B main.py --terminal
```

Essa validação não é execução de 24 horas nem implantação no servidor docente.
Não houve nova inspeção visual: o CSS validado anteriormente está inalterado;
esta mudança trata inicialização e porta. Não houve push.
