import { app } from '../../../scripts/app.js';

import { api } from '../../scripts/api.js';
import { $el } from '../../scripts/ui.js';
import { fetchAndPlayAudio, fetchAndPlayAudioSingle, get_video_files, play_ding_dong_text, set_play_type } from './utils.js';

const ID_PREFIX = '⏰Ding_Dong';
const MUSIC_SETTING_PREFIX = `${ID_PREFIX}.music`;
const PREFERRED_DEFAULT_AUDIO = 'ringtone1.mp3';
const LEGACY_DEFAULT_AUDIO = 'is18age.MP3';
const AUDIO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mp3', '.wav'];

const audioSettings = {
  success: {
    id: `${MUSIC_SETTING_PREFIX}.name`,
    selected: null,
    select: null,
  },
  fail: {
    id: `${MUSIC_SETTING_PREFIX}.fail_name`,
    selected: null,
    select: null,
  },
};

let audioFiles = [];
let volume = 100;
let open = true;
let failTip = false;

function createAudioSelect(kind) {
  return $el('select', {
    onchange: (event) => {
      setSelectedAudio(kind, event.target.value || null, { persist: true });
    },
  });
}

audioSettings.success.select = createAudioSelect('success');
audioSettings.fail.select = createAudioSelect('fail');

function audioExists(filename) {
  return Boolean(filename) && audioFiles.includes(filename);
}

function getPreferredAudio() {
  return audioExists(PREFERRED_DEFAULT_AUDIO) ? PREFERRED_DEFAULT_AUDIO : audioFiles[0] || null;
}

function normalizeAudio(value) {
  if (value === undefined) {
    return getPreferredAudio();
  }

  const filename = value || null;
  if (filename === null) {
    return null;
  }

  if (filename === LEGACY_DEFAULT_AUDIO && audioExists(PREFERRED_DEFAULT_AUDIO)) {
    return PREFERRED_DEFAULT_AUDIO;
  }

  return audioExists(filename) ? filename : getPreferredAudio();
}

function shouldPersistAudioSetting(savedValue, normalizedValue) {
  if (savedValue === undefined || (savedValue || null) === normalizedValue) {
    return false;
  }
  return savedValue === LEGACY_DEFAULT_AUDIO || Boolean(savedValue);
}

function setSelectedAudio(kind, value, { persist = false } = {}) {
  const state = audioSettings[kind];
  state.selected = value || null;
  state.select.value = state.selected || '';

  if (persist) {
    app.ui.settings.setSettingValue(state.id, state.selected || '');
  }
}

function renderAudioSelect(kind) {
  const state = audioSettings[kind];
  const options = audioFiles.map((filename) =>
    $el('option', {
      value: filename,
      textContent: filename,
    })
  );

  options.push(
    $el('option', {
      value: '',
      textContent: 'None',
    })
  );

  state.select.replaceChildren(...options);
  state.select.value = state.selected || '';
}

function renderAudioSelects() {
  renderAudioSelect('success');
  renderAudioSelect('fail');
}

function applySavedAudio(kind, savedValue) {
  const normalizedValue = normalizeAudio(savedValue);
  setSelectedAudio(kind, normalizedValue);
  return normalizedValue;
}

function migrateAudioSetting(kind, savedValue, normalizedValue) {
  if (shouldPersistAudioSetting(savedValue, normalizedValue)) {
    app.ui.settings.setSettingValue(audioSettings[kind].id, normalizedValue || '');
  }
}

function addAudioSetting(kind, name, tooltip, defaultValue) {
  const state = audioSettings[kind];
  app.ui.settings.addSetting({
    id: state.id,
    name,
    tooltip,
    defaultValue,
    type: () => state.select,
    onChange(value) {
      setSelectedAudio(kind, normalizeAudio(value));
    },
  });
}

async function reloadAudioFiles() {
  audioFiles = await get_video_files();
  audioSettings.success.selected = normalizeAudio(audioSettings.success.selected);
  audioSettings.fail.selected = normalizeAudio(audioSettings.fail.selected);
  renderAudioSelects();
}

function isSupportedAudioFile(file) {
  return file && AUDIO_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
}

