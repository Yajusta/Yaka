import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ListManager from '../ListManager';
import { useAuth } from '../../../hooks/useAuth';
import { useToast } from '../../../hooks/use-toast';
import { listsApi } from '../../../services/listsApi';
import { UserRole } from '../../../types';

// Mock dependencies
vi.mock('../../../hooks/useAuth');
vi.mock('../../../hooks/use-toast');
vi.mock('../../../services/listsApi');

const mockUseAuth = vi.mocked(useAuth);
const mockUseToast = vi.mocked(useToast);
const mockListsApi = vi.mocked(listsApi);

const mockToast = vi.fn();

const mockAdminUser = {
    id: 1,
    username: 'admin',
    email: 'admin@test.com',
    role: UserRole.ADMIN,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z'
};

const mockLists = [
    {
        id: 1,
        name: 'À faire',
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
    }
];

const renderListManager = (props = {}) => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
        onListsUpdated: vi.fn(),
        ...props
    };

    return render(
        <BrowserRouter>
            <ListManager {...defaultProps} />
        </BrowserRouter>
    );
};

describe('ListManager', () => {
    beforeEach(() => {
        vi.clearAllMocks();

        mockUseAuth.mockReturnValue({
            user: mockAdminUser,
            loading: false,
            login: vi.fn(),
            logout: vi.fn()
        });

        mockUseToast.mockReturnValue({
            toast: mockToast,
            dismiss: vi.fn()
        });

        mockListsApi.getLists.mockResolvedValue(mockLists);
        mockListsApi.getListCardsCount.mockResolvedValue({
            list: mockLists[0],
            card_count: 0
        });
    });

    it('should render list manager dialog when open', async () => {
        renderListManager();

        await waitFor(() => {
            expect(screen.getByText('Gestion des listes')).toBeInTheDocument();
        });
    });

    it('should show progress bar during list deletion with cards', async () => {
        // Mock a list with cards
        mockListsApi.getListCardsCount.mockResolvedValue({
            list: mockLists[0],
            card_count: 3
        });

        mockListsApi.deleteListWithProgress.mockImplementation(
            (_listId, _targetId, onProgress) => {
                // Simulate progress updates
                if (onProgress) {
                    onProgress(0, 3, 'Card 1');
                    setTimeout(() => onProgress(1, 3, 'Card 2'), 100);
                    setTimeout(() => onProgress(2, 3, 'Card 3'), 200);
                    setTimeout(() => onProgress(3, 3, ''), 300);
                }
                return Promise.resolve();
            }
        );

        renderListManager();

        await waitFor(() => {
            expect(screen.getByText('À faire')).toBeInTheDocument();
        });

        // Click delete button for first list
        const deleteButton = screen.getByRole('button', {
            name: /delete|trash|supprimer/i
        });
        fireEvent.click(deleteButton);

        await waitFor(() => {
            expect(screen.getByText('Supprimer la liste')).toBeInTheDocument();
        });

        // Select target list and confirm deletion
        const targetSelect = screen.getByRole('combobox');
        fireEvent.click(targetSelect);

        await waitFor(() => {
            const option = screen.getByText('En cours (Ordre: 2)');
            fireEvent.click(option);
        });

        const confirmButton = screen.getByText('Déplacer et supprimer');
        fireEvent.click(confirmButton);

        // Should show progress during deletion
        await waitFor(() => {
            expect(screen.getByText('Suppression en cours...')).toBeInTheDocument();
        });
    });

    it('should not render for non-admin users', () => {
        mockUseAuth.mockReturnValue({
            user: { ...mockAdminUser, role: UserRole.SUPERVISOR },
            loading: false,
            login: vi.fn(),
            logout: vi.fn()
        });

        const { container } = renderListManager();
        expect(container.firstChild).toBeNull();
    });
});