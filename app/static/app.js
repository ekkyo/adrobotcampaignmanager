const $ = (selector) => document.querySelector(selector);
const form = $("#create");
const campaignPicker = $("#campaign-picker");
const notice = $("#notice");

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  })[char]);
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Запрос не выполнен");
  return data;
}

async function loadOptions(fieldName, endpoint) {
  const select = document.querySelector(`[name="${fieldName}"]`);
  try {
    const rows = await fetchJson(`/api/options/${endpoint}`);
    select.innerHTML = '<option value="">Выберите…</option>' + rows
      .map((item) => `<option value="${Number(item.id)}">${escapeHtml(item.name)} (ID ${Number(item.id)})</option>`)
      .join("");
    if (!rows.length) select.innerHTML = '<option value="">Список пуст</option>';
  } catch (error) {
    select.innerHTML = '<option value="">Ошибка загрузки</option>';
    notice.textContent = error.message;
  }
}

function renderCampaignOptions(campaigns) {
  campaignPicker.innerHTML = '<option value="">Выберите кампанию…</option>' + campaigns
    .map((campaign) => `<option value="${campaign.id}">${escapeHtml(campaign.name)} (ID ${campaign.id})</option>`)
    .join("");
}

async function loadCampaigns(selectedId = "") {
  try {
    const campaigns = await fetchJson("/api/campaigns");
    renderCampaignOptions(campaigns);
    campaignPicker.value = selectedId;
    if (campaignPicker.value) await loadEditor(campaignPicker.value);
    else $("#editor").innerHTML = '<p class="muted">Выберите кампанию, чтобы посмотреть её офферы.</p>';
  } catch (error) {
    campaignPicker.innerHTML = '<option value="">Ошибка загрузки</option>';
    $("#editor").textContent = error.message;
  }
}

async function loadEditor(campaignId) {
  try {
    const campaign = await fetchJson(`/api/campaigns/${campaignId}`);
    const offers = campaign.offers.map((offer) => `
      <div class="row">
        <div>
          <strong>Оффер ${offer.id}</strong>
          <div class="muted">Доля: ${offer.share}%</div>
        </div>
        <button class="remove" data-remove-offer="${offer.id}">Удалить</button>
      </div>
    `).join("") || '<p class="muted">Поток офферов пуст.</p>';

    $("#editor").innerHTML = `
      <p class="muted">${escapeHtml(campaign.country)} · ${campaign.offers.length} оффер(ов)</p>
      <div class="offer-list">${offers}</div>
      <div class="actions add-offer">
        <select id="new-offer"><option value="">Выберите оффер…</option>${window.offerOptions
          .map((offer) => `<option value="${Number(offer.id)}">${escapeHtml(offer.name)} (ID ${Number(offer.id)})</option>`)
          .join("")}</select>
        <button class="secondary" id="add-offer">Добавить оффер</button>
      </div>
    `;
    $("#add-offer").onclick = () => addOffer(campaignId);
    document.querySelectorAll("[data-remove-offer]").forEach((button) => {
      button.onclick = () => removeOffer(campaignId, Number(button.dataset.removeOffer));
    });
  } catch (error) {
    $("#editor").textContent = error.message;
  }
}

async function addOffer(campaignId) {
  const offerId = Number($("#new-offer").value);
  if (!offerId) return;
  try {
    await fetchJson(`/api/campaigns/${campaignId}/offers`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: offerId }),
    });
    notice.textContent = "Оффер добавлен";
    await loadEditor(campaignId);
  } catch (error) {
    notice.textContent = error.message;
  }
}

async function removeOffer(campaignId, offerId) {
  try {
    await fetchJson(`/api/campaigns/${campaignId}/offers/${offerId}`, { method: "DELETE" });
    notice.textContent = "Оффер удалён";
    await loadEditor(campaignId);
  } catch (error) {
    notice.textContent = error.message;
  }
}

form.onsubmit = async (event) => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(form));
  for (const key of ["offer_id", "domain_id", "group_id", "traffic_source_id"]) {
    body[key] = Number(body[key]);
  }
  try {
    const campaign = await fetchJson("/api/campaigns", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    notice.textContent = `Кампания создана · Keitaro ID ${campaign.keitaro_id}`;
    form.reset();
    await loadCampaigns(campaign.id);
  } catch (error) {
    notice.textContent = error.message;
  }
};

campaignPicker.onchange = () => {
  if (campaignPicker.value) loadEditor(campaignPicker.value);
  else $("#editor").replaceChildren();
};

async function init() {
  try {
    window.offerOptions = await fetchJson("/api/options/offers");
    await Promise.all([
      loadOptions("offer_id", "offers"),
      loadOptions("domain_id", "domains"),
      loadOptions("group_id", "groups"),
      loadOptions("traffic_source_id", "sources"),
    ]);
    await loadCampaigns();
  } catch (error) {
    notice.textContent = error.message;
  }
}

init();
