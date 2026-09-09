/* Hotel Food Service - single page client.
 * No framework: a hash router, a fetch wrapper and one render function per view.
 */
(() => {
  const API = "/api/v1";
  const $ = (sel, el = document) => el.querySelector(sel);
  const view = $("#view");
  let me = null;

  // ---------- helpers ----------
  const money = (minor) =>
    (minor / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const num = (n, d = 2) => Number(n).toLocaleString(undefined, { maximumFractionDigits: d });
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const badge = (s) => `<span class="badge ${esc(s)}">${esc(String(s).replace(/_/g, " "))}</span>`;
  const today = () => new Date().toISOString().slice(0, 10);
  const monthStart = () => today().slice(0, 8) + "01";

  function toast(msg, isError = false) {
    const t = $("#toast");
    t.textContent = msg;
    t.className = "toast" + (isError ? " error" : "");
    t.hidden = false;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => (t.hidden = true), 3500);
  }

  async function api(path, { method = "GET", body, form } = {}) {
    const headers = {};
    const token = localStorage.getItem("token");
    if (token) headers.Authorization = `Bearer ${token}`;
    let payload;
    if (form) {
      headers["Content-Type"] = "application/x-www-form-urlencoded";
      payload = new URLSearchParams(form).toString();
    } else if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      payload = JSON.stringify(body);
    }
    const res = await fetch(API + path, { method, headers, body: payload });
    if (res.status === 401 && path !== "/auth/login") {
      localStorage.removeItem("token");
      me = null;
      render();
      throw new Error("Session expired, please sign in again");
    }
    if (res.status === 204) return null;
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const d = data.detail;
      throw new Error(Array.isArray(d) ? d.map((e) => `${e.loc.slice(-1)}: ${e.msg}`).join("; ") : d || res.statusText);
    }
    return data;
  }

  function formData(formEl) {
    const out = {};
    for (const [k, v] of new FormData(formEl).entries()) {
      if (v === "") continue;
      const input = formEl.elements[k];
      out[k] = input.type === "number" ? Number(v) : v;
    }
    return out;
  }

  function table(columns, rows, empty = "Nothing here yet.") {
    if (!rows.length) return `<p class="muted">${esc(empty)}</p>`;
    const head = columns.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.label)}</th>`).join("");
    const body = rows
      .map((r) => `<tr>${columns.map((c) => `<td class="${c.num ? "num" : ""}">${c.render(r)}</td>`).join("")}</tr>`)
      .join("");
    return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  const options = (items, label, value = "id") =>
    items.map((i) => `<option value="${i[value]}">${esc(label(i))}</option>`).join("");

  // Bind a submit handler that posts formData and re-renders on success.
  function onSubmit(formEl, handler) {
    formEl.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        await handler(formData(formEl), formEl);
        render();
      } catch (err) {
        toast(err.message, true);
      }
    });
  }
  // Buttons carry data-action="..."; each view registers its handlers and a single
  // delegated listener (bound once, below) dispatches to the current view's set.
  let actionHandlers = {};
  function onAction(_root, handlers) {
    actionHandlers = handlers;
  }
  view.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;
    const fn = actionHandlers[btn.dataset.action];
    if (!fn) return;
    btn.disabled = true;
    try {
      await fn(btn.dataset, btn);
      render();
    } catch (err) {
      toast(err.message, true);
      btn.disabled = false;
    }
  });

  // ---------- views ----------
  const views = {};

  views.login = () => {
    view.innerHTML = `
      <div class="card login">
        <h1>Sign in</h1>
        <form id="login-form">
          <label>Email <input name="username" type="email" required autofocus></label>
          <label>Password <input name="password" type="password" required></label>
          <button>Sign in</button>
        </form>
        <p class="muted">Demo accounts (after <code>python -m app.seed</code>): admin@example.com / Password123</p>
      </div>`;
    $("#login-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const data = await api("/auth/login", { method: "POST", form: formData(e.target) });
        localStorage.setItem("token", data.access_token);
        await loadMe();
        location.hash = "#dashboard";
        render();
      } catch (err) {
        toast(err.message, true);
      }
    });
  };

  views.dashboard = async () => {
    const [d, low, open] = await Promise.all([
      api("/reports/dashboard"),
      api("/inventory/low-stock"),
      api("/orders?status=open"),
    ]);
    const kpi = (label, value) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`;
    view.innerHTML = `
      <h1>Dashboard</h1>
      <div class="kpis">
        ${kpi("Today's sales", money(d.today_sales_minor))}
        ${kpi("Orders paid today", d.today_orders)}
        ${kpi("Open orders", d.open_orders)}
        ${kpi("Open purchase orders", d.open_purchase_orders)}
        ${kpi("Low-stock items", `<span class="${d.low_stock_items ? "warn" : ""}">${d.low_stock_items}</span>`)}
        ${kpi("Inventory value", money(d.inventory_value_minor))}
        ${kpi("Active employees", d.active_employees)}
        ${kpi("Reservations today", d.reservations_today)}
      </div>
      <div class="grid cols-2">
        <div class="card"><h2>Low stock</h2>${table(
          [
            { label: "Item", render: (r) => esc(r.name) },
            { label: "On hand", num: true, render: (r) => `${num(r.quantity_on_hand)} ${r.unit}` },
            { label: "Reorder at", num: true, render: (r) => num(r.reorder_level) },
            { label: "Shortfall", num: true, render: (r) => `<span class="warn">${num(r.shortfall)}</span>` },
          ],
          low,
          "All ingredients above reorder level."
        )}</div>
        <div class="card"><h2>Open orders</h2>${table(
          [
            { label: "Order", render: (r) => esc(r.number) },
            { label: "Type", render: (r) => esc(r.order_type.replace("_", " ")) },
            { label: "Where", render: (r) => esc(r.location) },
            { label: "Total", num: true, render: (r) => money(r.total_minor) },
          ],
          open,
          "No open orders."
        )}</div>
      </div>`;
  };

  views.suppliers = async () => {
    const rows = await api("/suppliers?include_inactive=true");
    view.innerHTML = `
      <h1>Suppliers</h1>
      <div class="card"><h2>Add supplier</h2>
        <form id="f" class="inline">
          <label>Name <input name="name" required></label>
          <label>Contact <input name="contact_name"></label>
          <label>Phone <input name="phone"></label>
          <label>Email <input name="email" type="email"></label>
          <label>Lead time (days) <input name="lead_time_days" type="number" min="0" value="2"></label>
          <button>Add</button>
        </form></div>
      <div class="card">${table(
        [
          { label: "Name", render: (r) => esc(r.name) },
          { label: "Contact", render: (r) => esc(r.contact_name) },
          { label: "Phone", render: (r) => esc(r.phone) },
          { label: "Lead time", num: true, render: (r) => `${r.lead_time_days} d` },
          { label: "Status", render: (r) => (r.is_active ? "active" : '<span class="muted">inactive</span>') },
          { label: "", render: (r) => `<button class="small secondary" data-action="toggle" data-id="${r.id}" data-active="${r.is_active}">${r.is_active ? "Deactivate" : "Activate"}</button>` },
        ],
        rows
      )}</div>`;
    onSubmit($("#f"), (d) => api("/suppliers", { method: "POST", body: d }));
    onAction(view, { toggle: (d) => api(`/suppliers/${d.id}`, { method: "PATCH", body: { is_active: d.active !== "true" } }) });
  };

  views.ingredients = async () => {
    const [rows, moves] = await Promise.all([api("/inventory/ingredients?include_inactive=true"), api("/inventory/movements?limit=30")]);
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    view.innerHTML = `
      <h1>Inventory</h1>
      <div class="grid cols-2">
      <div class="card"><h2>Add ingredient</h2>
        <form id="f" class="inline">
          <label>SKU <input name="sku" required></label>
          <label>Name <input name="name" required></label>
          <label>Category <input name="category" value="general"></label>
          <label>Unit <select name="unit">${["kg", "g", "l", "ml", "pcs"].map((u) => `<option>${u}</option>`).join("")}</select></label>
          <label>Reorder level <input name="reorder_level" type="number" min="0" step="any" value="0"></label>
          <button>Add</button>
        </form></div>
      <div class="card"><h2>Stock adjustment / wastage</h2>
        <form id="adj" class="inline">
          <label>Ingredient <select name="ingredient_id" required>${options(rows.filter((r) => r.is_active), (r) => `${r.name} (${num(r.quantity_on_hand)} ${r.unit})`)}</select></label>
          <label>Type <select name="movement_type"><option value="adjustment">Adjustment (+/-)</option><option value="wastage">Wastage (-)</option></select></label>
          <label>Quantity <input name="quantity" type="number" step="any" required></label>
          <label>Note <input name="note"></label>
          <button>Record</button>
        </form></div>
      </div>
      <div class="card">${table(
        [
          { label: "SKU", render: (r) => esc(r.sku) },
          { label: "Name", render: (r) => esc(r.name) },
          { label: "Category", render: (r) => esc(r.category) },
          { label: "On hand", num: true, render: (r) => `<span class="${r.quantity_on_hand <= r.reorder_level ? "warn" : ""}">${num(r.quantity_on_hand, 3)} ${r.unit}</span>` },
          { label: "Reorder at", num: true, render: (r) => num(r.reorder_level) },
          { label: "Avg cost", num: true, render: (r) => money(r.avg_cost_minor) },
          { label: "Value", num: true, render: (r) => money(Math.max(r.quantity_on_hand, 0) * r.avg_cost_minor) },
        ],
        rows
      )}</div>
      <div class="card"><h2>Recent movements</h2>${table(
        [
          { label: "When", render: (r) => esc(r.created_at.replace("T", " ").slice(0, 16)) },
          { label: "Ingredient", render: (r) => esc(byId[r.ingredient_id]?.name ?? r.ingredient_id) },
          { label: "Type", render: (r) => esc(r.movement_type) },
          { label: "Qty", num: true, render: (r) => num(r.quantity, 3) },
          { label: "Unit cost", num: true, render: (r) => money(r.unit_cost_minor) },
          { label: "Ref", render: (r) => esc(r.reference_type ? `${r.reference_type} #${r.reference_id ?? ""}` : "") },
          { label: "Note", render: (r) => esc(r.note) },
        ],
        moves
      )}</div>`;
    onSubmit($("#f"), (d) => api("/inventory/ingredients", { method: "POST", body: d }));
    onSubmit($("#adj"), (d) => api(`/inventory/ingredients/${d.ingredient_id}/adjust`, { method: "POST", body: d }));
  };

  // Dynamic "lines" editor used by purchase orders, menu recipes and sales orders.
  function linesEditor(container, { items, label, qtyLabel = "Qty", extra = "" }) {
    const addRow = () => {
      const row = document.createElement("div");
      row.className = "row";
      row.innerHTML = `
        <label>${label} <select name="item">${options(items, (i) => i.name || i.code)}</select></label>
        <label>${qtyLabel} <input name="qty" type="number" step="any" min="0" value="1" required></label>
        ${extra}
        <button type="button" class="small secondary" data-remove>×</button>`;
      row.querySelector("[data-remove]").onclick = () => row.remove();
      container.appendChild(row);
    };
    addRow();
    return {
      addRow,
      read: () =>
        [...container.querySelectorAll(".row")].map((row) => ({
          item: Number(row.querySelector("[name=item]").value),
          qty: Number(row.querySelector("[name=qty]").value),
          extra: row.querySelector("[name=extra]")?.value,
        })),
    };
  }

  views["purchase-orders"] = async () => {
    const [pos, suppliers, ingredients] = await Promise.all([api("/purchase-orders"), api("/suppliers"), api("/inventory/ingredients")]);
    const ingById = Object.fromEntries(ingredients.map((i) => [i.id, i]));
    const supById = Object.fromEntries(suppliers.map((s) => [s.id, s]));
    view.innerHTML = `
      <h1>Purchasing</h1>
      <div class="card"><h2>New purchase order</h2>
        <form id="f">
          <div class="inline" style="display:flex;gap:8px;flex-wrap:wrap">
            <label>Supplier <select name="supplier_id" required>${options(suppliers, (s) => s.name)}</select></label>
            <label>Expected date <input name="expected_date" type="date" value="${today()}"></label>
            <label>Notes <input name="notes"></label>
          </div>
          <div class="lines" id="lines"></div>
          <div class="actions"><button type="button" class="secondary" id="add-line">+ line</button><button>Create draft</button></div>
        </form></div>
      <div class="card">${pos
        .map(
          (po) => `
        <details ${po.status === "submitted" || po.status === "partially_received" ? "open" : ""}>
          <summary>${esc(po.number)} · ${esc(supById[po.supplier_id]?.name ?? "")} · ${badge(po.status)} · ${money(po.total_minor)}</summary>
          ${table(
            [
              { label: "Ingredient", render: (l) => esc(ingById[l.ingredient_id]?.name ?? l.ingredient_id) },
              { label: "Ordered", num: true, render: (l) => num(l.quantity, 3) },
              { label: "Received", num: true, render: (l) => num(l.received_quantity, 3) },
              { label: "Unit price", num: true, render: (l) => money(l.unit_price_minor) },
              { label: "Total", num: true, render: (l) => money(l.line_total_minor) },
            ],
            po.lines
          )}
          <div class="actions" style="margin-top:8px">
            ${po.status === "draft" ? `<button class="small" data-action="submit" data-id="${po.id}">Submit</button>` : ""}
            ${["submitted", "partially_received"].includes(po.status) ? `<button class="small" data-action="receive" data-id="${po.id}">Receive all outstanding</button>` : ""}
            ${["draft", "submitted", "partially_received"].includes(po.status) ? `<button class="small danger" data-action="cancel" data-id="${po.id}">Cancel</button>` : ""}
          </div>
        </details>`
        )
        .join("") || '<p class="muted">No purchase orders yet.</p>'}</div>`;
    const editor = linesEditor($("#lines"), {
      items: ingredients,
      label: "Ingredient",
      extra: `<label>Unit price <input name="extra" type="number" step="0.01" min="0" value="0" required></label>`,
    });
    $("#add-line").onclick = editor.addRow;
    onSubmit($("#f"), (d) =>
      api("/purchase-orders", {
        method: "POST",
        body: { ...d, lines: editor.read().map((l) => ({ ingredient_id: l.item, quantity: l.qty, unit_price_minor: Math.round(Number(l.extra) * 100) })) },
      })
    );
    onAction(view, {
      submit: (d) => api(`/purchase-orders/${d.id}/submit`, { method: "POST" }),
      cancel: (d) => api(`/purchase-orders/${d.id}/cancel`, { method: "POST" }),
      receive: async (d) => {
        const po = pos.find((p) => p.id === Number(d.id));
        const lines = po.lines.filter((l) => l.outstanding_quantity > 0).map((l) => ({ purchase_order_line_id: l.id, quantity: l.outstanding_quantity }));
        await api(`/purchase-orders/${d.id}/receipts`, { method: "POST", body: { lines } });
        toast(`${po.number} received into stock`);
      },
    });
  };

  views.menu = async () => {
    const [items, ingredients] = await Promise.all([api("/menu/items"), api("/inventory/ingredients")]);
    const costings = await Promise.all(items.map((i) => api(`/menu/items/${i.id}/costing`)));
    const ingById = Object.fromEntries(ingredients.map((i) => [i.id, i]));
    view.innerHTML = `
      <h1>Menu &amp; recipes</h1>
      <div class="card"><h2>New menu item</h2>
        <form id="f">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <label>Code <input name="code" required></label>
            <label>Name <input name="name" required></label>
            <label>Category <input name="category" value="main"></label>
            <label>Price <input name="price" type="number" step="0.01" min="0" required></label>
          </div>
          <p class="muted">Recipe (per portion):</p>
          <div class="lines" id="lines"></div>
          <div class="actions"><button type="button" class="secondary" id="add-line">+ ingredient</button><button>Create</button></div>
        </form></div>
      <div class="card">${table(
        [
          { label: "Code", render: (r) => esc(r.code) },
          { label: "Name", render: (r) => esc(r.name) },
          { label: "Category", render: (r) => esc(r.category) },
          { label: "Price", num: true, render: (r) => money(r.price_minor) },
          { label: "Food cost", num: true, render: (r, i) => money(r._c.food_cost_minor) },
          { label: "Cost %", num: true, render: (r) => `<span class="${r._c.food_cost_percent > 35 ? "warn" : ""}">${r._c.food_cost_percent}%</span>` },
          { label: "Portions left", num: true, render: (r) => (r._c.portions_available == null ? "—" : num(Math.floor(r._c.portions_available), 0)) },
          { label: "Recipe", render: (r) => r.recipe.map((l) => `${esc(ingById[l.ingredient_id]?.name ?? l.ingredient_id)} ${num(l.quantity, 3)} ${ingById[l.ingredient_id]?.unit ?? ""}`).join("<br>") },
          { label: "", render: (r) => `<button class="small secondary" data-action="toggle" data-id="${r.id}" data-avail="${r.is_available}">${r.is_available ? "Mark sold out" : "Mark available"}</button>` },
        ],
        items.map((it, i) => ({ ...it, _c: costings[i] }))
      )}</div>`;
    const editor = linesEditor($("#lines"), { items: ingredients, label: "Ingredient", qtyLabel: "Qty per portion" });
    $("#add-line").onclick = editor.addRow;
    onSubmit($("#f"), (d) =>
      api("/menu/items", {
        method: "POST",
        body: { code: d.code, name: d.name, category: d.category, price_minor: Math.round(d.price * 100), recipe: editor.read().map((l) => ({ ingredient_id: l.item, quantity: l.qty })) },
      })
    );
    onAction(view, { toggle: (d) => api(`/menu/items/${d.id}`, { method: "PATCH", body: { is_available: d.avail !== "true" } }) });
  };

  views.orders = async () => {
    const [orders, items] = await Promise.all([api("/orders?limit=50"), api("/menu/items?available_only=true")]);
    const itemById = Object.fromEntries(items.map((i) => [i.id, i]));
    const next = { open: ["in_kitchen", "cancelled"], in_kitchen: ["served", "cancelled"], served: ["cancelled"] };
    view.innerHTML = `
      <h1>Orders</h1>
      <div class="card"><h2>New order</h2>
        <form id="f">
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <label>Type <select name="order_type"><option value="dine_in">Dine-in</option><option value="room_service">Room service</option><option value="takeaway">Takeaway</option></select></label>
            <label>Table / room <input name="location"></label>
          </div>
          <div class="lines" id="lines"></div>
          <div class="actions"><button type="button" class="secondary" id="add-line">+ item</button><button>Open order</button></div>
        </form></div>
      <div class="card">${orders
        .map((o) => {
          const paid = o.payments.reduce((s, p) => s + p.amount_minor, 0);
          const due = o.total_minor - paid;
          return `<details ${["open", "in_kitchen", "served"].includes(o.status) ? "open" : ""}>
          <summary>${esc(o.number)} · ${esc(o.order_type.replace("_", " "))} ${esc(o.location ?? "")} · ${badge(o.status)} · ${money(o.total_minor)}${due > 0 && paid > 0 ? ` <span class="warn">(due ${money(due)})</span>` : ""}</summary>
          ${table(
            [
              { label: "Item", render: (l) => esc(itemById[l.menu_item_id]?.name ?? `#${l.menu_item_id}`) },
              { label: "Qty", num: true, render: (l) => l.quantity },
              { label: "Price", num: true, render: (l) => money(l.unit_price_minor) },
              { label: "Total", num: true, render: (l) => money(l.line_total_minor) },
              { label: "", render: (l) => (o.status === "open" ? `<button class="small secondary" data-action="rm" data-id="${o.id}" data-line="${l.id}">remove</button>` : "") },
            ],
            o.lines,
            "Empty order"
          )}
          ${o.status === "open" ? `<div class="actions" style="margin:6px 0">
              <select class="small" data-add-item="${o.id}">${options(items, (i) => `${i.name} · ${money(i.price_minor)}`)}</select>
              <input class="small" type="number" min="1" value="1" style="width:70px" data-add-qty="${o.id}">
              <button class="small secondary" data-action="addline" data-id="${o.id}">Add item</button></div>` : ""}
          <p class="muted">Subtotal ${money(o.subtotal_minor)} · tax ${money(o.tax_minor)} · <b>total ${money(o.total_minor)}</b></p>
          <div class="actions">
            ${(next[o.status] || []).map((s) => `<button class="small ${s === "cancelled" ? "danger" : ""}" data-action="status" data-id="${o.id}" data-status="${s}">${s.replace("_", " ")}</button>`).join("")}
            ${o.lines.length ? `<button class="small secondary" data-action="bill" data-id="${o.id}">Print bill</button>` : ""}
            ${["open", "in_kitchen", "served"].includes(o.status) && o.lines.length
              ? `<select class="small" data-method="${o.id}"><option value="cash">Cash</option><option value="card">Card</option><option value="upi">UPI</option><option value="room_charge">Room charge</option></select>
                 <button class="small" data-action="pay" data-id="${o.id}" data-due="${due}">Pay ${money(due)}</button>`
              : ""}
          </div></details>`;
        })
        .join("") || '<p class="muted">No orders yet.</p>'}</div>`;
    const editor = linesEditor($("#lines"), { items, label: "Menu item" });
    $("#add-line").onclick = editor.addRow;
    onSubmit($("#f"), (d) =>
      api("/orders", { method: "POST", body: { ...d, lines: editor.read().map((l) => ({ menu_item_id: l.item, quantity: l.qty })) } })
    );
    onAction(view, {
      status: (d) => api(`/orders/${d.id}/status`, { method: "POST", body: { status: d.status } }),
      rm: (d) => api(`/orders/${d.id}/lines/${d.line}`, { method: "DELETE" }),
      bill: (d) => printBill(d.id),
      addline: (d) =>
        api(`/orders/${d.id}/lines`, {
          method: "POST",
          body: { menu_item_id: Number($(`[data-add-item="${d.id}"]`).value), quantity: Number($(`[data-add-qty="${d.id}"]`).value) },
        }),
      pay: async (d) => {
        const method = $(`[data-method="${d.id}"]`).value;
        await api(`/orders/${d.id}/payments`, { method: "POST", body: { method, amount_minor: Number(d.due) } });
        toast("Payment recorded, stock consumed");
      },
    });
  };

  views.employees = async () => {
    const rows = await api("/hr/employees?include_inactive=true");
    view.innerHTML = `
      <h1>Employees</h1>
      <div class="card"><h2>Add employee</h2>
        <form id="f" class="inline">
          <label>Code <input name="employee_code" required></label>
          <label>Full name <input name="full_name" required></label>
          <label>Department <input name="department" required></label>
          <label>Designation <input name="designation" required></label>
          <label>Pay type <select name="pay_type"><option value="monthly">Monthly salary</option><option value="hourly">Hourly rate</option></select></label>
          <label>Base pay <input name="pay" type="number" step="0.01" min="0" required></label>
          <label>Hired on <input name="hired_on" type="date" value="${today()}" required></label>
          <label>Phone <input name="phone"></label>
          <label>Bank account <input name="bank_account"></label>
          <button>Add</button>
        </form></div>
      <div class="card"><h2>Salary advance</h2>
        <form id="adv" class="inline">
          <label>Employee <select name="employee_id">${options(rows.filter((r) => r.is_active), (r) => `${r.employee_code} ${r.full_name}`)}</select></label>
          <label>Amount <input name="amount" type="number" step="0.01" min="0" required></label>
          <label>Date <input name="given_on" type="date" value="${today()}" required></label>
          <label>Note <input name="note"></label>
          <button>Record advance</button>
        </form></div>
      <div class="card">${table(
        [
          { label: "Code", render: (r) => esc(r.employee_code) },
          { label: "Name", render: (r) => esc(r.full_name) },
          { label: "Department", render: (r) => esc(r.department) },
          { label: "Designation", render: (r) => esc(r.designation) },
          { label: "Pay", num: true, render: (r) => `${money(r.base_pay_minor)} / ${r.pay_type === "monthly" ? "month" : "hour"}` },
          { label: "Hired", render: (r) => esc(r.hired_on) },
          { label: "Status", render: (r) => (r.is_active ? "active" : '<span class="muted">left</span>') },
          { label: "", render: (r) => `<button class="small secondary" data-action="toggle" data-id="${r.id}" data-active="${r.is_active}">${r.is_active ? "Mark left" : "Reactivate"}</button>` },
        ],
        rows
      )}</div>`;
    onSubmit($("#f"), (d) => api("/hr/employees", { method: "POST", body: { ...d, base_pay_minor: Math.round(d.pay * 100) } }));
    onSubmit($("#adv"), (d) => api("/hr/advances", { method: "POST", body: { ...d, amount_minor: Math.round(d.amount * 100) } }));
    onAction(view, { toggle: (d) => api(`/hr/employees/${d.id}`, { method: "PATCH", body: { is_active: d.active !== "true" } }) });
  };

  views.attendance = async () => {
    const day = sessionStorage.getItem("att-day") || today();
    const [emps, marks] = await Promise.all([api("/hr/employees"), api(`/hr/attendance?date_from=${day}&date_to=${day}`)]);
    const byEmp = Object.fromEntries(marks.map((m) => [m.employee_id, m]));
    const statuses = ["present", "absent", "half_day", "leave", "holiday"];
    view.innerHTML = `
      <h1>Attendance</h1>
      <div class="card">
        <form class="inline" id="day"><label>Date <input name="day" type="date" value="${day}"></label><button class="secondary">Load</button></form>
      </div>
      <div class="card">${table(
        [
          { label: "Employee", render: (e) => `${esc(e.employee_code)} ${esc(e.full_name)}` },
          { label: "Status", render: (e) => `<select data-status="${e.id}">${statuses.map((s) => `<option value="${s}" ${byEmp[e.id]?.status === s ? "selected" : ""}>${s.replace("_", " ")}</option>`).join("")}</select>` },
          { label: "Check in", render: (e) => `<input type="time" data-in="${e.id}" value="${byEmp[e.id]?.check_in?.slice(11, 16) ?? ""}">` },
          { label: "Check out", render: (e) => `<input type="time" data-out="${e.id}" value="${byEmp[e.id]?.check_out?.slice(11, 16) ?? ""}">` },
          { label: "Hours", num: true, render: (e) => (byEmp[e.id] ? num(byEmp[e.id].hours_worked) : "—") },
          { label: "", render: (e) => `<button class="small" data-action="mark" data-id="${e.id}">Save</button>` },
        ],
        emps,
        "No active employees."
      )}</div>`;
    $("#day").addEventListener("submit", (e) => {
      e.preventDefault();
      sessionStorage.setItem("att-day", e.target.day.value);
      render();
    });
    onAction(view, {
      mark: (d) => {
        const t = (v) => (v ? `${day}T${v}:00` : null);
        return api("/hr/attendance", {
          method: "POST",
          body: { employee_id: Number(d.id), work_date: day, status: $(`[data-status="${d.id}"]`).value, check_in: t($(`[data-in="${d.id}"]`).value), check_out: t($(`[data-out="${d.id}"]`).value) },
        });
      },
    });
  };

  views.payroll = async () => {
    const [runs, emps] = await Promise.all([api("/payroll/runs"), api("/hr/employees?include_inactive=true")]);
    const empById = Object.fromEntries(emps.map((e) => [e.id, e]));
    const now = new Date();
    view.innerHTML = `
      <h1>Payroll</h1>
      <div class="card"><h2>New payroll run</h2>
        <form id="f" class="inline">
          <label>Year <input name="period_year" type="number" value="${now.getFullYear()}" required></label>
          <label>Month <input name="period_month" type="number" min="1" max="12" value="${now.getMonth() + 1}" required></label>
          <label>Working days <input name="working_days" type="number" min="1" max="31" value="26" required></label>
          <button>Compute draft</button>
        </form></div>
      ${runs
        .map(
          (r) => `<div class="card">
          <h2>${r.period_year}-${String(r.period_month).padStart(2, "0")} ${badge(r.status)} <span class="muted">gross ${money(r.total_gross_minor)} · deductions ${money(r.total_deductions_minor)} · <b>net ${money(r.total_net_minor)}</b></span></h2>
          ${table(
            [
              { label: "Employee", render: (p) => esc(empById[p.employee_id]?.full_name ?? p.employee_id) },
              { label: "Present", num: true, render: (p) => num(p.days_present, 1) },
              { label: "Absent", num: true, render: (p) => num(p.days_absent, 1) },
              { label: "OT hrs", num: true, render: (p) => num(p.overtime_hours, 1) },
              { label: "Basic", num: true, render: (p) => money(p.basic_minor) },
              { label: "Overtime", num: true, render: (p) => money(p.overtime_minor) },
              { label: "Allowance", num: true, render: (p) => money(p.allowance_minor) },
              { label: "Gross", num: true, render: (p) => money(p.gross_minor) },
              { label: "Absence", num: true, render: (p) => money(p.absence_deduction_minor) },
              { label: "Statutory", num: true, render: (p) => money(p.statutory_deduction_minor) },
              { label: "Advance", num: true, render: (p) => money(p.advance_deduction_minor) },
              { label: "Net pay", num: true, render: (p) => `<b>${money(p.net_minor)}</b>` },
            ],
            r.payslips
          )}
          ${r.status === "draft" ? `<div class="actions" style="margin-top:8px">
            <button class="small secondary" data-action="recompute" data-id="${r.id}">Recompute</button>
            <button class="small" data-action="finalize" data-id="${r.id}">Finalize &amp; lock</button>
            <button class="small danger" data-action="delete" data-id="${r.id}">Delete draft</button></div>` : `<p class="muted">Finalized ${esc(r.finalized_at?.slice(0, 16).replace("T", " "))}</p>`}
        </div>`
        )
        .join("")}`;
    onSubmit($("#f"), (d) => api("/payroll/runs", { method: "POST", body: d }));
    onAction(view, {
      recompute: (d) => api(`/payroll/runs/${d.id}/recompute`, { method: "POST" }),
      finalize: (d) => confirm("Finalize this payroll run? It cannot be changed afterwards.") ? api(`/payroll/runs/${d.id}/finalize`, { method: "POST" }) : null,
      delete: (d) => api(`/payroll/runs/${d.id}`, { method: "DELETE" }),
    });
  };

  views.reports = async () => {
    const from = sessionStorage.getItem("rep-from") || monthStart();
    const to = sessionStorage.getItem("rep-to") || today();
    const q = `date_from=${from}&date_to=${to}`;
    const [sales, top, spend] = await Promise.all([api(`/reports/sales?${q}`), api(`/reports/top-items?${q}`), api(`/reports/supplier-spend?${q}`)]);
    const kpi = (label, value) => `<div class="kpi"><div class="label">${label}</div><div class="value">${value}</div></div>`;
    view.innerHTML = `
      <h1>Reports</h1>
      <div class="card"><form class="inline" id="range">
        <label>From <input name="from" type="date" value="${from}"></label>
        <label>To <input name="to" type="date" value="${to}"></label>
        <button class="secondary">Run</button></form></div>
      <div class="kpis">
        ${kpi("Orders paid", sales.orders_paid)}
        ${kpi("Cancelled", sales.orders_cancelled)}
        ${kpi("Net sales", money(sales.net_sales_minor))}
        ${kpi("Tax collected", money(sales.tax_collected_minor))}
        ${kpi("Gross sales", money(sales.gross_sales_minor))}
        ${kpi("Food cost", money(sales.food_cost_minor))}
        ${kpi("Gross margin", `${money(sales.gross_margin_minor)} <span class="muted">(${sales.gross_margin_percent}%)</span>`)}
        ${kpi("Average ticket", money(sales.average_ticket_minor))}
      </div>
      <div class="grid cols-2">
        <div class="card"><h2>Top menu items</h2>${table(
          [
            { label: "Item", render: (r) => esc(r.name) },
            { label: "Sold", num: true, render: (r) => r.quantity_sold },
            { label: "Revenue", num: true, render: (r) => money(r.revenue_minor) },
          ],
          top,
          "No sales in this period."
        )}</div>
        <div class="card"><h2>Supplier spend (goods received)</h2>${table(
          [
            { label: "Supplier", render: (r) => esc(r.supplier_name) },
            { label: "POs", num: true, render: (r) => r.purchase_orders },
            { label: "Value", num: true, render: (r) => money(r.received_value_minor) },
          ],
          spend,
          "No goods received in this period."
        )}</div>
      </div>`;
    $("#range").addEventListener("submit", (e) => {
      e.preventDefault();
      sessionStorage.setItem("rep-from", e.target.from.value);
      sessionStorage.setItem("rep-to", e.target.to.value);
      render();
    });
  };

  // Fetch the printable bill with the bearer token, then hand it to a print window.
  async function printBill(orderId) {
    const res = await fetch(`${API}/orders/${orderId}/bill.html`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
    const win = window.open("", "_blank", "width=420,height=640");
    if (!win) throw new Error("Pop-up blocked: allow pop-ups for this site to print bills");
    win.document.open();
    win.document.write(await res.text());
    win.document.close();
    win.focus();
    win.addEventListener("load", () => win.print());
  }

  views.reservations = async () => {
    const day = sessionStorage.getItem("res-day") || today();
    const rows = await api(`/reservations?on=${day}`);
    const fmtTime = (iso) => iso.slice(11, 16);
    const endOf = (r) => {
      const d = new Date(r.reserved_at);
      d.setMinutes(d.getMinutes() + r.duration_minutes);
      return d.toTimeString().slice(0, 5);
    };
    view.innerHTML = `
      <h1>Table reservations</h1>
      <div class="card"><h2>New reservation</h2>
        <form id="f" class="inline">
          <label>Guest name <input name="guest_name" required></label>
          <label>Phone <input name="guest_phone"></label>
          <label>Party size <input name="party_size" type="number" min="1" value="2" required></label>
          <label>Table <input name="table_number" required placeholder="T4"></label>
          <label>Date <input name="date" type="date" value="${day}" required></label>
          <label>Time <input name="time" type="time" value="19:30" required></label>
          <label>Duration (min) <input name="duration_minutes" type="number" min="15" step="15" value="90"></label>
          <label>Notes <input name="notes"></label>
          <button>Book</button>
        </form></div>
      <div class="card">
        <form class="inline" id="day"><label>Show date <input name="day" type="date" value="${day}"></label><button class="secondary">Load</button></form>
        ${table(
          [
            { label: "Time", render: (r) => `${fmtTime(r.reserved_at)} to ${endOf(r)}` },
            { label: "Table", render: (r) => esc(r.table_number) },
            { label: "Guest", render: (r) => `${esc(r.guest_name)}<br><span class="muted">${esc(r.guest_phone ?? "")}</span>` },
            { label: "Party", num: true, render: (r) => r.party_size },
            { label: "Status", render: (r) => badge(r.status) },
            { label: "Notes", render: (r) => esc(r.notes) },
            { label: "", render: (r) => `<div class="actions">
                ${r.status === "booked" ? `<button class="small" data-action="seat" data-id="${r.id}">Seat &amp; open order</button>
                  <button class="small secondary" data-action="status" data-id="${r.id}" data-status="no_show">No-show</button>` : ""}
                ${r.status === "seated" ? `<a class="btn small" href="#orders">Go to order</a>` : ""}
                ${["booked", "seated"].includes(r.status) ? `<button class="small danger" data-action="status" data-id="${r.id}" data-status="cancelled">Cancel</button>` : ""}
              </div>` },
          ],
          rows,
          "No reservations for this day."
        )}
      </div>`;
    onSubmit($("#f"), (d) =>
      api("/reservations", {
        method: "POST",
        body: { ...d, reserved_at: `${d.date}T${d.time}:00`, date: undefined, time: undefined },
      })
    );
    $("#day").addEventListener("submit", (e) => {
      e.preventDefault();
      sessionStorage.setItem("res-day", e.target.day.value);
      render();
    });
    onAction(view, {
      seat: async (d) => {
        await api(`/reservations/${d.id}/seat`, { method: "POST" });
        toast("Guests seated; a dine-in order is open on the Orders page");
      },
      status: (d) => api(`/reservations/${d.id}/status`, { method: "POST", body: { status: d.status } }),
    });
  };

  views.users = async () => {
    const rows = await api("/auth/users");
    const roles = ["admin", "manager", "chef", "cashier", "storekeeper", "hr", "accountant"];
    view.innerHTML = `
      <h1>Users</h1>
      <div class="card"><h2>Create user</h2>
        <form id="f" class="inline">
          <label>Email <input name="email" type="email" required></label>
          <label>Full name <input name="full_name" required></label>
          <label>Role <select name="role">${roles.map((r) => `<option>${r}</option>`).join("")}</select></label>
          <label>Password (8+ chars) <input name="password" type="password" minlength="8" required></label>
          <button>Create</button>
        </form></div>
      <div class="card">${table(
        [
          { label: "Email", render: (u) => esc(u.email) },
          { label: "Name", render: (u) => esc(u.full_name) },
          { label: "Role", render: (u) => `<select data-role="${u.id}">${roles.map((r) => `<option ${u.role === r ? "selected" : ""}>${r}</option>`).join("")}</select>` },
          { label: "Status", render: (u) => (u.is_active ? "active" : '<span class="muted">disabled</span>') },
          { label: "", render: (u) => `<div class="actions">
              <button class="small secondary" data-action="role" data-id="${u.id}">Save role</button>
              <button class="small ${u.is_active ? "danger" : ""}" data-action="toggle" data-id="${u.id}" data-active="${u.is_active}">${u.is_active ? "Disable" : "Enable"}</button>
              <button class="small secondary" data-action="reset" data-id="${u.id}">Reset password</button></div>` },
        ],
        rows
      )}
      <p class="muted">Demo accounts use a public password. Once your own admin works, disable them here.</p></div>`;
    onSubmit($("#f"), (d) => api("/auth/users", { method: "POST", body: d }));
    onAction(view, {
      role: (d) => api(`/auth/users/${d.id}`, { method: "PATCH", body: { role: $(`[data-role="${d.id}"]`).value } }),
      toggle: (d) => api(`/auth/users/${d.id}`, { method: "PATCH", body: { is_active: d.active !== "true" } }),
      reset: async (d) => {
        const pw = prompt("New password (at least 8 characters):");
        if (!pw) return;
        await api(`/auth/users/${d.id}/reset-password`, { method: "POST", body: { new_password: pw } });
        toast("Password reset");
      },
    });
  };

  async function changeOwnPassword() {
    const current = prompt("Current password:");
    if (!current) return;
    const next = prompt("New password (at least 8 characters):");
    if (!next) return;
    try {
      await api("/auth/change-password", { method: "POST", body: { current_password: current, new_password: next } });
      toast("Password changed");
    } catch (err) {
      toast(err.message, true);
    }
  }

  // ---------- router ----------
  async function loadMe() {
    if (!localStorage.getItem("token")) return (me = null);
    try {
      me = await api("/auth/me");
    } catch {
      me = null;
    }
  }

  async function render() {
    const nav = $("#nav"), box = $("#user-box");
    if (!me) {
      nav.hidden = box.hidden = true;
      return views.login();
    }
    nav.hidden = box.hidden = false;
    $("#user-name").textContent = me.full_name;
    $("#user-role").textContent = me.role;
    $("#nav-users").hidden = me.role !== "admin";
    const route = location.hash.replace("#", "") || "dashboard";
    nav.querySelectorAll("a").forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${route}`));
    const fn = views[route] || views.dashboard;
    view.innerHTML = '<p class="muted">Loading…</p>';
    try {
      await fn();
    } catch (err) {
      view.innerHTML = `<div class="card"><p class="warn">${esc(err.message)}</p></div>`;
    }
  }

  $("#change-pw").onclick = changeOwnPassword;
  $("#logout").onclick = () => {
    localStorage.removeItem("token");
    me = null;
    location.hash = "";
    render();
  };
  window.addEventListener("hashchange", render);
  loadMe().then(render);
})();
