# Plano: frontend de consulta do inventário

Escopo aprovado: etapas 1, 2 e 3 da proposta de 25/11/2026, no checkout oficial.

1. Consulta HTML de ativos, vulnerabilidades, dependências e riscos com Python.
   Reutilizar a leitura sem escrita e o cálculo independente; dados fictícios.
   Arquivos: app_web.py, templates/inventario.html, static/inventario.css,
   exemplos/inventario_web.json, requirements.txt, tests/test_app_web.py.
   Aceite: quatro ativos e riscos do cenário manual visíveis na página.
2. Estados de erro, vazio e segurança da consulta.
   Arquivo: tests/test_app_web.py; ajustes mínimos na implementação se necessários.
   Aceite: cálculo falha sem ocultar ativos; base falha gera HTTP 503; apenas []
   significa vazio; leitura não cria backup, trava ou temporário e preserva bytes.
3. Imagem independente, Compose e operação.
   Arquivos: docker/Dockerfile, docker/compose.yaml, README.md, OPERACAO.md,
   registro de validação e este acompanhamento.
   Aceite: frontend no navegador, suíte completa em Windows e Linux, imagem sem
   montagem do código, Compose habitual com frontend e CLI preservada.

Decisões: Flask com templates escapados; Waitress para servir em Windows/Linux;
sem JavaScript; porta publicada em loopback; contêiner frontend sem privilégios
com filesystem somente leitura. O exemplo web é um retrato do lote fictício
original, validado por teste. Sem NVD automático nem alterações no núcleo.

Pendências de escopo: orientação complementar sobre CRUD no navegador.
Implantação na faculdade e 24 horas ficam para depois. Fazer um commit ao
concluir as três etapas, preservar os dois arquivos não rastreados originais e
não fazer push sem autorização específica.
