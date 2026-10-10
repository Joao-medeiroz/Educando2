'use strict';

/**
 * página Contato: validação e envio do formulário pelo Formspree
 * troque SEU_ID_AQUI, no action do formulário (contato.html), pelo seu endereço do Formspree
 */

(function () {

  const form = document.querySelector("[data-contact-form]");
  const status = document.querySelector("[data-form-status]");

  if (!form) return;

  const setStatus = function (message, type) {
    status.textContent = message;
    status.className = "form-status " + (type || "");
  }

  const isValidEmail = function (value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const nome = form.nome.value.trim();
    const email = form.email.value.trim();
    const telefone = form.telefone.value.trim();
    const mensagem = form.mensagem.value.trim();

    form.querySelectorAll(".input").forEach(function (field) { field.classList.remove("invalid"); });

    const fail = function (field, message) {
      field.classList.add("invalid");
      field.focus();
      setStatus(message, "error");
    }

    if (!nome) return fail(form.nome, "Informe o seu nome.");
    if (!isValidEmail(email)) return fail(form.email, "Informe um e-mail válido.");
    if (telefone && telefone.replace(/\D/g, "").length < 10) return fail(form.telefone, "Informe um telefone com DDD.");
    if (!mensagem) return fail(form.mensagem, "Escreva a sua mensagem.");

    if (form.action.includes("SEU_ID_AQUI")) {
      setStatus("O envio ainda não foi configurado. Troque SEU_ID_AQUI pelo endereço do seu Formspree.", "error");
      return;
    }

    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    setStatus("Enviando...", "");

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: new FormData(form),
        headers: { "Accept": "application/json" }
      });

      if (response.ok) {
        form.reset();
        setStatus("Mensagem enviada! Em breve entraremos em contato.", "success");
      } else {
        setStatus("Não foi possível enviar agora. Tente novamente em instantes.", "error");
      }
    } catch (error) {
      setStatus("Sem conexão. Verifique a internet e tente novamente.", "error");
    }

    button.disabled = false;
  });

})();
