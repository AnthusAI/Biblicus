import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import CorpusDashboardPage from './pages/CorpusDashboardPage';
import CatalogBrowserPage from './pages/CatalogBrowserPage';
import CatalogItemDetailPage from './pages/CatalogItemDetailPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/corpus/:corpusName" element={<CorpusDashboardPage />} />
        <Route path="/corpus/:corpusName/catalog" element={<CatalogBrowserPage />} />
        <Route path="/corpus/:corpusName/catalog/:itemId" element={<CatalogItemDetailPage />} />
      </Routes>
    </Router>
  );
}

export default App;
