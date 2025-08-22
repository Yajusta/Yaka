import { useState, useEffect, useRef } from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Badge } from '../ui/badge';
import { GlassmorphicCard } from '../ui/GlassmorphicCard';
import { Search, Filter, X, Plus, ChevronDown, ChevronUp } from 'lucide-react';
import { cn } from '../../lib/utils';

interface User {
    id: number;
    email: string;
    display_name?: string;
    role?: string;
}

interface Label {
    id: number;
    nom: string;
    couleur: string;
}

interface Filters {
    search: string;
    assignee_id: number | null;
    priorite: string | null;
    label_id: number | null;
}

interface FilterBarProps {
    filters: Filters;
    onFiltersChange: (filters: Filters) => void;
    onCreateCard: () => void;
    users: User[];
    labels: Label[];
    localSearchValue?: string;
    onLocalSearchChange?: (value: string) => void;
}

export const FilterBar = ({
    filters,
    onFiltersChange,
    onCreateCard,
    users,
    labels,
    localSearchValue = '',
}: FilterBarProps) => {
    const [showFilters, setShowFilters] = useState(false);
    const [searchValue, setSearchValue] = useState(localSearchValue);
    const searchInputRef = useRef<HTMLInputElement>(null);

    // Debounce search value
    useEffect(() => {
        const timer = setTimeout(() => {
            if (searchValue !== filters.search) {
                onFiltersChange({
                    ...filters,
                    search: searchValue
                });
            }
        }, 300); // 300ms debounce

        return () => clearTimeout(timer);
    }, [searchValue, filters, onFiltersChange]);

    // Update local search value when filters change externally
    useEffect(() => {
        if (filters.search !== searchValue) {
            setSearchValue(filters.search || '');
        }
    }, [filters.search]);

    // Ne restaurer le focus que si l'utilisateur a explicitement interagi avec la recherche
    const [hasUserInteracted, setHasUserInteracted] = useState(false);

    useEffect(() => {
        // Seulement restaurer le focus si l'utilisateur avait le focus avant ET qu'il y a eu une interaction
        if (hasUserInteracted && searchInputRef.current && document.activeElement !== searchInputRef.current) {
            const timeoutId = setTimeout(() => {
                if (searchInputRef.current) {
                    searchInputRef.current.focus();
                }
            }, 100); // Petit délai pour éviter les conflits avec d'autres événements

            return () => clearTimeout(timeoutId);
        }
    }, [hasUserInteracted]);

    // Gérer les interactions utilisateur
    const handleSearchFocus = () => {
        setHasUserInteracted(true);
    };

    const handleSearchBlur = () => {
        // Attendre un peu avant de marquer comme non-interagit pour éviter les problèmes
        setTimeout(() => setHasUserInteracted(false), 200);
    };

    const handleFilterChange = (key: keyof Filters, value: string | number | null): void => {
        onFiltersChange({
            ...filters,
            [key]: value === 'all' ? null : value
        });
    };

    const clearFilters = (): void => {
        onFiltersChange({
            search: '',
            assignee_id: null,
            priorite: null,
            label_id: null
        });
    };

    const hasActiveFilters = (): boolean => {
        return !!(filters.search || filters.assignee_id || filters.priorite || filters.label_id);
    };

    const getActiveFilterCount = (): number => {
        return [filters.assignee_id, filters.priorite, filters.label_id].filter(Boolean).length;
    };

    const getSelectedUser = (): User | undefined => {
        return users.find(u => u.id === filters.assignee_id);
    };

    const getSelectedLabel = (): Label | undefined => {
        return labels.find(l => l.id === filters.label_id);
    };

    return (
        <GlassmorphicCard className="border-b border-border/50 rounded-none rounded-t-lg py-0">
            <div className="p-4">
                {/* Main filter row */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4 flex-1">
                        {/* Search */}
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
                            <Input
                                ref={searchInputRef}
                                placeholder="Rechercher des cartes..."
                                value={searchValue}
                                onChange={(e) => setSearchValue(e.target.value)}
                                onFocus={handleSearchFocus}
                                onBlur={handleSearchBlur}
                                className="pl-10 bg-background/50 border-border/50 focus:bg-background transition-colors"
                            />
                        </div>

                        {/* Advanced filters toggle */}
                        <Button
                            variant="outline"
                            onClick={() => setShowFilters(!showFilters)}
                            className={cn(
                                "transition-all duration-200",
                                hasActiveFilters() && "border-primary text-primary bg-primary/5"
                            )}
                        >
                            <Filter className="h-4 w-4 mr-2" />
                            Filtres
                            {hasActiveFilters() && (
                                <Badge variant="secondary" className="ml-2 bg-primary text-primary-foreground">
                                    {getActiveFilterCount()}
                                </Badge>
                            )}
                            {showFilters ? (
                                <ChevronUp className="h-4 w-4 ml-2" />
                            ) : (
                                <ChevronDown className="h-4 w-4 ml-2" />
                            )}
                        </Button>

                        {/* Clear filters */}
                        {hasActiveFilters() && (
                            <Button variant="ghost" onClick={clearFilters} className="text-muted-foreground hover:text-foreground">
                                <X className="h-4 w-4 mr-2" />
                                Effacer
                            </Button>
                        )}
                    </div>

                    {/* Create card button */}
                    <Button onClick={onCreateCard} className="bg-primary hover:bg-primary/90 shadow-sm">
                        <Plus className="h-4 w-4 mr-2" />
                        Nouvelle carte
                    </Button>
                </div>

                {/* Advanced filters */}
                {showFilters && (
                    <div className="space-y-3">
                        <div className="border-t border-border/30 pt-3" />

                        <div className="flex flex-col md:flex-row gap-3">
                            {/* Label filter */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-foreground">Libellé</label>
                                <Select
                                    value={filters.label_id?.toString() || ''}
                                    onValueChange={(value) => handleFilterChange('label_id', value ? parseInt(value) : null)}
                                >
                                    <SelectTrigger className="bg-background/50 border-border/50">
                                        <SelectValue placeholder="Tous les libellés" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Tous les libellés</SelectItem>
                                        {labels.map(label => (
                                            <SelectItem key={label.id} value={label.id.toString()}>
                                                <div className="flex items-center">
                                                    <div
                                                        className="w-3 h-3 rounded-full mr-2 border border-border/50"
                                                        style={{ backgroundColor: label.couleur }}
                                                    />
                                                    {label.nom}
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Priority filter */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-foreground">Priorité</label>
                                <Select
                                    value={filters.priorite || ''}
                                    onValueChange={(value) => handleFilterChange('priorite', value)}
                                >
                                    <SelectTrigger className="bg-background/50 border-border/50">
                                        <SelectValue placeholder="Toutes les priorités" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Toutes les priorités</SelectItem>
                                        <SelectItem value="high">Élevé</SelectItem>
                                        <SelectItem value="medium">Moyen</SelectItem>
                                        <SelectItem value="low">Faible</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>

                            {/* Assignee filter */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-foreground">Assigné à</label>
                                <Select
                                    value={filters.assignee_id?.toString() || ''}
                                    onValueChange={(value) => handleFilterChange('assignee_id', value ? parseInt(value) : null)}
                                >
                                    <SelectTrigger className="bg-background/50 border-border/50">
                                        <SelectValue placeholder="Tous les utilisateurs" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="all">Tous les utilisateurs</SelectItem>
                                        {users.map(user => (
                                            <SelectItem key={user.id} value={user.id.toString()}>
                                                {user.display_name || user.email || 'Utilisateur sans nom'}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                        </div>
                    </div>
                )}

                {/* Active filters display */}
                {hasActiveFilters() && (
                    <>
                        <div className="border-t border-border/30 pt-3" />
                        <div className="flex flex-wrap gap-2">
                            {getSelectedUser() && (
                                <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                                    Assigné: {getSelectedUser()?.display_name || getSelectedUser()?.email || 'Utilisateur sans nom'}
                                    <X
                                        className="h-3 w-3 ml-1 cursor-pointer hover:text-primary/80"
                                        onClick={() => handleFilterChange('assignee_id', null)}
                                    />
                                </Badge>
                            )}
                            {filters.priorite && (
                                <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                                    Priorité: {filters.priorite === 'low' ? 'Faible' : filters.priorite === 'medium' ? 'Moyen' : filters.priorite === 'high' ? 'Élevé' : filters.priorite}
                                    <X
                                        className="h-3 w-3 ml-1 cursor-pointer hover:text-primary/80"
                                        onClick={() => handleFilterChange('priorite', null)}
                                    />
                                </Badge>
                            )}
                            {getSelectedLabel() && (
                                <Badge variant="secondary" className="bg-primary/10 text-primary border-primary/20">
                                    Libellé: {getSelectedLabel()?.nom}
                                    <X
                                        className="h-3 w-3 ml-1 cursor-pointer hover:text-primary/80"
                                        onClick={() => handleFilterChange('label_id', null)}
                                    />
                                </Badge>
                            )}
                        </div>
                    </>
                )}
            </div>
        </GlassmorphicCard>
    );
}; 