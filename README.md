# Trabalho_ufu.1

# Sistema de Inventário de Segurança — Ativos de TI e Vulnerabilidades

Trabalho da disciplina de Cibersegurança (UFU) — Sprints 1 e 2.

## Como executar

O programa cria automaticamente um arquivo `ativos_db.txt` (JSON) na primeira
gravação, que funciona como a base de dados da aplicação. Não é necessário
instalar nenhuma biblioteca externa (usa apenas a biblioteca padrão do Python)
e o código é compatível com Python 3.8 ou superior.

### Pelo terminal

```bash
python3 main.py
```

### Pelo VS Code

1. Abra esta pasta inteira no VS Code (`File > Open Folder...`), não apenas
   um arquivo — os módulos (`tipos.py`, `modelos.py`, `banco_dados.py`)
   precisam estar na mesma pasta que `main.py` para os `import` funcionarem.
2. Instale a extensão oficial **Python** (Microsoft), se ainda não tiver.
3. No canto inferior direito, selecione o interpretador Python instalado na
   sua máquina (`Ctrl+Shift+P` → "Python: Select Interpreter").
4. Abra `main.py` e pressione **F5** (ou use o ícone de "Run and Debug" na
   barra lateral) — a pasta `.vscode/` já traz uma configuração pronta
   (`launch.json`) que roda o programa no terminal integrado, essencial
   porque o programa usa `input()` para interagir com você.
5. Alternativamente, clique com o botão direito em `main.py` e escolha
   "Run Python File in Terminal".

## Estrutura do projeto

| Arquivo          | Responsabilidade                                              |
| `tipos.py`       | Enums: `TipoAtivo`, `Severidade`, `StatusVulnerabilidade`, + rótulos amigáveis para exibição |
| `modelos.py`     | Classes de domínio `Ativo` e `Vulnerabilidade`                  |
| `banco_dados.py` | Persistência em arquivo de texto + índices em `dict`            |
| `main.py`        | Menu textual e todas as operações CRUD                          |

## Mapeamento para os requisitos da Tabela 1

| Req. | Onde está implementado |
| 1 — Menu + tratamento de erros | `main.py`: `ler_inteiro`, `ler_texto`, `ler_sim_nao`, `escolher_enum`, `try/except` no loop principal |
| 2 — Enum de tipos de ativo (≥4 categorias, com código) | `tipos.py`: `TipoAtivo` |
| 3 — Cadastro gravado em arquivo | `banco_dados.py`: `salvar()` / `_carregar()` (JSON em `ativos_db.txt`) |
| 4 — Busca por ID ou hostname | `banco_dados.py`: `buscar_por_id`, `buscar_por_hostname` |
| 5 — Atualização de ativo | `main.py`: `atualizar_ativo` |
| 6 — Remoção em cascata | `main.py`: `deletar_ativo` + `banco_dados.py`: `remover` |
| 7 — Cadastro de vulnerabilidade a qualquer momento | `main.py`: `cadastrar_vulnerabilidade` |
| 8 — Visualização de vulnerabilidades | `main.py`: `visualizar_vulnerabilidades` |
| 9 — Uso de dict (hash map) | `banco_dados.py`: `ativos_por_id`, `ativos_por_hostname` |
| 10 — Git com múltiplas branches e merge | Ver seção abaixo (depende de você) |

## Requisito 10 — Roteiro de Git sugerido

```bash
git init
git add .
git commit -m "Estrutura inicial: enums e modelos"

git checkout -b feature/cadastro-ativos
# ... trabalhe no CRUD de ativos, faça commits ...
git checkout main
git merge feature/cadastro-ativos

git checkout -b feature/vulnerabilidades
# ... trabalhe no CRUD de vulnerabilidades, faça commits ...
git checkout main
git merge feature/vulnerabilidades

git remote add origin <url-do-seu-repositorio>
git push -u origin main
```

Isso já demonstra o uso de mais de 2 branches (`main` + 2 `feature/*`) com
merges de volta para a `main`, como pedido no requisito 10.

## Possíveis melhorias (para elegância técnica / capricho)

- Adicionar testes automatizados (ex.: `unittest` ou `pytest`) para as
  funções de `banco_dados.py`.
- Adicionar exportação/relatório em CSV das vulnerabilidades por severidade.
- Adicionar um campo de descrição livre no ativo.
- Usar `logging` em vez de `print` para mensagens de erro internas.
