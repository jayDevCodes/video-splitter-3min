export class ManagedFacebookManager {
  constructor({ connectButton, platformSelect, statusBox, pagePicker, onAccountsAdded }) {
    this.connectButton = connectButton;
    this.platformSelect = platformSelect;
    this.statusBox = statusBox;
    this.pagePicker = pagePicker;
    this.onAccountsAdded = onAccountsAdded;
    this.popup = null;
    this.flowId = null;
    this.starting = false;

    this.connectButton?.addEventListener('click', () => {
      this.start().catch((error) => this.setStatus(error?.message || 'Unable to connect Facebook.', true));
    });
    this.platformSelect?.addEventListener('change', () => this.updateVisibility());
    window.addEventListener('message', (event) => {
      this.handleMessage(event).catch((error) => this.setStatus(error?.message || 'Unable to finish Facebook connection.', true));
    });
    this.updateVisibility();
  }

  updateVisibility() {
    const facebook = this.platformSelect?.value === 'facebook';
    if (this.connectButton) this.connectButton.hidden = !facebook;
    if (this.pagePicker) this.pagePicker.hidden = !facebook || !this.flowId;
  }

  async start() {
    if (this.starting) return;
    this.starting = true;
    this.connectButton.disabled = true;
    this.setStatus('Opening secure Facebook connection…');
    this.pagePicker.hidden = true;

    // Create the popup synchronously from the click before awaiting the backend.
    this.popup = window.open('about:blank', 'managed-facebook-connect', 'popup,width=680,height=820,resizable=yes,scrollbars=yes');
    if (!this.popup) {
      this.connectButton.disabled = false;
      throw new Error('Facebook connection window was blocked. Allow popups for this local app and try again.');
    }

    try {
      const response = await fetch('/api/oauth/facebook/managed/start', { cache: 'no-store' });
      const data = await this.readJson(response);
      if (!response.ok) throw new Error(data.detail || 'Managed Facebook connection is unavailable.');
      if (!data.flow_id || !data.login_url) throw new Error('Connection provider did not return a valid login URL.');

      this.flowId = data.flow_id;
      this.popup.location.href = data.login_url;
      this.setStatus('Complete Facebook login and Page authorization in the new window…');
    } catch (error) {
      try { if (this.popup && !this.popup.closed) this.popup.close(); } catch (_) {}
      this.popup = null;
      this.flowId = null;
      throw error;
    } finally {
      this.starting = false;
      this.connectButton.disabled = false;
    }
  }

  async handleMessage(event) {
    if (event.origin !== window.location.origin) return;
    const message = event.data || {};
    if (message.type !== 'managed-facebook-oauth') return;

    if (message.status === 'error') {
      this.flowId = null;
      this.setStatus(message.message || 'Facebook authorization failed.', true);
      return;
    }
    if (message.status !== 'ready' || !message.flow_id) return;

    this.flowId = message.flow_id;
    this.setStatus(`Facebook connected. ${message.page_count || 0} Page(s) found.`);
    await this.loadPages();
  }

  async loadPages() {
    if (!this.flowId) throw new Error('Facebook connection is missing. Start again.');
    const response = await fetch(`/api/oauth/facebook/managed/pages?flow_id=${encodeURIComponent(this.flowId)}`, { cache: 'no-store' });
    const data = await this.readJson(response);
    if (!response.ok) throw new Error(data.detail || 'Unable to load Facebook Pages.');

    const pages = data.pages || [];
    this.pagePicker.innerHTML = pages.length
      ? `<div class="oauth-page-picker-head"><strong>Select Facebook Pages</strong><span>${pages.length} available</span></div>` + pages.map((page) => `
          <label class="oauth-page-option">
            <input type="checkbox" value="${this.escape(page.id)}" data-page-id="${this.escape(page.id)}">
            <span><strong>${this.escape(page.name)}</strong><small>Page ID: ${this.escape(page.id)}</small></span>
          </label>`).join('') + `<button id="add-selected-facebook-pages" class="secondary-btn oauth-add-pages" type="button">Add Selected Pages</button>`
      : '<div class="oauth-empty">No Facebook Pages were returned. Make sure the logged-in Facebook account can manage the Page.</div>';

    this.pagePicker.hidden = false;
    this.pagePicker.querySelector('#add-selected-facebook-pages')?.addEventListener('click', () => {
      this.complete().catch((error) => this.setStatus(error?.message || 'Unable to save Facebook Pages.', true));
    });
  }

  async complete() {
    const pageIds = [...this.pagePicker.querySelectorAll('input[data-page-id]:checked')].map((input) => input.dataset.pageId);
    if (!pageIds.length) {
      this.setStatus('Select at least one Facebook Page.', true);
      return;
    }
    this.setStatus('Saving selected Pages…');
    const response = await fetch('/api/oauth/facebook/managed/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flow_id: this.flowId, page_ids: pageIds }),
    });
    const data = await this.readJson(response);
    if (!response.ok) throw new Error(data.detail || 'Unable to save Facebook Pages.');

    this.setStatus(`Added ${data.accounts?.length || 0} Facebook Page account(s).`);
    this.pagePicker.hidden = true;
    this.flowId = null;
    this.popup = null;
    await this.onAccountsAdded?.();
  }

  async readJson(response) {
    const text = await response.text();
    if (!text) return {};
    try { return JSON.parse(text); } catch (_) { return { detail: text.slice(0, 300) }; }
  }

  setStatus(message, error = false) {
    if (!this.statusBox) return;
    this.statusBox.hidden = false;
    this.statusBox.textContent = message;
    this.statusBox.dataset.state = error ? 'error' : 'ready';
  }

  escape(value) {
    return String(value).replace(/[&<>\"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
  }
}
