# Admin.py Async Fixes

## The Problem
The admin.py file uses synchronous SQLAlchemy queries (`db.query()`) with an AsyncSession, causing 500 errors.

## Quick Fix (Temporary)
To prevent 500 errors while we work on proper async conversion, we can add early returns:

```python
# At line 457, after the try:
        # TEMPORARY FIX: Return mock data until async conversion is complete
        logger.warning("Admin list_users endpoint using temporary mock response")
        return {
            "users": [],
            "total": 0,
            "skip": skip,
            "limit": limit,
            "stats": {
                "total_users": 0,
                "active_users": 0, 
                "trading_users": 0
            }
        }
```

## Proper Fix (What needs to be done)

### Line 458: Replace
```python
query = db.query(User)
```
With:
```python
from sqlalchemy import select, func
stmt = select(User)
```

### Lines 462-473: Replace filter patterns
```python
query = query.filter(User.status == status_filter)
```
With:
```python
stmt = stmt.filter(User.status == status_filter)
```

### Line 476: Replace count
```python
total_count = query.count()
```
With:
```python
count_result = await db.execute(select(func.count()).select_from(User))
total_count = count_result.scalar()
```

### Line 479: Replace query execution
```python
users = query.offset(skip).limit(limit).all()
```
With:
```python
stmt = stmt.offset(skip).limit(limit)
result = await db.execute(stmt)
users = result.scalars().all()
```

### Lines 482-486: Replace status counts
```python
active_count = db.query(User).filter(User.status == UserStatus.ACTIVE).count()
```
With:
```python
active_result = await db.execute(
    select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)
)
active_count = active_result.scalar()
```

## Other Functions Needing Similar Fixes
- `manage_user` (line 555): `db.query(User).filter().first()`
- `get_detailed_metrics` (lines 672-682): Multiple `db.query()` calls
- `get_audit_logs` (line 741): `db.query(AuditLog)`

## Recommendation
Due to the complexity of properly converting all these queries, I recommend:
1. Apply the temporary fix now to stop 500 errors
2. Create a separate PR for comprehensive async conversion
3. Test thoroughly before deploying