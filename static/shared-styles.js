// Shared Tailwind components
document.write(`
<style type="text/tailwindcss">
    @layer components {
        .app-header {
            @apply bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm shadow-lg p-6 md:p-8 rounded-2xl mb-4 md:mb-8;
        }
        .player-container {
            @apply bg-white/95 dark:bg-gray-800/95 backdrop-blur-sm p-3 sm:p-4 md:p-6 shadow-2xl;
        }
        .btn {
            @apply bg-primary hover:bg-primary/90 text-white font-bold py-2 px-4 sm:py-3 sm:px-5 md:py-3 md:px-6 rounded-xl transition-all transform hover:scale-105 active:scale-95 shadow-lg;
        }
        .tab-btn {
            @apply flex-1 py-2 px-4 rounded-lg font-bold text-gray-600 dark:text-gray-300 hover:bg-white/50 dark:hover:bg-gray-700/50 transition-all text-center whitespace-nowrap;
        }
        .tab-btn.active {
            @apply bg-white dark:bg-gray-700 text-primary dark:text-white shadow-sm;
        }
        .btn-secondary {
            @apply bg-gray-600 hover:bg-gray-500 text-white font-bold py-2 px-4 sm:py-3 sm:px-5 md:py-3 md:px-6 rounded-xl transition-all;
        }
        .btn-danger {
            @apply bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 sm:py-3 sm:px-5 md:py-3 md:px-6 rounded-xl transition-all;
        }
        .modal-container {
            @apply bg-white dark:bg-gray-800 rounded-2xl p-8 max-w-md w-full shadow-2xl;
        }
        .form-input {
            @apply w-full py-4 px-6 text-lg border-2 border-gray-300 dark:border-gray-600 rounded-xl focus:border-primary focus:outline-none bg-white dark:bg-gray-700 dark:text-white transition-all;
        }
    }
</style>
`);