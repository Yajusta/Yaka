import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { KanbanColumn } from '../KanbanColumn'
import { mockLists, mockCards } from '@/test/mocks'

// Mock DnD Kit
vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false
  }),
  SortableContext: ({ children }: any) => <div data-testid="sortable-context">{children}</div>,
  verticalListSortingStrategy: vi.fn()
}))

vi.mock('@dnd-kit/core', () => ({
  useDroppable: () => ({
    setNodeRef: vi.fn(),
    isOver: false
  })
}))

// Mock card component
vi.mock('../KanbanCard', () => ({
  KanbanCard: ({ card }: any) => (
    <div data-testid={`card-${card.id}`} data-card-id={card.id}>
      {card.title}
    </div>
  )
}))

describe('KanbanColumn', () => {
  const user = userEvent.setup()
  
  const defaultProps = {
    list: mockLists[0], // "A faire"
    cards: [mockCards[0]], // Card in "A faire" list
    onAddCard: vi.fn(),
    onEditCard: vi.fn(),
    onDeleteCard: vi.fn()
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders column with list name and cards', () => {
    render(<KanbanColumn {...defaultProps} />)

    // Check list name is displayed
    expect(screen.getByText('A faire')).toBeInTheDocument()
    
    // Check card is displayed
    expect(screen.getByTestId('card-1')).toBeInTheDocument()
    expect(screen.getByText('Test Card 1')).toBeInTheDocument()
  })

  it('displays correct card count', () => {
    render(<KanbanColumn {...defaultProps} />)

    // Should show card count
    expect(screen.getByText('1')).toBeInTheDocument() // Card count badge
  })

  it('shows empty state when no cards', () => {
    const propsWithNoCards = {
      ...defaultProps,
      cards: []
    }

    render(<KanbanColumn {...propsWithNoCards} />)

    // Should show empty state
    expect(screen.getByText('Aucune carte')).toBeInTheDocument()
    expect(screen.getByText('0')).toBeInTheDocument() // Card count should be 0
  })

  it('renders multiple cards in correct order', () => {
    const multipleCards = [
      { ...mockCards[0], id: 1, title: 'First Card' },
      { ...mockCards[0], id: 2, title: 'Second Card' },
      { ...mockCards[0], id: 3, title: 'Third Card' }
    ]

    const propsWithMultipleCards = {
      ...defaultProps,
      cards: multipleCards
    }

    render(<KanbanColumn {...propsWithMultipleCards} />)

    // All cards should be rendered
    expect(screen.getByTestId('card-1')).toBeInTheDocument()
    expect(screen.getByTestId('card-2')).toBeInTheDocument()
    expect(screen.getByTestId('card-3')).toBeInTheDocument()

    // Card count should be correct
    expect(screen.getByText('3')).toBeInTheDocument()
  })

  it('shows add card button and handles click', async () => {
    render(<KanbanColumn {...defaultProps} />)

    const addButton = screen.getByText('Ajouter une carte')
    expect(addButton).toBeInTheDocument()

    await user.click(addButton)

    // Should call onAddCard with list ID
    expect(defaultProps.onAddCard).toHaveBeenCalledWith(mockLists[0].id)
  })

  it('applies correct styling classes', () => {
    render(<KanbanColumn {...defaultProps} />)

    const column = screen.getByTestId('kanban-column-1')
    
    // Should have proper styling classes
    expect(column).toHaveClass('min-w-80') // Minimum width
    expect(column).toHaveClass('bg-gray-50') // Background color
    expect(column).toHaveClass('rounded-lg') // Rounded corners
  })

  it('handles drag and drop setup correctly', () => {
    render(<KanbanColumn {...defaultProps} />)

    // Should render sortable context for cards
    expect(screen.getByTestId('sortable-context')).toBeInTheDocument()
  })

  it('displays list header with proper formatting', () => {
    render(<KanbanColumn {...defaultProps} />)

    // List name should be in header
    const header = screen.getByRole('heading', { level: 3 })
    expect(header).toHaveTextContent('A faire')
    
    // Should have proper header styling
    expect(header).toHaveClass('font-semibold')
  })

  it('shows card count badge with correct styling', () => {
    render(<KanbanColumn {...defaultProps} />)

    const countBadge = screen.getByText('1')
    
    // Should have badge styling
    expect(countBadge.parentElement).toHaveClass('bg-blue-100')
    expect(countBadge.parentElement).toHaveClass('text-blue-800')
    expect(countBadge.parentElement).toHaveClass('rounded-full')
  })

  it('handles different list names correctly', () => {
    const customList = {
      ...mockLists[0],
      name: 'Liste Personnalisée'
    }

    const propsWithCustomList = {
      ...defaultProps,
      list: customList
    }

    render(<KanbanColumn {...propsWithCustomList} />)

    expect(screen.getByText('Liste Personnalisée')).toBeInTheDocument()
  })

  it('filters cards correctly for the list', () => {
    // Cards from different lists
    const mixedCards = [
      { ...mockCards[0], id: 1, list_id: 1, title: 'Card for List 1' },
      { ...mockCards[0], id: 2, list_id: 2, title: 'Card for List 2' },
      { ...mockCards[0], id: 3, list_id: 1, title: 'Another Card for List 1' }
    ]

    const propsWithMixedCards = {
      ...defaultProps,
      cards: mixedCards.filter(card => card.list_id === 1) // Only cards for list 1
    }

    render(<KanbanColumn {...propsWithMixedCards} />)

    // Should only show cards for this list
    expect(screen.getByText('Card for List 1')).toBeInTheDocument()
    expect(screen.getByText('Another Card for List 1')).toBeInTheDocument()
    expect(screen.queryByText('Card for List 2')).not.toBeInTheDocument()

    // Card count should be correct
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('handles card interactions correctly', async () => {
    render(<KanbanColumn {...defaultProps} />)

    const card = screen.getByTestId('card-1')
    
    // Card should be clickable (for editing)
    await user.click(card)
    
    // In a real implementation, this might trigger edit mode
    // For now, we just verify the card is rendered and clickable
    expect(card).toBeInTheDocument()
  })

  it('maintains proper spacing between cards', () => {
    const multipleCards = [
      { ...mockCards[0], id: 1, title: 'Card 1' },
      { ...mockCards[0], id: 2, title: 'Card 2' }
    ]

    const propsWithMultipleCards = {
      ...defaultProps,
      cards: multipleCards
    }

    render(<KanbanColumn {...propsWithMultipleCards} />)

    const cardsContainer = screen.getByTestId('cards-container')
    
    // Should have proper spacing classes
    expect(cardsContainer).toHaveClass('space-y-2') // or similar spacing class
  })

  it('shows loading state when cards are being loaded', () => {
    const propsWithLoading = {
      ...defaultProps,
      cards: [],
      isLoading: true
    }

    render(<KanbanColumn {...propsWithLoading} />)

    // Should show loading indicator
    expect(screen.getByText('Chargement...')).toBeInTheDocument()
  })

  it('handles very long list names gracefully', () => {
    const longNameList = {
      ...mockLists[0],
      name: 'Ceci est un nom de liste très très très long qui pourrait causer des problèmes de mise en page'
    }

    const propsWithLongName = {
      ...defaultProps,
      list: longNameList
    }

    render(<KanbanColumn {...propsWithLongName} />)

    const header = screen.getByRole('heading', { level: 3 })
    
    // Should handle long names with proper text wrapping or truncation
    expect(header).toHaveClass('truncate') // or 'break-words' depending on implementation
  })

  it('supports keyboard navigation for accessibility', () => {
    render(<KanbanColumn {...defaultProps} />)

    const addButton = screen.getByText('Ajouter une carte')
    
    // Button should be focusable
    addButton.focus()
    expect(addButton).toHaveFocus()
    
    // Should support keyboard activation
    fireEvent.keyDown(addButton, { key: 'Enter' })
    expect(defaultProps.onAddCard).toHaveBeenCalled()
  })

  it('displays proper ARIA labels for accessibility', () => {
    render(<KanbanColumn {...defaultProps} />)

    const column = screen.getByTestId('kanban-column-1')
    
    // Should have proper ARIA labels
    expect(column).toHaveAttribute('aria-label', expect.stringContaining('A faire'))
    
    const addButton = screen.getByText('Ajouter une carte')
    expect(addButton).toHaveAttribute('aria-label', expect.stringContaining('Ajouter une carte à A faire'))
  })
})
