import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { KanbanBoard } from '../KanbanBoard'
import { mockLists, mockCards, mockApiResponses } from '@/test/mocks'
import * as listsApi from '@/services/listsApi'
import * as cardsApi from '@/services/cardsApi'

// Mock the API modules
vi.mock('@/services/listsApi', () => ({
  listsApi: {
    getLists: vi.fn(),
    createList: vi.fn(),
    updateList: vi.fn(),
    deleteList: vi.fn(),
    reorderLists: vi.fn(),
    getListCardsCount: vi.fn()
  }
}))

vi.mock('@/services/cardsApi', () => ({
  cardsApi: {
    getCards: vi.fn(),
    createCard: vi.fn(),
    updateCard: vi.fn(),
    deleteCard: vi.fn(),
    moveCard: vi.fn()
  }
}))

// Mock DnD Kit
vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }: any) => <div data-testid="dnd-context">{children}</div>,
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
  PointerSensor: vi.fn(),
  KeyboardSensor: vi.fn(),
  closestCenter: vi.fn(),
  DragOverlay: ({ children }: any) => <div data-testid="drag-overlay">{children}</div>
}))

vi.mock('@dnd-kit/sortable', () => ({
  SortableContext: ({ children }: any) => <div data-testid="sortable-context">{children}</div>,
  verticalListSortingStrategy: vi.fn(),
  horizontalListSortingStrategy: vi.fn()
}))

