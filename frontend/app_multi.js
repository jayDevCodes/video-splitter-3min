import { ProgressManager } from './progress/progress_manager.js';
import { ManagedFacebookManager } from './accounts/managed_facebook.js';

const $ = (selector) => document.querySelector(selector);
const splitForm = $('#split-form');
const uploadForm = $('#multi-upload-form');
const accountForm = $('#account-form');
const oldBtn = $('#show-old-upload-btn');
const oldSection = $('#old-upload-section');
const uploadSection = $('#upload-section');
const folderSelect = $('#old-folder-select');
const folderEmpty = $('#old-folder-empty');
const fileInput = $('#video-file');
const fileName = $('#file-name');
const statusBox = $('#status');
const resultBox = $('#result');
const uploadResultBox = $('#upload-result');
const accountTargetsBox = $('#account-targets');
const uploadButton = $('#upload-btn');
const splitButton = $('#split-btn');
const outputFolderBox = $('#output-folder');
const partsCountBox = $('#parts-count');
const outputDirectoryInput = $('#upload-output-directory');
const titleInput = $('#upload-title-template');
const descriptionInput = $('#upload-description');
const gapInput = $('#upload-gap');
const tagsInput = $('#upload-tags');
const privacyInput = $('#upload-privacy');
const categoryInput = $('#upload-category-id');
const deleteInput = $('#delete-after-upload');
const thumbnailInput = $('#upload-thumbnail');
const liveProgressBox = $('#live-progress');
const accountPlatform = $('#account-platform');
const accountIdInput = $('#account-id');
const accountNameInput = $('#account-name');
const accountExternalIdInput = $('#account-external-id');
const accountConfiguredInput = $('#account-configured');
const manualAccountButton = $('#manual-account-btn');

let generatedFolder = '';
let accounts = { youtube: [], facebook: [], instagram: [] };
const progress = new ProgressManager(liveProgressBox);

const facebookOAuth = new ManagedFacebookManager({
  connectButton: $('#connect-facebook-btn'),
  platformSelect: accountPlatform,
  statusBox: $('#oauth-status'),
  pagePicker: $('#facebook-page-picker'),
  onAccountsAdded: async () => {
    await loadAccounts();
    statusBox.hidden = false;
    statusBox.textContent = 'Facebook Pages added. Select them in the upload targets below.';
  },
});

function updateAccountFormMode() {
  const facebook = accountPlatform.value === 'facebook';
  accountIdInput.required = !facebook;
  accountNameInput.required = !facebook;
  accountIdInput.disabled = facebook;
  accountNameInput.disabled = facebook;
  accountExternalIdInput.disabled = facebook;
  accountConfiguredInput.disabled = facebook;
  manualAccountButton.hidden = facebook;
}

accountPlatform?.addEventListener('change', updateAccountFormMode);
updateAccountFormMode();

fileInput?.addEventListener('change', () => {
  fileName.textContent = fileInput.files?.[0]?.name || 'MP4, MOV, MKV, AVI, WEBM and more';
});

async function loadAccounts() {
  const response = await fetch('/api/accounts', { cache: 'no-store' });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Unable to load accounts.');
  accounts = data.accounts || accounts;
  renderAccounts();
}

