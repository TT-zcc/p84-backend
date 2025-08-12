# -*- coding: utf-8 -*-
"""
Database module

This module initializes the SQLAlchemy database object and provides
a base model class with a primary key (id).
"""

from .extensions import db

# Aliases for common SQLAlchemy objects
Column = db.Column
relationship = db.relationship


class PkModel(db.Model):
    """
    Abstract base model class with a primary key.

    Adds:
        - id (int): Primary key column.
    """
    __abstract__ = True
    id = Column(db.Integer, primary_key=True)

def reference_col(
    tablename, nullable=False, pk_name="id", foreign_key_kwargs=None, column_kwargs=None
):
    """
    Create a foreign key column referencing a primary key in another table.

    Args:
        tablename (str): Target table name.
        nullable (bool): Whether the foreign key can be null.
        pk_name (str): Primary key column name of the referenced table.
        foreign_key_kwargs (dict): Additional kwargs for ForeignKey.
        column_kwargs (dict): Additional kwargs for Column.

    Usage:
        ```python
        category_id = reference_col('category')
        category = relationship('Category', backref='categories')
        ```

    Returns:
        sqlalchemy.Column: A foreign key column definition.
    """
    foreign_key_kwargs = foreign_key_kwargs or {}
    column_kwargs = column_kwargs or {}

    return Column(
        db.ForeignKey(f"{tablename}.{pk_name}", **foreign_key_kwargs),
        nullable=nullable,
        **column_kwargs,
    )
