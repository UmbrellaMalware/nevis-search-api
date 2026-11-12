from sqlalchemy.exc import IntegrityError


def violated_constraint(exc: IntegrityError) -> str | None:
    """Name of the constraint or unique index that rejected the write, if Postgres reports one.

    IntegrityError on uq_clients_email_lower -> "uq_clients_email_lower"
    """
    # SQLAlchemy wraps the driver error; asyncpg exposes the constraint/index name on the cause.
    driver_error = exc.orig.__cause__ if exc.orig is not None else None
    name = getattr(driver_error, "constraint_name", None)
    return name if isinstance(name, str) else None
