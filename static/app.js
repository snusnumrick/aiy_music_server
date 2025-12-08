let currentTrackIndex = -1;
let filteredTracks = [];
let currentTab = 'music';
let picturesData = [];
let documentsData = [];
let currentImageIndex = -1;
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
    confirmDelete: document.getElementById('confirm-delete'),
    
    // Views and Tabs
    musicView: document.getElementById('music-view'),
    picturesView: document.getElementById('pictures-view'),
    documentsView: document.getElementById('documents-view'),
    picturesGrid: document.getElementById('pictures-grid'),
    documentsList: document.getElementById('documents-list'),
    tabs: document.querySelectorAll('.tab-btn'),
    
    // Image Viewer
    fullscreenImage: document.getElementById('fullscreen-image'),
    fullscreenImgDisplay: document.getElementById('fullscreen-img-display'),
    imageTitle: document.getElementById('image-title'),
    imageCaption: document.getElementById('image-caption'),
    imageMeta: document.getElementById('image-meta'),
    imageCloseBtn: document.getElementById('image-close-btn'),
    prevImageBtn: document.getElementById('prev-image-btn'),
    nextImageBtn: document.getElementById('next-image-btn')
};


async function fetchAllData() {
    await Promise.all([fetchMusic(), fetchPictures(), fetchDocuments()]);
    elements.status.textContent = 'Ready';
    updateFileCount();
}
    
async function fetchMusic() {
    try {
        const response = await fetch('/api/music');
        if (response.ok) {
            musicData = await response.json();
            filteredTracks = musicData;
            if (currentTab === 'music') updateUI();
        }
    } catch (error) {
        console.error('Error fetching music:', error);
    }
}

async function fetchPictures() {
    try {
        const response = await fetch('/api/pictures');
        if (response.ok) {
            picturesData = await response.json();
            if (currentTab === 'pictures') updateUI();
        }
    } catch (error) {
        console.error('Error fetching pictures:', error);
    }
}

async function fetchDocuments() {
    try {
        const response = await fetch('/api/documents');
        if (response.ok) {
            documentsData = await response.json();
            if (currentTab === 'documents') updateUI();
        }
    } catch (error) {
        console.error('Error fetching documents:', error);
    }
}

function updateFileCount() {
    const total = musicData.length + picturesData.length + documentsData.length;
    elements.fileCount.textContent = `${total} files`;
}

