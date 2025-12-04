import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Login from "./pages/Login";
import ServiceSelector from "./pages/ServiceSelector";
import DevDashboard from "./pages/data-validation/DevDashboard";
import NewProjectUpload from "./pages/data-validation/NewProjectUpload";
import DevWorkspace from "./pages/data-validation/DevWorkspace";
import ReplicasDashboard from "./pages/replicas/ReplicasDashboard";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminValidationDashboard from "./pages/admin/AdminValidationDashboard";
import AdminValidationReview from "./pages/admin/AdminValidationReview";
import AdminReplicasDashboard from "./pages/admin/AdminReplicasDashboard";
import MainLayout from "./components/MainLayout";
import "./App.css";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<Login />} />

        {/* Rotas autenticadas com MainLayout */}
        <Route element={<MainLayout />}>
          <Route path="/services" element={<ServiceSelector />} />

          {/* Replicas Module */}
          <Route path="/replicas" element={<ReplicasDashboard />} />

          {/* Data Validation Module - Dev Routes */}
          <Route path="/validation" element={<DevDashboard />} />
          <Route path="/validation/new" element={<NewProjectUpload />} />
          <Route path="/validation/:projectId" element={<DevWorkspace />} />

          {/* Admin Routes */}
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route
            path="/admin/validation"
            element={<AdminValidationDashboard />}
          />
          <Route
            path="/admin/validation/:projectId"
            element={<AdminValidationReview />}
          />
          <Route path="/admin/replicas" element={<AdminReplicasDashboard />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
