import { KanbanList, Card } from '@/types'

export const mockLists: KanbanList[] = [
  {
    id: 1,
    name: 'A faire',
    order: 1,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    name: 'En cours',
    order: 2,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 3,
    name: 'Terminé',
    order: 3,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
]

export const mockCards: Card[] = [
  {
    id: 1,
    title: 'Test Card 1',
    description: 'Description 1',
    list_id: 1,
    priority: 'medium',
    due_date: null,
    assignee_id: 1,
    created_by: 1,
    is_archived: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  },
  {
    id: 2,
    title: 'Test Card 2',
    description: 'Description 2',
    list_id: 2,
    priority: 'high',
    due_date: '2024-12-31',
    assignee_id: 1,
    created_by: 1,
    is_archived: false,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
  }
]

export const mockUser = {
  id: 1,
  email: 'test@example.com',
  display_name: 'Test User',
  role: 'admin',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z'
}

// Mock API responses
export const mockApiResponses = {
  getLists: () => Promise.resolve(mockLists),
  createList: (data: any) => Promise.resolve({
    id: 4,
    ...data,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  }),
  updateList: (id: number, data: any) => {
    const list = mockLists.find(l => l.id === id)
    if (!list) throw new Error('List not found')
    return Promise.resolve({ ...list, ...data, updated_at: new Date().toISOString() })
  },
  deleteList: () => Promise.resolve(),
  reorderLists: () => Promise.resolve(),
  getListCardsCount: (id: number) => Promise.resolve({
    list_id: id,
    list_name: mockLists.find(l => l.id === id)?.name || 'Unknown',
    cards_count: mockCards.filter(c => c.list_id === id).length
  })
}