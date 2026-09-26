/**
 * Règles de complexité des mots de passe (miroir de `_validate_password_strength`
 * côté backend). Renvoie la clé i18n de l'erreur, ou null si le mot de passe est valide.
 */
export const getPasswordErrorKey = (password: string): string | null => {
  // Longueur en points de code et classes Unicode, comme len()/islower()/
  // isupper()/isdigit() en Python (é est une minuscule, pas seulement a-z)
  if ([...password].length < 8) return "invite.passwordTooShort";
  // Limite de bcrypt (72 octets UTF-8), vérifiée aussi côté backend
  if (new TextEncoder().encode(password).length > 72)
    return "invite.passwordTooLong";
  if (!/\p{Ll}/u.test(password)) return "invite.passwordMissingLowercase";
  if (!/\p{Lu}/u.test(password)) return "invite.passwordMissingUppercase";
  if (!/\p{Nd}/u.test(password)) return "invite.passwordMissingNumber";
  return null;
};

/** Clés i18n décrivant les règles ci-dessus, pour l'aide affichée sous les formulaires. */
export const PASSWORD_REQUIREMENT_KEYS = [
  "invite.passwordMinLength",
  "invite.passwordLowercase",
  "invite.passwordUppercase",
  "invite.passwordNumber",
] as const;
