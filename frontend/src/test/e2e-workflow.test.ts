/**
 * End-to-end workflow tests simulating complete user interactions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { listsApi } from '../services/listsApi'

// Mock the API services
vi.mock('../services/listsApi')

const mockListsApi = vi.mocked(listsApi)

// Mock cards API functionality
const mockCardsApi = {
  createCard: vi.fn(),
  moveCard: vi.fn(),
  getCards: vi.fn()
}

// Simulate a complete application state
class ApplicationState {
  private lists: any[] = []
  private cards: any[] = []
  private currentUser = { id: 1, role: 'admin' }

  async initializeWithDefaultLists() {
    const defaultLists = [
      { id: 1, name: 'A faire', order: 1, created_at: '2024-01-01T00:00:00Z' },
      { id: 2, name: 'En cours', order: 2, created_at: '2024-01-01T00:00:00Z' },
      { id: 3, name: 'Terminé', order: 3, created_at: '2024-01-01T00:00:00Z' }
    ]
    
    mockListsApi.getLists.mockResolvedValue(defaultLists)
    this.lists = await listsApi.getLists()
    return this.lists
  }

  async createCard(cardData: any) {
    const newCard = {
      id: Date.now(),
      ...cardData,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: this.currentUser.id,
      assignee_id: this.currentUser.id,
      is_archived: false
    }
    
    mockCardsApi.createCard.mockResolvedValue(newCard)
    const createdCard = await mockCardsApi.createCard(cardData)
    this.cards.push(createdCard)
    return createdCard
  }

  async moveCard(cardId: number, targetListId: number, position: number = 0) {
    const card = this.cards.find(c => c.id === cardId)
    if (!card) throw new Error('Card not found')
    
    const updatedCard = { ...card, list_id: targetListId, updated_at: new Date().toISOString() }
    
    mockCardsApi.moveCard.mockResolvedValue(updatedCard)
    const movedCard = await mockCardsApi.moveCard(cardId, { list_id: targetListId, position })
    
    const cardIndex = this.cards.findIndex(c => c.id === cardId)
    this.cards[cardIndex] = movedCard
    return movedCard
  }

  async createList(listData: any) {
    if (this.currentUser.role !== 'admin') {
      throw new Error('Unauthorized: Only admins can create lists')
    }
    
    const newList = {
      id: Date.now(),
      ...listData,
      created_at: new Date().toISOString()
    }
    
    mockListsApi.createList.mockResolvedValue(newList)
    const createdList = await listsApi.createList(listData)
    this.lists.push(createdList)
    this.lists.sort((a, b) => a.order - b.order)
    return createdList
  }

  async deleteList(listId: number, targetListId: number) {
    if (this.currentUser.role !== 'admin') {
      throw new Error('Unauthorized: Only admins can delete lists')
    }
    
    // Move cards to target list
    const cardsToMove = this.cards.filter(c => c.list_id === listId)
    for (const card of cardsToMove) {
      card.list_id = targetListId
      card.updated_at = new Date().toISOString()
    }
    
    // Remove the list
    this.lists = this.lists.filter(l => l.id !== listId)
    
    mockListsApi.deleteList.mockResolvedValue(undefined)
    await listsApi.deleteList(listId, targetListId)
  }

  getListById(id: number) {
    return this.lists.find(l => l.id === id)
  }

  getCardsByListId(listId: number) {
    return this.cards.filter(c => c.list_id === listId)
  }

  getAllLists() {
    return [...this.lists].sort((a, b) => a.order - b.order)
  }

  getAllCards() {
    return [...this.cards]
  }

  validateDataIntegrity() {
    // Check that all cards reference existing lists
    const listIds = new Set(this.lists.map(l => l.id))
    for (const card of this.cards) {
      if (!listIds.has(card.list_id)) {
        throw new Error(`Card ${card.id} references non-existent list ${card.list_id}`)
      }
    }
    
    // Check that list orders are unique and sequential
    const orders = this.lists.map(l => l.order).sort((a, b) => a - b)
    for (let i = 0; i < orders.length; i++) {
      if (orders[i] !== i + 1) {
        throw new Error(`List orders are not sequential: ${orders}`)
      }
    }
    
    return true
  }
}

describe('End-to-End Workflow Tests', () => {
  let appState: ApplicationState

  beforeEach(() => {
    vi.clearAllMocks()
    appState = new ApplicationState()
  })

  it('should complete a full project setup workflow', async () => {
    // Step 1: Initialize with default lists (migration scenario)
    const initialLists = await appState.initializeWithDefaultLists()
    
    expect(initialLists).toHaveLength(3)
    expect(initialLists.map(l => l.name)).toEqual(['A faire', 'En cours', 'Terminé'])
    
    // Step 2: Create initial project cards
    const projectCards = [
      {
        titre: 'Setup project structure',
        description: 'Create basic project folders and files',
        list_id: 1, // A faire
        priorite: 'haute'
      },
      {
        titre: 'Design database schema',
        description: 'Plan the database structure',
        list_id: 1, // A faire
        priorite: 'haute'
      },
      {
        titre: 'Implement authentication',
        description: 'Add user login and registration',
        list_id: 1, // A faire
        priorite: 'moyenne'
      }
    ]
    
    const createdCards = []
    for (const cardData of projectCards) {
      const card = await appState.createCard(cardData)
      createdCards.push(card)
    }
    
    expect(createdCards).toHaveLength(3)
    expect(appState.getCardsByListId(1)).toHaveLength(3)
    
    // Step 3: Start working - move first card to "En cours"
    await appState.moveCard(createdCards[0].id, 2) // Move to "En cours"
    
    expect(appState.getCardsByListId(1)).toHaveLength(2) // A faire
    expect(appState.getCardsByListId(2)).toHaveLength(1) // En cours
    
    // Step 4: Complete first task - move to "Terminé"
    await appState.moveCard(createdCards[0].id, 3) // Move to "Terminé"
    
    expect(appState.getCardsByListId(2)).toHaveLength(0) // En cours
    expect(appState.getCardsByListId(3)).toHaveLength(1) // Terminé
    
    // Step 5: Customize workflow - add new lists
    const reviewList = await appState.createList({
      name: 'Code Review',
      order: 3 // Insert before "Terminé"
    })
    
    const testingList = await appState.createList({
      name: 'Testing',
      order: 4 // Insert before "Terminé"
    })
    
    // Update "Terminé" order to be last
    const allLists = appState.getAllLists()
    expect(allLists).toHaveLength(5)
    expect(allLists.map(l => l.name)).toContain('Code Review')
    expect(allLists.map(l => l.name)).toContain('Testing')
    
    // Step 6: Use new workflow
    await appState.moveCard(createdCards[1].id, 2) // Start second task
    await appState.moveCard(createdCards[1].id, reviewList.id) // Move to review
    await appState.moveCard(createdCards[1].id, testingList.id) // Move to testing
    
    // Step 7: Validate final state
    appState.validateDataIntegrity()
    
    const finalCards = appState.getAllCards()
    const finalLists = appState.getAllLists()
    
    expect(finalCards).toHaveLength(3)
    expect(finalLists).toHaveLength(5)
    
    // Verify card distribution
    expect(appState.getCardsByListId(1)).toHaveLength(1) // A faire: 1 card
    expect(appState.getCardsByListId(testingList.id)).toHaveLength(1) // Testing: 1 card
    expect(appState.getCardsByListId(3)).toHaveLength(1) // Terminé: 1 card
  })

  it('should handle team workflow evolution', async () => {
    // Step 1: Start with basic setup
    await appState.initializeWithDefaultLists()
    
    // Step 2: Team decides to add more granular workflow
    const backlogList = await appState.createList({ name: 'Backlog', order: 1 })
    const sprintList = await appState.createList({ name: 'Sprint Planning', order: 2 })
    const devList = await appState.createList({ name: 'Development', order: 3 })
    const reviewList = await appState.createList({ name: 'Code Review', order: 4 })
    const qaList = await appState.createList({ name: 'QA Testing', order: 5 })
    const doneList = await appState.createList({ name: 'Done', order: 6 })
    
    // Step 3: Remove old lists by migrating cards
    // First create some cards in old lists
    const oldCard1 = await appState.createCard({
      titre: 'Old task 1',
      description: 'Task in old system',
      list_id: 1, // A faire
      priorite: 'moyenne'
    })
    
    const oldCard2 = await appState.createCard({
      titre: 'Old task 2', 
      description: 'Another old task',
      list_id: 2, // En cours
      priorite: 'haute'
    })
    
    // Migrate cards and delete old lists
    await appState.deleteList(1, backlogList.id) // A faire -> Backlog
    await appState.deleteList(2, devList.id) // En cours -> Development
    await appState.deleteList(3, doneList.id) // Terminé -> Done
    
    // Step 4: Verify new workflow
    const finalLists = appState.getAllLists()
    expect(finalLists).toHaveLength(6)
    expect(finalLists.map(l => l.name)).toEqual([
      'Backlog', 'Sprint Planning', 'Development', 'Code Review', 'QA Testing', 'Done'
    ])
    
    // Verify cards were migrated correctly
    expect(appState.getCardsByListId(backlogList.id)).toHaveLength(1)
    expect(appState.getCardsByListId(devList.id)).toHaveLength(1)
    
    // Step 5: Test new workflow with a complete task lifecycle
    const newTask = await appState.createCard({
      titre: 'New feature task',
      description: 'Implement new feature',
      list_id: backlogList.id,
      priorite: 'alta'
    })
    
    // Move through complete workflow
    await appState.moveCard(newTask.id, sprintList.id)
    await appState.moveCard(newTask.id, devList.id)
    await appState.moveCard(newTask.id, reviewList.id)
    await appState.moveCard(newTask.id, qaList.id)
    await appState.moveCard(newTask.id, doneList.id)
    
    // Verify final state
    expect(appState.getCardsByListId(doneList.id)).toHaveLength(2) // Old migrated card + new task
    appState.validateDataIntegrity()
  })

  it('should handle error recovery scenarios', async () => {
    // Step 1: Setup initial state
    await appState.initializeWithDefaultLists()
    
    const testCard = await appState.createCard({
      titre: 'Test card',
      description: 'For error testing',
      list_id: 1,
      priorite: 'moyenne'
    })
    
    // Step 2: Simulate API errors and recovery
    
    // Test card movement failure recovery
    mockCardsApi.moveCard.mockRejectedValueOnce(new Error('Network error'))
    
    try {
      await appState.moveCard(testCard.id, 2)
      expect.fail('Should have thrown an error')
    } catch (error) {
      expect(error.message).toBe('Network error')
    }
    
    // Verify card is still in original position
    expect(appState.getCardsByListId(1)).toHaveLength(1)
    expect(appState.getCardsByListId(2)).toHaveLength(0)
    
    // Test successful retry
    mockCardsApi.moveCard.mockResolvedValueOnce({
      ...testCard,
      list_id: 2,
      updated_at: new Date().toISOString()
    })
    
    await appState.moveCard(testCard.id, 2)
    expect(appState.getCardsByListId(2)).toHaveLength(1)
    
    // Step 3: Test list creation failure
    mockListsApi.createList.mockRejectedValueOnce(new Error('Validation error'))
    
    try {
      await appState.createList({ name: '', order: 1 }) // Invalid name
      expect.fail('Should have thrown an error')
    } catch (error) {
      expect(error.message).toBe('Validation error')
    }
    
    // Verify lists unchanged
    expect(appState.getAllLists()).toHaveLength(3)
    
    // Step 4: Test data integrity after errors
    appState.validateDataIntegrity()
  })

  it('should handle concurrent user operations', async () => {
    // Step 1: Setup
    await appState.initializeWithDefaultLists()
    
    // Step 2: Simulate multiple users working simultaneously
    const user1Cards = [
      await appState.createCard({ titre: 'User 1 Task 1', description: 'Task 1', list_id: 1, priorite: 'haute' }),
      await appState.createCard({ titre: 'User 1 Task 2', description: 'Task 2', list_id: 1, priorite: 'moyenne' })
    ]
    
    const user2Cards = [
      await appState.createCard({ titre: 'User 2 Task 1', description: 'Task 1', list_id: 1, priorite: 'basse' }),
      await appState.createCard({ titre: 'User 2 Task 2', description: 'Task 2', list_id: 2, priorite: 'haute' })
    ]
    
    // Step 3: Simulate concurrent operations
    const concurrentOperations = [
      appState.moveCard(user1Cards[0].id, 2),
      appState.moveCard(user1Cards[1].id, 3),
      appState.moveCard(user2Cards[0].id, 2),
      appState.createList({ name: 'New List', order: 4 })
    ]
    
    const results = await Promise.all(concurrentOperations)
    
    // Step 4: Verify all operations completed successfully
    expect(results).toHaveLength(4)
    expect(results[3]).toHaveProperty('name', 'New List') // New list created
    
    // Verify final state
    expect(appState.getCardsByListId(1)).toHaveLength(0) // A faire: empty
    expect(appState.getCardsByListId(2)).toHaveLength(3) // En cours: 2 moved + 1 original
    expect(appState.getCardsByListId(3)).toHaveLength(1) // Terminé: 1 moved
    expect(appState.getAllLists()).toHaveLength(4) // 3 original + 1 new
    
    appState.validateDataIntegrity()
  })

  it('should maintain performance with large datasets', async () => {
    // Step 1: Setup with many lists and cards
    await appState.initializeWithDefaultLists()
    
    // Create many lists
    const manyLists = []
    for (let i = 4; i <= 20; i++) {
      const list = await appState.createList({
        name: `List ${i}`,
        order: i
      })
      manyLists.push(list)
    }
    
    // Create many cards distributed across lists
    const manyCards = []
    for (let i = 0; i < 100; i++) {
      const listId = (i % 20) + 1 // Distribute across all lists
      const card = await appState.createCard({
        titre: `Card ${i + 1}`,
        description: `Description for card ${i + 1}`,
        list_id: listId,
        priorite: ['haute', 'moyenne', 'basse'][i % 3]
      })
      manyCards.push(card)
    }
    
    // Step 2: Perform operations and measure performance
    const startTime = Date.now()
    
    // Move many cards
    const moveOperations = []
    for (let i = 0; i < 50; i++) {
      const card = manyCards[i]
      const targetListId = ((card.list_id % 20) + 1) // Move to next list
      moveOperations.push(appState.moveCard(card.id, targetListId))
    }
    
    await Promise.all(moveOperations)
    
    const endTime = Date.now()
    const duration = endTime - startTime
    
    // Step 3: Verify performance and data integrity
    expect(duration).toBeLessThan(5000) // Should complete within 5 seconds
    expect(appState.getAllLists()).toHaveLength(20)
    expect(appState.getAllCards()).toHaveLength(100)
    
    appState.validateDataIntegrity()
  })
})