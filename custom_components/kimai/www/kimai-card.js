/**
 * Kimai dashboard card.
 *
 * Plain custom element, no build step or bundled dependencies. It reads
 * Kimai project sensor state from the `hass` object that Home Assistant's
 * frontend already keeps live over its existing websocket connection, and
 * writes new time entries via the `kimai.add_timesheet` service call (same
 * connection). There is no separate backend for this card to talk to.
 */
const CARD_VERSION = "0.1.6";
console.info(`Kimai Card version ${CARD_VERSION}`);

class KimaiCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
    this._showDialog = false;
    this._error = null;
    this._form = null;
    this._render();
  }

  set hass(hass) {
    const firstAssignment = !this._hass;
    this._hass = hass;
    if (this._showDialog && !firstAssignment) {
      return;
    }
    this._render();
  }

  getCardSize() {
    return 3;
  }

  static getStubConfig() {
    return { title: "Kimai" };
  }

  _labelFor(entityId) {
    const state = this._hass && this._hass.states[entityId];
    const attrs = (state && state.attributes) || {};
    return attrs.project_name || attrs.friendly_name || entityId;
  }

  _entityIds() {
    if (this._config.entities && this._config.entities.length) {
      return this._config.entities;
    }
    if (!this._hass) {
      return [];
    }
    return Object.keys(this._hass.states)
      .filter((entityId) => entityId.startsWith("sensor."))
      .filter((entityId) => {
        const attrs = this._hass.states[entityId].attributes || {};
        return "week_hours" in attrs && "month_hours" in attrs && "activities" in attrs;
      })
      .sort();
  }

  _openDialog(entityIds) {
    const firstEntity = entityIds[0] || "";
    const activities = this._activitiesFor(firstEntity);
    this._form = {
      entityId: firstEntity,
      activityId: activities[0] ? String(activities[0].id) : "",
      date: new Date().toISOString().slice(0, 10),
      startTime: "",
      durationMinutes: "",
      endTime: "",
      description: "",
      billable: true,
    };
    this._error = null;
    this._showDialog = true;
    this._render();
  }

  _closeDialog() {
    this._showDialog = false;
    this._form = null;
    this._error = null;
    this._render();
  }

  _activitiesFor(entityId) {
    const state = this._hass && this._hass.states[entityId];
    return (state && state.attributes && state.attributes.activities) || [];
  }

  _onProjectChange(entityId) {
    const activities = this._activitiesFor(entityId);
    this._form = {
      ...this._form,
      entityId,
      activityId: activities[0] ? String(activities[0].id) : "",
    };
    this._render();
  }

  async _submit() {
    const form = this._form;
    if (!form.entityId || !form.activityId || !form.date || !form.startTime) {
      this._error = "Please fill in project, activity, date, and start time.";
      this._render();
      return;
    }
    const hasDuration = !!form.durationMinutes;
    const hasEndTime = !!form.endTime;
    if (hasDuration === hasEndTime) {
      this._error = "Provide exactly one of duration or end time (not both, not neither).";
      this._render();
      return;
    }

    const data = {
      entity_id: form.entityId,
      activity_id: Number(form.activityId),
      date: form.date,
      start_time: form.startTime,
    };
    if (hasDuration) {
      data.duration_minutes = Number(form.durationMinutes);
    } else {
      data.end_time = form.endTime;
    }
    if (form.description) {
      data.description = form.description;
    }
    data.billable = !!form.billable;

    try {
      await this._hass.callService("kimai", "add_timesheet", data);
      this._closeDialog();
    } catch (err) {
      this._error = (err && err.message) || "Failed to add time entry.";
      this._render();
    }
  }

  _renderRow(entityId) {
    const state = this._hass.states[entityId];
    if (!state) {
      return "";
    }
    const attrs = state.attributes || {};
    const name = this._labelFor(entityId);
    const week = attrs.week_hours ?? 0;
    const month = attrs.month_hours ?? 0;
    const budget = attrs.time_budget_hours || 0;
    const pct = budget > 0 ? Math.min(100, (month / budget) * 100) : 0;
    return `
      <div class="row">
        <div class="row-header">
          <span class="name">${name}</span>
          ${attrs.active ? '<span class="badge">&#9679; running</span>' : ""}
        </div>
        <div class="totals">
          <span>Week: <b>${week}h</b></span>
          <span>Month: <b>${month}h</b></span>
        </div>
        ${budget > 0 ? `<div class="bar"><div class="bar-fill" style="width:${pct}%"></div></div>` : ""}
      </div>
    `;
  }

  _renderDialog(entityIds) {
    const form = this._form;
    const activities = this._activitiesFor(form.entityId);
    return `
      <div class="overlay" id="overlay">
        <div class="dialog">
          <h2>Add time entry</h2>
          ${this._error ? `<div class="error">${this._error}</div>` : ""}
          <div class="dialog-grid">
            <label>Project
              <select id="f-project">
                ${entityIds
                  .map((id) => {
                    const label = this._labelFor(id);
                    return `<option value="${id}" ${id === form.entityId ? "selected" : ""}>${label}</option>`;
                  })
                  .join("")}
              </select>
            </label>
            <label>Activity
              <select id="f-activity">
                ${activities
                  .map(
                    (a) =>
                      `<option value="${a.id}" ${String(a.id) === form.activityId ? "selected" : ""}>${a.name}</option>`
                  )
                  .join("")}
              </select>
            </label>
            <label>Date
              <input type="date" id="f-date" value="${form.date}" />
            </label>
            <label>Start time
              <input type="time" id="f-start" value="${form.startTime}" />
            </label>
            <label>Duration (minutes)
              <input type="number" id="f-duration" min="1" placeholder="e.g. 60" value="${form.durationMinutes}" />
            </label>
            <label>OR end time
              <input type="time" id="f-end" value="${form.endTime}" />
            </label>
            <label class="span-2">Description
              <textarea id="f-desc" rows="3">${form.description}</textarea>
            </label>
            <label class="span-2 checkbox-row">
              <input type="checkbox" id="f-billable" ${form.billable ? "checked" : ""} />
              Billable
            </label>
          </div>
          <div class="dialog-actions">
            <button id="f-cancel">Cancel</button>
            <button id="f-submit" class="primary">Submit</button>
          </div>
        </div>
      </div>
    `;
  }

  _render() {
    if (!this.shadowRoot || !this._hass) {
      return;
    }
    const entityIds = this._entityIds();
    const rows = entityIds.map((id) => this._renderRow(id)).join("");
    const title = this._config.title || "Kimai";

    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 8px 0; }
        .card-header { display: flex; align-items: baseline; gap: 8px; padding: 8px 16px 0; }
        .card-header h1 { font-size: 1.5em; margin: 0; font-weight: 400; }
        .card-version { font-size: 0.65em; color: var(--secondary-text-color); }
        .card-content { padding: 0 16px 16px; }
        .rows-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
        .row { padding: 8px 0; border-bottom: 1px solid var(--divider-color, #eee); }
        .row-header { display: flex; justify-content: space-between; align-items: center; }
        .name { font-weight: 500; }
        .badge { font-size: 0.8em; color: var(--success-color, green); }
        .totals { display: flex; gap: 16px; font-size: 0.9em; color: var(--secondary-text-color); margin-top: 2px; }
        .bar { height: 4px; background: var(--divider-color, #eee); border-radius: 2px; margin-top: 6px; overflow: hidden; }
        .bar-fill { height: 100%; background: var(--primary-color, #03a9f4); }
        .empty { color: var(--secondary-text-color); padding: 8px 0; }
        .add-btn {
          margin-top: 12px; width: 100%; padding: 10px; border: none; border-radius: 4px;
          background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff);
          font-size: 1em; cursor: pointer;
        }
        .overlay {
          position: fixed; inset: 0; background: rgba(0,0,0,0.5);
          display: flex; align-items: center; justify-content: center; z-index: 1000;
        }
        .dialog {
          background: var(--card-background-color, #fff); color: var(--primary-text-color, #000);
          padding: 16px 20px; border-radius: 8px; width: 460px; max-width: 90vw;
          max-height: 85vh; overflow-y: auto;
        }
        .dialog h2 { margin-top: 0; }
        .dialog-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12px; }
        .dialog label { display: block; margin-bottom: 10px; font-size: 0.9em; }
        .dialog label.span-2 { grid-column: 1 / -1; }
        .dialog input, .dialog select, .dialog textarea {
          width: 100%; box-sizing: border-box; padding: 6px; margin-top: 4px;
          border: 1px solid var(--divider-color, #ccc); border-radius: 4px; background: transparent; color: inherit;
          font-family: inherit; font-size: inherit; resize: vertical;
        }
        .dialog label.checkbox-row { display: flex; align-items: center; gap: 8px; margin-bottom: 0; }
        .dialog input[type="checkbox"] { width: auto; margin-top: 0; }
        .dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
        .dialog-actions button { padding: 8px 14px; border-radius: 4px; border: 1px solid var(--divider-color, #ccc); background: none; cursor: pointer; color: inherit; }
        .dialog-actions button.primary { background: var(--primary-color, #03a9f4); color: var(--text-primary-color, #fff); border: none; }
        .error { color: var(--error-color, #db4437); margin-bottom: 10px; font-size: 0.9em; }
        @media (max-width: 480px) {
          .dialog-grid { grid-template-columns: 1fr; }
        }
      </style>
      <ha-card>
        <div class="card-header">
          <h1>${title}</h1>
          <span class="card-version">v${CARD_VERSION}</span>
        </div>
        <div class="card-content">
          ${rows ? `<div class="rows-grid">${rows}</div>` : '<div class="empty">No Kimai project activity this week or month yet.</div>'}
          <button class="add-btn" id="add-btn">+ Add time</button>
        </div>
      </ha-card>
      ${this._showDialog ? this._renderDialog(entityIds) : ""}
    `;

    const addBtn = this.shadowRoot.getElementById("add-btn");
    if (addBtn) {
      addBtn.addEventListener("click", () => this._openDialog(entityIds));
    }

    if (this._showDialog) {
      const overlay = this.shadowRoot.getElementById("overlay");
      overlay.addEventListener("click", (ev) => {
        if (ev.target === overlay) {
          this._closeDialog();
        }
      });
      this.shadowRoot.getElementById("f-cancel").addEventListener("click", () => this._closeDialog());
      this.shadowRoot.getElementById("f-submit").addEventListener("click", () => this._submit());
      this.shadowRoot.getElementById("f-project").addEventListener("change", (ev) => this._onProjectChange(ev.target.value));

      const bindField = (id, key) => {
        const el = this.shadowRoot.getElementById(id);
        el.addEventListener("input", (ev) => {
          this._form[key] = ev.target.value;
        });
      };
      bindField("f-activity", "activityId");
      bindField("f-date", "date");
      bindField("f-start", "startTime");
      bindField("f-duration", "durationMinutes");
      bindField("f-end", "endTime");
      bindField("f-desc", "description");

      this.shadowRoot.getElementById("f-billable").addEventListener("change", (ev) => {
        this._form.billable = ev.target.checked;
      });
    }
  }
}

customElements.define("kimai-card", KimaiCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "kimai-card",
  name: "Kimai Card",
  description: "Shows Kimai project time tracked this week/month and lets you log new entries.",
});
