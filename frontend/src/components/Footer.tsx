export function Footer() {
  return (
    <footer className="bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 py-6">
      <div className="container mx-auto px-4">
        <div className="flex flex-col md:flex-row items-center justify-between text-sm text-gray-500 dark:text-gray-400">
          <div>
            ComputeChain Explorer &copy; {new Date().getFullYear()}
          </div>
          <div className="flex items-center space-x-4 mt-2 md:mt-0">
            <a
              href="https://github.com/computechain"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-primary-600"
            >
              GitHub
            </a>
            <a
              href="/api/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-primary-600"
            >
              API Docs
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