function updateUI() {
    if (elements.loading.style.display !== 'none') {
        elements.loading.style.display = 'none';
    }

    if (currentTab === 'music') {
        renderTrackList();
    } else if (currentTab === 'pictures') {
        renderPicturesGrid();
    } else if (currentTab === 'documents') {
        renderDocumentsList();
    }
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

function renderPicturesGrid() {
    if (picturesData.length === 0) {
        elements.picturesGrid.innerHTML = `
            <div class="col-span-full py-10 text-center text-gray-500 text-lg">
                No pictures found
            </div>
        `;
        return;
    }

    elements.picturesGrid.innerHTML = picturesData.map((pic, index) => `
        <div class="bg-white/90 dark:bg-gray-800/90 rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all cursor-pointer aspect-square relative group" onclick="showFullscreenImage(${index})">
            <img src="${pic.thumbnail_url}" alt="${escapeHtml(pic.title)}" loading="lazy" class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-110">
            <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end h-1/2">
                <div class="text-white text-sm font-semibold truncate">${escapeHtml(pic.title)}</div>
            </div>
        </div>
    `).join('');
}

function renderDocumentsList() {
    if (documentsData.length === 0) {
        elements.documentsList.innerHTML = `
            <div class="py-10 text-center text-gray-500 text-lg">
                No documents found
            </div>
        `;
        return;
    }

    elements.documentsList.innerHTML = documentsData.map((doc) => `
        <a href="${doc.url}" target="_blank" class="block bg-white/90 dark:bg-gray-800/90 rounded-xl p-4 mb-3 shadow-sm hover:shadow-md transition-all border border-transparent hover:border-primary/30 group">
            <div class="flex items-center gap-3">
                <div class="bg-primary/10 p-3 rounded-lg text-primary group-hover:bg-primary group-hover:text-white transition-colors">
                    <i data-lucide="file-text" class="w-6 h-6"></i>
                </div>
                <div class="flex-1 min-w-0">
                    <div class="font-bold text-gray-800 dark:text-gray-200 truncate">${escapeHtml(doc.filename)}</div>
                    <div class="flex gap-3 text-xs text-gray-500 dark:text-gray-400 mt-1">
                        <span>${formatFileSize(doc.size)}</span>
                        <span>${formatDate(doc.modified)}</span>
                    </div>
                </div>
                <div class="text-gray-400">
                    <i data-lucide="download" class="w-5 h-5"></i>
                </div>
            </div>
        </a>
    `).join('');

    if (typeof lucide !== 'undefined') lucide.createIcons();
}

// Image Viewer Logic
function showFullscreenImage(index) {
    if (index < 0 || index >= picturesData.length) return;
    
    currentImageIndex = index;
    const pic = picturesData[index];
    
    elements.fullscreenImgDisplay.src = pic.url;
    elements.imageTitle.textContent = pic.title;
    elements.imageCaption.textContent = pic.caption || '';
    
    // Meta info - parse various date formats
    let dateStr = 'Unknown date';
    if (pic.date_taken) {
        try {
            const dt = pic.date_taken;
            let d;
            
            // IPTC format: "20241215" (YYYYMMDD)
            if (/^\d{8}$/.test(dt)) {
                d = new Date(dt.slice(0,4) + '-' + dt.slice(4,6) + '-' + dt.slice(6,8));
            }
            // EXIF format: "2024:01:15 14:30:00"
            else if (dt.includes(':')) {
                const normalized = dt.replace(/^(\d{4}):(\d{2}):(\d{2})/, '$1-$2-$3').replace(' ', 'T');
                d = new Date(normalized);
            }
            // ISO format or other
            else {
                d = new Date(dt);
            }
            
            if (d && !isNaN(d.getTime())) {
                dateStr = d.toLocaleDateString();
            }
        } catch (e) {}
    }
    elements.imageMeta.textContent = `${pic.width}x${pic.height} • ${dateStr}`;


    
    elements.fullscreenImage.classList.remove('hidden');
    elements.fullscreenImage.style.display = 'flex';
    
    // Button states
    elements.prevImageBtn.style.opacity = index === 0 ? '0.3' : '1';
    elements.nextImageBtn.style.opacity = index === picturesData.length - 1 ? '0.3' : '1';
}

function closeFullscreenImage() {
    elements.fullscreenImage.classList.add('hidden');
    elements.fullscreenImage.style.display = 'none';
}

function nextImage() {
    if (currentImageIndex < picturesData.length - 1) {
        showFullscreenImage(currentImageIndex + 1);
    }
}

function prevImage() {
    if (currentImageIndex > 0) {
        showFullscreenImage(currentImageIndex - 1);
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
    document.getElementById('fullscreen-lyrics').style.display = 'flex';

    currentFontSize = 'medium';
    updateFontSize();
}

function hideFullscreenLyrics() {
    document.getElementById('fullscreen-lyrics').classList.add('hidden');
    document.getElementById('fullscreen-lyrics').style.display = 'none';
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

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

async function refreshMetadata() {
    try {
        elements.status.textContent = 'Refreshing...';
        const response = await fetch('/api/refresh', { method: 'POST' });
        if (response.ok) {
            await fetchAllData();
            elements.status.textContent = 'Updated';
        } else {
            throw new Error('Refresh failed');
        }
    } catch (error) {
        console.error('Error refreshing:', error);
        showError('Failed to refresh: ' + error.message);
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

// Tab Switching
elements.tabs.forEach(tab => {
    tab.addEventListener('click', () => {
        const targetTab = tab.dataset.tab;
        if (currentTab === targetTab) return;
        
        // Update state
        currentTab = targetTab;
        
        // Update tab buttons
        elements.tabs.forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Update views
        elements.musicView.classList.add('hidden');
        elements.picturesView.classList.add('hidden');
        elements.documentsView.classList.add('hidden');
        
        if (currentTab === 'music') elements.musicView.classList.remove('hidden');
        if (currentTab === 'pictures') elements.picturesView.classList.remove('hidden');
        if (currentTab === 'documents') elements.documentsView.classList.remove('hidden');
        
        updateUI();
    });
});

// Image Viewer Events
elements.imageCloseBtn?.addEventListener('click', closeFullscreenImage);
elements.prevImageBtn?.addEventListener('click', (e) => { e.stopPropagation(); prevImage(); });
elements.nextImageBtn?.addEventListener('click', (e) => { e.stopPropagation(); nextImage(); });

// Keyboard nav
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeFullscreenImage();
        // ... existing escape logic ...
    }
    if (!elements.fullscreenImage.classList.contains('hidden')) {
        if (e.key === 'ArrowLeft') prevImage();
        if (e.key === 'ArrowRight') nextImage();
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Lucide icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    fetchAllData();
});
