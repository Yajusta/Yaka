import {
  useState,
  useEffect,
  createContext,
  useContext,
  ReactNode,
  JSX,
} from "react";
import { authService, PASSWORD_CHANGE_REQUIRED_EVENT } from "../services/api";
import { User, AuthContextType } from "../types";

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps): JSX.Element => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [aiAvailable, setAiAvailable] = useState<boolean>(false);

  useEffect(() => {
    const initAuth = async (): Promise<void> => {
      try {
        if (authService.isAuthenticated()) {
          const userData = authService.getCurrentUserFromStorage();
          if (userData && typeof userData === "object" && "id" in userData) {
            // Rafraîchir depuis le serveur avant d'afficher l'application :
            // l'état stocké peut être périmé (ex. changement de mot de passe
            // exigé depuis la dernière connexion). Un seul setUser évite de
            // déclencher deux fois les chargements dépendant de `user`.
            // Les deux appels sont indépendants : lancés en parallèle.
            const [meResult, aiResult] = await Promise.allSettled([
              authService.getCurrentUser(),
              authService.checkAIFeatures(),
            ]);
            // 401 géré par l'intercepteur axios (session effacée)
            if (!authService.isAuthenticated()) {
              return;
            }
            // En cas d'échec réseau, on garde l'état en cache
            setUser(
              meResult.status === "fulfilled" ? meResult.value : userData,
            );
            if (aiResult.status === "fulfilled") {
              setAiAvailable(aiResult.value.ai_available);
            } else {
              console.error(
                "Erreur lors de la vérification des fonctionnalités IA:",
                aiResult.reason,
              );
              setAiAvailable(false);
            }
          } else {
            // Données invalides, forcer la déconnexion
            // Session locale seulement : un état local corrompu ne doit pas
            // révoquer les sessions des autres appareils
            console.warn("Données utilisateur invalides, déconnexion forcée");
            authService.clearSession();
          }
        }
      } catch (error) {
        console.error(
          "Erreur lors de l'initialisation de l'authentification:",
          error,
        );
        authService.clearSession();
      } finally {
        setLoading(false);
      }
    };
    initAuth();
  }, []);

  // Session déjà ouverte quand le backend exige un changement de mot de passe
  // (403 dédié détecté par l'intercepteur axios) : basculer sur l'écran bloquant.
  useEffect(() => {
    const onPasswordChangeRequired = () => {
      setUser((current) => {
        if (!current || current.must_change_password) return current;
        const flagged = { ...current, must_change_password: true };
        localStorage.setItem("user", JSON.stringify(flagged));
        return flagged;
      });
    };
    window.addEventListener(
      PASSWORD_CHANGE_REQUIRED_EVENT,
      onPasswordChangeRequired,
    );
    return () =>
      window.removeEventListener(
        PASSWORD_CHANGE_REQUIRED_EVENT,
        onPasswordChangeRequired,
      );
  }, []);

  const login = async (email: string, password: string): Promise<void> => {
    try {
      const userData = await authService.login(email, password);
      setUser(userData);

      // Note: Language setting is handled by authService.login which sets localStorage.
      // The i18n instance in each app (mobile/desktop) should detect this change.
      // We don't change the language here because the hook is in shared code
      // and each app has its own i18n instance.

      // Check AI features availability after login
      try {
        const aiFeatures = await authService.checkAIFeatures();
        setAiAvailable(aiFeatures.ai_available);
      } catch (error) {
        console.error(
          "Erreur lors de la vérification des fonctionnalités IA:",
          error,
        );
        setAiAvailable(false);
      }
    } catch (error) {
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    // La session locale est toujours effacée ; une erreur signale que la
    // révocation côté serveur a échoué (propagée à l'appelant)
    try {
      await authService.logout();
    } finally {
      setUser(null);
      setAiAvailable(false);
    }
  };

  const changePassword = async (
    currentPassword: string,
    newPassword: string,
  ): Promise<void> => {
    const userData = await authService.changePassword(
      currentPassword,
      newPassword,
    );
    setUser(userData);
  };

  const value: AuthContextType = {
    user,
    login,
    logout,
    loading,
    aiAvailable,
    changePassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