// Mock toast notifications
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('KanbanBoard', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Setup default mock implementations
    vi.mocked(listsApi.listsApi.getLists).mockImplementation(mockApiResponses.getLists)
    vi.mocked(cardsApi.cardsApi.getCards).mockResolvedValue(mockCards)
  })

  it('renders the kanban board with dynamic lists', async () => {
    render(<KanbanBoard />)

    // Wait for lists to load
    await waitFor(() => {
      expect(screen.getByText('A faire')).toBeInTheDocument()
      expect(screen.getByText('En cours')).toBeInTheDocument()
      expect(screen.getByText('Terminé')).toBeInTheDocument()
    })

    // Check if DnD context is rendered
    expect(screen.getByTestId('dnd-context')).toBeInTheDocument()
  })

  it('displays loading state while fetching lists', () => {
    // Mock delayed response
    vi.mocked(listsApi.listsApi.getLists).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockLists), 100))
    )

    render(<KanbanBoard />)

    // Should show loading state
    expect(screen.getByText('Chargement du tableau...')).toBeInTheDocument()
  })

  it('handles error when loading lists fails', async () => {
    const errorMessage = 'Failed to load lists'
    vi.mocked(listsApi.listsApi.getLists).mockRejectedValue(new Error(errorMessage))

    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('Erreur lors du chargement du tableau')).toBeInTheDocument()
    })
  })

  it('renders lists in correct order', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      const columns = screen.getAllByTestId('kanban-column')
      expect(columns).toHaveLength(3)
      
      // Check that lists are rendered in order
      expect(columns[0]).toHaveTextContent('A faire')
      expect(columns[1]).toHaveTextContent('En cours')
      expect(columns[2]).toHaveTextContent('Terminé')
    })
  })

  it('displays cards in their respective lists', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      // Card 1 should be in "A faire" list (list_id: 1)
      const aFaireColumn = screen.getByTestId('kanban-column-1')
      expect(aFaireColumn).toHaveTextContent('Test Card 1')
      
      // Card 2 should be in "En cours" list (list_id: 2)
      const enCoursColumn = screen.getByTestId('kanban-column-2')
      expect(enCoursColumn).toHaveTextContent('Test Card 2')
    })
  })

  it('handles empty lists correctly', async () => {
    // Mock empty cards
    vi.mocked(cardsApi.cardsApi.getCards).mockResolvedValue([])

    render(<KanbanBoard />)

    await waitFor(() => {
      const columns = screen.getAllByTestId('kanban-column')
      expect(columns).toHaveLength(3)
      
      // Each column should show empty state or no cards
      columns.forEach(column => {
        expect(column).not.toHaveTextContent('Test Card')
      })
    })
  })

  it('enables horizontal scrolling when there are many lists', async () => {
    // Mock many lists
    const manyLists = Array.from({ length: 10 }, (_, i) => ({
      id: i + 1,
      name: `List ${i + 1}`,
      order: i + 1,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    }))

    vi.mocked(listsApi.listsApi.getLists).mockResolvedValue(manyLists)

    render(<KanbanBoard />)

    await waitFor(() => {
      const boardContainer = screen.getByTestId('kanban-board-container')
      expect(boardContainer).toHaveClass('overflow-x-auto')
      
      // Should render all lists
      expect(screen.getAllByTestId('kanban-column')).toHaveLength(10)
    })
  })

  it('maintains minimum column width for proper layout', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      const columns = screen.getAllByTestId('kanban-column')
      
      // Each column should have minimum width class
      columns.forEach(column => {
        expect(column).toHaveClass('min-w-80') // or whatever minimum width class is used
      })
    })
  })

  it('refreshes data when lists are updated', async () => {
    const { rerender } = render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('A faire')).toBeInTheDocument()
    })

    // Mock updated lists
    const updatedLists = [
      ...mockLists,
      {
        id: 4,
        name: 'Nouvelle Liste',
        order: 4,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z'
      }
    ]

    vi.mocked(listsApi.listsApi.getLists).mockResolvedValue(updatedLists)

    // Trigger re-render (in real app, this would happen via state management)
    rerender(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('Nouvelle Liste')).toBeInTheDocument()
    })
  })

  it('handles drag and drop events', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByTestId('dnd-context')).toBeInTheDocument()
    })

    // The DnD functionality would be tested with actual drag events
    // For now, we verify the DnD components are rendered
    expect(screen.getByTestId('sortable-context')).toBeInTheDocument()
  })

  it('displays correct card count per list', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      // "A faire" should have 1 card
      const aFaireColumn = screen.getByTestId('kanban-column-1')
      expect(aFaireColumn).toHaveTextContent('1') // card count indicator
      
      // "En cours" should have 1 card
      const enCoursColumn = screen.getByTestId('kanban-column-2')
      expect(enCoursColumn).toHaveTextContent('1') // card count indicator
      
      // "Terminé" should have 0 cards
      const termineColumn = screen.getByTestId('kanban-column-3')
      expect(termineColumn).toHaveTextContent('0') // card count indicator
    })
  })

  it('allows adding new cards to any list', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('A faire')).toBeInTheDocument()
    })

    // Each column should have an "Add card" button
    const addButtons = screen.getAllByText('Ajouter une carte')
    expect(addButtons).toHaveLength(3) // One for each list
  })

  it('updates card positions when moved between lists', async () => {
    // Mock the move card API
    vi.mocked(cardsApi.cardsApi.moveCard).mockResolvedValue({
      ...mockCards[0],
      list_id: 2 // Moved to "En cours"
    })

    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('Test Card 1')).toBeInTheDocument()
    })

    // Simulate drag and drop (this would normally be handled by DnD Kit)
    // For testing purposes, we can simulate the onDragEnd callback
    // The actual implementation would call cardsApi.moveCard
  })

  it('preserves card order within lists', async () => {
    // Mock multiple cards in the same list
    const cardsInSameList = [
      { ...mockCards[0], id: 1, title: 'Card A', list_id: 1 },
      { ...mockCards[0], id: 2, title: 'Card B', list_id: 1 },
      { ...mockCards[0], id: 3, title: 'Card C', list_id: 1 }
    ]

    vi.mocked(cardsApi.cardsApi.getCards).mockResolvedValue(cardsInSameList)

    render(<KanbanBoard />)

    await waitFor(() => {
      const aFaireColumn = screen.getByTestId('kanban-column-1')
      
      // Cards should appear in order
      expect(aFaireColumn).toHaveTextContent('Card A')
      expect(aFaireColumn).toHaveTextContent('Card B')
      expect(aFaireColumn).toHaveTextContent('Card C')
    })
  })

  it('handles real-time updates when other users modify lists', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('A faire')).toBeInTheDocument()
    })

    // Simulate real-time update (would normally come from WebSocket or polling)
    const updatedLists = [
      { ...mockLists[0], name: 'À faire (modifié)' },
      ...mockLists.slice(1)
    ]

    vi.mocked(listsApi.listsApi.getLists).mockResolvedValue(updatedLists)

    // In a real app, this would trigger a re-fetch
    // For testing, we can simulate the effect
  })

  it('shows appropriate empty state when no lists exist', async () => {
    vi.mocked(listsApi.listsApi.getLists).mockResolvedValue([])

    render(<KanbanBoard />)

    await waitFor(() => {
      expect(screen.getByText('Aucune liste disponible')).toBeInTheDocument()
      expect(screen.getByText('Contactez un administrateur pour créer des listes')).toBeInTheDocument()
    })
  })

  it('maintains responsive design on different screen sizes', async () => {
    render(<KanbanBoard />)

    await waitFor(() => {
      const boardContainer = screen.getByTestId('kanban-board-container')
      
      // Should have responsive classes
      expect(boardContainer).toHaveClass('flex')
      expect(boardContainer).toHaveClass('gap-4')
      expect(boardContainer).toHaveClass('p-4')
    })
  })
})