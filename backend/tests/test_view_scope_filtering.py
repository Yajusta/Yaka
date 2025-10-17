"""Tests for view scope filtering functionality."""

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base
from app.models.card import Card, CardPriority
from app.models.kanban_list import KanbanList
from app.models.user import User, UserRole, UserStatus, ViewScope
from app.models.label import Label
from app.services.card import apply_view_scope_filter, can_access_card, get_cards, get_archived_cards
from app.schemas.card import CardFilter

# Configuration de la base de données de test
TEST_DB_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(TEST_DB_DIR, exist_ok=True)
TEST_DB_PATH = os.path.join(TEST_DB_DIR, "test_view_scope.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db_session():
    """Fixture pour créer une session de base de données de test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_users(db_session):
    """Fixture pour créer des utilisateurs de test avec différents périmètres."""
    users = {}
    
    # Admin user (should see all cards regardless of view scope)
    users['admin'] = User(
        email="admin@example.com",
        display_name="Admin User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        view_scope=ViewScope.MINE_ONLY  # Even with restrictive scope, admin should see all
    )
    
    # User with ALL scope
    users['all_scope'] = User(
        email="all@example.com",
        display_name="All Scope User",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
        view_scope=ViewScope.ALL
    )
    
    # User with UNASSIGNED_PLUS_MINE scope
    users['unassigned_plus_mine'] = User(
        email="unassigned@example.com",
        display_name="Unassigned Plus Mine User",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
        view_scope=ViewScope.UNASSIGNED_PLUS_MINE
    )
    
    # User with MINE_ONLY scope
    users['mine_only'] = User(
        email="mine@example.com",
        display_name="Mine Only User",
        role=UserRole.EDITOR,
        status=UserStatus.ACTIVE,
        view_scope=ViewScope.MINE_ONLY
    )
    
    for user in users.values():
        db_session.add(user)
    db_session.commit()
    
    # Refresh to get IDs
    for user in users.values():
        db_session.refresh(user)
    
    return users


@pytest.fixture
def sample_kanban_lists(db_session):
    """Fixture pour créer des listes Kanban de test."""
    lists = [
        KanbanList(name="To Do", order=1),
        KanbanList(name="In Progress", order=2),
        KanbanList(name="Done", order=3)
    ]
    
    for kanban_list in lists:
        db_session.add(kanban_list)
    db_session.commit()
    
    for kanban_list in lists:
        db_session.refresh(kanban_list)
    
    return lists


@pytest.fixture
def sample_cards(db_session, sample_users, sample_kanban_lists):
    """Fixture pour créer des cartes de test avec différentes assignations."""
    cards = []
    
    # Card assigned to admin
    card1 = Card(
        title="Admin Card",
        description="Card assigned to admin",
        list_id=sample_kanban_lists[0].id,
        position=1,
        priority=CardPriority.HIGH,
        assignee_id=sample_users['admin'].id,
        created_by=sample_users['admin'].id
    )
    
    # Card assigned to all_scope user
    card2 = Card(
        title="All Scope Card",
        description="Card assigned to all scope user",
        list_id=sample_kanban_lists[0].id,
        position=2,
        priority=CardPriority.MEDIUM,
        assignee_id=sample_users['all_scope'].id,
        created_by=sample_users['admin'].id
    )
    
    # Card assigned to unassigned_plus_mine user
    card3 = Card(
        title="Unassigned Plus Mine Card",
        description="Card assigned to unassigned plus mine user",
        list_id=sample_kanban_lists[1].id,
        position=1,
        priority=CardPriority.LOW,
        assignee_id=sample_users['unassigned_plus_mine'].id,
        created_by=sample_users['admin'].id
    )
    
    # Card assigned to mine_only user
    card4 = Card(
        title="Mine Only Card",
        description="Card assigned to mine only user",
        list_id=sample_kanban_lists[1].id,
        position=2,
        priority=CardPriority.HIGH,
        assignee_id=sample_users['mine_only'].id,
        created_by=sample_users['admin'].id
    )
    
    # Unassigned card
    card5 = Card(
        title="Unassigned Card",
        description="Card with no assignee",
        list_id=sample_kanban_lists[2].id,
        position=1,
        priority=CardPriority.MEDIUM,
        assignee_id=None,
        created_by=sample_users['admin'].id
    )
    
    # Archived card assigned to mine_only user
    card6 = Card(
        title="Archived Mine Only Card",
        description="Archived card assigned to mine only user",
        list_id=sample_kanban_lists[2].id,
        position=2,
        priority=CardPriority.LOW,
        assignee_id=sample_users['mine_only'].id,
        is_archived=True,
        created_by=sample_users['admin'].id
    )
    
    cards.extend([card1, card2, card3, card4, card5, card6])
    
    for card in cards:
        db_session.add(card)
    db_session.commit()
    
    for card in cards:
        db_session.refresh(card)
    
    return cards


class TestViewScopeFiltering:
    """Tests for view scope filtering functions."""
    

    
    def test_apply_view_scope_filter_all_scope(self, db_session, sample_users, sample_cards):
        """Test that users with ALL scope can see all cards."""
        user = sample_users['all_scope']
        query = db_session.query(Card).filter(Card.is_archived == False)
        
        filtered_query = apply_view_scope_filter(query, user)
        result = filtered_query.all()
        
        # User with ALL scope should see all 5 non-archived cards
        assert len(result) == 5
        card_titles = [card.title for card in result]
        assert "Admin Card" in card_titles
        assert "All Scope Card" in card_titles
        assert "Unassigned Plus Mine Card" in card_titles
        assert "Mine Only Card" in card_titles
        assert "Unassigned Card" in card_titles
    
    def test_apply_view_scope_filter_unassigned_plus_mine(self, db_session, sample_users, sample_cards):
        """Test that users with UNASSIGNED_PLUS_MINE scope see unassigned cards + their cards."""
        user = sample_users['unassigned_plus_mine']
        query = db_session.query(Card).filter(Card.is_archived == False)
        
        filtered_query = apply_view_scope_filter(query, user)
        result = filtered_query.all()
        
        # Should see their card + unassigned cards
        assert len(result) == 2
        card_titles = [card.title for card in result]
        assert "Unassigned Plus Mine Card" in card_titles
        assert "Unassigned Card" in card_titles
        assert "All Scope Card" not in card_titles
        assert "Mine Only Card" not in card_titles
        assert "Admin Card" not in card_titles
    
    def test_apply_view_scope_filter_mine_only(self, db_session, sample_users, sample_cards):
        """Test that users with MINE_ONLY scope see only their assigned cards."""
        user = sample_users['mine_only']
        query = db_session.query(Card).filter(Card.is_archived == False)
        
        filtered_query = apply_view_scope_filter(query, user)
        result = filtered_query.all()
        
        # Should see only their card
        assert len(result) == 1
        card_titles = [card.title for card in result]
        assert "Mine Only Card" in card_titles
        assert "Unassigned Card" not in card_titles
        assert "All Scope Card" not in card_titles
        assert "Unassigned Plus Mine Card" not in card_titles
        assert "Admin Card" not in card_titles
    
    def test_can_access_card_admin_user(self, sample_users, sample_cards):
        """Test that admin users can access any card."""
        admin_user = sample_users['admin']
        
        for card in sample_cards:
            if not card.is_archived:  # Only test non-archived cards
                assert can_access_card(admin_user, card) is True
    
    def test_can_access_card_all_scope(self, sample_users, sample_cards):
        """Test that users with ALL scope can access any card."""
        user = sample_users['all_scope']
        
        for card in sample_cards:
            if not card.is_archived:  # Only test non-archived cards
                assert can_access_card(user, card) is True
    
    def test_can_access_card_unassigned_plus_mine(self, sample_users, sample_cards):
        """Test access permissions for UNASSIGNED_PLUS_MINE scope."""
        user = sample_users['unassigned_plus_mine']
        
        for card in sample_cards:
            if card.is_archived:
                continue
                
            if card.assignee_id == user.id or card.assignee_id is None:
                assert can_access_card(user, card) is True
            else:
                assert can_access_card(user, card) is False
    
    def test_can_access_card_mine_only(self, sample_users, sample_cards):
        """Test access permissions for MINE_ONLY scope."""
        user = sample_users['mine_only']
        
        for card in sample_cards:
            if card.is_archived:
                continue
                
            if card.assignee_id == user.id:
                assert can_access_card(user, card) is True
            else:
                assert can_access_card(user, card) is False
    
    def test_get_cards_with_view_scope_filtering(self, db_session, sample_users, sample_kanban_lists, sample_cards):
        """Test get_cards function with view scope filtering."""
        user_mine_only = sample_users['mine_only']
        
        filters = CardFilter()
        
        # Test with mine_only user
        result = get_cards(db_session, filters, user=user_mine_only)
        card_titles = [card.title for card in result]
        
        # Should see only cards assigned to mine_only user (from sample_cards)
        assert "Mine Only Card" in card_titles
        # Should not see unassigned cards or other users' cards
        assert "Unassigned Card" not in card_titles
        assert "All Scope Card" not in card_titles
        assert "Unassigned Plus Mine Card" not in card_titles
        assert "Admin Card" not in card_titles
    
    def test_get_archived_cards_with_view_scope_filtering(self, db_session, sample_users, sample_kanban_lists, sample_cards):
        """Test get_archived_cards function with view scope filtering."""
        user_mine_only = sample_users['mine_only']
        user_all_scope = sample_users['all_scope']
        
        # Test with mine_only user
        result = get_archived_cards(db_session, user=user_mine_only)
        card_titles = [card.title for card in result]
        
        # Should see only their archived card
        assert len(result) == 1
        assert "Archived Mine Only Card" in card_titles
        
        # Test with all_scope user
        result = get_archived_cards(db_session, user=user_all_scope)
        card_titles = [card.title for card in result]
        
        # Should see the archived card
        assert len(result) == 1
        assert "Archived Mine Only Card" in card_titles


class TestViewScopeIntegration:
    """Integration tests for view scope functionality."""
    
    def test_view_scope_filtering_with_search(self, db_session, sample_users, sample_cards):
        """Test that search respects view scope filtering."""
        user = sample_users['unassigned_plus_mine']
        query = db_session.query(Card)
        
        # Apply non-archived filter first
        query = query.filter(Card.is_archived == False)
        
        # Apply view scope filter
        filtered_query = apply_view_scope_filter(query, user)
        
        # Then apply search filter
        search_term = "Card"
        filtered_query = filtered_query.filter(
            Card.title.ilike(f"%{search_term}%")
        )
        
        result = filtered_query.all()
        
        # Should only find cards within their view scope
        card_titles = [card.title for card in result]
        assert "Unassigned Plus Mine Card" in card_titles
        assert "Unassigned Card" in card_titles
        assert len(result) == 2
    
    def test_view_scope_filtering_with_list_filter(self, db_session, sample_users, sample_cards, sample_kanban_lists):
        """Test that list filtering respects view scope."""
        user = sample_users['mine_only']
        query = db_session.query(Card)
        
        # Apply non-archived filter first
        query = query.filter(Card.is_archived == False)
        
        # Apply view scope filter
        filtered_query = apply_view_scope_filter(query, user)
        
        # Then apply list filter
        filtered_query = filtered_query.filter(Card.list_id == sample_kanban_lists[1].id)
        
        result = filtered_query.all()
        
        # Should only find their card in that list if it exists
        card_titles = [card.title for card in result]
        # The mine_only card is in list 2 (index 1)
        assert "Mine Only Card" in card_titles
        assert len(result) == 1


if __name__ == "__main__":
    pytest.main([__file__])
