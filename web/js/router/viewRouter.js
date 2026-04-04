export function inferViewFromHash(hashValue) {
  const hash = (hashValue || "").replace("#", "");
  const alias = {
    overview: "overview",
    "shortlist-screen": "shortlist",
    shortlist: "shortlist",
    records: "records",
    analytics: "analytics",
    geo: "geo",
  };
  return alias[hash] || "overview";
}

export function switchView({ screenViews, viewLinks, view }) {
  const selected = view || "overview";
  screenViews.forEach(el => {
    const isActive = el.dataset.view === selected;
    el.classList.toggle("active", isActive);
  });
  viewLinks.forEach(link => {
    link.classList.toggle("active", link.dataset.viewLink === selected);
  });
}
