'use strict';

/**
 * Assistente Edu: abre pelo botão verde (data-chatbot-toggle) e conversa com /api/chat.
 * Todo texto vindo da API é inserido com textContent (nunca innerHTML).
 */
(function () {
  // Em produção a API fica no mesmo domínio. No Live Server (porta 5500), aponta para o back-end local.
  const API_URL = window.EDUCANDO_API_URL ||
    (location.port === '5500' ? 'http://127.0.0.1:8000/api/chat' : '/api/chat');
  const SAUDACAO = 'Oi, tudo bem? Eu sou o Edu, assistente do Educando. Você está precisando de alguma oportunidade?';
  const LINK_VALIDO = /^https:\/\//;

  const botao = document.querySelector('[data-chatbot-toggle]');
  if (!botao) return;

  const painel = document.createElement('section');
  painel.id = 'chatbot';
  painel.className = 'chatbot';
  painel.hidden = true;
  painel.setAttribute('aria-label', 'Assistente Edu');
  painel.innerHTML = `
    <header class="chatbot-header">
      <h2 class="chatbot-title">Edu, assistente do Educando</h2>
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
  // Últimas trocas da conversa, enviadas à API para o Edu entender o contexto. Não são guardadas no servidor.
  const historico = [];

  function rolarParaFim() {
    log.scrollTop = log.scrollHeight;
  }

  function adicionarMensagem(texto, autor) {
    const bolha = document.createElement('div');
    bolha.className = 'chat-' + autor;
    bolha.textContent = texto;
    log.appendChild(bolha);
    rolarParaFim();
    return bolha;
  }

  // Cards do site: um link com nome, tipo, descrição e ação. Estilo embutido no próprio elemento,
  // para que nenhuma regra do CSS geral do template consiga esconder ou apagar o conteúdo.
  function criarTexto(tag, texto, estilo) {
    const el = document.createElement(tag);
    el.textContent = texto;
    Object.assign(el.style, { display: 'block', visibility: 'visible', opacity: '1' }, estilo);
    return el;
  }

  function adicionarOportunidades(lista) {
    lista.forEach(function (op) {
      const temLink = LINK_VALIDO.test(op.link);
      const card = document.createElement(temLink ? 'a' : 'div');
      if (temLink) {
        card.href = op.link;
        card.target = '_blank';
        card.rel = 'noopener';
      }
      Object.assign(card.style, {
        display: 'block',
        visibility: 'visible',
        opacity: '1',
        boxSizing: 'border-box',
        width: '100%',
        padding: '12px 14px',
        background: '#ffffff',
        borderRadius: '10px',
        boxShadow: '0 6px 15px rgba(0, 0, 0, 0.06)',
        color: '#222222',
        textDecoration: 'none',
        fontFamily: "'Poppins', sans-serif",
      });

      const meta = [op.tipo, op.local].filter(Boolean).join(' · ');
      card.append(
        criarTexto('span', meta, { fontSize: '11px', color: '#777777', marginBottom: '3px' }),
        criarTexto('span', op.titulo, {
          fontFamily: "'League Spartan', sans-serif", fontSize: '15px', fontWeight: '600',
          color: '#1a1a1a', lineHeight: '1.35', marginBottom: '4px',
        }),
        criarTexto('span', op.descricao, { fontSize: '13px', color: '#333333', lineHeight: '1.5' })
      );
      if (temLink) {
        card.appendChild(criarTexto('span', 'Ver oportunidade →', {
          marginTop: '8px', fontSize: '13px', fontWeight: '500', color: '#1ab394', textDecoration: 'underline',
        }));
      }
      log.appendChild(card);
    });
    rolarParaFim();
  }

  function adicionarRotulo(texto) {
    const rotulo = document.createElement('p');
    rotulo.className = 'chat-links-titulo';
    rotulo.textContent = texto;
    log.appendChild(rotulo);
    rolarParaFim();
  }

  // Opções online oficiais: botões de link.
  function adicionarCaminhos(lista, rotulo) {
    const bloco = document.createElement('div');
    bloco.className = 'chat-links';

    const titulo = document.createElement('p');
    titulo.className = 'chat-links-titulo';
    titulo.textContent = rotulo;
    bloco.appendChild(titulo);

    lista.forEach(function (item) {
      if (!LINK_VALIDO.test(item.link)) return;
      const link = document.createElement('a');
      link.href = item.link;
      link.target = '_blank';
      link.rel = 'noopener';
      link.className = 'chat-link';
      link.textContent = item.titulo;
      if (item.descricao) link.title = item.descricao;
      bloco.appendChild(link);
    });

    log.appendChild(bloco);
    rolarParaFim();
  }

  async function enviarMensagem(texto) {
    const mensagem = texto.trim();
    if (!mensagem || ocupado) return;

    ocupado = true;
    enviar.disabled = true;
    adicionarMensagem(mensagem, 'user');
    input.value = '';
    const pensando = adicionarMensagem('Edu está pensando...', 'bot chat-typing');

    try {
      const resposta = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: mensagem, historico: historico.slice(-6) }),
      });
      pensando.remove();

      if (resposta.status === 429) {
        adicionarMensagem('Recebi muitas mensagens em pouco tempo. Aguarde um minuto e tente de novo.', 'bot');
        return;
      }
      if (!resposta.ok) throw new Error('HTTP ' + resposta.status);

      const dados = await resposta.json();
      adicionarMensagem(dados.texto, 'bot');
      historico.push({ papel: 'usuario', texto: mensagem.slice(0, 300) });
      historico.push({ papel: 'edu', texto: String(dados.texto).slice(0, 300) });
      while (historico.length > 12) historico.shift();
      if (Array.isArray(dados.oportunidades) && dados.oportunidades.length) {
        adicionarRotulo('No nosso site:');
        adicionarOportunidades(dados.oportunidades);
      }
      if (Array.isArray(dados.opcoes_online) && dados.opcoes_online.length) {
        adicionarCaminhos(dados.opcoes_online, 'Opções online:');
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
