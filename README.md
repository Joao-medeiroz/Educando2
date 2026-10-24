# Educando

Portal de oportunidades educacionais e profissionais (cursos, estágios e vagas, idiomas e intercâmbios).

## Estrutura

```
educando/
├── index.html, sobre.html, oportunidades.html, contato.html, favicon.svg
├── assets/
│   ├── css/style.css
│   ├── js/                 scripts da interface e dados (dados-oportunidades.js é a fonte)
│   └── images/             organizadas por uso: logo, categorias, oportunidades, noticias,
│                           home, sobre, ilustracoes
├── backend/                chatbot (FastAPI + Gemini)
│   ├── app/                código do back-end
│   ├── data/oportunidades.json   gerado a partir do JS (não edite à mão)
│   ├── scripts/exportar_oportunidades.js
│   ├── tests/
│   ├── server.py           ponto de entrada
│   └── requirements*.txt
└── docs/guia-de-estilo.md
```

## Como atualizar as oportunidades

1. Edite apenas `assets/js/dados-oportunidades.js`.
2. Na raiz do projeto, rode `node backend/scripts/exportar_oportunidades.js`.
3. Confirme com `node backend/scripts/exportar_oportunidades.js --verificar`.

Antes de publicar, rode o `--verificar` junto com os testes do back-end.

## Rodar o back-end no Windows (PowerShell)

Pré-requisitos: Python 3.12 e Node.js instalados e disponíveis no `PATH`.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt

# chave do Gemini, só nesta sessão do terminal
$env:GEMINI_API_KEY = "sua-chave-aqui"

python -m pytest -q
python -m uvicorn server:app --reload
```

Para testar sem a IA, basta não definir `GEMINI_API_KEY`: saudações e buscas simples continuam funcionando.

Se o PowerShell bloquear a ativação do venv, rode uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Segurança

- A chave do Gemini existe apenas no back-end, em variável de ambiente. Nunca vai para HTML, JS ou Git.
- `.env` está no `.gitignore`.
- A IA só interpreta a mensagem. Oportunidades, links e prazos vêm sempre da base local.

## Limitações conhecidas

- A limitação de frequência é feita em memória, por instância. Em hospedagem serverless, a contagem pode se reiniciar.
- Nenhuma conversa é guardada: cada mensagem é tratada de forma independente.
- A publicação na Vercel ainda precisa ser validada (ver próximos passos).

## Chatbot no site

O botão verde (`data-chatbot-toggle`) abre o assistente, implementado em `assets/js/chatbot.js`. Ele chama `/api/chat` no mesmo domínio. Para testar o front com um servidor em outra porta, defina `window.EDUCANDO_API_URL` antes do script e libere a origem em `ALLOWED_ORIGINS`.

O botão deixou de ser "voltar ao topo". O aparecimento após rolar a página continua igual.

## Próximos passos

- Avaliar a busca na web apenas em uma fase futura.
