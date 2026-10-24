'use strict';

/**
 * Assistente de oportunidades.
 * Abre pelo botão verde (data-chatbot-toggle) e conversa com o back-end em /api/chat.
 * Todo texto vindo da API é inserido com textContent (nunca innerHTML).
 */
(function () {
  const API_URL = window.EDUCANDO_API_URL || '/api/chat';
  const SAUDACAO = 'Olá! Sou o assistente do Educando. Posso buscar cursos, faculdades, estágios e vagas, idiomas e intercâmbios. O que você está procurando?';
  const IMAGEM_VALIDA = /^\.?\/?assets\/images\/[\w\/.-]+$/;
  const LINK_VALIDO = /^https:\/\//;

  const botao = document.querySelector('[data-chatbot-toggle]');
  if (!botao) return;

  const painel = document.createElement('section');
  painel.id = 'chatbot';
  painel.className = 'chatbot';
  painel.hidden = true;
  painel.setAttribute('aria-label', 'Assistente de oportunidades');
  painel.innerHTML = `
    <header class="chatbot-header">
      <h2 class="chatbot-title">Assistente Educando</h2>
      <button type="button" class="chatbot-close" aria-label="Fechar assistente" data-chatbot-close>
        <ion-icon name="close-outline" aria-hidden="true"></ion-icon>
      </button>
    </header>
    <div class="chatbot-log" role="log" aria-live="polite" data-chatbot-log></div>
    <div class="chat-chips" data-chatbot-chips>
      <button type="button" data-sugestao="quero um estágio">Estágios</button>
      <button type="button" data-sugestao="cursos e faculdades">Cursos</button>
      <button type="button" data-sugestao="cursos de idiomas">Idiomas</button>
      <button type="button" data-sugestao="intercâmbio">Intercâmbio</button>
    </div>
    <form class="chatbot-form" data-chatbot-form>
      <label class="visually-hidden" for="chatbot-input">Sua mensagem</label>
      <input id="chatbot-input" type="text" maxlength="500" autocomplete="off"
             placeholder="Digite sua mensagem..." data-chatbot-input>
      <button type="submit" class="chatbot-send" aria-label="Enviar mensagem" data-chatbot-send>
        <ion-icon name="arrow-forward-outline" aria-hidden="true"></ion-icon>
      </button>
    </form>`;
  document.body.appendChild(painel);

  const log = painel.querySelector('[data-chatbot-log]');
  const form = painel.querySelector('[data-chatbot-form]');
  const input = painel.querySelector('[data-chatbot-input]');
  const enviar = painel.querySelector('[data-chatbot-send]');
  let ocupado = false;

  function adicionarMensagem(texto, autor) {
    const bolha = document.createElement('div');
    bolha.className = 'chat-' + autor;
    bolha.textContent = texto;
    log.appendChild(bolha);
    log.scrollTop = log.scrollHeight;
    return bolha;
  }

  function adicionarCartoes(lista) {
    lista.forEach(function (op) {
      const card = document.createElement('article');
      card.className = 'chat-card';

      if (IMAGEM_VALIDA.test(op.imagem)) {
        const img = document.createElement('img');
        img.src = op.imagem;
        img.alt = '';
        img.loading = 'lazy';
        card.appendChild(img);
      }

      const corpo = document.createElement('div');
      corpo.className = 'chat-card-body';

      const tipo = document.createElement('span');
      tipo.className = 'chat-card-tipo';
      tipo.textContent = op.local ? op.tipo + ' · ' + op.local : op.tipo;

      const titulo = document.createElement('h3');
      titulo.className = 'chat-card-titulo';
      titulo.textContent = op.titulo;

      const descricao = document.createElement('p');
      descricao.className = 'chat-card-descricao';
      descricao.textContent = op.descricao;

      corpo.append(tipo, titulo, descricao);

      if (LINK_VALIDO.test(op.link)) {
        const link = document.createElement('a');
        link.href = op.link;
        link.target = '_blank';
        link.rel = 'noopener';
        link.className = 'chat-card-link';
        link.textContent = 'Acessar site oficial';
        corpo.appendChild(link);
      }

      card.appendChild(corpo);
      log.appendChild(card);
    });
    log.scrollTop = log.scrollHeight;
  }

  async function enviarMensagem(texto) {
    const mensagem = texto.trim();
    if (!mensagem || ocupado) return;

    ocupado = true;
    enviar.disabled = true;
    adicionarMensagem(mensagem, 'user');
    input.value = '';
    const pensando = adicionarMensagem('Pesquisando...', 'bot chat-typing');

    try {
      const resposta = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: mensagem }),
      });
      pensando.remove();

      if (resposta.status === 429) {
        adicionarMensagem('Muitas mensagens em pouco tempo. Aguarde um minuto e tente de novo.', 'bot');
        return;
      }
      if (!resposta.ok) throw new Error('HTTP ' + resposta.status);

      const dados = await resposta.json();
      adicionarMensagem(dados.texto, 'bot');
      if (Array.isArray(dados.oportunidades) && dados.oportunidades.length) {
        adicionarCartoes(dados.oportunidades);
      }
    } catch (erro) {
      pensando.remove();
      adicionarMensagem('Não consegui responder agora. Tente novamente em instantes.', 'bot');
    } finally {
      ocupado = false;
      enviar.disabled = false;
      input.focus();
    }
  }

  function abrir(aberto) {
    painel.hidden = !aberto;
    botao.setAttribute('aria-expanded', String(aberto));
    if (aberto) {
      if (!log.children.length) adicionarMensagem(SAUDACAO, 'bot');
      input.focus();
    }
  }

  botao.addEventListener('click', function (evento) {
    evento.preventDefault();
    abrir(painel.hidden);
  });

  painel.querySelector('[data-chatbot-close]').addEventListener('click', function () {
    abrir(false);
    botao.focus();
  });

  form.addEventListener('submit', function (evento) {
    evento.preventDefault();
    enviarMensagem(input.value);
  });

  painel.querySelector('[data-chatbot-chips]').addEventListener('click', function (evento) {
    const sugestao = evento.target.closest('[data-sugestao]');
    if (sugestao) enviarMensagem(sugestao.dataset.sugestao);
  });

  document.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && !painel.hidden) abrir(false);
  });
})();
