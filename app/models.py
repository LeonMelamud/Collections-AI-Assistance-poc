from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    projects = relationship("Project", back_populates="owner")
    project_members = relationship("ProjectMember", back_populates="user")
    tasks_assigned = relationship("Task", back_populates="assignee")
    comments = relationship("Comment", back_populates="author")
    
    __table_args__ = (
        Index('idx_users_email_active', 'email', 'is_active'),
        Index('idx_users_username_active', 'username', 'is_active'),
    )


class Project(Base):
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    settings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    members = relationship("ProjectMember", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_projects_owner_active', 'owner_id', 'is_active'),
        Index('idx_projects_name', 'name'),
    )


class ProjectMember(Base):
    __tablename__ = "project_members"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role = Column(String(50), nullable=False, default="member")  # owner, admin, member, viewer
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="members")
    user = relationship("User", back_populates="project_members")
    
    __table_args__ = (
        Index('idx_project_members_project_user', 'project_id', 'user_id', unique=True),
        Index('idx_project_members_user', 'user_id'),
    )


class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    assignee_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(String(50), nullable=False, default="todo")  # todo, in_progress, in_review, done, cancelled
    priority = Column(String(20), nullable=False, default="medium")  # low, medium, high, urgent
    labels = Column(JSON, nullable=True)  # Array of label strings
    due_date = Column(DateTime(timezone=True), nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks_assigned")
    comments = relationship("Comment", back_populates="task", cascade="all, delete-orphan")
    embeddings = relationship("TaskEmbedding", back_populates="task", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_tasks_project_status', 'project_id', 'status'),
        Index('idx_tasks_assignee', 'assignee_id'),
        Index('idx_tasks_project_order', 'project_id', 'order_index'),
        Index('idx_tasks_due_date', 'due_date'),
        Index('idx_tasks_priority', 'priority'),
    )


class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    author = relationship("User", back_populates="comments")
    
    __table_args__ = (
        Index('idx_comments_task_created', 'task_id', 'created_at'),
        Index('idx_comments_author', 'author_id'),
    )


class TaskEmbedding(Base):
    __tablename__ = "task_embeddings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False)
    embedding_type = Column(String(50), nullable=False)  # title, description, full_content
    qdrant_point_id = Column(String(255), nullable=False)
    content_hash = Column(String(64), nullable=False)  # SHA256 hash of the content
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="embeddings")
    
    __table_args__ = (
        Index('idx_task_embeddings_task_type', 'task_id', 'embedding_type'),
        Index('idx_task_embeddings_qdrant', 'qdrant_point_id', unique=True),
        Index('idx_task_embeddings_hash', 'content_hash'),
    )