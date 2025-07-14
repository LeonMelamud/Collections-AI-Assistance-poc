#!/usr/bin/env python3
"""
Database seeding script for Vibe Kanban
Creates test data for development and testing
"""

import sys
import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
import uuid
from faker import Faker

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import User, Project, ProjectMember, Task, Comment, Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
fake = Faker()

def create_test_users(db: Session, count: int = 10) -> list[User]:
    """Create test users"""
    users = []
    
    # Create admin user
    admin_user = User(
        id=uuid.uuid4(),
        email="admin@vibekanban.com",
        username="admin",
        full_name="Admin User",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwkF8m.QYhKQTjpzm",  # password: admin123
        is_active=True,
        is_superuser=True
    )
    db.add(admin_user)
    users.append(admin_user)
    
    # Create regular test users
    for i in range(count - 1):
        user = User(
            id=uuid.uuid4(),
            email=fake.email(),
            username=f"user_{i+1}",
            full_name=fake.name(),
            hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LwkF8m.QYhKQTjpzm",  # password: password123
            is_active=True,
            is_superuser=False
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    logger.info(f"Created {len(users)} test users")
    return users

def create_test_projects(db: Session, users: list[User], count: int = 5) -> list[Project]:
    """Create test projects"""
    projects = []
    
    project_names = [
        "Website Redesign",
        "Mobile App Development",
        "API Integration",
        "Database Migration",
        "User Authentication System"
    ]
    
    for i in range(min(count, len(project_names))):
        project = Project(
            id=uuid.uuid4(),
            name=project_names[i],
            description=fake.text(max_nb_chars=200),
            owner_id=users[i % len(users)].id,
            is_active=True,
            settings={
                "task_statuses": ["todo", "in_progress", "in_review", "done"],
                "priority_levels": ["low", "medium", "high", "urgent"],
                "auto_assign": False
            }
        )
        db.add(project)
        projects.append(project)
    
    db.commit()
    logger.info(f"Created {len(projects)} test projects")
    return projects

def create_project_members(db: Session, projects: list[Project], users: list[User]):
    """Add users as members to projects"""
    members_count = 0
    
    for project in projects:
        # Add 3-5 random users to each project
        project_users = fake.random_elements(elements=users, length=fake.random_int(min=3, max=5), unique=True)
        
        for user in project_users:
            # Skip if user is already the owner
            if user.id == project.owner_id:
                continue
                
            member = ProjectMember(
                id=uuid.uuid4(),
                project_id=project.id,
                user_id=user.id,
                role=fake.random_element(elements=["admin", "member", "viewer"]),
                joined_at=fake.date_time_between(start_date='-30d', end_date='now')
            )
            db.add(member)
            members_count += 1
    
    db.commit()
    logger.info(f"Created {members_count} project members")

def create_test_tasks(db: Session, projects: list[Project], users: list[User], tasks_per_project: int = 15) -> list[Task]:
    """Create test tasks"""
    tasks = []
    statuses = ["todo", "in_progress", "in_review", "done", "cancelled"]
    priorities = ["low", "medium", "high", "urgent"]
    
    task_titles = [
        "Design landing page",
        "Implement user authentication",
        "Create database schema",
        "Write API documentation",
        "Set up CI/CD pipeline",
        "Fix login bug",
        "Add search functionality",
        "Optimize database queries",
        "Create user dashboard",
        "Implement file upload",
        "Add email notifications",
        "Write unit tests",
        "Update dependencies",
        "Refactor code structure",
        "Add logging system"
    ]
    
    for project in projects:
        for i in range(tasks_per_project):
            task = Task(
                id=uuid.uuid4(),
                title=fake.random_element(elements=task_titles) + f" #{i+1}",
                description=fake.text(max_nb_chars=500),
                project_id=project.id,
                assignee_id=fake.random_element(elements=users).id if fake.boolean(chance_of_getting_true=70) else None,
                status=fake.random_element(elements=statuses),
                priority=fake.random_element(elements=priorities),
                labels=fake.random_elements(elements=["frontend", "backend", "bug", "feature", "urgent", "api"], length=fake.random_int(min=0, max=3), unique=True),
                due_date=fake.date_time_between(start_date='+1d', end_date='+30d') if fake.boolean(chance_of_getting_true=60) else None,
                estimated_hours=fake.random_int(min=1, max=40) if fake.boolean(chance_of_getting_true=50) else None,
                actual_hours=fake.random_int(min=1, max=50) if fake.boolean(chance_of_getting_true=30) else None,
                order_index=i
            )
            db.add(task)
            tasks.append(task)
    
    db.commit()
    logger.info(f"Created {len(tasks)} test tasks")
    return tasks

def create_test_comments(db: Session, tasks: list[Task], users: list[User], comments_per_task: int = 3):
    """Create test comments"""
    comments_count = 0
    
    for task in tasks:
        # Not all tasks have comments
        if fake.boolean(chance_of_getting_true=60):
            num_comments = fake.random_int(min=1, max=comments_per_task)
            
            for i in range(num_comments):
                comment = Comment(
                    id=uuid.uuid4(),
                    task_id=task.id,
                    author_id=fake.random_element(elements=users).id,
                    content=fake.text(max_nb_chars=300),
                    created_at=fake.date_time_between(start_date='-7d', end_date='now')
                )
                db.add(comment)
                comments_count += 1
    
    db.commit()
    logger.info(f"Created {comments_count} test comments")

def seed_database():
    """Main seeding function"""
    print("🌱 Seeding database with test data...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if data already exists
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Database already contains {existing_users} users. Use --reset to clear existing data.")
            return False
        
        # Create test data
        users = create_test_users(db, count=10)
        projects = create_test_projects(db, users, count=5)
        create_project_members(db, projects, users)
        tasks = create_test_tasks(db, projects, users, tasks_per_project=15)
        create_test_comments(db, tasks, users, comments_per_task=3)
        
        print("✅ Database seeded successfully!")
        print(f"📊 Created: {len(users)} users, {len(projects)} projects, {len(tasks)} tasks")
        return True
        
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

def reset_database():
    """Reset database by dropping and recreating all tables"""
    print("🔄 Resetting database...")
    
    try:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        print("✅ Database reset completed")
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        if reset_database():
            success = seed_database()
        else:
            success = False
    else:
        success = seed_database()
    
    if success:
        print("\n🎉 Database seeding completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Database seeding failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()