from fastapi import APIRouter, HTTPException

from app.core.path import get_prefix_from_path
from app.services.events import events

router_prefix = get_prefix_from_path(__file__)
router = APIRouter(prefix=router_prefix, tags=[router_prefix])


@router.get(
    "/get_card_id",
    summary="Get the current card ID",
    description="Returns the card ID for the specified user.",
)
async def get_card_id():
    """
    Retrieve the current card ID.
    """
    try:
        return {"card_id": events.card_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# CRUD routes for user management based on card_id and user_id
@router.post(
    "/create_user",
    summary="Create a new user",
    description="Creates a new user with the provided user ID and card ID.",
)
async def create_user(user_id: str, card_id: str):
    """
    Create a new user in the system.
    """
    try:
        result = await events.create_user(user_id, card_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.put(
    "/update_user_card",
    summary="Update user's card ID",
    description="Updates the card ID associated with the given user ID.",
)
async def update_user_card(user_id: str, card_id: str):
    """
    Update the card ID for an existing user.
    """
    try:
        result = await events.update_user_card(user_id, card_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete(
    "/delete_user",
    summary="Delete a user",
    description="Deletes the user with the specified user ID.",
)
async def delete_user(user_id: str):
    """
    Delete a user from the system.
    """
    try:
        result = await events.delete_user(user_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/get_all_users",
    summary="Get all users",
    description="Retrieves information about all registered users.",
)
async def get_all_users():
    """
    Retrieve all users from the system.
    """
    try:
        users_list = await events.get_all_users()
        # Convert SQLAlchemy objects to dict format
        users_data = []
        for user in users_list:
            users_data.append({
                "user_id": user.user_id,
                "card_id": user.card_id
            })
        return {"users": users_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))