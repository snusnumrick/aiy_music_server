let musicData = [];
let currentTrackIndex = -1;
let filteredTracks = [];
const POLLING_INTERVAL = 3000;
let pollingTimer = null;
let currentFontSize = 'medium';
let deleteTrackIndex = null;

const elements = {
    musicList: document.getElementById('music-list'),
    loading: document.getElementById('loading'),
    errorMessage: document.getElementById('error-message'),
    status: document.getElementById('status'),
    fileCount: document.getElementById('file-count'),
//    refreshBtn: document.getElementById('refresh-btn'),
//    searchInput: document.getElementById('search-input'),
    audioPlayer: document.getElementById('audio-player'),
    currentTitle: document.getElementById('current-title'),
    currentArtist: document.getElementById('current-artist'),
    deleteModal: document.getElementById('delete-modal'),
    deleteModalText: document.getElementById('delete-modal-text'),
    cancelDelete: document.getElementById('cancel-delete'),
    confirmDelete: document.getElementById('confirm-delete')
};

async function fetchMusic() {
    try {
        const response = await fetch('/api/music');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        musicData = await response.json();
        filteredTracks = musicData;
        updateUI();
        elements.status.textContent = 'Ready';
        elements.fileCount.textContent = `${musicData.length} file${musicData.length !== 1 ? 's' : ''}`;
        elements.errorMessage.style.display = 'none';
    } catch (error) {
        console.error('Error fetching music:', error);
        elements.status.textContent = 'Error';
        elements.errorMessage.textContent = `Failed to load music: ${error.message}`;
        elements.errorMessage.style.display = 'block';
    }
}

function updateUI() {
    if (elements.loading.style.display !== 'none') {
        elements.loading.style.display = 'none';
    }

//    const searchTerm = elements.searchInput.value.toLowerCase().trim();

    if (searchTerm) {
        filteredTracks = musicData.filter(track =>
            track.title.toLowerCase().includes(searchTerm) ||
            track.artist.toLowerCase().includes(searchTerm) ||
            track.filename.toLowerCase().includes(searchTerm)
        );
    } else {
        filteredTracks = musicData;
    }

    renderTrackList();
}

