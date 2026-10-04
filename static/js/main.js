// CampusFind - Core Frontend Interactions

document.addEventListener('DOMContentLoaded', () => {
    // 1. Dark Mode Initialization & Toggle
    initTheme();

    // 2. Image Upload Preview
    initImagePreview();

    // 3. Live Search Autocomplete
    initLiveSearch();

    // 4. Copy to Clipboard Utility
    initCopyButtons();
});

/* Theme Handling */
function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const storedTheme = localStorage.getItem('campusfind_theme');

    if (storedTheme === 'dark' || (!storedTheme && prefersDark)) {
        document.documentElement.classList.add('dark');
    } else {
        document.documentElement.classList.remove('dark');
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const isDark = document.documentElement.classList.toggle('dark');
            localStorage.setItem('campusfind_theme', isDark ? 'dark' : 'light');
        });
    }
}

/* Image Upload Preview */
function initImagePreview() {
    const fileInputs = document.querySelectorAll('input[type="file"][data-preview]');
    fileInputs.forEach(input => {
        const previewTargetId = input.getAttribute('data-preview');
        const previewImg = document.getElementById(previewTargetId);
        const container = input.closest('.image-upload-wrapper');

        if (input && previewImg) {
            input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        previewImg.src = event.target.result;
                        previewImg.classList.remove('hidden');
                        if (container) {
                            const placeholder = container.querySelector('.upload-placeholder');
                            if (placeholder) placeholder.classList.add('hidden');
                        }
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });
}

/* Live Search Autocomplete */
function initLiveSearch() {
    const searchInput = document.getElementById('nav-live-search');
    const dropdown = document.getElementById('nav-search-results');

    if (!searchInput || !dropdown) return;

    let debounceTimer;

    searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        const query = e.target.value.trim();

        if (query.length < 2) {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
            return;
        }

        debounceTimer = setTimeout(() => {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(items => {
                    if (items.length === 0) {
                        dropdown.innerHTML = `
                            <div class="p-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                                No matching campus items found for "${escapeHtml(query)}"
                            </div>
                        `;
                    } else {
                        dropdown.innerHTML = items.map(item => `
                            <a href="/items/${item.id}" class="flex items-center gap-3 p-3 hover:bg-gray-100 dark:hover:bg-gray-800 border-b border-gray-100 dark:border-gray-800 transition">
                                <span class="px-2 py-0.5 text-xs font-semibold rounded ${
                                    item.item_type === 'lost' ? 'bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300' : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
                                }">
                                    ${item.item_type.toUpperCase()}
                                </span>
                                <div class="flex-1 min-w-0">
                                    <p class="text-sm font-medium text-gray-900 dark:text-white truncate">${escapeHtml(item.title)}</p>
                                    <p class="text-xs text-gray-500 dark:text-gray-400 truncate">${escapeHtml(item.category)} &bull; ${escapeHtml(item.location || 'Campus')}</p>
                                </div>
                            </a>
                        `).join('');
                    }
                    dropdown.classList.remove('hidden');
                })
                .catch(() => {
                    dropdown.classList.add('hidden');
                });
        }, 250);
    });

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
            dropdown.classList.add('hidden');
        }
    });
}

/* Copy to Clipboard */
function initCopyButtons() {
    const copyBtns = document.querySelectorAll('[data-copy]');
    copyBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const textToCopy = btn.getAttribute('data-copy');
            if (navigator.clipboard && textToCopy) {
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalText = btn.innerHTML;
                    btn.innerHTML = `<i class="fa-solid fa-check text-emerald-500"></i> Copied!`;
                    setTimeout(() => {
                        btn.innerHTML = originalText;
                    }, 2000);
                });
            }
        });
    });
}

function escapeHtml(string) {
    if (!string) return '';
    return String(string).replace(/[&<>"'`=\/]/g, function (s) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;',
            '/': '&#x2F;',
            '`': '&#x60;',
            '=': '&#x3D;'
        }[s];
    });
}
