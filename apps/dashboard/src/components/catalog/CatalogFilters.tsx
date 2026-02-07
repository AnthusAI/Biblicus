import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';

export default function CatalogFilters() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(searchParams);
    if (searchInput) {
      params.set('search', searchInput);
    } else {
      params.delete('search');
    }
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSearchParams({});
    setSearchInput('');
  };

  const activeFilters = Array.from(searchParams.entries());

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearchSubmit} className="flex gap-2">
        <input
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search by title or path..."
          className="flex-1 px-4 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          Search
        </button>
      </form>

      {activeFilters.length > 0 && (
        <div className="flex gap-2 items-center flex-wrap">
          <span className="text-sm text-gray-600">Active filters:</span>
          {activeFilters.map(([key, value]) => (
            <span key={key} className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded">
              {key}: {value}
            </span>
          ))}
          <button
            onClick={clearFilters}
            className="px-3 py-1 text-sm text-red-600 hover:underline"
          >
            Clear all
          </button>
        </div>
      )}
    </div>
  );
}
