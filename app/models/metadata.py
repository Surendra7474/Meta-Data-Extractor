from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
import datetime
import json
from app.utils.database import Base

class File(Base):
    """File model to keep track of uploaded files."""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(255), nullable=False)
    file_extension = Column(String(50), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship with metadata
    file_metadata = relationship("Metadata", back_populates="file", cascade="all, delete-orphan")

class Metadata(Base):
    """Metadata model to store extracted metadata from files."""
    __tablename__ = "metadata"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    metadata_type = Column(String(50), nullable=False)  # e.g., 'image', 'document', 'audio'
    metadata_json = Column(JSON, nullable=False, default=dict)
    extracted_at = Column(DateTime, default=datetime.datetime.utcnow)
    extraction_duration = Column(Integer, nullable=True)  # Time taken to extract metadata in ms

    # Plain text representation of extracted text content (if applicable)
    extracted_text = Column(Text, nullable=True)

    # Relationship with file
    file = relationship("File", back_populates="file_metadata")

    # Relationship with AI analysis
    ai_analysis = relationship("AIAnalysis", back_populates="metadata_rel", uselist=False, cascade="all, delete-orphan")

    def get_metadata(self):
        """Return metadata as a Python dictionary."""
        return self.metadata_json

    def set_metadata(self, metadata_dict):
        """Set metadata from a Python dictionary."""
        self.metadata_json = metadata_dict


class AIAnalysis(Base):
    """AI Analysis model to store results from Gemini API analysis."""
    __tablename__ = "ai_analysis"

    id = Column(Integer, primary_key=True, index=True)
    metadata_id = Column(Integer, ForeignKey("metadata.id", ondelete="CASCADE"), nullable=False)
    analysis_json = Column(JSON, nullable=False, default=dict)  # Store the full analysis result
    has_anomalies = Column(Boolean, default=False)  # Quick flag for anomalies
    has_privacy_concerns = Column(Boolean, default=False)  # Quick flag for privacy concerns
    summary = Column(Text, nullable=True)  # Store the summary text
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship with metadata
    metadata_rel = relationship("Metadata", back_populates="ai_analysis")