"""
Customer and Order models.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date
from uuid import UUID


class Customer(BaseModel):
    """Customer information."""
    customer_id: Optional[UUID] = Field(None, description="Unique customer identifier")
    customer_name: str = Field(..., description="Customer full name")
    customer_email: EmailStr = Field(..., description="Customer email address")


class Order(BaseModel):
    """Order information."""
    order_id: Optional[UUID] = Field(None, description="Unique order identifier")
    order_date: Optional[date] = Field(None, description="Date order was placed")
    requested_delivery_date: Optional[date] = Field(None, description="Requested delivery date")
    customer: Customer = Field(..., description="Customer information")
    structure_hash: Optional[str] = Field(None, description="SHA-256 hash of the structure data")
    # structure will be referenced from structure.py to avoid circular imports
