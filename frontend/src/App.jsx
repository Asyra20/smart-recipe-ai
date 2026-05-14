import { useState, useMemo } from "react"
import api from "./services/api"
import SearchBar from "./components/SearchBar"
import RecipeCard from "./components/RecipeCard"

function SkeletonCard() {
  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-5 animate-pulse">
      <div className="flex gap-1.5 mb-3">
        <div className="h-4 w-14 bg-zinc-700 rounded-full" />
        <div className="h-4 w-10 bg-zinc-800 rounded-full" />
      </div>
      <div className="h-4 w-3/4 bg-zinc-700 rounded-md mb-2" />
      <div className="h-3 w-full bg-zinc-800 rounded-md mt-1" />
      <div className="h-3 w-2/3 bg-zinc-800 rounded-md mt-1.5" />
      <div className="h-1.5 w-full bg-zinc-800 rounded-full mt-5" />
    </div>
  )
}

function FilterBar({ filters, onChange, total, filtered }) {
  const options = [
    { key: "quick",       label: "⚡ Quick",        field: "is_quick" },
    { key: "protein",     label: "💪 High protein",  field: "is_high_protein" },
    { key: "lowcal",      label: "🥗 Low calorie",   field: "is_low_calorie" },
  ]

  const active = Object.values(filters).some(Boolean)

  return (
    <div className="flex flex-wrap items-center gap-2 mb-6">
      <span className="text-xs text-zinc-600">Filter:</span>
      {options.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onChange(key, !filters[key])}
          className={`
            text-xs px-3 py-1 rounded-full border transition-all duration-150
            ${filters[key]
              ? "border-green-600 bg-green-900/40 text-green-400"
              : "border-zinc-800 bg-zinc-900 text-zinc-500 hover:border-zinc-700 hover:text-zinc-400"}
          `}
        >
          {label}
        </button>
      ))}
      {active && (
        <button
          onClick={() => onChange("reset")}
          className="text-xs text-zinc-600 hover:text-zinc-400 transition ml-1"
        >
          Clear
        </button>
      )}
      {active && (
        <span className="text-xs text-zinc-600 ml-auto">
          {filtered} of {total}
        </span>
      )}
    </div>
  )
}

function RecipeGrid({ recipes, onCardClick, loading, skeletonCount = 6 }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: skeletonCount }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    )
  }
  if (recipes.length === 0) {
    return (
      <p className="text-xs text-zinc-600 py-6 text-center">
        No recipes match the selected filters.
      </p>
    )
  }
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {recipes.map((recipe) => (
        <RecipeCard
          key={recipe.recipe_id}
          recipe={recipe}
          onClick={onCardClick}
        />
      ))}
    </div>
  )
}

function EmptyState({ searched }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-14 h-14 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
        <svg className="w-6 h-6 text-zinc-600" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" strokeLinecap="round" />
        </svg>
      </div>
      {searched ? (
        <>
          <p className="text-white text-sm font-medium">No recipes found</p>
          <p className="text-zinc-600 text-xs mt-1">Try a different keyword</p>
        </>
      ) : (
        <p className="text-zinc-600 text-sm">Search for a recipe to get started</p>
      )}
    </div>
  )
}

const EMPTY_FILTERS = { quick: false, protein: false, lowcal: false }

function applyFilters(recipes, filters) {
  return recipes.filter(r => {
    if (filters.quick   && !r.is_quick)        return false
    if (filters.protein && !r.is_high_protein) return false
    if (filters.lowcal  && !r.is_low_calorie)  return false
    return true
  })
}

