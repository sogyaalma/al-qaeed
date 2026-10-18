// Project-only routing: NDS.lang changes component strings, not static page URLs.
// NDS.Toc owns its scrollspy and replaces the hash without dispatching hashchange.
// Read the hash again on activation so both native anchors and TOC navigation work.
const sectionIds = new Set(
  Array.from(document.querySelectorAll('.nds-info-content > [id]'), el => el.id),
);
const languageLink = document.querySelector('[data-language-switch]');
if (languageLink) {
  const destination = languageLink.getAttribute('href');
  const updateLanguageLink = () => {
    const id = location.hash.slice(1);
    languageLink.setAttribute('href', destination + (sectionIds.has(id) ? `#${id}` : ''));
  };
  addEventListener('hashchange', updateLanguageLink);
  addEventListener('pageshow', updateLanguageLink);
  languageLink.addEventListener('click', updateLanguageLink);
  languageLink.addEventListener('focus', updateLanguageLink);
  updateLanguageLink();
}
