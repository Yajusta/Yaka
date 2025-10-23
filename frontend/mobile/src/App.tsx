import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from '@shared/hooks/useAuth';
import { UsersProvider } from '@shared/hooks/useUsers';
import { DisplayModeProvider } from '@shared/hooks/useDisplayMode';
import { useTheme } from '@shared/hooks/useTheme';
import { Toaster } from './components/ui/sonner';
import BoardConfigScreen from './screens/BoardConfigScreen';
import LoginScreen from './screens/LoginScreen';
import MainScreen from './screens/MainScreen';
import './index.css';

// Protected route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, loading } = useAuth();
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

