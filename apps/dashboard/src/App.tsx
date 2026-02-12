import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ExplorerPage from './components/explorer/ExplorerPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="*" element={<ExplorerPage />} />
      </Routes>
    </Router>
  );
}

export default App;
