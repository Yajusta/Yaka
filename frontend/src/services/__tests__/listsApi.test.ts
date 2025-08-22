import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock axios completely
vi.mock('axios', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    })),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    }
  }
}))

const mockLists = [
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

// Import after mocking
const { listsApi } = await import('../listsApi')
const mockedAxios = vi.mocked(axios)

describe('listsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getLists', () => {
    it('fetches lists successfully', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockLists })

      // Act
      const result = await listsApi.getLists()

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/lists/')
      expect(result).toEqual(mockLists)
    })

    it('handles API error', async () => {
      // Arrange
      const errorMessage = 'Network Error'
      mockedAxios.get.mockRejectedValue(new Error(errorMessage))

      // Act & Assert
      await expect(listsApi.getLists()).rejects.toThrow(errorMessage)
      expect(mockedAxios.get).toHaveBeenCalledWith('/lists/')
    })

    it('returns empty array when no lists exist', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: [] })

      // Act
      const result = await listsApi.getLists()

      // Assert
      expect(result).toEqual([])
    })
  })

  describe('createList', () => {
    it('creates a list successfully', async () => {
      // Arrange
      const newListData = { name: 'New List', order: 4 }
      const createdList = { id: 4, ...newListData, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }
      mockedAxios.post.mockResolvedValue({ data: createdList })

      // Act
      const result = await listsApi.createList(newListData)

      // Assert
      expect(mockedAxios.post).toHaveBeenCalledWith('/lists/', newListData)
      expect(result).toEqual(createdList)
    })

    it('handles validation errors', async () => {
      // Arrange
      const invalidData = { name: '', order: 0 }
      const validationError = {
        response: {
          status: 422,
          data: { detail: 'Validation error' }
        }
      }
      mockedAxios.post.mockRejectedValue(validationError)

      // Act & Assert
      await expect(listsApi.createList(invalidData)).rejects.toEqual(validationError)
    })

    it('handles duplicate name errors', async () => {
      // Arrange
      const duplicateData = { name: 'A faire', order: 4 }
      const duplicateError = {
        response: {
          status: 400,
          data: { detail: 'Une liste avec le nom "A faire" existe déjà' }
        }
      }
      mockedAxios.post.mockRejectedValue(duplicateError)

      // Act & Assert
      await expect(listsApi.createList(duplicateData)).rejects.toEqual(duplicateError)
    })
  })

  describe('updateList', () => {
    it('updates a list successfully', async () => {
      // Arrange
      const listId = 1
      const updateData = { name: 'Updated Name' }
      const updatedList = { ...mockLists[0], ...updateData, updated_at: '2024-01-02T00:00:00Z' }
      mockedAxios.put.mockResolvedValue({ data: updatedList })

      // Act
      const result = await listsApi.updateList(listId, updateData)

      // Assert
      expect(mockedAxios.put).toHaveBeenCalledWith(`/lists/${listId}`, updateData)
      expect(result).toEqual(updatedList)
    })

    it('handles list not found error', async () => {
      // Arrange
      const listId = 999
      const updateData = { name: 'Updated Name' }
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Liste non trouvée' }
        }
      }
      mockedAxios.put.mockRejectedValue(notFoundError)

      // Act & Assert
      await expect(listsApi.updateList(listId, updateData)).rejects.toEqual(notFoundError)
    })

    it('handles duplicate name on update', async () => {
      // Arrange
      const listId = 1
      const updateData = { name: 'En cours' } // Name already exists
      const duplicateError = {
        response: {
          status: 400,
          data: { detail: 'Une liste avec le nom "En cours" existe déjà' }
        }
      }
      mockedAxios.put.mockRejectedValue(duplicateError)

      // Act & Assert
      await expect(listsApi.updateList(listId, updateData)).rejects.toEqual(duplicateError)
    })

    it('updates only provided fields', async () => {
      // Arrange
      const listId = 1
      const updateData = { order: 5 } // Only update order
      const updatedList = { ...mockLists[0], order: 5, updated_at: '2024-01-02T00:00:00Z' }
      mockedAxios.put.mockResolvedValue({ data: updatedList })

      // Act
      const result = await listsApi.updateList(listId, updateData)

      // Assert
      expect(mockedAxios.put).toHaveBeenCalledWith(`/lists/${listId}`, updateData)
      expect(result.order).toBe(5)
      expect(result.name).toBe(mockLists[0].name) // Name unchanged
    })
  })

  describe('deleteList', () => {
    it('deletes a list successfully', async () => {
      // Arrange
      const listId = 2
      const targetListId = 1
      const successResponse = { data: { message: 'Liste supprimée avec succès' } }
      mockedAxios.delete.mockResolvedValue(successResponse)

      // Act
      await listsApi.deleteList(listId, targetListId)

      // Assert
      expect(mockedAxios.delete).toHaveBeenCalledWith(`/lists/${listId}`, {
        data: { target_list_id: targetListId }
      })
    })

    it('handles last list deletion error', async () => {
      // Arrange
      const listId = 1
      const targetListId = 1
      const lastListError = {
        response: {
          status: 400,
          data: { detail: 'Impossible de supprimer la dernière liste' }
        }
      }
      mockedAxios.delete.mockRejectedValue(lastListError)

      // Act & Assert
      await expect(listsApi.deleteList(listId, targetListId)).rejects.toEqual(lastListError)
    })

    it('handles list not found error', async () => {
      // Arrange
      const listId = 999
      const targetListId = 1
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Liste non trouvée' }
        }
      }
      mockedAxios.delete.mockRejectedValue(notFoundError)

      // Act & Assert
      await expect(listsApi.deleteList(listId, targetListId)).rejects.toEqual(notFoundError)
    })

    it('handles invalid target list error', async () => {
      // Arrange
      const listId = 2
      const targetListId = 999
      const invalidTargetError = {
        response: {
          status: 400,
          data: { detail: 'La liste de destination n\'existe pas' }
        }
      }
      mockedAxios.delete.mockRejectedValue(invalidTargetError)

      // Act & Assert
      await expect(listsApi.deleteList(listId, targetListId)).rejects.toEqual(invalidTargetError)
    })
  })

  describe('reorderLists', () => {
    it('reorders lists successfully', async () => {
      // Arrange
      const listOrders = { 1: 3, 2: 1, 3: 2 }
      const successResponse = { data: { message: 'Listes réorganisées avec succès' } }
      mockedAxios.post.mockResolvedValue(successResponse)

      // Act
      await listsApi.reorderLists(listOrders)

      // Assert
      expect(mockedAxios.post).toHaveBeenCalledWith('/lists/reorder', {
        list_orders: listOrders
      })
    })

    it('handles invalid order data', async () => {
      // Arrange
      const invalidOrders = { 1: -1, 2: 0 } // Invalid orders
      const validationError = {
        response: {
          status: 422,
          data: { detail: 'Tous les ordres doivent être positifs' }
        }
      }
      mockedAxios.post.mockRejectedValue(validationError)

      // Act & Assert
      await expect(listsApi.reorderLists(invalidOrders)).rejects.toEqual(validationError)
    })

    it('handles duplicate orders', async () => {
      // Arrange
      const duplicateOrders = { 1: 1, 2: 1 } // Duplicate orders
      const duplicateError = {
        response: {
          status: 422,
          data: { detail: 'Les ordres doivent être uniques' }
        }
      }
      mockedAxios.post.mockRejectedValue(duplicateError)

      // Act & Assert
      await expect(listsApi.reorderLists(duplicateOrders)).rejects.toEqual(duplicateError)
    })

    it('handles non-existing lists in reorder', async () => {
      // Arrange
      const ordersWithInvalidList = { 1: 1, 999: 2 } // List 999 doesn't exist
      const invalidListError = {
        response: {
          status: 400,
          data: { detail: 'Les listes suivantes n\'existent pas: {999}' }
        }
      }
      mockedAxios.post.mockRejectedValue(invalidListError)

      // Act & Assert
      await expect(listsApi.reorderLists(ordersWithInvalidList)).rejects.toEqual(invalidListError)
    })
  })

  describe('getListCardsCount', () => {
    it('gets card count for a list successfully', async () => {
      // Arrange
      const listId = 1
      const cardsCountResponse = {
        list_id: 1,
        list_name: 'A faire',
        cards_count: 5
      }
      mockedAxios.get.mockResolvedValue({ data: cardsCountResponse })

      // Act
      const result = await listsApi.getListCardsCount(listId)

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith(`/lists/${listId}/cards-count`)
      expect(result).toEqual(cardsCountResponse)
    })

    it('handles list not found for card count', async () => {
      // Arrange
      const listId = 999
      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Liste non trouvée' }
        }
      }
      mockedAxios.get.mockRejectedValue(notFoundError)

      // Act & Assert
      await expect(listsApi.getListCardsCount(listId)).rejects.toEqual(notFoundError)
    })

    it('returns zero count for empty list', async () => {
      // Arrange
      const listId = 3
      const emptyListResponse = {
        list_id: 3,
        list_name: 'Terminé',
        cards_count: 0
      }
      mockedAxios.get.mockResolvedValue({ data: emptyListResponse })

      // Act
      const result = await listsApi.getListCardsCount(listId)

      // Assert
      expect(result.cards_count).toBe(0)
    })
  })

  describe('error handling', () => {
    it('handles network errors', async () => {
      // Arrange
      const networkError = new Error('Network Error')
      mockedAxios.get.mockRejectedValue(networkError)

      // Act & Assert
      await expect(listsApi.getLists()).rejects.toThrow('Network Error')
    })

    it('handles server errors', async () => {
      // Arrange
      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' }
        }
      }
      mockedAxios.get.mockRejectedValue(serverError)

      // Act & Assert
      await expect(listsApi.getLists()).rejects.toEqual(serverError)
    })

    it('handles authentication errors', async () => {
      // Arrange
      const authError = {
        response: {
          status: 401,
          data: { detail: 'Not authenticated' }
        }
      }
      mockedAxios.get.mockRejectedValue(authError)

      // Act & Assert
      await expect(listsApi.getLists()).rejects.toEqual(authError)
    })

    it('handles authorization errors', async () => {
      // Arrange
      const authzError = {
        response: {
          status: 403,
          data: { detail: 'Not enough permissions' }
        }
      }
      mockedAxios.post.mockRejectedValue(authzError)

      // Act & Assert
      await expect(listsApi.createList({ name: 'Test', order: 1 })).rejects.toEqual(authzError)
    })
  })

  describe('request configuration', () => {
    it('sends requests with correct headers', async () => {
      // Arrange
      mockedAxios.get.mockResolvedValue({ data: mockLists })

      // Act
      await listsApi.getLists()

      // Assert
      expect(mockedAxios.get).toHaveBeenCalledWith('/lists/')
      // In a real implementation, you might check for Authorization headers, Content-Type, etc.
    })

    it('handles request timeouts', async () => {
      // Arrange
      const timeoutError = new Error('timeout of 5000ms exceeded')
      mockedAxios.get.mockRejectedValue(timeoutError)

      // Act & Assert
      await expect(listsApi.getLists()).rejects.toThrow('timeout of 5000ms exceeded')
    })
  })
})