function App() {
  const [results,         setResults]         = useState([])
  const [recommendations, setRecommendations] = useState([])
  const [loading,         setLoading]         = useState(false)
  const [recLoading,      setRecLoading]      = useState(false)
  const [searched,        setSearched]        = useState(false)
  const [lastQuery,       setLastQuery]       = useState("")
  const [activeId,        setActiveId]        = useState(null)
  const [error,           setError]           = useState(null)
  const [filters,         setFilters]         = useState(EMPTY_FILTERS)
  const [recFilters,      setRecFilters]      = useState(EMPTY_FILTERS)

  const handleFilterChange = (key, value, setFn) => {
    if (key === "reset") { setFn(EMPTY_FILTERS); return }
    setFn(prev => ({ ...prev, [key]: value }))
  }

  const filteredResults = useMemo(
    () => applyFilters(results, filters),
    [results, filters]
  )
  const filteredRecs = useMemo(
    () => applyFilters(recommendations, recFilters),
    [recommendations, recFilters]
  )

  const handleSearch = async (query) => {
    setLoading(true)
    setError(null)
    setSearched(true)
    setLastQuery(query)
    setRecommendations([])
    setActiveId(null)
    setFilters(EMPTY_FILTERS)
    try {
      const res = await api.get(`/search?q=${encodeURIComponent(query)}`)
      setResults(res.data.results)
    } catch {
      setError("Search failed. Please try again.")
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const fetchRecommendations = async (recipe_id) => {
    if (activeId === recipe_id) return
    setActiveId(recipe_id)
    setRecLoading(true)
    setRecFilters(EMPTY_FILTERS)
    try {
      const res = await api.get(`/recommend/${recipe_id}`)
      setRecommendations(res.data.recommendations)
      setTimeout(() => {
        document.getElementById("recommendations-section")
          ?.scrollIntoView({ behavior: "smooth", block: "start" })
      }, 100)
    } catch {
      setRecommendations([])
    } finally {
      setRecLoading(false)
    }
  }

  const showResults = !loading && results.length > 0
  const showEmpty   = !loading && searched && results.length === 0 && !error

  return (
    <div className="min-h-screen bg-gradient-to-b from-black to-zinc-900 text-white">
      {/* Header */}
      <header className="border-b border-zinc-900 px-6 py-4 flex items-center gap-3">
        <div className="w-7 h-7 rounded-lg bg-green-600 flex items-center justify-center shrink-0">
          <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2Z" />
            <path d="M8 12c0-2.21 1.79-4 4-4s4 1.79 4 4-1.79 4-4 4-4-1.79-4-4Z" />
          </svg>
        </div>
        <span className="text-sm font-semibold tracking-tight">Smart Recipe AI</span>
        <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-zinc-800 text-zinc-500 border border-zinc-700">
          v2 · Hybrid
        </span>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-12">
        {/* Hero */}
        <div className="mb-10">
          <h1 className="text-4xl font-bold tracking-tight text-white mb-2">
            What are you cooking?
          </h1>
          <p className="text-zinc-500 text-sm">
            AI-powered semantic search & hybrid recommendations
          </p>
        </div>

        {/* Search */}
        <div className="max-w-xl mx-auto mb-12">
          <SearchBar onSearch={handleSearch} />
        </div>

        {/* Error */}
        {error && (
          <div className="flex items-center gap-2 text-sm text-red-400 bg-red-950/40 border border-red-900/50 rounded-xl px-4 py-3 mb-8 max-w-xl mx-auto">
            <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 8v4m0 4h.01" strokeLinecap="round" />
            </svg>
            {error}
          </div>
        )}

        {/* Search results */}
        {(loading || showResults) && (
          <section className="mb-16">
            <div className="flex items-baseline gap-3 mb-4">
              <h2 className="text-2xl font-semibold text-white">
                {loading ? "Searching…" : `Results for "${lastQuery}"`}
              </h2>
              {showResults && (
                <span className="text-xs text-zinc-500">
                  {results.length} {results.length === 1 ? "recipe" : "recipes"}
                </span>
              )}
            </div>

            {showResults && (
              <FilterBar
                filters={filters}
                onChange={(k, v) => handleFilterChange(k, v, setFilters)}
                total={results.length}
                filtered={filteredResults.length}
              />
            )}

            <RecipeGrid
              recipes={filteredResults}
              onCardClick={fetchRecommendations}
              loading={loading}
            />
          </section>
        )}

        {/* Empty / idle state */}
        {(showEmpty || (!searched && !loading)) && (
          <EmptyState searched={searched} />
        )}

        {/* Recommendations */}
        {(recLoading || recommendations.length > 0) && (
          <section id="recommendations-section">
            <div className="flex items-center gap-3 mb-6">
              <div className="h-px flex-1 bg-zinc-800" aria-hidden="true" />
              <span className="text-xs text-zinc-600 uppercase tracking-widest font-medium">
                Similar recipes
              </span>
              <div className="h-px flex-1 bg-zinc-800" aria-hidden="true" />
            </div>

            {!recLoading && (
              <>
                <div className="flex items-baseline gap-3 mb-4">
                  <h2 className="text-2xl font-semibold text-white">Recommended for you</h2>
                  <span className="text-xs text-zinc-500">
                    {recommendations.length} {recommendations.length === 1 ? "recipe" : "recipes"}
                  </span>
                </div>
                <FilterBar
                  filters={recFilters}
                  onChange={(k, v) => handleFilterChange(k, v, setRecFilters)}
                  total={recommendations.length}
                  filtered={filteredRecs.length}
                />
              </>
            )}

            <RecipeGrid
              recipes={filteredRecs}
              onCardClick={fetchRecommendations}
              loading={recLoading}
              skeletonCount={3}
            />
          </section>
        )}
      </main>
    </div>
  )
}

export default App