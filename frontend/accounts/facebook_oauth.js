export class FacebookOAuthManager {
  constructor({ connectButton, platformSelect, statusBox, pagePicker, onAccountsAdded }) {
    this.connectButton = connectButton;
    this.platformSelect = platformSelect;
    this.statusBox = statusBox;
    this.pagePicker = pagePicker;
    this.onAccountsAdded = onAccountsAdded;
    this.popup = null;
    this.flowId = null;

    this.connectButton?.addEventListener('click', () => this.start());
    this.platformSelect?.addEventListener('change', () => this.updateVisibility());
    window.addEventListener('message', (event) => this.handleMessage(event));
    this.updateVisibility();
  }

  updateVisibility() {
    const facebook = this.platformSelect?.value === 'facebook';
    if (this.connectButton) this.connectButton.hidden = !facebook;
    if (this.pagePicker) this.pagePicker.hidden = !facebook || !this.flowId;
  }

  async start() {
    this.setStatus('Starting secure Facebook connection…');
    this.pagePicker.hidden = true;
    const response = await fetch('/api/oauth/facebook/start', { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to start Facebook connection.');

    this.flowId = data.flow_id;
    this.popup = window.open(data.login_url, 'meta-facebook-connect', 'popup,width=620,height=760,resizable=yes,scrollbars=yes');
    if (!this.popup) throw new Error('Popup was blocked. Allow popups for this local app and try again.');
    this.setStatus('Complete Facebook authorization in the new window…');
  }

  async handleMessage(event) {
    if (event.origin !== window.location.origin) return;
    const message = event.data || {};
    if (message.type !== 'meta-oauth') return;

    if (message.status === 'error') {
      this.setStatus(message.message || 'Facebook authorization failed.', true);
      return;
    }
    if (message.status !== 'ready' || !message.flow_id) return;

    this.flowId = message.flow_id;
    this.setStatus(`Facebook connected. ${message.page_count || 0} Page(s) found. Select what to add.`);
    await this.loadPages();
  }

  async loadPages() {
    const response = await fetch(`/api/oauth/facebook/pages?flow_id=${encodeURIComponent(this.flowId)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to load Facebook Pages.');

    const pages = data.pages || [];
    this.pagePicker.innerHTML = pages.length
      ? `<div class="oauth-page-picker-head"><strong>Select Facebook Pages</strong><span>${pages.length} available</span></div>` + pages.map((page) => `
          <label class="oauth-page-option">
            <input type="checkbox" value="${this.escape(page.id)}" data-page-id="${this.escape(page.id)}">
            <span><strong>${this.escape(page.name)}</strong><small>Page ID: ${this.escape(page.id)}</small></span>
          </label>`).join('') + `<button id="add-selected-facebook-pages" class="secondary-btn oauth-add-pages" type="button">Add Selected Pages</button>`
      : '<div class="oauth-empty">No Facebook Pages were returned for this account. Check Page access and reconnect.</div>';

    this.pagePicker.hidden = false;
    this.pagePicker.querySelector('#add-selected-facebook-pages')?.addEventListener('click', () => this.complete());
  }

  async complete() {
    const pageIds = [...this.pagePicker.querySelectorAll('input[data-page-id]:checked')].map((input) => input.dataset.pageId);
    if (!pageIds.length) {
      this.setStatus('Select at least one Facebook Page.', true);
      return;
    }

    this.setStatus('Saving selected Pages securely…');
    const response = await fetch('/api/oauth/facebook/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ flow_id: this.flowId, page_ids: pageIds }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Unable to save Facebook Pages.');

    this.setStatus(`Added ${data.accounts?.length || 0} Facebook Page account(s).`);
    this.pagePicker.hidden = true;
    this.flowId = null;
    this.onAccountsAdded?.();
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
