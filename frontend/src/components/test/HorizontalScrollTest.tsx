import React from 'react';
import { KanbanList } from '@shared/types/index';

/**
 * Test component to verify horizontal scrolling behavior with various numbers of lists
 * This component demonstrates the responsive horizontal scrolling implementation
 */
export const HorizontalScrollTest: React.FC = () => {
  // Create test scenarios with different numbers of lists
  const testScenarios = [
    { name: '2 Lists', count: 2 },
    { name: '3 Lists', count: 3 },
    { name: '5 Lists', count: 5 },
    { name: '8 Lists', count: 8 },
    { name: '12 Lists', count: 12 }
  ];

  const generateTestLists = (count: number): KanbanList[] => {
    return Array.from({ length: count }, (_, index) => ({
      id: index + 1,
      name: `Liste ${index + 1}`,
      order: index + 1,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }));
  };

  return (
    <div className="p-4 space-y-6">
      <h2 className="text-2xl font-bold">Test de Défilement Horizontal</h2>
      
      {testScenarios.map((scenario) => {
        const testLists = generateTestLists(scenario.count);
        
        return (
          <div key={scenario.name} className="space-y-2">
            <h3 className="text-lg font-semibold">{scenario.name}</h3>
            <div className="border rounded-lg p-4 bg-background">
              {/* Horizontal scrolling container - same as KanbanBoard */}
              <div className="h-64 kanban-horizontal-scroll">
                <div className="kanban-lists-container h-full">
                  {testLists.map(list => (
                    <div
                      key={list.id}
                      className={`kanban-list-column ${testLists.length <= 3 ? 'flex-1' : ''}`}
                      style={testLists.length <= 3 ? { width: `${100 / testLists.length}%` } : undefined}
                    >
                      <div className="h-full bg-card border-2 border-border/50 rounded-xl p-4">
                        <h4 className="font-medium text-foreground">{list.name}</h4>
                        <p className="text-sm text-muted-foreground mt-1">
                          {scenario.count <= 3 ? 'Pas de scroll' : 'Scroll horizontal'}
                        </p>
                        <div className="mt-4 space-y-2">
                          {/* Mock cards */}
                          <div className="h-16 bg-muted rounded border">
                            <div className="p-2 text-xs">Carte exemple 1</div>
                          </div>
                          <div className="h-16 bg-muted rounded border">
                            <div className="p-2 text-xs">Carte exemple 2</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        );
      })}
      
      <div className="mt-8 p-4 bg-muted rounded-lg">
        <h3 className="font-semibold mb-2">Comportement Attendu:</h3>
        <ul className="text-sm space-y-1 text-muted-foreground">
          <li>• <strong>≤ 3 listes:</strong> Les colonnes s'étendent pour remplir la largeur disponible</li>
          <li>• <strong>&gt; 3 listes:</strong> Largeur fixe (320px) avec défilement horizontal</li>
          <li>• <strong>Responsive:</strong> Largeur minimale réduite sur mobile (280px → 260px)</li>
          <li>• <strong>Scrollbar:</strong> Barre de défilement fine et stylisée</li>
          <li>• <strong>Espacement:</strong> Gap de 1rem entre les colonnes</li>
        </ul>
      </div>
    </div>
  );
};
