"""SQLAlchemy 2.0 declarative models for EvoGraph."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Taxon(Base):
    __tablename__ = "taxa"

    ott_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, index=True)
    rank: Mapped[str] = mapped_column(Text, index=True)
    parent_ott_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("taxa.ott_id"), nullable=True, index=True
    )
    lineage: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True
    )
    ncbi_tax_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bold_tax_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    synonyms: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_extinct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # Relationships
    parent: Mapped[Taxon | None] = relationship(
        "Taxon", remote_side=[ott_id], back_populates="children"
    )
    children: Mapped[list[Taxon]] = relationship(
        "Taxon", back_populates="parent"
    )
    sequences: Mapped[list[Sequence]] = relationship(
        "Sequence", back_populates="taxon"
    )


class Sequence(Base):
    __tablename__ = "sequences"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=func.gen_random_uuid()
    )
    ott_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxa.ott_id"), index=True
    )
    marker: Mapped[str] = mapped_column(Text, default="COI")
    source: Mapped[str] = mapped_column(Text)
    accession: Mapped[str] = mapped_column(Text)
    sequence: Mapped[str] = mapped_column(Text)
    length: Mapped[int] = mapped_column(Integer)
    quality: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_canonical: Mapped[bool] = mapped_column(Boolean, default=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relationships
    taxon: Mapped[Taxon] = relationship("Taxon", back_populates="sequences")


class Edge(Base):
    __tablename__ = "edges"
    __table_args__ = (
        PrimaryKeyConstraint("src_ott_id", "dst_ott_id", "marker"),
        Index("ix_edges_src_distance", "src_ott_id", "distance"),
    )

    src_ott_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxa.ott_id"), index=True
    )
    dst_ott_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxa.ott_id"), index=True
    )
    marker: Mapped[str] = mapped_column(Text)
    distance: Mapped[float] = mapped_column(Double)
    mi_norm: Mapped[float] = mapped_column(Double)
    align_len: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class NodeMedia(Base):
    __tablename__ = "node_media"

    ott_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("taxa.ott_id"), primary_key=True
    )
    image_url: Mapped[str] = mapped_column(Text)
    attribution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    step: Mapped[str] = mapped_column(Text, index=True)
    scope: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, index=True, default="pending")
    progress: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
