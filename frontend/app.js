const form = document.getElementById('upload-form');
const fileInput = document.getElementById('pdf-file');
const predictionEl = document.getElementById('prediction');
const resultSection = document.getElementById('result-section');
const loader = document.getElementById('loader');
const uploadBtn = document.getElementById('upload-btn');
const downloadBtn = document.getElementById('download-btn');

// If your backend runs on a different port, change this:
const API_URL = 'http://127.0.0.1:8000/predict-question-paper/';

form.addEventListener('submit', async function (e) {
  e.preventDefault();
  resultSection.style.display = 'none';
  loader.style.display = 'block';
  uploadBtn.disabled = true;
  predictionEl.textContent = '';
  downloadBtn.style.display = 'none';

  // Validate file input
  if (!fileInput.files.length) {
    alert('Please select a PDF file.');
    loader.style.display = 'none';
    uploadBtn.disabled = false;
    return;
  }
  const file = fileInput.files[0];

  // Prepare form data
  const formData = new FormData();
  formData.append('file', file);

  try {
    // Make POST request to FastAPI backend
    const response = await fetch(API_URL, {
      method: 'POST',
      body: formData,
    });

    loader.style.display = 'none';
    uploadBtn.disabled = false;

    if (!response.ok) {
      const data = await response.json();
      predictionEl.textContent =
        'Error: ' + (data.detail || response.statusText);
      resultSection.style.display = 'block';
      return;
    }

    const text = await response.text();
    predictionEl.textContent = text;
    resultSection.style.display = 'block';
    downloadBtn.style.display = 'inline';
  } catch (err) {
    loader.style.display = 'none';
    uploadBtn.disabled = false;
    predictionEl.textContent = 'Unexpected error: ' + err;
    resultSection.style.display = 'block';
  }
});

// Download as .txt
downloadBtn.addEventListener('click', function () {
  const blob = new Blob([predictionEl.textContent], {
    type: 'text/plain;charset=utf-8',
  });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.download = 'predicted_question_paper.txt';
  link.href = url;
  link.click();
  URL.revokeObjectURL(url);
});

const showLatestBtn = document.getElementById('show-latest-btn');

showLatestBtn.addEventListener('click', async function () {
  predictionEl.textContent = '';
  resultSection.style.display = 'none';
  loader.style.display = 'block';

  try {
    const response = await fetch('http://localhost:8000/latest-prediction/');
    loader.style.display = 'none';

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      predictionEl.textContent =
        'Error: ' + (data.error || response.statusText);
      resultSection.style.display = 'block';
      return;
    }

    const data = await response.json();
    // Format output—if "predicted_question_paper" exists, show only that. Otherwise, show all.
    if (data.predicted_question_paper) {
      predictionEl.textContent = data.predicted_question_paper;
    } else {
      predictionEl.textContent = JSON.stringify(data, null, 2);
    }
    resultSection.style.display = 'block';
    downloadBtn.style.display = 'inline'; // Optional: allow download
  } catch (err) {
    loader.style.display = 'none';
    predictionEl.textContent = 'Unexpected error: ' + err;
    resultSection.style.display = 'block';
  }
});