async function uploadSelectedFile() {
  const file = fileInput.files[0];
  if (!isSupportedAudioFile(file)) {
    fileInput.value = '';
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await api.fetchApi('/pc_upload_video', {
      method: 'POST',
      body: formData,
    });
    const result = await response.json();
    if (!result.success) {
      console.error('Upload failed:', result.error);
      return;
    }

    await reloadAudioFiles();
  } catch (err) {
    console.error('Error uploading file:', err);
  } finally {
    fileInput.value = '';
  }
}

function getWorkflowAudio(status) {
  if (status === 'error') {
    return failTip ? audioSettings.fail.selected : null;
  }
  return audioSettings.success.selected;
}

const fileInput = $el('input', {
  type: 'file',
  accept: AUDIO_EXTENSIONS.join(','),
  style: { display: 'none' },
  parent: document.body,
  onchange: uploadSelectedFile,
});

app.registerExtension({
  name: `${ID_PREFIX}.menu`,
  async init() {
    try {
      audioFiles = await get_video_files();

      const defaultAudio = getPreferredAudio() || '';

      setSelectedAudio('success', defaultAudio || null);
      setSelectedAudio('fail', defaultAudio || null);
      renderAudioSelects();
      addAudioSetting('success', 'play music name', 'select music name', defaultAudio);
      addAudioSetting('fail', 'fail music name', 'select music name for failed workflows', defaultAudio);

      const savedSuccessAudio = app.ui.settings.getSettingValue?.(audioSettings.success.id);
      const savedFailAudio = app.ui.settings.getSettingValue?.(audioSettings.fail.id);
      const normalizedSuccessAudio = applySavedAudio('success', savedSuccessAudio);
      const normalizedFailAudio = applySavedAudio('fail', savedFailAudio);

      renderAudioSelects();
      migrateAudioSetting('success', savedSuccessAudio, normalizedSuccessAudio);
      migrateAudioSetting('fail', savedFailAudio, normalizedFailAudio);

      app.ui.settings.addSetting({
        id: `${MUSIC_SETTING_PREFIX}.play`,
        name: 'play music select',
        type: () =>
          $el('button', {
            textContent: 'play',
            onclick: () => fetchAndPlayAudioSingle(audioSettings.success.selected, volume / 100),
          }),
      });
    } catch (e) {
      console.error('get_video_files error', e);
    }

    api.addEventListener('pc.play_ding_dong_audio', ({ detail }) => {
      if (!open) {
        return;
      }

      const filename = getWorkflowAudio(detail.status);
      if (filename) {
        fetchAndPlayAudioSingle(filename, volume / 100);
      }
    });

    api.addEventListener('pc.play_ding_dong_mui', ({ detail }) => {
      fetchAndPlayAudio(detail.music, detail.volume / 100);
    });

    api.addEventListener('pc.play_ding_dong_text', ({ detail }) => {
      play_ding_dong_text(detail.text, detail.pitch, detail.rate, detail.volume);
    });

    app.ui.settings.addSetting({
      id: `${MUSIC_SETTING_PREFIX}.volume`,
      name: 'Volume',
      type: 'slider',
      attrs: {
        min: 0,
        max: 100,
        step: 1,
      },
      tooltip: 'set ding dong volume',
      defaultValue: 100,
      onChange(v) {
        volume = v;
      },
    });

    app.ui.settings.addSetting({
      id: `${MUSIC_SETTING_PREFIX}.open`,
      name: 'open',
      type: 'boolean',
      defaultValue: true,
      onChange(v) {
        open = v;
      },
    });

    app.ui.settings.addSetting({
      id: `${MUSIC_SETTING_PREFIX}.play_type`,
      name: 'play type',
      tooltip: 'play after all workflows finish or after each single workflow finishes',
      type: 'combo',
      defaultValue: 'all',
      options: [
        { value: 'all', text: 'all' },
        { value: 'one', text: 'one' },
      ],
      onChange(v) {
        set_play_type(v);
      },
    });

    app.ui.settings.addSetting({
      id: `${MUSIC_SETTING_PREFIX}.upload`,
      name: 'upload file',
      type: () =>
        $el('button', {
          textContent: 'upload',
          onclick: () => fileInput.click(),
        }),
    });

    app.ui.settings.addSetting({
      id: `${MUSIC_SETTING_PREFIX}.fail_tip`,
      name: 'fail tip',
      tooltip: 'workflow fail tip',
      type: 'boolean',
      defaultValue: false,
      onChange(v) {
        failTip = v;
      },
    });
  },
});
