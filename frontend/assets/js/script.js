'use strict';



/**
 * add event on element
 */

const addEventOnElem = function (elem, type, callback) {
  if (elem.length > 1) {
    for (let i = 0; i < elem.length; i++) {
      elem[i].addEventListener(type, callback);
    }
  } else {
    elem.addEventListener(type, callback);
  }
}



/**
 * navbar toggle
 */

const navbar = document.querySelector("[data-navbar]");
const navTogglers = document.querySelectorAll("[data-nav-toggler]");
const navLinks = document.querySelectorAll("[data-nav-link]");
const overlay = document.querySelector("[data-overlay]");

const toggleNavbar = function () {
  navbar.classList.toggle("active");
  overlay.classList.toggle("active");
}

addEventOnElem(navTogglers, "click", toggleNavbar);

const closeNavbar = function () {
  navbar.classList.remove("active");
  overlay.classList.remove("active");
}

addEventOnElem(navLinks, "click", closeNavbar);



/**
 * header active when scroll down to 100px
 */

const header = document.querySelector("[data-header]");
const backTopBtn = document.querySelector("[data-back-top-btn]");

const activeElem = function () {
  if (window.scrollY > 100) {
    header.classList.add("active");
    backTopBtn.classList.add("active");
  } else {
    header.classList.remove("active");
    backTopBtn.classList.remove("active");
  }
}

addEventOnElem(window, "scroll", activeElem);



/**
 * news carousel
 * os dados vêm de noticias.js (window.NOTICIAS)
 */

const newsTrack = document.querySelector("[data-news-track]");
const newsPrev = document.querySelector("[data-news-prev]");
const newsNext = document.querySelector("[data-news-next]");

const escapeHtml = function (text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

const formatNewsDate = function (isoDate) {
  const date = new Date(isoDate + "T12:00:00");
  return date.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
}

const renderNews = function () {
  if (!newsTrack || !Array.isArray(window.NOTICIAS)) return;

  newsTrack.innerHTML = window.NOTICIAS.map(function (item) {
    return `
      <li class="news-item">
        <article class="news-card">

          <figure class="card-banner img-holder" style="--width: 370; --height: 220;">
            <img src="${escapeHtml(item.imagem)}" width="370" height="220" loading="lazy" alt="" class="img-cover">
          </figure>

          <div class="card-content">

            <span class="badge">${escapeHtml(item.categoria)}</span>

            <h3 class="h3">
              <a href="${escapeHtml(item.link)}" class="card-title" target="_blank" rel="noopener">${escapeHtml(item.titulo)}</a>
            </h3>

            <ul class="card-meta-list">

              <li class="card-meta-item">
                <ion-icon name="calendar-outline" aria-hidden="true"></ion-icon>
                <span class="span">${formatNewsDate(item.data)}</span>
              </li>

              <li class="card-meta-item">
                <ion-icon name="newspaper-outline" aria-hidden="true"></ion-icon>
                <span class="span">${escapeHtml(item.fonte)}</span>
              </li>

            </ul>

            <p class="card-text">${escapeHtml(item.resumo)}</p>

            <span class="card-link">
              <span class="span">Ler notícia</span>
              <ion-icon name="arrow-forward-outline" aria-hidden="true"></ion-icon>
            </span>

          </div>

        </article>
      </li>
    `;
  }).join("");
}

const newsStep = function () {
  const firstItem = newsTrack.querySelector(".news-item");
  if (!firstItem) return 0;

  const gap = parseFloat(getComputedStyle(newsTrack).columnGap) || 0;
  return firstItem.getBoundingClientRect().width + gap;
}

const slideNews = function (direction) {
  const step = newsStep();
  if (!step) return;

  const maxScroll = newsTrack.scrollWidth - newsTrack.clientWidth;

  /* volta ao início/fim quando chega na ponta */
  if (direction > 0 && newsTrack.scrollLeft >= maxScroll - 5) {
    newsTrack.scrollTo({ left: 0, behavior: "smooth" });
  } else if (direction < 0 && newsTrack.scrollLeft <= 5) {
    newsTrack.scrollTo({ left: maxScroll, behavior: "smooth" });
  } else {
    newsTrack.scrollBy({ left: step * direction, behavior: "smooth" });
  }
}

if (newsTrack) {
  renderNews();

  newsNext.addEventListener("click", function () { slideNews(1); });
  newsPrev.addEventListener("click", function () { slideNews(-1); });

  /* movimento automático (desligado se o usuário prefere menos animação) */
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let newsTimer = null;

  const startNewsAutoplay = function () {
    if (reduceMotion || newsTimer) return;
    newsTimer = setInterval(function () { slideNews(1); }, 5000);
  }

  const stopNewsAutoplay = function () {
    clearInterval(newsTimer);
    newsTimer = null;
  }

  const newsCarousel = newsTrack.closest(".news-carousel");

  newsCarousel.addEventListener("mouseenter", stopNewsAutoplay);
  newsCarousel.addEventListener("mouseleave", startNewsAutoplay);
  newsCarousel.addEventListener("focusin", stopNewsAutoplay);
  newsCarousel.addEventListener("focusout", startNewsAutoplay);
  newsCarousel.addEventListener("touchstart", stopNewsAutoplay, { passive: true });

  startNewsAutoplay();
}




/**
 * lupa do header: leva para a busca da página de oportunidades
 */

const searchBtn = document.querySelector("[data-search-btn]");

if (searchBtn) {
  searchBtn.addEventListener("click", function () {
    const searchInput = document.querySelector("[data-opp-search]");

    if (searchInput) {
      searchInput.scrollIntoView({ behavior: "smooth", block: "center" });
      searchInput.focus();
    } else {
      window.location.href = "./oportunidades.html#busca";
    }
  });
}
