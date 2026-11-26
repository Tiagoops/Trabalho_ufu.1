GUIA DE APRESENTAÇÃO — REVISÃO 26/11/2026
Código: 2e1195e. Slides: apresentacao/Inventario_UFU.pptx.
Materiais locais no workspace: outputs/revisao_final_2026-11-26/.
O PowerPoint e o replay foram entregues localmente; não fazem parte do código-fonte versionado.
Este material prepara o aluno; não comprova ensaio oral nem revisão por pares.
O tutor pede programa em execução. Slides são apoio; use dados fictícios.

PREPARAÇÃO
Set-Location -LiteralPath 'C:\Users\Nitro\Downloads\Trabalho_UFU_COMMIT'
docker run --rm -it trabalho-ufu:local python -B main.py --demo
Deixe modelos.py, banco_dados.py, matematica/risco.py e docker/Dockerfile abertos.
Para a web habitual: http://127.0.0.1:8000. Não apagar ou editar dados reais
para demonstrar. Use ambiente fictício separado ou o modo --demo.

ROTEIRO — 300 SEGUNDOS PLANEJADOS
0:00–0:25 (25s): problema, entradas e solução Python compartilhada por CLI/web.
0:25–1:15 (50s): Ativo.criar, herança/composição e orientações polimórficas.
1:15–2:00 (45s): array JSON, IDs estáveis, recarga, temporário e rollback.
2:00–3:30 (90s): M, v, A, b=Mv, (I-A)x=b e conta manual dos quatro ativos.
3:30–4:15 (45s): interface, CVSS, categoria e confirmação de aplicabilidade.
4:15–5:00 (45s): Docker, evidências, WinError 5 e requisito das 24h em aberto.
Tempos são planejamento; o aluno ainda deve medir uma execução oral real.

PLANO ALTERNATIVO
Abra apresentacao/demonstracao_gravada.html sem internet e clique Reproduzir.
É uma gravação real de terminal, com 44.27s, 66 eventos
e código de saída 0. O arquivo demonstracao.cast guarda os eventos originais.
Sem narração do aluno; não apresentar o replay como ensaio oral realizado.

PERGUNTAS PARA TREINAR
1. Onde está o polimorfismo?
Na chamada comum orientacoes_tratamento(), com resultados específicos por classe;
from_dict também reconstrói o tipo concreto pela fábrica.
2. Enum sozinho demonstra herança?
Não. TipoAtivo identifica categorias; subclasses e comportamento demonstram POO.
3. Por que uma lista JSON?
Representa o conjunto de ativos conforme a Tabela 1; cada objeto preserva seus
IDs, ocorrências e vínculos. to_dict/from_dict fazem a tradução e reconstrução.
4. Por que temporário e os.replace?
Para preparar o documento completo antes de substituir a base. flush/fsync
precedem a troca. Falha não é sucesso; existe rollback. Queda de energia não foi certificada.
5. O que causa o WinError 5?
A recusa de acesso na substituição foi reproduzida fora da aplicação. Um handle
do destino sem FILE_SHARE_DELETE reproduz exatamente o erro. O responsável
pelas recusas espontâneas ainda depende de captura de I/O; não culpar um processo sem evidência.
6. M, v e A têm quais dimensões e significado?
M é n×m, ativos por ocorrências; v tem m severidades; A é n×n. A[i,j] transmite
risco de j para i, porque i depende de j.
7. Por que não calcular a inversa ou apenas o determinante?
solve(I-A,b) resolve diretamente. rho(A)<1 certifica estabilidade/invertibilidade;
condição e resíduo ajudam a controlar a confiabilidade numérica.
8. Ativo sem vulnerabilidade pode ter risco?
Sim: o ativo 40 tem b=0 e recebe 0,25×16,92=4,23 pela dependência do ativo 10.
Sem ocorrências e sem dependências, b e x são zero com os dados registrados.
9. Categoria ou nome mudam CVSS? Por que 9,8 se repete?
Categoria e descrição organizam o registro; o vetor Base determina a nota. O
mesmo vetor produz o mesmo resultado. Use critérios técnicos da falha.
10. CVE encontrada prova que o ativo está vulnerável?
Não. É necessário conferir produto/versão/configuração e aplicabilidade. O
cadastro exige confirmação; não existe varredura automática no inventário.
11. Peso de serviço é indisponibilidade percentual?
São grandezas separadas. Peso é serviços fornecidos/total necessário; os tempos
observados servem de registro e não são multiplicadores do risco.
12. Build Docker comprova 24h?
Não. Precisa executar a versão identificada no servidor autorizado, registrar
período e verificações funcionais. Essa etapa continua adiada.

ENSAIO PELO ALUNO
Execute sem ler as respostas; cronometre 5 minutos; explique a conta de x10 e
x40; peça a um colega perguntas e comentários. Registre tempo real e pontos
de dificuldade. Não registrar essa atividade como concluída antes de fazê-la.
