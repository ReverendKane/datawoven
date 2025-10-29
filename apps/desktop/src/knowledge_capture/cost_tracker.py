"""
Cost Tracking Database Manager using SQLAlchemy
Tracks token usage and costs for all batch processing assignments
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

Base = declarative_base()


class BatchProcessing(Base):
    """Main batch processing table"""
    __tablename__ = 'batch_processing'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, unique=True, nullable=False, index=True)
    batch_name = Column(String)
    assignment_type = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    status = Column(String, default='running')
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    items_processed = Column(Integer, default=0)
    items_total = Column(Integer, default=0)
    notes = Column(String, nullable=True)

    # Relationship to items
    items = relationship("ItemProcessing", back_populates="batch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BatchProcessing(batch_id='{self.batch_id}', type='{self.assignment_type}', status='{self.status}')>"


class ItemProcessing(Base):
    """Individual item tracking within batches"""
    __tablename__ = 'item_processing'

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey('batch_processing.batch_id'), nullable=False, index=True)
    item_name = Column(String, nullable=False)
    item_type = Column(String)
    processing_time = Column(DateTime, nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)
    status = Column(String, default='completed')

    # Relationship back to batch
    batch = relationship("BatchProcessing", back_populates="items")

    def __repr__(self):
        return f"<ItemProcessing(item_name='{self.item_name}', tokens={self.total_tokens})>"


class CostTracker:
    """Manages cost tracking database using SQLAlchemy"""

    # Claude Sonnet 4 pricing (per 1M tokens)
    INPUT_COST_PER_MILLION = 3.0
    OUTPUT_COST_PER_MILLION = 15.0

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize cost tracker with database path
        If db_path is None, uses default location: ~/.knowledge_capture/cost_tracking.db
        """
        if db_path is None:
            # Default to user's home directory (legacy)
            db_path = Path.home() / ".knowledge_capture" / "cost_tracking.db"

        self.db_path = Path(db_path)

        # Create parent directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine and session
        self.engine = create_engine(f'sqlite:///{self.db_path}')
        Base.metadata.create_all(self.engine)

        # Create session factory
        self.Session = sessionmaker(bind=self.engine)

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost based on token usage"""
        input_cost = (input_tokens * self.INPUT_COST_PER_MILLION) / 1_000_000
        output_cost = (output_tokens * self.OUTPUT_COST_PER_MILLION) / 1_000_000
        return input_cost + output_cost

    def start_batch(self, batch_name: str, assignment_type: str, items_total: int = 0) -> str:
        """
        Start tracking a new batch
        Returns: batch_id (UUID string)
        """
        batch_id = str(uuid.uuid4())

        session = self.Session()
        try:
            batch = BatchProcessing(
                batch_id=batch_id,
                batch_name=batch_name,
                assignment_type=assignment_type,
                start_time=datetime.now(),
                status='running',
                items_total=items_total
            )
            session.add(batch)
            session.commit()
            return batch_id
        finally:
            session.close()

    def update_batch(self, batch_id: str,
                     input_tokens: int = 0,
                     output_tokens: int = 0,
                     items_processed: Optional[int] = None,
                     status: Optional[str] = None):
        """Update batch with new token counts and progress"""
        session = self.Session()
        try:
            batch = session.query(BatchProcessing).filter_by(batch_id=batch_id).first()

            if not batch:
                return

            # Add new tokens to existing counts
            batch.input_tokens += input_tokens
            batch.output_tokens += output_tokens
            batch.total_tokens = batch.input_tokens + batch.output_tokens

            # Recalculate cost
            batch.estimated_cost = self._calculate_cost(batch.input_tokens, batch.output_tokens)

            # Update items processed if provided
            if items_processed is not None:
                batch.items_processed = items_processed

            # Update status
            if status:
                batch.status = status
                if status in ['completed', 'failed', 'stopped']:
                    batch.end_time = datetime.now()

            session.commit()
        finally:
            session.close()

    def complete_batch(self, batch_id: str, status: str = 'completed'):
        """Mark batch as completed"""
        self.update_batch(batch_id, status=status)

    def add_item(self, batch_id: str, item_name: str, item_type: str,
                 input_tokens: int, output_tokens: int):
        """Add individual item processing record"""
        total_tokens = input_tokens + output_tokens
        cost = self._calculate_cost(input_tokens, output_tokens)

        session = self.Session()
        try:
            item = ItemProcessing(
                batch_id=batch_id,
                item_name=item_name,
                item_type=item_type,
                processing_time=datetime.now(),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                estimated_cost=cost
            )
            session.add(item)
            session.commit()
        finally:
            session.close()

    def get_total_stats(self) -> Dict:
        """Get all-time statistics"""
        session = self.Session()
        try:
            from sqlalchemy import func

            result = session.query(
                func.count(BatchProcessing.id).label('total_batches'),
                func.sum(BatchProcessing.total_tokens).label('total_tokens'),
                func.sum(BatchProcessing.estimated_cost).label('total_cost'),
                func.sum(BatchProcessing.items_processed).label('total_items')
            ).filter(
                BatchProcessing.status.in_(['completed', 'running'])
            ).first()

            return {
                'total_batches': result.total_batches or 0,
                'total_tokens': result.total_tokens or 0,
                'total_cost': result.total_cost or 0.0,
                'total_items': result.total_items or 0
            }
        finally:
            session.close()

    def get_recent_batches(self, limit: int = 10) -> List[Dict]:
        """Get recent batch records"""
        session = self.Session()
        try:
            batches = session.query(BatchProcessing).order_by(
                BatchProcessing.start_time.desc()
            ).limit(limit).all()

            result = []
            for batch in batches:
                result.append({
                    'batch_id': batch.batch_id,
                    'batch_name': batch.batch_name,
                    'assignment_type': batch.assignment_type,
                    'start_time': batch.start_time.isoformat(),
                    'end_time': batch.end_time.isoformat() if batch.end_time else None,
                    'status': batch.status,
                    'total_tokens': batch.total_tokens,
                    'estimated_cost': batch.estimated_cost,
                    'items_processed': batch.items_processed,
                    'items_total': batch.items_total
                })

            return result
        finally:
            session.close()

    def get_batch_details(self, batch_id: str) -> Optional[Dict]:
        """Get detailed information for a specific batch"""
        session = self.Session()
        try:
            batch = session.query(BatchProcessing).filter_by(batch_id=batch_id).first()

            if not batch:
                return None

            # Get items for this batch
            items = session.query(ItemProcessing).filter_by(batch_id=batch_id).order_by(
                ItemProcessing.processing_time
            ).all()

            return {
                'batch': {
                    'batch_id': batch.batch_id,
                    'batch_name': batch.batch_name,
                    'assignment_type': batch.assignment_type,
                    'start_time': batch.start_time.isoformat(),
                    'end_time': batch.end_time.isoformat() if batch.end_time else None,
                    'status': batch.status,
                    'input_tokens': batch.input_tokens,
                    'output_tokens': batch.output_tokens,
                    'total_tokens': batch.total_tokens,
                    'estimated_cost': batch.estimated_cost,
                    'items_processed': batch.items_processed,
                    'items_total': batch.items_total,
                    'notes': batch.notes
                },
                'items': [
                    {
                        'item_name': item.item_name,
                        'item_type': item.item_type,
                        'input_tokens': item.input_tokens,
                        'output_tokens': item.output_tokens,
                        'total_tokens': item.total_tokens,
                        'estimated_cost': item.estimated_cost,
                        'status': item.status
                    }
                    for item in items
                ]
            }
        finally:
            session.close()

    def get_stats_by_type(self) -> List[Dict]:
        """Get statistics grouped by assignment type"""
        session = self.Session()
        try:
            from sqlalchemy import func

            results = session.query(
                BatchProcessing.assignment_type,
                func.count(BatchProcessing.id).label('batch_count'),
                func.sum(BatchProcessing.total_tokens).label('total_tokens'),
                func.sum(BatchProcessing.estimated_cost).label('total_cost'),
                func.avg(BatchProcessing.estimated_cost).label('avg_cost')
            ).filter(
                BatchProcessing.status.in_(['completed', 'running'])
            ).group_by(
                BatchProcessing.assignment_type
            ).order_by(
                func.sum(BatchProcessing.estimated_cost).desc()
            ).all()

            stats = []
            for row in results:
                stats.append({
                    'assignment_type': row.assignment_type,
                    'batch_count': row.batch_count,
                    'total_tokens': row.total_tokens or 0,
                    'total_cost': row.total_cost or 0.0,
                    'avg_cost': row.avg_cost or 0.0
                })

            return stats
        finally:
            session.close()

    def get_batch_by_id(self, batch_id: str) -> Optional[BatchProcessing]:
        """Get a batch object by ID (for ORM operations)"""
        session = self.Session()
        try:
            return session.query(BatchProcessing).filter_by(batch_id=batch_id).first()
        finally:
            session.close()

    def delete_batch(self, batch_id: str) -> bool:
        """Delete a batch and all its items"""
        session = self.Session()
        try:
            batch = session.query(BatchProcessing).filter_by(batch_id=batch_id).first()
            if batch:
                session.delete(batch)
                session.commit()
                return True
            return False
        finally:
            session.close()






