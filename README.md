# Educando

Portal de oportunidades educacionais e profissionais (cursos, estágios e vagas, idiomas e intercâmbios), com o assistente **Edu**.

## Estrutura

```
educando/
├── frontend/                  site público (HTML, CSS e JavaScript puro)
│   ├── index.html, sobre.html, oportunidades.html, contato.html, favicon.svg
│   └── assets/
│       ├── css/style.css
│       ├── js/                chatbot.js (o Edu), dados-oportunidades.js (fonte das oportunidades)
│       └── images/            logo, categorias, oportunidades, noticias, home, sobre, ilustracoes
├── backend/                   API do Edu (FastAPI + Gemini)
│   ├── app/                   código: config, rules, opportunities, gemini_client, main, schemas
│   ├── data/oportunidades.json   gerado a partir do JS (não edite à mão)
│   ├── scripts/exportar_oportunidades.js
│   ├── tests/                 testes automatizados (sem chamadas reais ao Gemini)
│   ├── server.py              ponto de entrada local (uvicorn)
│   ├── requirements-dev.txt   dependências de teste
│   └── .env.example           modelo do arquivo de configuração local
├── api/index.py               ponto de entrada da Vercel (chama backend/app)
├── requirements.txt           dependências de produção (a Vercel lê este arquivo)
├── vercel.json                publicação: site em frontend/, API em api/
└── README.md
```

## Pré-requisitos

- **Python 3.12**
- **Node.js** (só para atualizar a base de oportunidades)
- **Git**
- Uma **chave do Gemini** (Google AI Studio), se quiser que a IA responda frases livres

## Rodar localmente (Windows, PowerShell)

Abra o PowerShell na pasta `educando`.

```powershell
# 1. Ambiente virtual e dependências
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt

# 2. Testes (não gastam cota do Gemini)
python -m pytest -q

# 3. Chave do Gemini, só nesta janela do terminal
$env:GEMINI_API_KEY = "sua-chave-aqui"

# 4. Subir a API na porta 8000
python -m uvicorn server:app --reload --port 8000
```

Sem `GEMINI_API_KEY`, o chat continua funcionando para saudações e buscas simples. Frases livres caem nos caminhos úteis.

Para ver o site localmente, abra a pasta `frontend` no VS Code e use **Live Server** (porta 5500). Para o chat conversar com a API local, a origem precisa estar liberada. Antes de subir o uvicorn, rode:

```powershell
$env:ALLOWED_ORIGINS = "http://127.0.0.1:5500"
```

Se o site abrir como `localhost:5500`, troque por `http://localhost:5500`.

Teste de saúde da API: `http://127.0.0.1:8000/api/saude` deve mostrar `{"status":"ok"}`.

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Para que serve |
|---|---|---|---|
| `GEMINI_API_KEY` | Não (sem ela, a IA fica desligada) | vazio | Chave do Gemini. Nunca coloque no código ou no GitHub. |
| `GEMINI_MODEL` | Não | `gemini-3.5-flash-lite` | Modelo usado. Os nomes mudam; confira em ai.google.dev. |
| `RATE_LIMIT_POR_MINUTO` | Não | `10` | Mensagens por minuto por visitante. |
| `ALLOWED_ORIGINS` | Não | vazio | Origens liberadas para CORS (só para desenvolvimento local). |

Na Vercel, cadastre essas variáveis em **Settings → Environment Variables** (Production e Preview). Depois de alterar, faça um Redeploy sem cache.

## Como o Edu responde

Cada resposta do Edu tem até três partes:

1. **No nosso site**: até 2 oportunidades cadastradas em `dados-oportunidades.js`, com link.
2. **Opções online**: até 2 recursos oficiais curados em `backend/data/recursos_oficiais.json`.
3. **O texto**: escrito pela IA, usando só os nomes dessas listas.

Se não houver oportunidades no site, o Edu diz isso com clareza e mostra as opções online.

O Edu identifica a intenção da mensagem e age de acordo:
- **pedido**: recomenda oportunidades do site e opções online.
- **detalhar**: quando a pessoa pede mais informações sobre uma oportunidade citada na conversa, o Edu explica usando todos os dados cadastrados (tipo, local, categoria e descrição).
- **perfil**: quando a pessoa ainda não sabe o que quer, o Edu faz perguntas (situação atual, se quer estudar ou trabalhar, áreas de interesse) antes de recomendar.
- **direcionar**: quando a pessoa já citou uma área de interesse, o Edu sugere caminhos e pergunta o que ela quer explorar.

Para adicionar uma opção online, edite `backend/data/recursos_oficiais.json`. Use sempre links oficiais e descrições factuais. Não precisa rodar nenhum script.

### Custo em chamadas de IA

- Saudação: sem IA.
- Pedido com categoria clara ("quero um estágio"): 1 chamada, só para redigir.
- Frase livre ou mensagem curta: 2 chamadas (entender no contexto e redigir).
- IA indisponível: textos padrão, sem IA.

O front envia só as últimas trocas da conversa (no máximo 6), para o Edu entender frases como "acho uma boa, pode me indicar". Nada é guardado no servidor.

## Atualizar as oportunidades

1. Edite **somente** `frontend/assets/js/dados-oportunidades.js`. Cada item tem `tipo`, `titulo`, `descricao`, `local`, `link` (site oficial) e `imagem`.
2. Gere o arquivo que o back-end lê:

```powershell
node backend\scripts\exportar_oportunidades.js
```

3. Confira se está sincronizado (também útil antes de publicar):

```powershell
node backend\scripts\exportar_oportunidades.js --verificar
```

Datas e vagas mudam com frequência. Confira sempre o link oficial antes de cadastrar.

## Publicar na Vercel

1. Em **Settings → General → Root Directory**, deixe vazio ou `./`.
2. Confirme que `GEMINI_API_KEY` está cadastrada (e `GEMINI_MODEL`, se quiser).
3. Envie para o GitHub (`git add -A`, `git commit`, `git push`) ou rode `npx vercel --prod`.
4. Teste `https://SEU-DOMINIO.vercel.app/api/saude`. Deve aparecer `{"status":"ok"}`.

A Vercel publica o conteúdo de `frontend/` como site e as funções de `api/` como API. O arquivo `vercel.json` faz essa ligação.

## Solução de problemas

- **405 Method Not Allowed no Live Server:** o chat está chamando o servidor estático. Suba a API (passo 4 acima) e libere a origem em `ALLOWED_ORIGINS`.
- **404 em `/api/saude` na Vercel:** confira o Root Directory e se `api/index.py` e `requirements.txt` estão na raiz do repositório.
- **Frases livres mostram "caminhos que podem ajudar":** a IA não respondeu. Veja em **Logs → Runtime Logs** a linha `Gemini falhou`. Erro 404 indica modelo errado; 429, cota esgotada; 400 ou 403, chave inválida.
- **`ModuleNotFoundError` no pytest:** confirme que o `.venv` está ativado e que você rodou `pip install -r requirements-dev.txt`.

## Segurança

- A chave do Gemini fica somente no servidor, em variável de ambiente.
- `.env` está no `.gitignore` e não deve ser enviado ao GitHub.
- O servidor não registra mensagens nem chaves nos logs, só o tipo do erro.
- Não há login nem armazenamento de conversas. Cada mensagem é tratada de forma independente.
- Limite de mensagens por minuto por visitante, em memória. Em hospedagem serverless, cada instância conta separadamente.

## Próximos passos

- Ampliar a base de oportunidades (cada item é uma linha em `dados-oportunidades.js`).
- Avaliar a busca na web do Gemini apenas numa fase futura, com fontes verificáveis.
