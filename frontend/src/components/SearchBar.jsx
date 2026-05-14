import { useState, useRef } from "react"

const POPULAR_TAGS = ["Pasta", "Chicken", "Vegetarian", "Quick & Easy", "Soup"]

function SearchBar({ onSearch }) {
  const [query, setQuery] = useState("")
  const [focused, setFocused] = useState(false)
  const inputRef = useRef(null)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (query.trim()) onSearch(query.trim())
  }

  const handleTag = (tag) => {
    setQuery(tag)
    inputRef.current?.focus()
  }

  const handleClear = () => {
    setQuery("")
    inputRef.current?.focus()
  }

  return (
    <div className="w-full">
      <form
        onSubmit={handleSubmit}
        className={`
          flex items-center gap-2 bg-zinc-900 border rounded-2xl px-4 py-2
          transition-all duration-200
          ${focused
            ? "border-green-500 shadow-[0_0_0_3px_rgba(34,197,94,0.12)]"
            : "border-zinc-700 hover:border-zinc-600"
          }
        `}
      >
        <svg
          className="w-4 h-4 text-zinc-500 shrink-0"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" strokeLinecap="round" />
        </svg>

        <input
          ref={inputRef}
          type="text"
          placeholder="e.g. pasta, fried rice, chicken soup…"
          className="flex-1 bg-transparent outline-none text-sm text-white placeholder:text-zinc-500 py-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />

        {query && (
          <button
            type="button"
            onClick={handleClear}
            aria-label="Clear search"
            className="p-1 rounded-full text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition shrink-0"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" strokeLinecap="round" />
            </svg>
          </button>
        )}

        <div className="w-px h-5 bg-zinc-700 shrink-0" aria-hidden="true" />

        <button
          type="submit"
          className="
            flex items-center gap-1.5 shrink-0
            bg-green-600 hover:bg-green-500 active:scale-95
            text-white text-sm font-medium
            px-4 py-2 rounded-xl transition-all duration-150
          "
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.35-4.35" strokeLinecap="round" />
          </svg>
          Search
        </button>
      </form>

      <div className="flex flex-wrap items-center gap-2 mt-3">
        <span className="text-xs text-zinc-600">Popular:</span>
        {POPULAR_TAGS.map((tag) => (
          <button
            key={tag}
            type="button"
            onClick={() => handleTag(tag)}
            className="
              text-xs px-3 py-1 rounded-full
              border border-zinc-800 bg-zinc-900 text-zinc-400
              hover:border-green-700 hover:text-green-400 hover:bg-green-950/40
              transition-all duration-150
            "
          >
            {tag}
          </button>
        ))}
      </div>
    </div>
  )
}

export default SearchBar