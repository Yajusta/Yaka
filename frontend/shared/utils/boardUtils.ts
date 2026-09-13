/**
 * Utilitaires pour la gestion et la résolution des boards (interne ou spécifique).
 */

export const isInternalBoard = (boardName?: string | null): boolean => {
  if (!boardName) return true;
  const trimmed = boardName.trim().toLowerCase();
  return (
    trimmed === "" ||
    trimmed === "localhost" ||
    trimmed === "interne" ||
    trimmed === "internal"
  );
};

export interface ResolvedBoardInfo {
  boardName: string;
  apiUrl: string;
  isInternal: boolean;
  displayName: string;
}

/**
 * Résout le endpoint API et les informations du board à partir d'un nom de board.
 */
export const resolveBoardEndpoint = (
  boardName?: string | null,
): ResolvedBoardInfo => {
  const apiBaseUrl = (window as any).API_BASE_URL || "http://localhost:8000";

  if (isInternalBoard(boardName)) {
    return {
      boardName: "",
      apiUrl: apiBaseUrl,
      isInternal: true,
      displayName: "Board interne",
    };
  }

  const normalized = boardName!.trim().toLowerCase().replace(/\s+/g, "");

  return {
    boardName: normalized,
    apiUrl: `${apiBaseUrl}/board/${encodeURIComponent(normalized)}`,
    isInternal: false,
    displayName: normalized,
  };
};

/**
 * Extrait le board_uid depuis l'URL courante (desktop ou mobile).
 */
export const getBoardFromUrl = (): string | null => {
  const path = window.location.pathname;
  const match = path.match(/^(?:\/m)?\/board\/([^\/]+)/);
  return match ? match[1] : null;
};

/**
 * Récupère les informations du board actuellement actif
 * (soit via l'URL, soit via le localStorage, soit par défaut interne).
 */
export const getCurrentBoardInfo = (): ResolvedBoardInfo => {
  const urlBoard = getBoardFromUrl();
  if (urlBoard) {
    return resolveBoardEndpoint(urlBoard);
  }

  const storedBoardName = localStorage.getItem("board_name");
  if (storedBoardName && !isInternalBoard(storedBoardName)) {
    return resolveBoardEndpoint(storedBoardName);
  }

  return resolveBoardEndpoint(null);
};

/**
 * Met à jour le localStorage avec la configuration du board
 */
export const saveBoardConfig = (
  boardName?: string | null,
): ResolvedBoardInfo => {
  const resolved = resolveBoardEndpoint(boardName);
  if (resolved.isInternal) {
    localStorage.setItem("board_name", "");
    localStorage.setItem("api_base_url", resolved.apiUrl);
  } else {
    localStorage.setItem("board_name", resolved.boardName);
    localStorage.setItem("api_base_url", resolved.apiUrl);
  }
  return resolved;
};
