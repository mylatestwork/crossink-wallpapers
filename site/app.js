const state = {
  catalog: null,
  mode: "custom",
  query: "",
  lastHeroAsset: {
    custom: null,
    "page-overlay": null,
  },
};

const modeLabels = {
  custom: "Custom",
  "page-overlay": "Page Overlay",
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
  const units = ["B", "KB", "MB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function modeData(pack, mode = state.mode) {
  return pack.modes[mode] || null;
}

function assetsForMode(mode = state.mode) {
  return state.catalog.packs.flatMap((pack) => modeData(pack, mode)?.assets || []);
}

function randomHeroAsset(mode) {
  const assets = assetsForMode(mode);
  if (assets.length === 0) return null;
  const alternatives = assets.filter((asset) => asset.number !== state.lastHeroAsset[mode]);
  const pool = alternatives.length > 0 ? alternatives : assets;
  const asset = pool[Math.floor(Math.random() * pool.length)];
  state.lastHeroAsset[mode] = asset.number;
  return asset;
}

function pageSample() {
  const sample = element("div", "page-sample");
  sample.setAttribute("aria-hidden", "true");
  const image = element("img");
  image.src = "./media/book-page.png";
  image.alt = "";
  image.loading = "lazy";
  image.decoding = "async";
  image.draggable = false;
  sample.append(image);
  return sample;
}

function artworkPreview(asset, mode) {
  const preview = element("div", `asset-preview mode-${mode}`);
  if (mode === "page-overlay") preview.append(pageSample());
  const image = element("img");
  image.src = asset.previewUrl;
  image.alt = "";
  image.loading = "lazy";
  image.decoding = "async";
  preview.append(image);
  return preview;
}

function downloadLink(url, filename, text, className = "button") {
  const link = element("a", className, text);
  link.href = url;
  link.download = filename;
  return link;
}

function renderPacks() {
  const list = document.querySelector("#pack-list");
  list.replaceChildren();
  let collectionCount = 0;
  let fileCount = 0;

  for (const pack of state.catalog.packs) {
    for (const modeName of ["custom", "page-overlay"]) {
      const mode = modeData(pack, modeName);
      if (!mode) continue;
      collectionCount += 1;
      fileCount += mode.count;

      const card = element("article", "pack-card");
      card.dataset.mode = modeName;
      const visual = element("div", "pack-visual");
      for (const asset of mode.assets.slice(0, 6)) {
        visual.append(artworkPreview(asset, modeName));
      }

      const content = element("div", "pack-content");
      content.append(
        element("p", "kicker", mode.eyebrow || modeLabels[modeName]),
        element("h3", "", mode.title || `${pack.title} — ${modeLabels[modeName]}`),
        element("p", "pack-description", mode.description),
      );

      const tags = element("div", "pack-tags");
      for (const tag of pack.tags || []) tags.append(element("span", "", tag));
      content.append(tags);
      content.append(element(
        "p",
        "pack-meta",
        `${mode.count} files · ${formatBytes(mode.archiveSize)} · ${state.catalog.collection.resolution}`,
      ));

      const actions = element("div", "pack-actions");
      actions.append(downloadLink(
        mode.archiveUrl,
        mode.archive,
        `Download ${modeLabels[modeName]} ZIP`,
      ));
      const browse = element("a", "text-link", `Browse ${modeLabels[modeName]} files ↓`);
      browse.href = "#artwork";
      browse.addEventListener("click", () => setMode(modeName));
      actions.append(browse);
      content.append(actions);
      card.append(visual, content);
      list.append(card);
    }
  }

  document.querySelector("#collection-summary").textContent =
    `${fileCount} ready-to-use files across ${collectionCount} collections for ${state.catalog.collection.devices.join(" and ")}.`;
}

function openPreview(asset) {
  const dialog = document.querySelector("#preview-dialog");
  const screen = document.querySelector("#dialog-screen");
  const image = document.querySelector("#dialog-image");
  screen.className = `device-screen mode-${state.mode}`;
  image.src = asset.previewUrl;
  image.alt = `${asset.label} ${modeLabels[state.mode]} preview`;
  document.querySelector("#dialog-mode").textContent = modeLabels[state.mode];
  document.querySelector("#dialog-title").textContent = asset.label;
  document.querySelector("#dialog-meta").textContent =
    `${asset.name} · ${asset.width} × ${asset.height} · ${formatBytes(asset.size)}`;
  const download = document.querySelector("#dialog-download");
  download.href = asset.url;
  download.download = asset.name;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function renderAssets() {
  const grid = document.querySelector("#asset-grid");
  const query = state.query.trim().toLocaleLowerCase();
  const assets = assetsForMode().filter((asset) =>
    `${asset.label} ${asset.name}`.toLocaleLowerCase().includes(query)
  );
  grid.replaceChildren();

  for (const asset of assets) {
    const card = element("article", "asset-card");
    const previewButton = element("button", "asset-preview-button");
    previewButton.type = "button";
    previewButton.setAttribute("aria-label", `Preview ${asset.label}`);
    previewButton.append(artworkPreview(asset, state.mode));
    previewButton.addEventListener("click", () => openPreview(asset));

    const info = element("div", "asset-info");
    info.append(element("h3", "", asset.label));
    const row = element("div", "asset-row");
    row.append(
      element("p", "asset-meta", `#${String(asset.number).padStart(3, "0")} · ${asset.format} · ${formatBytes(asset.size)}`),
      downloadLink(asset.url, asset.name, "Download", "asset-download"),
    );
    info.append(row);
    card.append(previewButton, info);
    grid.append(card);
  }

  const total = assetsForMode().length;
  document.querySelector("#asset-count").textContent = query
    ? `${assets.length} of ${total} ${modeLabels[state.mode]} files`
    : `${total} ${modeLabels[state.mode]} files`;

  if (assets.length === 0) {
    grid.append(element("p", "empty-state", "No artwork matches this search."));
  }
}

function setMode(mode) {
  state.mode = mode;
  document.querySelectorAll(".mode-button").forEach((button) => {
    const active = button.dataset.mode === mode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", String(active));
  });

  const firstAsset = randomHeroAsset(mode);
  if (!firstAsset) return;
  const preview = document.querySelector("#hero-preview");
  const screen = document.querySelector("#hero-screen");
  screen.className = `device-screen mode-${mode}`;
  preview.src = firstAsset.previewUrl;
  preview.alt = `${firstAsset.label} ${modeLabels[mode]} preview`;
  document.querySelector("#preview-mode-label").textContent = modeLabels[mode];
  document.querySelector("#preview-behavior").textContent = mode === "custom"
    ? "random on every sleep"
    : "the last page stays visible";
  document.querySelector("#artwork-search").placeholder = `Search ${modeLabels[mode]}`;
  renderAssets();
}

function bindEvents() {
  document.querySelectorAll(".mode-button").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });
  document.querySelector("#artwork-search").addEventListener("input", (event) => {
    state.query = event.target.value;
    renderAssets();
  });
  document.querySelector("#preview-dialog").addEventListener("click", (event) => {
    if (event.target === event.currentTarget) event.currentTarget.close();
  });
}

async function initialize() {
  try {
    const response = await fetch("./catalog.json");
    if (!response.ok) throw new Error(`Catalog request failed: ${response.status}`);
    state.catalog = await response.json();
    document.querySelector("#license-note").textContent =
      `Artwork: ${state.catalog.collection.assetLicense}.`;
    bindEvents();
    renderPacks();
    setMode(state.mode);
  } catch (error) {
    console.error(error);
    document.querySelector("#collection-summary").textContent = "The collection could not be loaded.";
    document.querySelector("#pack-list").replaceChildren(
      element("p", "pack-description", "Please reload the page or use the GitHub release downloads."),
    );
    document.querySelector("#asset-count").textContent = "Artwork unavailable";
  }
}

initialize();
