import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom';
import { AuthProvider, useAuth } from '@shared/hooks/useAuth';
import { UsersProvider } from '@shared/hooks/useUsers';
import { DisplayModeProvider } from '@shared/hooks/useDisplayMode';
import { useTheme } from '@shared/hooks/useTheme';
import { Toaster } from './components/ui/sonner';
import BoardConfigScreen from './screens/BoardConfigScreen';
import LoginScreen from './screens/LoginScreen';
import MainScreen from './screens/MainScreen';
import './index.css';

// Board route handler - updates localStorage when board name is provided in URL and renders MainScreen
const BoardRouteHandler = () => {
  const { boardName } = useParams();
  const location = useLocation();

  useEffect(() => {
    if (boardName) {
      // Resolve endpoint using the same logic as BoardConfigScreen
      const resolveEndpoint = (name: string): string => {
        const apiBaseUrl = (window as any).API_BASE_URL || 'http://localhost:8000';

        if (name.trim().toLowerCase() === 'localhost') {
          return apiBaseUrl;
        } else {
          return `${apiBaseUrl}/board/${encodeURIComponent(name.trim())}`;
        }
      };

      // Update localStorage with the board name from URL
      localStorage.setItem('board_name', boardName.trim());
      localStorage.setItem('api_base_url', resolveEndpoint(boardName));
    }
  }, [boardName, location.pathname]);

  // Render MainScreen with protection, staying on the /board/:boardName URL
  return (
    <ProtectedRoute>
      <MainScreen />
    </ProtectedRoute>
  );
};

// Protected route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
  const location = useLocation();
  const apiUrl = localStorage.getItem('api_base_url');

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!apiUrl) {
    return <Navigate to="/config" replace />;
  }

  if (!user) {
    // If we're on a board route, redirect to the board's login page
    const boardMatch = location.pathname.match(/^\/board\/([^/]+)/);
    if (boardMatch) {
      return <Navigate to={`/board/${boardMatch[1]}/login`} replace />;
    }
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// App content with theme support
const AppContent = () => {
  const { theme } = useTheme();

  useEffect(() => {
    document.documentElement.className = theme;
  }, [theme]);

  return (
    <Routes>
      <Route path="/config" element={<BoardConfigScreen />} />
      <Route path="/login" element={<LoginScreen />} />
      <Route path="/board/:boardName/login" element={<LoginScreen />} />
      <Route path="/board/:boardName" element={<BoardRouteHandler />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <MainScreen />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

function App() {
  return (
    <Router>
      <AuthProvider>
        <UsersProvider>
          <DisplayModeProvider>
            <AppContent />
            <Toaster />
          </DisplayModeProvider>
        </UsersProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;

