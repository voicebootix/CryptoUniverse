"""
Fixed list_users function - Replace lines 439-520 in admin.py with this code
"""

# This is the complete PROPER async version of list_users function
# This file contains the fixed list_users function
# DO NOT IMPORT - for reference only

FIXED_FUNCTION = '''@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_database),
    current_user: User = Depends(require_role([UserRole.ADMIN]))
) -> UserListResponse:
    """
    List all users with filtering and pagination.
    Admin only endpoint.
    """
    logger.info(
        "Listing users",
        user_id=str(current_user.id)
    )
    
    try:
        from sqlalchemy import select, func, or_, and_
        
        # Build the base query
        stmt = select(User)
        
        # Track filter conditions for count query
        filter_conditions = []
        
        # Apply filters
        if status_filter:
            condition = User.status == status_filter
            stmt = stmt.filter(condition)
            filter_conditions.append(condition)
        
        if role_filter:
            condition = User.role == role_filter
            stmt = stmt.filter(condition)
            filter_conditions.append(condition)
        
        if search:
            condition = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            stmt = stmt.filter(condition)
            filter_conditions.append(condition)
        
        # Get total count with filters
        count_stmt = select(func.count()).select_from(User)
        if filter_conditions:
            count_stmt = count_stmt.filter(and_(*filter_conditions))
        
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar() or 0
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Count by status - proper async
        active_count_result = await db.execute(
            select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)
        )
        active_count = active_count_result.scalar() or 0
        
        trading_count_result = await db.execute(
            select(func.count()).select_from(User).filter(
                and_(
                    User.status == UserStatus.ACTIVE,
                    User.role.in_([UserRole.TRADER, UserRole.ADMIN])
                )
            )
        )
        trading_count = trading_count_result.scalar() or 0
        
        # Format user data
        user_list = []
        for user in users:
            user_data = {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role.value,
                "status": user.status.value,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None
            }
            
            # Get credit balance - async
            credit_result = await db.execute(
                select(CreditAccount).filter(CreditAccount.user_id == user.id)
            )
            credit_account = credit_result.scalar_one_or_none()
            user_data["credits"] = credit_account.available_credits if credit_account else 0
            
            # Get trading stats - async
            trade_count_result = await db.execute(
                select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)
            )
            trade_count = trade_count_result.scalar() or 0
            user_data["total_trades"] = trade_count
            
            user_list.append(user_data)
        
        return UserListResponse(
            users=user_list,
            total_count=total_count,
            active_count=active_count,
            trading_count=trading_count
        )
        
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )'''

if __name__ == "__main__":
    print("Replace the list_users function in admin.py with the code above")
    print("This is production-ready async code")