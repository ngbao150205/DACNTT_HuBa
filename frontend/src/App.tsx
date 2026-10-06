import {
  Navigate,
  Route,
  Routes,
} from "react-router-dom";

import AppLayout from "./layouts/AppLayout";
import ProductAnalysisLayout from "./layouts/ProductAnalysisLayout";

import Home from "./pages/Home";
import Analyze from "./pages/Analyze";
import History from "./pages/History";

import Dashboard from "./pages/Dashboard";
import Reviews from "./pages/Reviews";
import Issues from "./pages/Issues";
import Risk from "./pages/Risk";
import Competitor from "./pages/Competitor";

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route
          path="/"
          element={<Home />}
        />

        <Route
          path="/analyze"
          element={<Analyze />}
        />

        <Route
          path="/history"
          element={<History />}
        />

        <Route
          path="/products/:productId"
          element={<ProductAnalysisLayout />}
        >
          <Route
            index
            element={<Navigate to="dashboard" replace />}
          />

          <Route
            path="dashboard"
            element={<Dashboard />}
          />

          <Route
            path="reviews"
            element={<Reviews />}
          />

          <Route
            path="issues"
            element={<Issues />}
          />

          <Route
            path="risk"
            element={<Risk />}
          />

          <Route
            path="competitor"
            element={<Competitor />}
          />
        </Route>

        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />
      </Route>
    </Routes>
  );
}

export default App;