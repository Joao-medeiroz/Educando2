'use strict';

/**
 * Assistente Edu.
 * - Conversa com /api/chat.
 * - Guarda histórico e perfil no navegador da pessoa (localStorage).
 * - Todo texto vindo da API é montado com elementos e textContent (nunca innerHTML).
 */
(function () {
  const API_URL = window.EDUCANDO_API_URL ||
    (location.port === '5500' ? 'http://127.0.0.1:8000/api/chat' : '/api/chat');
  const SAUDACAO = 'Olá, tudo bem? Eu sou o Edu, assistente do Educando. Como posso te ajudar?';
  const LINK_VALIDO = /^https:\/\//;
  const CHAVE_ESTADO = 'educando_chat_v1';
  const CAMPOS_PERFIL = ['nome', 'area_interesse', 'situacao_atual', 'objetivo', 'expectativa', 'cidade_estado'];
  const MAX_MENSAGENS = 40;

  // Formatação: **negrito**, *itálico*, __sublinhado__ e links (https:// ou www., ou [texto](endereço)).
  const PADRAO_FORMATO = /\[([^\]]+)\]\(\s*((?:https?:\/\/|www\.)[^)\s]+)\s*\)|((?:https?:\/\/|www\.)[^\s)<>"']+)|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\n]+)\*/g;
  const RE_SEPARADOR = /^(\*\s*\*\s*\*+|-{3,}|_{3,})$/;
  const RE_TITULO = /^#{1,6}\s+(.*)$/;
  const RE_ITEM = /^[-•*]\s+(.*)$/;
  const RE_NUMERO = /^\d+[.)]\s+(.*)$/;

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
    </form>
    <div class="chat-apagar"><button type="button" data-chatbot-apagar>Apagar meus dados desta conversa</button></div>`;
  document.body.appendChild(painel);

  const log = painel.querySelector('[data-chatbot-log]');
  const form = painel.querySelector('[data-chatbot-form]');
  const input = painel.querySelector('[data-chatbot-input]');
  const enviar = painel.querySelector('[data-chatbot-send]');

  // ---------- Armazenamento no navegador ----------
  let estado = { mensagens: [], perfil: {} };
  let ocupado = false;

  function carregarEstado() {
    try {
      const salvo = JSON.parse(localStorage.getItem(CHAVE_ESTADO) || 'null');
      if (salvo && Array.isArray(salvo.mensagens)) estado = { mensagens: salvo.mensagens, perfil: salvo.perfil || {} };
    } catch (e) { /* dados corrompidos: começa do zero */ }
  }

  function salvarEstado() {
    try { localStorage.setItem(CHAVE_ESTADO, JSON.stringify(estado)); } catch (e) { /* armazenamento cheio ou bloqueado */ }
  }

  function apagarTudo() {
    try { localStorage.removeItem(CHAVE_ESTADO); } catch (e) { /* ignora */ }
    estado = { mensagens: [], perfil: {} };
    log.innerHTML = '';
    registrar({ tipo: 'texto', autor: 'bot', texto: SAUDACAO });
  }

  // ---------- Montagem segura de elementos ----------
  function criarTexto(tag, texto, estilo) {
    const el = document.createElement(tag);
    el.textContent = texto;
    Object.assign(el.style, { display: 'block', visibility: 'visible', opacity: '1' }, estilo);
    return el;
  }

  function rolarParaFim() { log.scrollTop = log.scrollHeight; }

  function criarLink(texto, url) {
    const endereco = /^www\./.test(url) ? 'https://' + url : url;
    if (!LINK_VALIDO.test(endereco)) return document.createTextNode(texto);
    const link = document.createElement('a');
    link.href = endereco;
    link.target = '_blank';
    link.rel = 'noopener';
    link.textContent = texto;
    return link;
  }

  // Escreve um trecho de texto aplicando negrito, itálico, sublinhado e links.
  function anexarTextoComLinks(elemento, texto) {
    const original = String(texto);
    let ultimo = 0;
    let encontrou;
    PADRAO_FORMATO.lastIndex = 0;
    while ((encontrou = PADRAO_FORMATO.exec(original)) !== null) {
      if (encontrou.index > ultimo) {
        elemento.appendChild(document.createTextNode(original.slice(ultimo, encontrou.index)));
      }
      if (encontrou[1] !== undefined) {
        elemento.appendChild(criarLink(encontrou[1], encontrou[2]));
      } else if (encontrou[3] !== undefined) {
        const url = encontrou[3].replace(/[.,;:!?]+$/, '');
        elemento.appendChild(criarLink(url.replace(/^https?:\/\//, '').replace(/\/$/, ''), url));
        ultimo = encontrou.index + url.length;
        continue;
      } else if (encontrou[4] !== undefined) {
        const forte = document.createElement('strong');
        forte.textContent = encontrou[4];
        elemento.appendChild(forte);
      } else if (encontrou[5] !== undefined) {
        const sublinhado = document.createElement('u');
        sublinhado.textContent = encontrou[5];
        elemento.appendChild(sublinhado);
      } else if (encontrou[6] !== undefined) {
        const enfase = document.createElement('em');
        enfase.textContent = encontrou[6];
        elemento.appendChild(enfase);
      }
      ultimo = PADRAO_FORMATO.lastIndex;
    }
    if (ultimo < original.length) {
      elemento.appendChild(document.createTextNode(original.slice(ultimo)));
    }
  }

  // ---------- Renderização ----------
  function desenharTexto(entrada) {
    const bolha = document.createElement('div');
    bolha.className = 'chat-' + (entrada.autor === 'user' ? 'user' : 'bot');
    if (entrada.autor === 'user') {
      bolha.textContent = entrada.texto;
      log.appendChild(bolha);
      return;
    }

    // Resposta do Edu: títulos (#), separadores (---), listas (- ou 1.) e parágrafos.
    let paragrafo = [];
    let lista = null;
    let tipoLista = null;

    function fecharParagrafo() {
      if (!paragrafo.length) return;
      const p = document.createElement('p');
      p.className = 'chat-paragrafo';
      anexarTextoComLinks(p, paragrafo.join(' '));
      bolha.appendChild(p);
      paragrafo = [];
    }

    function fecharLista() {
      if (!lista) return;
      bolha.appendChild(lista);
      lista = null;
      tipoLista = null;
    }

    String(entrada.texto).split('\n').forEach(function (bruta) {
      const linha = bruta.trim();
      if (!linha) { fecharParagrafo(); fecharLista(); return; }

      if (RE_SEPARADOR.test(linha)) {
        fecharParagrafo(); fecharLista();
        const separador = document.createElement('hr');
        separador.className = 'chat-sep';
        bolha.appendChild(separador);
        return;
      }

      const titulo = linha.match(RE_TITULO);
      if (titulo) {
        fecharParagrafo(); fecharLista();
        const h = document.createElement('p');
        h.className = 'chat-titulo';
        anexarTextoComLinks(h, titulo[1]);
        bolha.appendChild(h);
        return;
      }

      const numero = linha.match(RE_NUMERO);
      const item = numero ? { tipo: 'ol', texto: numero[1] } : (linha.match(RE_ITEM) ? { tipo: 'ul', texto: linha.match(RE_ITEM)[1] } : null);
      if (item) {
        fecharParagrafo();
        if (!lista || tipoLista !== item.tipo) {
          fecharLista();
          lista = document.createElement(item.tipo);
          lista.className = item.tipo === 'ol' ? 'chat-lista chat-lista-numero' : 'chat-lista';
          tipoLista = item.tipo;
        }
        const li = document.createElement('li');
        anexarTextoComLinks(li, item.texto);
        lista.appendChild(li);
        return;
      }

      fecharLista();
      paragrafo.push(linha);
    });
    fecharParagrafo();
    fecharLista();
    log.appendChild(bolha);
  }

  function desenharCards(itens) {
    itens.forEach(function (op) {
      const temLink = LINK_VALIDO.test(op.link);
      const card = document.createElement(temLink ? 'a' : 'div');
      if (temLink) { card.href = op.link; card.target = '_blank'; card.rel = 'noopener'; }
      Object.assign(card.style, {
        display: 'block', visibility: 'visible', opacity: '1', boxSizing: 'border-box', width: '100%',
        padding: '12px 14px', background: '#ffffff', borderRadius: '10px',
        boxShadow: '0 6px 15px rgba(0, 0, 0, 0.06)', color: '#222222', textDecoration: 'none',
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
          marginTop: '6px', fontSize: '12px', fontWeight: '500', color: '#1ab394', textDecoration: 'underline',
        }));
      }
      log.appendChild(card);
    });
  }

  function desenharCaminhos(rotulo, itens) {
    const bloco = document.createElement('div');
    bloco.className = 'chat-links';
    const titulo = document.createElement('p');
    titulo.className = 'chat-links-titulo';
    titulo.textContent = rotulo;
    bloco.appendChild(titulo);
    itens.forEach(function (item) {
      if (!LINK_VALIDO.test(item.link)) return;
      const link = document.createElement('a');
      link.href = item.link; link.target = '_blank'; link.rel = 'noopener';
      link.className = 'chat-link'; link.textContent = item.titulo;
      if (item.descricao) link.title = item.descricao;
      bloco.appendChild(link);
    });
    log.appendChild(bloco);
  }

  function desenharEntrada(entrada) {
    if (entrada.tipo === 'texto') desenharTexto(entrada);
    else if (entrada.tipo === 'cards') desenharCards(entrada.itens);
    else if (entrada.tipo === 'caminhos') desenharCaminhos(entrada.rotulo, entrada.itens);
    rolarParaFim();
  }

  function registrar(entrada) {
    estado.mensagens.push(entrada);
    if (estado.mensagens.length > MAX_MENSAGENS) estado.mensagens.splice(0, estado.mensagens.length - MAX_MENSAGENS);
    salvarEstado();
    desenharEntrada(entrada);
  }

  function redesenharConversa() {
    log.innerHTML = '';
    estado.mensagens.forEach(desenharEntrada);
    if (!estado.mensagens.length) registrar({ tipo: 'texto', autor: 'bot', texto: SAUDACAO });
  }

  function historicoParaApi() {
    return estado.mensagens
      .filter(function (e) { return e.tipo === 'texto'; })
      .slice(-6)
      .map(function (e) { return { papel: e.autor === 'user' ? 'usuario' : 'edu', texto: e.texto.slice(0, 300) }; });
  }

  function juntarPerfil(novo) {
    if (!novo || typeof novo !== 'object') return;
    CAMPOS_PERFIL.forEach(function (campo) {
      const valor = novo[campo];
      if (typeof valor === 'string' && valor.trim()) estado.perfil[campo] = valor.trim().slice(0, 160);
    });
    salvarEstado();
  }

  // ---------- Conversa ----------
  function desligarChat(mensagemFinal) {
    if (mensagemFinal) registrar({ tipo: 'texto', autor: 'bot', texto: mensagemFinal });
    painel.hidden = true;
    botao.setAttribute('aria-expanded', 'false');
    botao.style.setProperty('display', 'none', 'important');
  }

  async function enviarMensagem(texto) {
    const mensagem = texto.trim();
    if (!mensagem || ocupado) return;

    ocupado = true;
    enviar.disabled = true;
    registrar({ tipo: 'texto', autor: 'user', texto: mensagem });
    input.value = '';
    const pensando = criarTexto('div', 'Edu está pensando...', { opacity: '0.6' });
    pensando.className = 'chat-bot chat-typing';
    log.appendChild(pensando);
    rolarParaFim();

    try {
      const resposta = await fetch(API_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: mensagem, historico: historicoParaApi(), perfil: estado.perfil }),
      });
      pensando.remove();

      if (resposta.status === 429) {
        registrar({ tipo: 'texto', autor: 'bot', texto: 'Recebi muitas mensagens em pouco tempo. Aguarde um minuto e tente de novo.' });
        return;
      }
      if (!resposta.ok) throw new Error('HTTP ' + resposta.status);

      const dados = await resposta.json();
      if (dados.chat_indisponivel) { desligarChat(dados.texto); return; }

      registrar({ tipo: 'texto', autor: 'bot', texto: dados.texto });
      if (Array.isArray(dados.oportunidades) && dados.oportunidades.length) {
        registrar({ tipo: 'cards', itens: dados.oportunidades });
      }
      if (Array.isArray(dados.opcoes_online) && dados.opcoes_online.length) {
        registrar({
          tipo: 'caminhos',
          rotulo: dados.origem === 'web' ? 'Saiba mais:' : 'Opções online:',
          itens: dados.opcoes_online,
        });
      }
      juntarPerfil(dados.perfil_atualizado);
    } catch (erro) {
      pensando.remove();
      registrar({ tipo: 'texto', autor: 'bot', texto: 'Não consegui responder agora. Tente novamente em instantes.' });
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
      redesenharConversa();
      input.focus();
    }
  }

  // ---------- Inicialização ----------
  carregarEstado();

  painel.querySelector('[data-chatbot-apagar]').addEventListener('click', apagarTudo);

  fetch(API_URL.replace('/api/chat', '/api/status'))
    .then(function (r) { return r.json(); })
    .then(function (dados) { if (dados && dados.disponivel === false) desligarChat(); })
    .catch(function () { /* se a consulta falhar, o chat fica visível */ });

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
