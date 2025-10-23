import { useState } from 'react';
import { User } from '@shared/types';
import { User as UserIcon, Menu, X } from 'lucide-react';

interface BoardHeaderProps {
  boardTitle: string;
  user: User;
  onMenuClick: () => void;
}

const BoardHeader = ({ boardTitle, user, onMenuClick }: BoardHeaderProps) => {
  const getInitials = (name?: string, email?: string) => {
    if (name) {
      return name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .toUpperCase()
        .substring(0, 2);
    }
    if (email) {
      return email.substring(0, 2).toUpperCase();
    }
    return 'U';
  };

  return (
    <header className="mobile-header">
      {/* Left: Menu button (placeholder for now) */}
      <button
        className="p-2 text-foreground hover:text-primary active:bg-accent rounded-lg transition-colors"
        aria-label="Menu"
      >
        <Menu className="w-6 h-6" />
      </button>

      {/* Center: Board title */}
      <h1 className="text-lg font-bold text-foreground truncate px-4 flex-1 text-center">
        {boardTitle}
      </h1>

      {/* Right: User avatar */}
      <button
        onClick={onMenuClick}
        className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-medium hover:bg-primary/90 active:bg-primary/80 transition-colors"
        aria-label="User menu"
      >
        {getInitials(user.display_name, user.email)}
      </button>
    </header>
  );
};

export default BoardHeader;

