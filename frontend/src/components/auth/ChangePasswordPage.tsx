import { useTranslation } from "react-i18next";
import { Lock } from "lucide-react";
import { useChangePasswordForm } from "@shared/hooks/useChangePasswordForm";
import { PASSWORD_REQUIREMENT_KEYS } from "@shared/utils/password";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { Alert, AlertDescription } from "../ui/alert";
import LanguageSelector from "../common/LanguageSelector.tsx";

// Écran bloquant affiché tant que le backend exige un changement de mot de passe
const ChangePasswordPage = () => {
  const { t } = useTranslation();
  const { fields, error, loading, handleSubmit, logout } =
    useChangePasswordForm();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background via-background to-muted/20">
      <div className="absolute top-4 right-4">
        <LanguageSelector />
      </div>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Lock className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">
            {t("changePassword.title")}
          </CardTitle>
          <CardDescription>{t("changePassword.description")}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {fields.map((field) => (
              <div key={field.id} className="space-y-2">
                <label htmlFor={field.id} className="text-sm font-medium">
                  {field.label}
                </label>
                <Input
                  id={field.id}
                  type="password"
                  value={field.value}
                  onChange={(e) => field.setValue(e.target.value)}
                  autoComplete={field.autoComplete}
                  placeholder="••••••••"
                  required
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

            <Button type="submit" className="w-full" disabled={loading}>
              {loading
                ? t("changePassword.submitting")
                : t("changePassword.submit")}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => logout()}
            >
              {t("auth.logout")}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default ChangePasswordPage;
