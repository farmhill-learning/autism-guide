/**
 * Search functionality for Autism Bharat website
 */

class Search {
    constructor() {
        this.index = null;
        this.searchInput = null;
        this.resultsContainer = null;
        this.isLoading = false;
        this.currentResults = [];
        this.selectedIndex = -1;
        this.init();
    }

    async init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setup());
        } else {
            this.setup();
        }
    }

    async setup() {
        // Find search elements first
        this.searchInput = document.getElementById('search-input');
        this.resultsContainer = document.getElementById('search-results');

        if (!this.searchInput || !this.resultsContainer) {
            console.warn('Search elements not found');
            return;
        }

        // Load search index
        try {
            const response = await fetch('/search.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            this.index = await response.json();
            console.log('Search index loaded:', this.index.pages?.length || 0, 'pages');
        } catch (error) {
            console.error('Failed to load search index:', error);
            this.showMessage('Search temporarily unavailable');
            return;
        }

        // Initialize Lucide icons for search icon (in case it wasn't initialized yet)
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }

        // Setup event listeners
        this.searchInput.addEventListener('input', (e) => this.handleInput(e));
        this.searchInput.addEventListener('keydown', (e) => this.handleKeydown(e));
        
        // Close results when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container')) {
                this.hideResults();
            }
        });

        // Handle escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.resultsContainer.classList.contains('show')) {
                this.hideResults();
                this.searchInput.blur();
            }
        });
    }

    handleInput(e) {
        const query = e.target.value.trim();
        
        if (query.length === 0) {
            this.hideResults();
            return;
        }

        if (query.length < 2) {
            this.showMessage('Type at least 2 characters to search');
            return;
        }

        this.search(query);
    }

    handleKeydown(e) {
        if (!this.resultsContainer.classList.contains('show')) {
            return;
        }

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                this.selectedIndex = Math.min(
                    this.selectedIndex + 1,
                    this.currentResults.length - 1
                );
                this.highlightResult();
                break;
            case 'ArrowUp':
                e.preventDefault();
                this.selectedIndex = Math.max(this.selectedIndex - 1, -1);
                this.highlightResult();
                break;
            case 'Enter':
                e.preventDefault();
                if (this.selectedIndex >= 0 && this.currentResults[this.selectedIndex]) {
                    const result = this.currentResults[this.selectedIndex];
                    window.location.href = result.url;
                }
                break;
        }
    }

    highlightResult() {
        const items = this.resultsContainer.querySelectorAll('.search-result-item');
        items.forEach((item, index) => {
            if (index === this.selectedIndex) {
                item.classList.add('selected');
                item.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
            } else {
                item.classList.remove('selected');
            }
        });
    }

    search(query) {
        if (!this.index || !this.index.pages) {
            return;
        }

        const queryLower = query.toLowerCase();
        const queryWords = queryLower.split(/\s+/).filter(w => w.length > 0);

        // Score and rank results
        const results = this.index.pages.map(page => {
            const score = this.calculateScore(page, queryLower, queryWords);
            return { ...page, score };
        })
        .filter(result => result.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 15); // Limit to top 15 results

        this.currentResults = results;
        this.selectedIndex = -1;
        this.displayResults(results, query);
    }

    calculateScore(page, queryLower, queryWords) {
        let score = 0;
        const titleLower = page.title.toLowerCase();
        const descriptionLower = (page.description || '').toLowerCase();
        const contentLower = (page.content || '').toLowerCase();
        const headingsLower = (page.headings || []).join(' ').toLowerCase();

        // Exact title match gets highest score
        if (titleLower === queryLower) {
            score += 1000;
        } else if (titleLower.includes(queryLower)) {
            score += 500;
        }

        // Title word matches
        queryWords.forEach(word => {
            if (titleLower.includes(word)) {
                score += 100;
            }
        });

        // Description matches
        queryWords.forEach(word => {
            if (descriptionLower.includes(word)) {
                score += 50;
            }
        });

        // Heading matches
        queryWords.forEach(word => {
            if (headingsLower.includes(word)) {
                score += 30;
            }
        });

        // Content matches (lower weight)
        queryWords.forEach(word => {
            const matches = (contentLower.match(new RegExp(word, 'g')) || []).length;
            score += matches * 5;
        });

        return score;
    }

    displayResults(results, query) {
        if (results.length === 0) {
            this.showMessage('No results found');
            return;
        }

        const queryWords = query.toLowerCase().split(/\s+/).filter(w => w.length > 0);
        const html = results.map(result => {
            const highlightedTitle = this.highlightText(result.title, queryWords);
            const highlightedDescription = result.description 
                ? this.highlightText(result.description.substring(0, 150), queryWords)
                : '';
            const highlightedResource = this.highlightText(result.resource, queryWords);

            return `
                <a href="${result.url}" class="search-result-item">
                    <div class="search-result-title">${highlightedTitle}</div>
                    <div class="search-result-resource">${highlightedResource}</div>
                    ${highlightedDescription ? `<div class="search-result-description">${highlightedDescription}...</div>` : ''}
                </a>
            `;
        }).join('');

        this.resultsContainer.innerHTML = html;
        this.showResults();
    }

    highlightText(text, queryWords) {
        let highlighted = text;
        queryWords.forEach(word => {
            const regex = new RegExp(`(${this.escapeRegex(word)})`, 'gi');
            highlighted = highlighted.replace(regex, '<mark>$1</mark>');
        });
        return highlighted;
    }

    escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    showMessage(message) {
        this.resultsContainer.innerHTML = `<div class="search-message">${message}</div>`;
        this.showResults();
    }

    showResults() {
        // Always show if there's content, even if empty (for messages)
        this.resultsContainer.classList.add('show');
    }

    hideResults() {
        this.resultsContainer.classList.remove('show');
        this.selectedIndex = -1;
    }
}

// Initialize search when script loads
const search = new Search();
