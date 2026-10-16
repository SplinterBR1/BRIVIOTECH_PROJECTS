/* Brivio Tech — comportamento da página
   1) ano atual no rodapé
   2) linha divisória no cabeçalho ao rolar a página
   3) destaque do item do menu da seção que está na tela */
(function () {
  'use strict';

  var header = document.querySelector('.site-header');
  var yearEl = document.getElementById('ano');
  var links = Array.prototype.slice.call(
    document.querySelectorAll('.nav a[href^="#"]:not(.btn)')
  );

  // 1) Ano do rodapé
  if (yearEl) {
    yearEl.textContent = String(new Date().getFullYear());
  }

  // 2) Cabeçalho com borda depois que a página rola
  function onScroll() {
    if (header) {
      header.classList.toggle('is-scrolled', window.scrollY > 8);
    }
  }
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  // 3) Item do menu da seção atual
  if (!('IntersectionObserver' in window) || links.length === 0) {
    return;
  }

  var linkById = {};
  links.forEach(function (a) {
    linkById[a.getAttribute('href').slice(1)] = a;
  });

  function setActive(id) {
    links.forEach(function (a) {
      if (linkById[id] === a) {
        a.setAttribute('aria-current', 'location');
      } else {
        a.removeAttribute('aria-current');
      }
    });
  }

  var observer = new IntersectionObserver(
    function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          setActive(entry.target.id);
        }
      });
    },
    { rootMargin: '-40% 0px -55% 0px' }
  );

  ['inicio'].concat(Object.keys(linkById)).forEach(function (id) {
    var section = document.getElementById(id);
    if (section) {
      observer.observe(section);
    }
  });
})();
