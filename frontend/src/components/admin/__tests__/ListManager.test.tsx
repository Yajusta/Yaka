import { describe, it, expect, vi, beforeEach } from "vitest";
import { createContext, useContext, type ReactNode } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import ListManager from "../ListManager";
import { useAuth } from "@shared/hooks/useAuth";
import { useToast } from "@shared/hooks/use-toast";
import { listsApi } from "@shared/services/listsApi";
import { UserRole } from "@shared/types";
import i18n from "@shared/i18n";

// Mock dependencies
vi.mock("@shared/hooks/useAuth");
vi.mock("@shared/hooks/use-toast");
vi.mock("@shared/services/listsApi");

// Le Select de Radix est inexploitable sous jsdom : son ouverture bloque le
// thread une vingtaine de secondes. Ce test cible la logique de suppression de
// ListManager, pas le rendu de la primitive : on la remplace par des boutons.
const SelectCtx = createContext<(value: string) => void>(() => {});

vi.mock("../../ui/select", () => ({
  Select: ({
    children,
    onValueChange,
  }: {
    children: ReactNode;
    onValueChange: (value: string) => void;
  }) => (
    <SelectCtx.Provider value={onValueChange}>{children}</SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  SelectValue: ({ placeholder }: { placeholder?: string }) => (
    <span>{placeholder}</span>
  ),
  SelectContent: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  SelectItem: ({ children, value }: { children: ReactNode; value: string }) => {
    const onValueChange = useContext(SelectCtx);
    return (
      <button
        type="button"
        role="option"
        aria-selected={false}
        onClick={() => onValueChange(value)}
      >
        {children}
      </button>
    );
  },
}));

const mockUseAuth = vi.mocked(useAuth);
const mockUseToast = vi.mocked(useToast);
const mockListsApi = vi.mocked(listsApi);

const mockToast = vi.fn();

const mockAdminUser = {
  id: 1,
  username: "admin",
  email: "admin@test.com",
  role: UserRole.ADMIN,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const mockLists = [
  {
    id: 1,
    name: "À faire",
    order: 1,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
  {
    id: 2,
    name: "En cours",
    order: 2,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
  },
];

/** Nombre de cartes par liste, utilisé par les mocks de getListCardsCount. */
const cardCounts: Record<number, number> = { 1: 0, 2: 0 };

const renderListManager = (props = {}) => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onListsUpdated: vi.fn(),
    ...props,
  };

  return render(
    <BrowserRouter>
      <ListManager {...defaultProps} />
    </BrowserRouter>,
  );
};

describe("ListManager", () => {
  beforeEach(async () => {
    vi.clearAllMocks();

    // jsdom annonce une locale en-US : on fixe la langue pour que les
    // assertions sur les libellés soient déterministes.
    await i18n.changeLanguage("fr");

    cardCounts[1] = 0;
    cardCounts[2] = 0;

    mockUseAuth.mockReturnValue({
      user: mockAdminUser,
      loading: false,
      aiAvailable: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    mockUseToast.mockReturnValue({
      toast: mockToast,
      dismiss: vi.fn(),
    });

    mockListsApi.getLists.mockResolvedValue(mockLists);
    mockListsApi.getListCardsCount.mockImplementation(
      async (listId: number) => ({
        list: mockLists.find((l) => l.id === listId) ?? mockLists[0],
        card_count: cardCounts[listId] ?? 0,
      }),
    );
  });

  it("should render list manager dialog when open", async () => {
    renderListManager();

    await waitFor(() => {
      expect(screen.getByText("Gestion des listes")).toBeInTheDocument();
    });
  });

  it("should show progress bar during list deletion with cards", async () => {
    // « À faire » contient 3 cartes : la suppression exige une liste de
    // destination et déclenche la barre de progression.
    cardCounts[1] = 3;

    // Différé, pour pouvoir observer l'état intermédiaire « en cours ».
    let finishDeletion!: () => void;
    const deletionDone = new Promise<void>((resolve) => {
      finishDeletion = resolve;
    });

    mockListsApi.deleteListWithProgress.mockImplementation(
      async (
        _listId: number,
        _targetId: number,
        onProgress?: (current: number, total: number, cardName: string) => void,
      ) => {
        onProgress?.(1, 3, "Card 1");
        await deletionDone;
      },
    );

    // Radix Select exige de vrais pointer events : fireEvent ne suffit pas.
    renderListManager();

    await waitFor(() => {
      expect(screen.getByText("À faire")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "Supprimer À faire" }));

    await waitFor(() => {
      expect(screen.getByText("Supprimer la liste")).toBeInTheDocument();
    });

    // Choisir la liste de destination
    fireEvent.click(
      await screen.findByRole("option", { name: "En cours (0 carte)" }),
    );

    fireEvent.click(
      screen.getByRole("button", {
        name: "Déplacer les cartes et supprimer la liste",
      }),
    );

    // Pendant la suppression : titre « en cours » et barre de progression
    await waitFor(() => {
      expect(screen.getByText("Suppression en cours...")).toBeInTheDocument();
    });
    expect(
      screen.getByText("Déplacement des cartes en cours..."),
    ).toBeInTheDocument();
    expect(mockListsApi.deleteListWithProgress).toHaveBeenCalledWith(
      1,
      2,
      expect.any(Function),
    );

    finishDeletion();

    await waitFor(() => {
      expect(
        screen.queryByText("Suppression en cours..."),
      ).not.toBeInTheDocument();
    });
  });

  it("should not render for non-admin users", () => {
    mockUseAuth.mockReturnValue({
      user: { ...mockAdminUser, role: UserRole.SUPERVISOR },
      loading: false,
      aiAvailable: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    const { container } = renderListManager();
    expect(container.firstChild).toBeNull();
  });
});
