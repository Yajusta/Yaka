import { useTranslation } from "react-i18next";
import { Loader2, Lock } from "lucide-react";
import { useChangePasswordForm } from "@shared/hooks/useChangePasswordForm";
import { PASSWORD_REQUIREMENT_KEYS } from "@shared/utils/password";

const inputClassName =
  "w-full px-4 py-3 bg-card border-2 border-border rounded-lg text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent";

// Écran bloquant affiché tant que le backend exige un changement de mot de passe
const ChangePasswordScreen = () => {
  const { t } = useTranslation();
  const { fields, error, loading, handleSubmit, logout } =
    useChangePasswordForm();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 bg-background">
      <div className="w-full max-w-md space-y-8 animate-fade-in">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <Lock className="w-12 h-12 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">
            {t("changePassword.title")}
          </h1>
          <p className="mt-2 text-muted-foreground">
            {t("changePassword.description")}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          {fields.map((field) => (
            <div key={field.id}>
              <label
                htmlFor={field.id}
                className="block text-sm font-medium text-foreground mb-2"
              >
                {field.label}
              </label>
              <input
                id={field.id}
                type="password"
                value={field.value}
                onChange={(e) => field.setValue(e.target.value)}
                required
                autoComplete={field.autoComplete}
                placeholder="••••••••"
                className={inputClassName}
              />
            </div>
          ))}

          <div className="text-xs text-muted-foreground space-y-1">
            <p>{t("invite.passwordRequirements")}</p>
            <ul className="list-disc list-inside space-y-1 ml-2">
              {PASSWORD_REQUIREMENT_KEYS.map((key) => (
                <li key={key}>{t(key)}</li>
              ))}
            </ul>
          </div>

          {error && (
            <div className="p-4 bg-destructive/10 border-2 border-destructive/40 rounded-lg animate-slide-up">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-touch bg-primary text-primary-foreground font-medium rounded-lg hover:bg-primary/90 active:bg-primary/80 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
          >
            {loading && <Loader2 className="mr-2 h-5 w-5 animate-spin" />}
            {loading
              ? t("changePassword.submitting")
              : t("changePassword.submit")}
          </button>
          <button
            type="button"
            onClick={() => logout()}
            className="w-full btn-touch text-muted-foreground font-medium rounded-lg hover:text-foreground transition-colors"
          >
            {t("auth.logout")}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChangePasswordScreen;
