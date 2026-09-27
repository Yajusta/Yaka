/**
 * Message d'erreur des formulaires d'authentification : 429 (limitation de
 * débit backend) traduit, sinon le détail renvoyé par l'API, sinon la clé i18n
 * de repli.
 */
export const getAuthErrorMessage = (
  error: any,
  t: (key: string) => string,
  fallbackKey: string,
): string =>
  error?.response?.status === 429
    ? t("auth.tooManyAttempts")
    : error?.response?.data?.detail || t(fallbackKey);
