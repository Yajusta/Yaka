import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { KanbanBoard } from "../KanbanBoard";
import { mockLists, mockCards } from "@/test/mocks";
import { listsApi } from "@shared/services/listsApi";
import i18n from "@shared/i18n";
import type { Card as CardType, KanbanList } from "@shared/types";

vi.mock("@shared/services/listsApi", () => ({
  listsApi: {
    getLists: vi.fn(),
    createList: vi.fn(),
    updateList: vi.fn(),
    deleteList: vi.fn(),
    reorderLists: vi.fn(),
    getListCardsCount: vi.fn(),
  },
}));

// dnd-kit : le drag n'est pas testable sous jsdom, on garde juste le rendu.
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="dnd-context">{children}</div>
  ),
  DragOverlay: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="drag-overlay">{children}</div>
  ),
  closestCenter: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
  PointerSensor: vi.fn(),
  TouchSensor: vi.fn(),
}));

// La colonne a ses propres tests ; ici on vérifie seulement ce que le board
// lui transmet.
vi.mock("../KanbanColumn", () => ({
  KanbanColumn: ({
    list,
    cards,
    onCreateCard,
  }: {
    list: KanbanList;
    cards: CardType[];
    onCreateCard?: (listId: number) => void;
  }) => (
    <div data-testid="kanban-column" data-list-id={list.id}>
      <span>{list.name}</span>
      <ul>
        {cards.map((card) => (
          <li key={card.id}>{card.title}</li>
        ))}
      </ul>
      <button type="button" onClick={() => onCreateCard?.(list.id)}>
        create-in-{list.id}
      </button>
    </div>
  ),
}));

vi.mock("../index", () => ({
  CardItem: ({ card }: { card: CardType }) => <div>{card.title}</div>,
}));

vi.mock("../../admin/ArchiveManager", () => ({
  ArchiveManager: () => null,
}));

const baseProps = {
  cards: mockCards,
  onCardUpdate: vi.fn(),
  onCardDelete: vi.fn(),
  onCardMove: vi.fn(),
};

const mockedGetLists = vi.mocked(listsApi.getLists);

describe("KanbanBoard", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("fr");
    localStorage.clear();
    mockedGetLists.mockResolvedValue(mockLists);
  });

  it("affiche un indicateur pendant le chargement des listes", () => {
    mockedGetLists.mockReturnValue(new Promise(() => {})); // jamais résolue

    render(<KanbanBoard {...baseProps} />);

    expect(screen.getByText("Chargement des listes...")).toBeInTheDocument();
  });

  it("affiche une erreur si le chargement des listes échoue", async () => {
    mockedGetLists.mockRejectedValue(new Error("boom"));

    render(<KanbanBoard {...baseProps} />);

    expect(
      await screen.findByText("Erreur de chargement des listes"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Recharger la page" }),
    ).toBeInTheDocument();
  });

  it("rend une colonne par liste, dans l'ordre", async () => {
    render(<KanbanBoard {...baseProps} />);

    await waitFor(() => {
      expect(screen.getAllByTestId("kanban-column")).toHaveLength(3);
    });

    expect(
      screen.getAllByTestId("kanban-column").map((c) => c.dataset.listId),
    ).toEqual(["1", "2", "3"]);
    expect(screen.getByText("A faire")).toBeInTheDocument();
    expect(screen.getByText("En cours")).toBeInTheDocument();
    expect(screen.getByText("Terminé")).toBeInTheDocument();
  });

  it("répartit les cartes dans la colonne de leur list_id", async () => {
    render(<KanbanBoard {...baseProps} />);

    await waitFor(() => {
      expect(screen.getAllByTestId("kanban-column")).toHaveLength(3);
    });

    const columns = screen.getAllByTestId("kanban-column");
    expect(columns[0]).toHaveTextContent("Test Card 1");
    expect(columns[1]).toHaveTextContent("Test Card 2");
    expect(columns[2]).not.toHaveTextContent("Test Card");
  });

  it("n'affiche aucune carte quand la liste de cartes est vide", async () => {
    render(<KanbanBoard {...baseProps} cards={[]} />);

    await waitFor(() => {
      expect(screen.getAllByTestId("kanban-column")).toHaveLength(3);
    });

    for (const column of screen.getAllByTestId("kanban-column")) {
      expect(column).not.toHaveTextContent("Test Card");
    }
  });

  it("rend autant de colonnes que de listes retournées", async () => {
    const manyLists: KanbanList[] = Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      name: `List ${i + 1}`,
      order: i + 1,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    }));
    mockedGetLists.mockResolvedValue(manyLists);

    render(<KanbanBoard {...baseProps} />);

    await waitFor(() => {
      expect(screen.getAllByTestId("kanban-column")).toHaveLength(10);
    });
  });

  it("recharge les listes quand refreshTrigger change", async () => {
    const { rerender } = render(
      <KanbanBoard {...baseProps} refreshTrigger={1} />,
    );

    await waitFor(() => {
      expect(mockedGetLists).toHaveBeenCalledTimes(1);
    });

    rerender(<KanbanBoard {...baseProps} refreshTrigger={2} />);

    await waitFor(() => {
      expect(mockedGetLists).toHaveBeenCalledTimes(2);
    });
  });

  it("transmet onCreateCard aux colonnes avec l'id de la liste", async () => {
    const onCreateCard = vi.fn();

    render(<KanbanBoard {...baseProps} onCreateCard={onCreateCard} />);

    const button = await screen.findByText("create-in-2");
    button.click();

    expect(onCreateCard).toHaveBeenCalledWith(2);
  });
});
