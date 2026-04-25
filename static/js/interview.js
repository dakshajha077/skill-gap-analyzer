const answerText = document.getElementById('answerText');
const micBtn = document.getElementById('micBtn');
const micStatus = document.getElementById('micStatus');
const submitBtn = document.getElementById('submitBtn');
const loadingOverlay = document.getElementById('loadingOverlay');

let mediaRecorder = null,
  audioChunks = [],
  isRecording = false;
let timerInterval = null;
const TIMER_SECONDS = 120;

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function postJsonWithRetry(url, payload, { maxAttempts = 2, retryDelayMs = 900 } = {}) {
  let lastError = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const contentType = (res.headers.get('content-type') || '').toLowerCase();
      let data = null;

      if (contentType.includes('application/json')) {
        data = await res.json();
      } else {
        const text = await res.text().catch(() => '');
        data = { error: `Server error (${res.status}). Please try again.` };
        if (res.ok) data.error = 'Unexpected server response. Please refresh and try again.';
        data._raw = text ? text.slice(0, 180) : undefined;
      }

      if (!res.ok) {
        const isRetryable = res.status >= 500 && res.status <= 599;
        if (isRetryable && attempt < maxAttempts) {
          await sleep(retryDelayMs);
          continue;
        }
        return { ok: false, status: res.status, data };
      }

      return { ok: true, status: res.status, data };
    } catch (err) {
      lastError = err;
      if (attempt < maxAttempts) {
        await sleep(retryDelayMs);
        continue;
      }
    }
  }

  throw lastError || new Error('Request failed');
}

function startTimer() {
  let remaining = TIMER_SECONDS;
  const timerEl = document.getElementById('questionTimer');
  const timerBar = document.getElementById('timerBar');

  timerInterval = setInterval(() => {
    remaining--;
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    timerEl.textContent = mins + ':' + (secs < 10 ? '0' : '') + secs;
    const pct = (remaining / TIMER_SECONDS) * 100;
    timerBar.style.width = pct + '%';
    if (remaining <= 30) {
      timerBar.style.background = '#ef4444';
      timerEl.style.color = '#ef4444';
    } else if (remaining <= 60) {
      timerBar.style.background = '#f59e0b';
      timerEl.style.color = '#f59e0b';
    }
    if (remaining <= 0) {
      clearInterval(timerInterval);
      timerEl.textContent = '0:00';
      answerText.disabled = true;
      submitBtn.disabled = false;
      showAlert('Time is up! Your answer has been locked and submitted automatically.', 'warning');
      setTimeout(() => autoSubmit(), 1200);
    }
  }, 1000);
}

async function autoSubmit() {
  const answer = answerText.value.trim() || '[No answer provided — time expired]';
  loadingOverlay.classList.remove('d-none');
  loadingOverlay.style.display = 'flex';
  try {
    const { ok, data } = await postJsonWithRetry('/submit_answer', { answer }, { maxAttempts: 2 });
    if (!ok || data?.error) throw new Error(data?.error || 'Server error');
    if (data.is_last) window.location.href = '/results';
    else window.location.href = '/interview';
  } catch {
    window.location.href = '/interview';
  }
}

answerText.addEventListener('paste', e => {
  e.preventDefault();
  const popup = document.getElementById('pastePopup');
  popup.classList.remove('d-none');
  setTimeout(() => popup.classList.add('d-none'), 2800);
});
answerText.addEventListener('copy', e => e.preventDefault());
answerText.addEventListener('cut', e => e.preventDefault());
answerText.addEventListener('contextmenu', e => e.preventDefault());

micBtn.addEventListener('click', async () => {
  if (isRecording) {
    mediaRecorder.stop();
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    isRecording = true;
    micBtn.classList.add('recording');
    micBtn.innerHTML = '<i class="bi bi-stop-fill me-1"></i> Stop';
    micStatus.textContent = '🔴 Recording...';
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
      isRecording = false;
      micBtn.classList.remove('recording');
      micBtn.innerHTML = '<i class="bi bi-mic-fill me-1"></i> Record Voice';
      micStatus.textContent = '⏳ Processing...';
      stream.getTracks().forEach(t => t.stop());
      const blob = new Blob(audioChunks, { type: 'audio/webm' });
      const b64 = await blobToBase64(blob);
      try {
        const { ok, data } = await postJsonWithRetry('/transcribe', { audio: b64 }, { maxAttempts: 2 });
        if (ok && data?.text) {
          answerText.value = data.text;
          micStatus.textContent = '✅ Done';
        } else {
          micStatus.textContent = '⚠️ ' + (data?.error || 'Could not transcribe');
        }
      } catch {
        micStatus.textContent = '⚠️ Server error';
      }
    };
    mediaRecorder.start();
  } catch {
    micStatus.textContent = '⚠️ Microphone access denied';
  }
});

submitBtn.addEventListener('click', async () => {
  const answer = answerText.value.trim();
  if (!answer) {
    showAlert('Please type or record your answer first.', 'warning');
    return;
  }
  if (answer.split(' ').length < 3) {
    showAlert('Please provide a more detailed answer.', 'warning');
    return;
  }

  clearInterval(timerInterval);
  submitBtn.disabled = true;
  loadingOverlay.classList.remove('d-none');
  loadingOverlay.style.display = 'flex';
  try {
    const { ok, data } = await postJsonWithRetry('/submit_answer', { answer }, { maxAttempts: 2 });
    if (!ok) throw new Error(data?.error || 'Server error');

    if (data?.error) {
      showAlert(data.error, 'danger');
      loadingOverlay.classList.add('d-none');
      submitBtn.disabled = false;
      return;
    }

    if (data.is_last) window.location.href = '/results';
    else window.location.href = '/interview';
  } catch (err) {
    showAlert(err?.message || 'Server error. Please try again.', 'danger');
    loadingOverlay.classList.add('d-none');
    submitBtn.disabled = false;
  }
});

function blobToBase64(blob) {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result.split(',')[1]);
    r.onerror = rej;
    r.readAsDataURL(blob);
  });
}

function showAlert(msg, type) {
  const div = document.createElement('div');
  div.className = `alert alert-${type === 'warning' ? 'warning' : 'danger'} mb-3`;
  div.style.cssText = 'border-radius:10px;font-size:0.9rem;';
  div.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-2"></i>${msg}`;
  document.querySelector('.container').prepend(div);
  setTimeout(() => {
    div.style.opacity = '0';
    setTimeout(() => div.remove(), 400);
  }, 4000);
}

document.addEventListener('DOMContentLoaded', () => {
  startTimer();
  // Warm up the ML stack while the user reads the question.
  fetch('/api/warmup', { method: 'POST' }).catch(() => {});
});
