import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import ServiceSelector from "./pages/ServiceSelector";
import DevDashboard from "./pages/data-validation/DevDashboard";
import NewProjectUpload from "./pages/data-validation/NewProjectUpload";
import DevWorkspace from "./pages/data-validation/DevWorkspace";
import "./App.css";

function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<Login />} />
          <Route path="/services" element={<ServiceSelector />} />

          {/* Data Validation Module - Dev Routes */}
          <Route path="/validation" element={<DevDashboard />} />
          <Route path="/validation/new" element={<NewProjectUpload />} />
          <Route path="/validation/:projectId" element={<DevWorkspace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
