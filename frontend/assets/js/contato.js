'use strict';

/**
 * Página Contato: validação e envio pelo Web3Forms
 */

(function () {
  const form = document.querySelector("[data-contact-form]");
  const status = document.querySelector("[data-form-status]");

  if (!form || !status) return;

  const nome = form.querySelector("#nome");
  const email = form.querySelector("#email");
  const telefone = form.querySelector("#telefone");
  const mensagem = form.querySelector("#mensagem");

  const setStatus = function (message, type) {
    status.textContent = message;
    status.className = "form-status " + (type || "");
  };

  const isValidEmail = function (value) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
  };

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    const nomeValue = nome.value.trim();
    const emailValue = email.value.trim();
    const telefoneValue = telefone.value.trim();
    const mensagemValue = mensagem.value.trim();

    form.querySelectorAll(".input").forEach(function (field) {
      field.classList.remove("invalid");
    });

    const fail = function (field, message) {
      field.classList.add("invalid");
      field.focus();
      setStatus(message, "error");
    };

    if (!nomeValue) {
      return fail(nome, "Informe o seu nome.");
    }

    if (!isValidEmail(emailValue)) {
      return fail(email, "Informe um e-mail válido.");
    }

    if (
      telefoneValue &&
      telefoneValue.replace(/\D/g, "").length < 10
    ) {
      return fail(telefone, "Informe um telefone com DDD.");
    }

    if (!mensagemValue) {
      return fail(mensagem, "Escreva a sua mensagem.");
    }

    const button = form.querySelector("button[type='submit']");
    const buttonLabel = button.querySelector(".span");
    const originalLabel = buttonLabel.textContent;

    button.disabled = true;
    buttonLabel.textContent = "Enviando...";
    setStatus("Enviando sua mensagem...", "");

    try {
      const response = await fetch(
        "https://api.web3forms.com/submit",
        {
          method: "POST",
          body: new FormData(form),
          headers: {
            Accept: "application/json"
          }
        }
      );

      const data = await response.json();

      if (response.ok && data.success) {
        form.reset();

        form.querySelectorAll(".input").forEach(function (field) {
          field.classList.remove("invalid");
        });

        setStatus(
          "Mensagem enviada! Em breve entraremos em contato.",
          "success"
        );
      } else {
        setStatus(
          data.message ||
            "Não foi possível enviar a mensagem. Tente novamente.",
          "error"
        );
      }
    } catch (error) {
      setStatus(
        "Falha na conexão. Verifique a internet e tente novamente.",
        "error"
      );
    } finally {
      button.disabled = false;
      buttonLabel.textContent = originalLabel;
    }
  });
})();