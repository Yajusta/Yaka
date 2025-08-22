// Mock data for Kanban application preview
export const mockUsers = [
  {
    id: 1,
    prenom: "Marie",
    nom: "Dubois",
    email: "marie.dubois@example.com",
    role: "admin" as const
  },
  {
    id: 2,
    prenom: "Pierre",
    nom: "Martin",
    email: "pierre.martin@example.com",
    role: "user" as const
  },
  {
    id: 3,
    prenom: "Sophie",
    nom: "Bernard",
    email: "sophie.bernard@example.com",
    role: "user" as const
  }
];

export const mockLabels = [
  {
    id: 1,
    nom: "Urgent",
    couleur: "#ef4444"
  },
  {
    id: 2,
    nom: "Bug",
    couleur: "#f97316"
  },
  {
    id: 3,
    nom: "Feature",
    couleur: "#3b82f6"
  },
  {
    id: 4,
    nom: "Documentation",
    couleur: "#10b981"
  }
];

export const mockCards = [
  {
    id: 1,
    titre: "Implémenter l'authentification utilisateur",
    description: "Créer le système de connexion et d'inscription avec validation des données",
    priorite: "high" as const,
    statut: "a_faire" as const,
    date_echeance: "2024-02-15",
    assignee_id: 2,
    assignee: mockUsers[1],
    labels: [mockLabels[2], mockLabels[0]],
    created_at: "2024-01-15T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z"
  },
  {
    id: 2,
    titre: "Corriger le bug de synchronisation",
    description: "Les données ne se synchronisent pas correctement entre les différents clients",
    priorite: "high" as const,
    statut: "en_cours" as const,
    date_echeance: "2024-02-10",
    assignee_id: 1,
    assignee: mockUsers[0],
    labels: [mockLabels[1], mockLabels[0]],
    created_at: "2024-01-10T09:30:00Z",
    updated_at: "2024-01-20T14:15:00Z"
  },
  {
    id: 3,
    titre: "Rédiger la documentation API",
    description: "Documenter tous les endpoints de l'API avec des exemples d'utilisation",
    priorite: "medium" as const,
    statut: "a_faire" as const,
    date_echeance: "2024-02-20",
    assignee_id: 3,
    assignee: mockUsers[2],
    labels: [mockLabels[3]],
    created_at: "2024-01-12T11:00:00Z",
    updated_at: "2024-01-12T11:00:00Z"
  },
  {
    id: 4,
    titre: "Optimiser les performances de la base de données",
    description: "Analyser et améliorer les requêtes lentes identifiées en production",
    priorite: "medium" as const,
    statut: "en_cours" as const,
    date_echeance: null,
    assignee_id: 2,
    assignee: mockUsers[1],
    labels: [],
    created_at: "2024-01-18T16:20:00Z",
    updated_at: "2024-01-22T09:45:00Z"
  },
  {
    id: 5,
    titre: "Mise en place des tests unitaires",
    description: "Ajouter une couverture de tests pour les modules critiques de l'application",
    priorite: "low" as const,
    statut: "termine" as const,
    date_echeance: "2024-01-25",
    assignee_id: 1,
    assignee: mockUsers[0],
    labels: [mockLabels[2]],
    created_at: "2024-01-05T08:15:00Z",
    updated_at: "2024-01-25T17:30:00Z"
  }
];

export const mockRootProps = {
  currentUser: mockUsers[0],
  cards: mockCards,
  users: mockUsers,
  labels: mockLabels,
  theme: "light" as const
};