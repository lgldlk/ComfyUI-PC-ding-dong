import { api } from '../../scripts/api.js';
import { francMap } from './addfranc.js';

export async function request(url, method, data) {
  let formData = undefined;
  if (method === 'POST') {
    formData = new FormData();
    if (data) {
      for (const [key, value] of Object.entries(data)) {
        formData.append(key, value);
      }
    }
  } else {
    url += '?' + new URLSearchParams(data).toString();
  }

  return api.fetchApi(url, { method, body: formData });
}

let currentAudio = null;
const activeAudios = new Set();

function audioUrl(filename) {
  return api.apiURL(`/pc_get_audio?${new URLSearchParams({ filename }).toString()}`);
}

function stopAudio(audio) {
  if (!audio) {
    return;
  }
  try {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
  } catch (e) {}

  activeAudios.delete(audio);
  if (currentAudio === audio) {
    currentAudio = null;
  }
}

async function createAudio(filename, volume = 1) {
  if (!filename) {
    return null;
  }

  const audio = new Audio(audioUrl(filename));
  audio.volume = Math.max(0, Math.min(1, Number(volume) || 0));

  const cleanup = () => {
    activeAudios.delete(audio);
    if (currentAudio === audio) {
      currentAudio = null;
    }
  };

  audio.addEventListener('ended', cleanup, { once: true });
  audio.addEventListener('error', cleanup, { once: true });
  activeAudios.add(audio);

  return audio;
}

async function playAudio(audio) {
  if (!audio) {
    return;
  }

  try {
    await audio.play();
  } catch (err) {
    stopAudio(audio);
    console.error('Failed to play ding-dong audio:', err);
  }
}

export async function fetchAndPlayAudioSingle(filename, volume = 1) {
  stopAudio(currentAudio);
  currentAudio = await createAudio(filename, volume);
  await playAudio(currentAudio);
}

export async function fetchAndPlayAudio(filename, volume = 1) {
  const audio = await createAudio(filename, volume);
  await playAudio(audio);
}

export function get_video_files() {
  return request('/pc_get_video_files', 'POST')
    .then(async (res) => (await res.json()).video_files)
    .catch((err) => {
      console.error('Error fetching video files:', err);
      return [];
    });
}

export function set_play_type(play_type) {
  return request('/pc_set_play_type', 'POST', { play_type });
}

export function play_ding_dong_text(text, pitch, rate, volume) {
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.pitch = pitch;
  utterance.rate = rate;
  utterance.volume = volume;

  if (window.pcFranc) {
    utterance.lang = francMap[window.pcFranc(text, { minLength: 3 })];
  }
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}
