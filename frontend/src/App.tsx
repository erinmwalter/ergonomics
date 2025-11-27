import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Container } from 'reactstrap';
import AppNavbar from './components/common/Navbar';
import ConfigPage from './components/config/ConfigPage';
import ProcessConfig from './components/process/ProcessConfig';
import AnalyzeProcess from './components/analyze/AnalyzeProcess';

const App: React.FC = () => {
  return (
    <Router>
      <div>
        <AppNavbar />
        <Container className="mt-4">
          <Routes>
            <Route path="/" element={
              <div>
                <h1>Manufacturing Process Adherence Monitoring</h1>
                <p>Welcome to your process monitoring dashboard!</p>
              </div>
            } />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/analysis" element={<AnalyzeProcess />} />
            <Route path="/process" element={<ProcessConfig />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Container>
      </div>
    </Router>
  );
};

export default App;