# Yaka - User Guide

Welcome to Yaka, your collaborative Kanban board application!

## Table of Contents

1. [Getting Started](#getting-started)
2. [Understanding User Roles](#understanding-user-roles)
3. [Managing Tasks](#managing-tasks)
4. [Collaboration Features](#collaboration-features)

---

## Getting Started

Yaka is a modern Kanban board application designed to help teams organize and track their work efficiently. This guide will walk you through all the features and help you make the most of the application.

---

## Understanding User Roles

Yaka implements a hierarchical role system that provides fine-grained control over what users can do. Each role inherits permissions from the roles below it, creating a clear progression of capabilities.

### Role Hierarchy

```
VISITOR
  └── COMMENTER
       └── CONTRIBUTOR
            └── EDITOR
                 └── SUPERVISOR
                      └── ADMIN
```

### Role Descriptions

#### 🔍 VISITOR (Read-Only)

**Best for:** External stakeholders, clients, or observers who need visibility without interaction.

**What they can do:**
- ✅ View the Kanban board
- ✅ See all tasks and their details
- ✅ Read all comments
- ✅ View task history and changes

**What they cannot do:**
- ❌ Create or modify anything
- ❌ Add comments
- ❌ Assign themselves to tasks

**Use case:** A client who wants to track project progress without interfering with the workflow.

---

#### 💬 COMMENTER

**Best for:** Stakeholders who need to provide feedback and ask questions.

**Inherits from:** VISITOR (all read permissions)

**Additional capabilities:**
- ✅ Add comments on any task
- ✅ Edit their own comments
- ✅ Delete their own comments

**What they cannot do:**
- ❌ Modify tasks
- ❌ Change task status or priority
- ❌ Assign tasks

**Use case:** A product owner who reviews tasks and provides feedback through comments.

---

#### 🤝 CONTRIBUTOR

**Best for:** Team members who work on specific assigned tasks.

**Inherits from:** COMMENTER (all read + comment permissions)

**Additional capabilities:**
- ✅ Self-assign to available tasks
- ✅ Check/uncheck checklist items on their assigned tasks
- ✅ Move their assigned tasks between lists (if workflow rules allow)

**What they cannot do:**
- ❌ Create new tasks
- ❌ Modify task content (title, description)
- ❌ Change task metadata (priority, due date)
- ❌ Work on tasks not assigned to them

**Use case:** A junior developer who picks up tasks from the backlog and marks progress on their assigned work.

---

#### ✏️ EDITOR

**Best for:** Independent contributors who manage their own work fully.

**Inherits from:** CONTRIBUTOR (all previous permissions)

**Additional capabilities:**
- ✅ Create new tasks (automatically assigned to themselves)
- ✅ Fully modify their assigned tasks:
  - Edit title and description
  - Change priority and due date
  - Add/remove labels
  - Create/modify/delete checklist items
  - Reassign to someone else (with approval)

**What they cannot do:**
- ❌ Modify tasks assigned to others
- ❌ Create tasks for other team members directly
- ❌ Delete or archive tasks

**Use case:** A senior developer who creates and manages their own tickets, adding detailed specifications and tracking their progress.

---

#### 👔 SUPERVISOR

**Best for:** Team leads, project managers, and scrum masters who coordinate the team's work.

**Inherits from:** EDITOR (all previous permissions)

**Additional capabilities:**
- ✅ Create tasks and assign them to anyone
- ✅ Modify **ALL** tasks (not just own):
  - Edit title and description
  - Change all metadata (priority, due date, labels)
  - Create/modify/delete checklist items
  - Reassign tasks freely
- ✅ Move any task between lists (full workflow control)
- ✅ Check/uncheck checklist items on any task
- ✅ Delete and archive tasks

**What they cannot do:**
- ❌ Manage users and their roles
- ❌ Configure board settings (lists, labels)
- ❌ Access system administration features

**Use case:** A team lead who organizes the sprint, adjusts task priorities, redistributes work when team members are unavailable, and ensures the board accurately reflects the team's status.

**Real-world scenario:**
- Bob is on vacation → Supervisor reassigns Bob's tasks to Alice
- A task needs clarification → Supervisor updates the description
- Sprint priorities change → Supervisor adjusts due dates and priorities across all tasks
- A task is blocked → Supervisor moves it to a different list

---

#### 👑 ADMIN

**Best for:** Application administrators and board owners.

**Inherits from:** SUPERVISOR (all task management permissions)

**Additional capabilities:**
- ✅ Everything a SUPERVISOR can do
- ✅ Invite new users to the board
- ✅ Change user roles
- ✅ Remove users from the board
- ✅ Create, modify, and delete lists
- ✅ Create, modify, and delete labels
- ✅ Configure board settings (title, preferences)
- ✅ Permanently delete archived tasks
- ✅ Access all administrative features

**Responsibilities:**
- Managing the team roster
- Configuring the board structure
- Maintaining labels and lists
- Ensuring proper role assignments
- System administration

**Use case:** The board owner who sets up the workspace, manages access, and maintains the board configuration.

---

### Choosing the Right Role

When assigning roles to team members, consider these guidelines:

| If the user needs to... | Assign this role |
|--------------------------|------------------|
| Just observe the project | **VISITOR** |
| Provide feedback and questions | **COMMENTER** |
| Work on specific assigned tasks | **CONTRIBUTOR** |
| Manage their own workload independently | **EDITOR** |
| Coordinate team work and adjust priorities | **SUPERVISOR** |
| Administer the board and manage users | **ADMIN** |

### Role Assignment Best Practices

1. **Start Conservative:** Begin with the lowest role necessary and upgrade as needed
2. **Review Regularly:** Periodically review role assignments as team members' responsibilities evolve
3. **Limit Admins:** Only assign ADMIN role to trusted individuals responsible for board management
4. **Use SUPERVISOR Wisely:** This role is powerful; typically assign it to team leads and project managers
5. **Empower EDITORs:** Give experienced team members EDITOR role to work independently
6. **CONTRIBUTOR for New Members:** Start new team members as CONTRIBUTOR until they're familiar with workflows

### Common Role Scenarios

#### Scenario 1: Development Team
- **Product Owner:** COMMENTER (provides requirements and feedback)
- **Scrum Master:** SUPERVISOR (manages sprint and workflow)
- **Senior Developers:** EDITOR (create and manage their own tickets)
- **Junior Developers:** CONTRIBUTOR (work on assigned tickets)
- **Stakeholders:** VISITOR (track progress)

#### Scenario 2: Marketing Team
- **Marketing Director:** ADMIN (board owner)
- **Campaign Managers:** SUPERVISOR (coordinate campaigns)
- **Content Creators:** EDITOR (manage their own content tasks)
- **External Freelancers:** CONTRIBUTOR (work on specific assignments)
- **Executives:** VISITOR (monitor progress)

#### Scenario 3: Support Team
- **Support Manager:** SUPERVISOR (prioritize and distribute tickets)
- **Senior Support Agents:** EDITOR (handle and document complex cases)
- **Support Agents:** CONTRIBUTOR (resolve assigned tickets)
- **Quality Team:** COMMENTER (provide feedback on resolutions)

---

### Permissions Quick Reference

| Action | Visitor | Commenter | Contributor | Editor | Supervisor | Admin |
|--------|---------|-----------|-------------|--------|------------|-------|
| View board and tasks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Read comments | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Add comments | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Edit own comments | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Self-assign tasks | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Check items (own tasks) | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Move own tasks | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Create tasks | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Modify own tasks | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Create tasks for others | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Modify all tasks | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Check items (all tasks) | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Move all tasks | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Delete/archive tasks | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Manage users | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Manage lists/labels | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Board settings | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

### Frequently Asked Questions

#### Q: Can I have multiple ADMINs on a board?
**A:** Yes! You can assign the ADMIN role to multiple trusted users. This is useful for shared responsibility and backup administration.

#### Q: What happens if I change someone's role?
**A:** The change takes effect immediately. The user's permissions will be updated on their next action or page refresh.

#### Q: Can a CONTRIBUTOR create tasks?
**A:** No, only EDITOR and above can create tasks. CONTRIBUTOR can self-assign to existing tasks.

#### Q: Can an EDITOR modify other people's tasks?
**A:** No, EDITOR can only fully modify their own assigned tasks. To modify all tasks, you need the SUPERVISOR role.

#### Q: What's the difference between SUPERVISOR and ADMIN?
**A:** SUPERVISOR can manage all tasks but cannot configure the board (users, lists, labels, settings). ADMIN has full administrative access.

#### Q: Can I customize these roles or create new ones?
**A:** Currently, the role system is fixed with these six roles. This ensures consistent permissions across the application.

#### Q: Can a user have different roles on different boards?
**A:** Currently, roles are per-board. Each user has one role for the board they're invited to.

---

## Managing Tasks

*(This section will cover task creation, editing, moving, etc.)*

---

## Collaboration Features

*(This section will cover comments, mentions, notifications, etc.)*

---

## Need Help?

If you have questions or need assistance:
- Contact your board administrator
- Check the technical documentation for advanced features
- Report issues through your organization's support channel
