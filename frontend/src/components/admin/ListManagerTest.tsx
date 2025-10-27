import React, { useState } from 'react';
import { Button } from '../ui/button';
import ListManager from './ListManager';

const ListManagerTest: React.FC = () => {
    const [showListManager, setShowListManager] = useState(false);

    return (
        <div className="p-4">
            <h2 className="text-xl font-bold mb-4">Test du ListManager</h2>
            <Button onClick={() => setShowListManager(true)}>
                Ouvrir le gestionnaire de listes
            </Button>

            <ListManager
                isOpen={showListManager}
                onClose={() => setShowListManager(false)}
                onListsUpdated={() => {
                }}
            />
        </div>
    );
};

export default ListManagerTest;
