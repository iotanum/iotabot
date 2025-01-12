from sqlalchemy import BigInteger
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    type_annotation_map = {
        int: BigInteger,
    }
