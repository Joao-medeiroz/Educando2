'use strict';

/**
 * página Oportunidades: seções por categoria, busca e filtros
 * os dados ficam em dados-oportunidades.js
 */

(function () {

  const data = window.OPORTUNIDADES;
  const root = document.querySelector("[data-opp-root]");
  const searchInput = document.querySelector("[data-opp-search]");
  const searchForm = document.querySelector("[data-opp-search-form]");
  const chips = document.querySelectorAll("[data-opp-filter]");
  const countEl = document.querySelector("[data-opp-count]");
  const emptyEl = document.querySelector("[data-opp-empty]");

  if (!data || !root) return;

  const escapeText = function (text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  const normalize = function (text) {
    return text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  /* monta as seções */

  root.innerHTML = data.categorias.map(function (cat, index) {
    const cards = data.itens[cat.id].map(function (item) {
      const search = normalize([item.titulo, item.tipo, item.descricao, item.local, cat.subtitulo].join(" "));

      return `
        <li data-opp-card data-search="${escapeText(search)}">
          <div class="course-card">

            <figure class="card-banner img-holder" style="--width: 370; --height: 220;">
              <img src="${escapeText(item.imagem)}" width="370" height="220" loading="lazy" alt="" class="img-cover">
            </figure>

            <div class="abs-badge">
              <ion-icon name="${item.local === "Online" ? "laptop-outline" : "location-outline"}" aria-hidden="true"></ion-icon>
              <span class="span">${escapeText(item.local)}</span>
            </div>

            <div class="card-content">

              <span class="badge">${escapeText(item.tipo)}</span>

              <h3 class="h3">
                <a href="${escapeText(item.link)}" class="card-title" target="_blank" rel="noopener">${escapeText(item.titulo)}</a>
              </h3>

              <p class="card-text">${escapeText(item.descricao)}</p>

              <span class="card-link">
                <span class="span">Acessar</span>
                <ion-icon name="arrow-forward-outline" aria-hidden="true"></ion-icon>
              </span>

            </div>

          </div>
        </li>
      `;
    }).join("");

    return `
      <section class="section featured opp-section ${index % 2 ? "alt" : ""}" id="${cat.id}" data-opp-section="${cat.id}" aria-label="${escapeText(cat.subtitulo)}">
        <div class="container">

          <p class="section-subtitle">${escapeText(cat.subtitulo)}</p>

          <h2 class="h2 section-title">${cat.titulo}</h2>

          <ul class="grid-list opp-grid">${cards}</ul>

        </div>
      </section>
    `;
  }).join("");

  const sections = root.querySelectorAll("[data-opp-section]");

  /* filtros */

  let currentFilter = "todas";

  const applyFilters = function () {
    const term = normalize(searchInput.value.trim());
    let total = 0;

    sections.forEach(function (section) {
      const inCategory = currentFilter === "todas" || section.dataset.oppSection === currentFilter;
      let visibleInSection = 0;

      section.querySelectorAll("[data-opp-card]").forEach(function (card) {
        const match = inCategory && (!term || card.dataset.search.includes(term));
        card.hidden = !match;
        if (match) visibleInSection++;
      });

      section.hidden = visibleInSection === 0;
      total += visibleInSection;
    });

    emptyEl.hidden = total > 0;
    countEl.textContent = total === 1 ? "1 oportunidade encontrada" : total + " oportunidades encontradas";
  }

  const setFilter = function (filter) {
    currentFilter = filter;

    chips.forEach(function (chip) {
      const isActive = chip.dataset.oppFilter === filter;
      chip.classList.toggle("active", isActive);
      chip.setAttribute("aria-pressed", isActive);
    });

    applyFilters();
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () { setFilter(chip.dataset.oppFilter); });
  });

  searchInput.addEventListener("input", applyFilters);
  searchForm.addEventListener("submit", function (event) { event.preventDefault(); });

  /* links da home (oportunidades.html#cursos) já abrem a categoria certa */

  const hash = window.location.hash.replace("#", "");
  const isCategory = data.categorias.some(function (cat) { return cat.id === hash; });

  setFilter(isCategory ? hash : "todas");

  if (isCategory) {
    document.querySelector("#busca").scrollIntoView();
  }

})();
