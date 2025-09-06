# Fixed version of list_users function for admin.py
# Replace the existing function (lines ~439-520) with this:

@router.get("/users", response_model=UserListResponse)
async def list_users(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin)
) -> UserListResponse:
    """
    List all users with filtering and pagination.
    Admin only endpoint.
    """
    logger.info(
        "Listing users",
        admin_id=current_user.id,
        filters={
            "status": status_filter,
            "role": role_filter,
            "search": search
        }
    )
    
    try:
        from sqlalchemy import select, func, or_, and_
        
        # Build base query
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)
        
        # Apply filters
        if status_filter:
            stmt = stmt.filter(User.status == status_filter)
            count_stmt = count_stmt.filter(User.status == status_filter)
        
        if role_filter:
            stmt = stmt.filter(User.role == role_filter)
            count_stmt = count_stmt.filter(User.role == role_filter)
        
        if search:
            search_filter = or_(
                User.email.ilike(f"%{search}%"),
                User.full_name.ilike(f"%{search}%")
            )
            stmt = stmt.filter(search_filter)
            count_stmt = count_stmt.filter(search_filter)
        
        # Get total count
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar()
        
        # Get paginated results
        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        # Count by status - using async
        active_count_result = await db.execute(
            select(func.count()).select_from(User).filter(User.status == UserStatus.ACTIVE)
        )
        active_count = active_count_result.scalar()
        
        trading_count_result = await db.execute(
            select(func.count()).select_from(User).filter(
                and_(
                    User.status == UserStatus.ACTIVE,
                    User.role.in_([UserRole.TRADER, UserRole.ADMIN])
                )
            )
        )
        trading_count = trading_count_result.scalar()
        
        # Build response
        user_list = []
        for user in users:
            user_data = {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "status": user.status,
                "created_at": user.created_at,
                "last_login": user.last_login
            }
            
            # Get credit balance - using async
            credit_result = await db.execute(
                select(CreditAccount).filter(CreditAccount.user_id == user.id)
            )
            credit_account = credit_result.scalar_one_or_none()
            user_data["credits"] = credit_account.available_credits if credit_account else 0
            
            # Get trading stats - using async
            trade_count_result = await db.execute(
                select(func.count()).select_from(Trade).filter(Trade.user_id == user.id)
            )
            trade_count = trade_count_result.scalar()
            user_data["total_trades"] = trade_count
            
            user_list.append(user_data)
        
        return UserListResponse(
            users=user_list,
            total=total_count,
            skip=skip,
            limit=limit,
            stats={
                "total_users": total_count,
                "active_users": active_count,
                "trading_users": trading_count
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to list users: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )