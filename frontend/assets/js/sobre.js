'use strict';

/**
 * página Sobre: pesquisa de setores/integrantes e janela "Ver Integrantes"
 * os nomes dos integrantes ficam em dados-setores.js
 */

(function () {

  const cards = document.querySelectorAll("[data-sector-card]");
  const searchInput = document.querySelector("[data-sector-search]");
  const searchForm = document.querySelector("[data-sector-search-form]");
  const emptyMessage = document.querySelector("[data-sector-empty]");
  const dialog = document.querySelector("[data-members-dialog]");
  const membersData = window.INTEGRANTES || {};

  if (!cards.length) return;

  const normalize = function (text) {
    return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  /* texto pesquisável de cada setor: área, nome, descrição e integrantes */
  const searchable = {};

  cards.forEach(function (card) {
    const id = card.dataset.sectorId;
    const members = (membersData[id] || []).map(function (m) { return m.nome + " " + (m.cargo || ""); }).join(" ");

    searchable[id] = normalize(card.textContent + " " + members);
  });

  const filterSectors = function () {
    const term = normalize(searchInput.value.trim());
    let visible = 0;

    cards.forEach(function (card) {
      const match = !term || searchable[card.dataset.sectorId].includes(term);
      card.hidden = !match;
      if (match) visible++;
    });

    emptyMessage.hidden = visible > 0;
  }

  searchInput.addEventListener("input", filterSectors);
  searchForm.addEventListener("submit", function (event) { event.preventDefault(); });


  /* janela de integrantes */

  const dialogTitle = dialog.querySelector("[data-members-title]");
  const dialogArea = dialog.querySelector("[data-members-area]");
  const dialogList = dialog.querySelector("[data-members-list]");

  const openMembers = function (id) {
    const card = document.querySelector('[data-sector-id="' + id + '"]');
    const members = membersData[id] || [];

    dialogArea.textContent = card.querySelector(".sector-area").textContent;
    dialogTitle.textContent = card.querySelector(".sector-name").textContent;
    dialogList.innerHTML = "";

    if (!members.length) {
      const empty = document.createElement("li");
      empty.className = "members-empty";
      empty.textContent = "Os integrantes deste setor serão divulgados em breve.";
      dialogList.appendChild(empty);
    } else {
      members.forEach(function (member) {
        const item = document.createElement("li");
        item.className = "member-item";

        const name = document.createElement("span");
        name.className = "member-name";
        name.textContent = member.nome;
        item.appendChild(name);

        if (member.cargo) {
          const role = document.createElement("span");
          role.className = "member-role";
          role.textContent = member.cargo;
          item.appendChild(role);
        }

        dialogList.appendChild(item);
      });
    }

    dialog.showModal();
  }

  document.querySelectorAll("[data-members-btn]").forEach(function (btn) {
    btn.addEventListener("click", function () { openMembers(btn.dataset.membersBtn); });
  });

  dialog.querySelector("[data-members-close]").addEventListener("click", function () { dialog.close(); });

  /* clicar fora da caixa também fecha */
  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) dialog.close();
  });

})();
