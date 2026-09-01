import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { KanbanColumn } from "../KanbanColumn";
import { mockLists, mockCards } from "@/test/mocks";
import i18n from "@shared/i18n";
import type { Card, KanbanList } from "@shared/types";

// La colonne s'enregistre comme zone de drop : on neutralise dnd-kit, hors sujet ici.
vi.mock("@dnd-kit/core", () => ({
  useDroppable: () => ({ setNodeRef: vi.fn(), isOver: false }),
}));

// Hook d'animation : dépend de mesures DOM indisponibles sous jsdom.
vi.mock("@shared/hooks/useElasticTransition", () => ({
  useElasticTransition: () => ({ current: null }),
}));

// On teste la colonne, pas le rendu d'une carte.
vi.mock("../CardItem", () => ({
  CardItem: ({
    card,
    onUpdate,
    onDelete,
  }: {
    card: Card;
    onUpdate: (card: Card) => void;
    onDelete: (id: number) => void;
  }) => (
    <div data-testid={`card-${card.id}`}>
      <span>{card.title}</span>
      <button type="button" onClick={() => onUpdate(card)}>
        update-{card.id}
      </button>
      <button type="button" onClick={() => onDelete(card.id)}>
        delete-{card.id}
      </button>
    </div>
  ),
}));

const baseProps = {
  id: "list-1",
  list: mockLists[0], // "A faire"
  cards: [mockCards[0]],
  onCardUpdate: vi.fn(),
  onCardDelete: vi.fn(),
  isDragging: false,
  dropTarget: null,
};

const renderColumn = (
  props: Partial<typeof baseProps> & Record<string, unknown> = {},
) => render(<KanbanColumn {...baseProps} {...props} />);

describe("KanbanColumn", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("fr");
  });

  it("affiche le nom de la liste et le nombre de cartes", () => {
    renderColumn();

    expect(
      screen.getByRole("heading", { level: 3, name: "A faire" }),
    ).toBeInTheDocument();
    expect(screen.getByText("1 carte")).toBeInTheDocument();
  });

  it("rend une carte par élément de `cards`", () => {
    const cards: Card[] = [
      { ...mockCards[0], id: 1, title: "First Card" },
      { ...mockCards[0], id: 2, title: "Second Card" },
      { ...mockCards[0], id: 3, title: "Third Card" },
    ];

    renderColumn({ cards });

    expect(screen.getByTestId("card-1")).toBeInTheDocument();
    expect(screen.getByTestId("card-2")).toBeInTheDocument();
    expect(screen.getByTestId("card-3")).toBeInTheDocument();
    expect(screen.getByText("3 cartes")).toBeInTheDocument();
  });

  it("affiche « 0 carte » pour une liste vide", () => {
    renderColumn({ cards: [] });

    expect(screen.getByText("0 carte")).toBeInTheDocument();
    expect(screen.queryByTestId("card-1")).not.toBeInTheDocument();
  });

  it("n'affiche le bouton d'ajout que si onCreateCard est fourni", () => {
    renderColumn();
    expect(
      screen.queryByRole("button", {
        name: "Créer une nouvelle carte dans cette liste",
      }),
    ).not.toBeInTheDocument();

    const onCreateCard = vi.fn();
    renderColumn({ onCreateCard });

    fireEvent.click(
      screen.getByRole("button", {
        name: "Créer une nouvelle carte dans cette liste",
      }),
    );
    expect(onCreateCard).toHaveBeenCalledWith(mockLists[0].id);
  });

  it("remonte les interactions des cartes", () => {
    const onCardUpdate = vi.fn();
    const onCardDelete = vi.fn();

    renderColumn({ onCardUpdate, onCardDelete });

    fireEvent.click(screen.getByText("update-1"));
    expect(onCardUpdate).toHaveBeenCalledWith(mockCards[0]);

    fireEvent.click(screen.getByText("delete-1"));
    expect(onCardDelete).toHaveBeenCalledWith(mockCards[0].id);
  });

  it("affiche un nom de liste arbitraire", () => {
    const list: KanbanList = { ...mockLists[0], name: "Liste Personnalisée" };

    renderColumn({ list });

    expect(screen.getByText("Liste Personnalisée")).toBeInTheDocument();
  });

  it("passe en rendu compact quand la liste est repliée", () => {
    const list: KanbanList = { ...mockLists[0], is_collapsed: true };

    const { container } = renderColumn({ list });

    expect(container.querySelector(".kanban-column-collapsed")).not.toBeNull();
    // Le nom reste affiché, mais à la verticale, et sans bouton d'ajout.
    expect(screen.getByText("A faire")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", {
        name: "Créer une nouvelle carte dans cette liste",
      }),
    ).not.toBeInTheDocument();
  });

  it("expose la colonne comme zone de drop via son id de liste", () => {
    const { container } = renderColumn();

    expect(container.querySelector('[data-list-id="list-1"]')).not.toBeNull();
  });
});
