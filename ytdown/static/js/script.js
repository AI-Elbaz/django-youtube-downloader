class DownloadTracker {
  constructor() {
    this.videoId = window.VIDEO_ID;
    this.statusElement = document.getElementById('status');
    this.progressElement = document.getElementById('progress');
    this.progressPercent = document.getElementById('progressPercent');
    this.progressContainer = document.getElementById('progressContainer');
    this.processing = false;
    this.maxPercentage = 0;
  }

  async startTracking(format = 'mp3') {
    try {
      while (true) {
        const response = await fetch('/dl/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': window.csrfToken
          },
          body: JSON.stringify({
            video_id: this.videoId,
            extension: format
          })
        });

        const data = await response.json();

        if (!response.ok)
          throw new Error(data.error || response.status);

        this.updateUI(data);

        if (data.status === 'SUCCESS')
          break;

        await new Promise(resolve => setTimeout(resolve, 2100));
      }
    } catch (error) {
      this.handleError(error);
    }
  }

  updateUI(data) {
    let properText = {
      'PENDING': 'Converting',
      'PROGRESS': 'Converting',
      'SUCCESS': 'Completed',
    };

    if (data.progress != 0 && data.progress <= this.maxPercentage)
      this.processing = true;

    this.maxPercentage = data.progress;

    if (this.processing) {
      this.statusElement.textContent = 'Processing';
    } else {
      this.statusElement.textContent = properText[data.status] || data.status.toLowerCase();
    }

    if (['PROGRESS', 'SUCCESS'].includes(data.status)) {
      this.progressElement.style.width = `${data.progress}%`;
      this.progressPercent.textContent = `${Math.round(data.progress)}%`;
    }

    if (data.status === 'SUCCESS') {
      let downloadLinkElement = document.createElement('a');

      downloadLinkElement.href = data.file_path;
      downloadLinkElement.download = "";
      downloadLinkElement.className = "btn";
      downloadLinkElement.textContent = "Download";

      this.progressContainer.appendChild(downloadLinkElement)
    }
  }

  handleError(error) {
    console.error('Error:', error);
    this.statusElement.textContent = error.message;
    this.statusElement.style.color = 'red';
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const downloadMP3Btn = document.getElementById('downloadMP3');
  const downloadMP4Btn = document.getElementById('downloadMP4');
  const videoWrapper = document.querySelector('.video-wrapper');
  const buttonsContainer = document.querySelector('.buttons-container');
  const tracker = new DownloadTracker();

  buttonsContainer.style.height = `${buttonsContainer.offsetHeight}px`;

  const toggleBtns = () => {
    buttonsContainer.addEventListener('transitionend', () => {
      buttonsContainer.innerHTML = '';
    }, { once: true });

    buttonsContainer.style.height = '0px';
    tracker.progressContainer.style.height = "200px";
  }

  videoWrapper.addEventListener('click', () => {
    let iframe = document.createElement('iframe');

    iframe.src = `https://www.youtube.com/embed/${window.VIDEO_ID}?autoplay=1`;
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
    iframe.allowFullscreen = 'true';

    videoWrapper.innerHTML = '';
    videoWrapper.appendChild(iframe);
  }, { once: true });

  downloadMP3Btn.addEventListener('click', (e) => {
    toggleBtns();
    tracker.startTracking('mp3');
  }, { once: true });

  downloadMP4Btn.addEventListener('click', (e) => {
    toggleBtns();
    tracker.startTracking('mp4');
  }, { once: true });
});