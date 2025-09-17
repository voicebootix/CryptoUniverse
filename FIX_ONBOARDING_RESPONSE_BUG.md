# Fix for Onboarding Response Bug

## Problem
When a user is already onboarded, the `onboard_new_user` method returns:
```python
{
    "success": True,
    "message": "User already onboarded", 
    "onboarding_id": onboarding_id,
    "skipped": True
}
```

But the API endpoint expects `user_id` to be in the response, causing a KeyError.

## Quick Fix

### File: `/workspace/app/services/user_onboarding_service.py`
### Line: 131-136

**Current:**
```python
return {
    "success": True,
    "message": "User already onboarded",
    "onboarding_id": onboarding_id,
    "skipped": True
}
```

**Fixed:**
```python
return {
    "success": True,
    "message": "User already onboarded",
    "onboarding_id": onboarding_id,
    "user_id": user_id,  # ADD THIS LINE
    "skipped": True
}
```

## Alternative Fix

### File: `/workspace/app/api/v1/endpoints/opportunity_discovery.py`
### Line: 389-393

Add a check for the skipped case:
```python
if onboarding_result.get("skipped"):
    return UserOnboardingResponse(
        success=True,
        onboarding_id=onboarding_result["onboarding_id"],
        user_id=str(current_user.id),  # Use current_user.id instead
        results={},
        execution_time_ms=0,
        onboarded_at=datetime.utcnow().isoformat(),
        next_steps=["User already onboarded"]
    )
```