function renderTrackList() {
    if (filteredTracks.length === 0) {
        elements.musicList.innerHTML = `
            <div class="track-item">
                <div class="track-title">No tracks found</div>
                <div class="track-artist">
                    ${musicData.length === 0 ? 'Add MP3 files to the music folder' : 'Try a different search'}
                </div>
            </div>
        `;
        return;
    }

    elements.musicList.innerHTML = filteredTracks.map((track, index) => {
        const isPlaying = musicData[currentTrackIndex]?.filename === track.filename;
        const lyricsPreview = track.lyrics ? track.lyrics.substring(0, 100) + '...' : 'No lyrics available';
        const actualIndex = musicData.indexOf(track);

        return `
            <div class="track-item ${isPlaying ? 'playing' : ''}" data-index="${actualIndex}">
                <div class="track-title">${escapeHtml(track.title)}</div>
                <div class="track-artist">${escapeHtml(track.artist)}</div>
                ${track.lyrics ? `<div class="track-lyrics-preview">${escapeHtml(lyricsPreview)}</div>` : ''}
                <div class="track-meta">
                    <span>${formatDuration(track.duration)}</span>
                    <span>${formatDate(track.created)}</span>
                </div>
                <div class="track-actions">
                    <button class="action-btn" onclick="playTrack(${actualIndex})" title="${isPlaying ? 'Pause' : 'Play'}">
                        ${isPlaying ? '<i data-lucide="pause" class="w-7 h-7"></i>' : '<i data-lucide="play" class="w-7 h-7"></i>'}
                    </button>
                    ${track.lyrics ? `<button class="action-btn fullscreen-btn" onclick="showFullscreenLyrics(${actualIndex})" title="Fullscreen Lyrics"><i data-lucide="maximize" class="w-7 h-7"></i></button>` : ''}
                    <button class="action-btn delete-btn" onclick="confirmDeleteTrack(${actualIndex})" title="Delete">
                        <i data-lucide="trash-2" class="w-7 h-7"></i>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    // Initialize Lucide icons for the new elements
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
}

function playTrack(index) {
    if (index < 0 || index >= musicData.length) return;

    const track = musicData[index];

    if (currentTrackIndex === index && !elements.audioPlayer.paused) {
        elements.audioPlayer.pause();
        elements.status.textContent = 'Paused';
        updateUI();
        return;
    }

    currentTrackIndex = index;
    elements.audioPlayer.src = `/music/${encodeURIComponent(track.filename)}`;
    elements.audioPlayer.play().catch(error => {
        console.error('Error playing track:', error);
        showError(`Failed to play track: ${error.message}`);
    });

    elements.currentTitle.textContent = track.title;
    elements.currentArtist.textContent = track.artist;
    elements.status.textContent = 'Playing';

    updateUI();

    elements.audioPlayer.onended = () => {
        playNextTrack();
    };
}

function playNextTrack() {
    if (currentTrackIndex < musicData.length - 1) {
        playTrack(currentTrackIndex + 1);
    } else {
        elements.status.textContent = 'Playlist ended';
        currentTrackIndex = -1;
        updateUI();
    }
}

function showFullscreenLyrics(index) {
    if (index < 0 || index >= musicData.length) return;

    const track = musicData[index];
    document.getElementById('fullscreen-title').textContent = track.title;
    document.getElementById('fullscreen-artist').textContent = track.artist;
    document.getElementById('fullscreen-lyrics-content').textContent = track.lyrics || 'No lyrics available';
    document.getElementById('fullscreen-lyrics').classList.remove('hidden');

    currentFontSize = 'medium';
    updateFontSize();
}

function hideFullscreenLyrics() {
    document.getElementById('fullscreen-lyrics').classList.add('hidden');
}

function updateFontSize() {
    const content = document.getElementById('fullscreen-lyrics-content');
    content.classList.remove('font-small', 'font-medium', 'font-large');
    content.classList.add(`font-${currentFontSize}`);
}

function confirmDeleteTrack(index) {
    if (index < 0 || index >= musicData.length) return;

    deleteTrackIndex = index;
    const track = musicData[index];
    elements.deleteModalText.textContent = `Are you sure you want to delete "${track.title}" by ${track.artist}?`;
    elements.deleteModal.classList.remove('hidden');
    elements.deleteModal.classList.add('flex');
}

async function deleteTrack() {
    if (deleteTrackIndex === null) return;

    const track = musicData[deleteTrackIndex];

    try {
        const response = await fetch(`/api/delete/${encodeURIComponent(track.filename)}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            elements.status.textContent = 'Track deleted';
            await fetchMusic();
        } else {
            throw new Error(result.message || 'Delete failed');
        }
    } catch (error) {
        console.error('Error deleting track:', error);
        showError(`Failed to delete track: ${error.message}`);
    }

    deleteTrackIndex = null;
    elements.deleteModal.classList.add('hidden');
    elements.deleteModal.classList.remove('flex');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDuration(seconds) {
    if (!seconds || seconds === 0) return '--:--';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

function formatDate(dateString) {
    if (!dateString) return '';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
}

function showError(message) {
    elements.errorMessage.textContent = message;
    elements.errorMessage.style.display = 'block';
    setTimeout(() => {
        elements.errorMessage.style.display = 'none';
    }, 5000);
}

async function refreshMetadata() {
    try {
        elements.status.textContent = 'Refreshing...';
        const response = await fetch('/api/refresh', { method: 'POST' });
        if (response.ok) {
            await fetchMusic();
            elements.status.textContent = 'Updated';
        } else {
            throw new Error('Refresh failed');
        }
    } catch (error) {
        console.error('Error refreshing:', error);
        showError('Failed to refresh: ' + error.message);
    }
}

function startPolling() {
    pollingTimer = setInterval(() => {
        fetchMusic();
    }, POLLING_INTERVAL);
}

function stopPolling() {
    if (pollingTimer) {
        clearInterval(pollingTimer);
        pollingTimer = null;
    }
}

//elements.refreshBtn.addEventListener('click', refreshMetadata);

//elements.searchInput.addEventListener('input', () => {
//    updateUI();
//});

elements.audioPlayer.addEventListener('play', () => {
    elements.status.textContent = 'Playing';
});

elements.audioPlayer.addEventListener('pause', () => {
    elements.status.textContent = 'Paused';
});

elements.audioPlayer.addEventListener('error', (e) => {
    console.error('Audio error:', e);
    showError('Audio playback error');
});

elements.cancelDelete.addEventListener('click', () => {
    deleteTrackIndex = null;
    elements.deleteModal.classList.add('hidden');
    elements.deleteModal.classList.remove('flex');
});

elements.confirmDelete.addEventListener('click', deleteTrack);

elements.deleteModal.addEventListener('click', (e) => {
    if (e.target === elements.deleteModal) {
        deleteTrackIndex = null;
        elements.deleteModal.classList.add('hidden');
        elements.deleteModal.classList.remove('flex');
    }
});

document.getElementById('fullscreen-close-btn').addEventListener('click', hideFullscreenLyrics);
document.getElementById('exit-fullscreen-btn').addEventListener('click', hideFullscreenLyrics);
document.getElementById('fullscreen-font-smaller').addEventListener('click', () => {
    if (currentFontSize === 'large') {
        currentFontSize = 'medium';
    } else if (currentFontSize === 'medium') {
        currentFontSize = 'small';
    }
    updateFontSize();
});
document.getElementById('fullscreen-font-larger').addEventListener('click', () => {
    if (currentFontSize === 'small') {
        currentFontSize = 'medium';
    } else if (currentFontSize === 'medium') {
        currentFontSize = 'large';
    }
    updateFontSize();
});

document.getElementById('fullscreen-lyrics').addEventListener('click', (e) => {
    if (e.target.id === 'fullscreen-lyrics') {
        hideFullscreenLyrics();
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (!elements.deleteModal.classList.contains('hidden')) {
            deleteTrackIndex = null;
            elements.deleteModal.classList.add('hidden');
            elements.deleteModal.classList.remove('flex');
        } else if (document.getElementById('fullscreen-lyrics').style.display === 'flex' ||
                   !document.getElementById('fullscreen-lyrics').classList.contains('hidden')) {
            hideFullscreenLyrics();
        }
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    fetchMusic();
    startPolling();
});

window.addEventListener('beforeunload', () => {
    stopPolling();
});
