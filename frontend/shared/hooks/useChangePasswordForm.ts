import { useState, FormEvent } from "react";
import { useTranslation } from "react-i18next";
import { useAuth } from "./useAuth";
import { useToast } from "./use-toast";
import { getPasswordErrorKey } from "../utils/password";

/**
 * État et soumission du formulaire de changement de mot de passe obligatoire,
 * partagés entre l'écran desktop et l'écran mobile (seul le rendu diffère).
 */
export const useChangePasswordForm = () => {
  const { t } = useTranslation();
  const { changePassword, logout } = useAuth();
  const { toast } = useToast();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      setError(t("invite.passwordsDoNotMatch"));
      return;
    }
    if (newPassword === currentPassword) {
      setError(t("changePassword.mustDiffer"));
      return;
    }
    const passwordErrorKey = getPasswordErrorKey(newPassword);
    if (passwordErrorKey) {
      setError(t(passwordErrorKey));
      return;
    }

    setLoading(true);
    setError("");
    try {
      await changePassword(currentPassword, newPassword);
      toast({ title: t("changePassword.success"), variant: "success" });
    } catch (err: any) {
      // Les messages du backend ne sont pas traduits : le seul 400 possible
      // ici est un mot de passe actuel incorrect (égalité, complexité et longueur sont vérifiées plus haut)
      setError(
        err?.response?.status === 400
          ? t("changePassword.wrongCurrentPassword")
          : t("changePassword.error"),
      );
    } finally {
      setLoading(false);
    }
  };

  const fields = [
    {
      id: "currentPassword",
      label: t("changePassword.currentPassword"),
      value: currentPassword,
      setValue: setCurrentPassword,
      autoComplete: "current-password",
    },
    {
      id: "newPassword",
      label: t("invite.newPassword"),
      value: newPassword,
      setValue: setNewPassword,
      autoComplete: "new-password",
    },
    {
      id: "confirmPassword",
      label: t("invite.confirmPassword"),
      value: confirmPassword,
      setValue: setConfirmPassword,
      autoComplete: "new-password",
    },
  ];

  // Session locale effacée même si la révocation serveur échoue
  const handleLogout = () =>
    logout().catch((err) =>
      console.warn("Révocation de la session impossible:", err),
    );

  return { fields, error, loading, handleSubmit, logout: handleLogout };
};
