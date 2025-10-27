import React, { useState } from 'react';
import { Button } from '../ui/button';
import ProgressBar from '../ui/progress-bar';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

const ListManagerDemo: React.FC = () => {
    const [showDemo, setShowDemo] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [progress, setProgress] = useState({ current: 0, total: 5, cardName: '' });

    const simulateCardMovement = async () => {
        setIsDeleting(true);
        const cards = ['Tâche 1', 'Tâche 2', 'Tâche 3', 'Tâche 4', 'Tâche 5'];
        
        for (let i = 0; i < cards.length; i++) {
            setProgress({ current: i, total: cards.length, cardName: cards[i] });
            await new Promise(resolve => setTimeout(resolve, 800));
        }
        
        setProgress({ current: cards.length, total: cards.length, cardName: '' });
        await new Promise(resolve => setTimeout(resolve, 500));
        
        setIsDeleting(false);
        setShowDemo(false);
        setProgress({ current: 0, total: 5, cardName: '' });
    };

    return (
        <>
            <Button onClick={() => setShowDemo(true)}>
                Démonstration du déplacement de cartes
            </Button>

            <Dialog open={showDemo} onOpenChange={(open) => {
                if (!isDeleting) {
                    setShowDemo(open);
                }
            }}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>
                            {isDeleting ? 'Suppression en cours...' : 'Démonstration'}
                        </DialogTitle>
                    </DialogHeader>

                    <div className="space-y-4">
                        <div className="p-3 bg-gray-50 rounded-md">
                            <p className="font-medium">
                                Liste à supprimer : "Anciennes tâches"
                            </p>
                            <p className="text-sm text-orange-600 mt-1">
                                ⚠️ Cette liste contient 5 cartes
                            </p>
                        </div>

                        {isDeleting ? (
                            <div className="space-y-3">
                                <div className="p-3 border border-blue-200 bg-blue-50 rounded-md">
                                    <p className="text-sm text-blue-800 font-medium mb-2">
                                        Déplacement des cartes en cours...
                                    </p>
                                    <ProgressBar
                                        current={progress.current}
                                        total={progress.total}
                                        label={progress.cardName ? `Déplacement: ${progress.cardName}` : 'Préparation...'}
                                        showPercentage={true}
                                    />
                                </div>
                            </div>
                        ) : (
                            <div className="p-3 border border-orange-200 bg-orange-50 rounded-md">
                                <p className="text-sm text-orange-800 font-medium">
                                    Simulation du déplacement de cartes
                                </p>
                                <p className="text-xs text-orange-700 mt-1">
                                    Cliquez sur "Démarrer" pour voir la barre de progression en action.
                                </p>
                            </div>
                        )}

                        {!isDeleting && (
                            <div className="flex justify-end space-x-2 pt-2">
                                <Button
                                    variant="outline"
                                    onClick={() => setShowDemo(false)}
                                >
                                    Fermer
                                </Button>
                                <Button
                                    variant="destructive"
                                    onClick={simulateCardMovement}
                                >
                                    Démarrer la simulation
                                </Button>
                            </div>
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </>
    );
};

export default ListManagerDemo;
