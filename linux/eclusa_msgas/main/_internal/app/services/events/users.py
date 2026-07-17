from app.db.database import database_engine
from app.models.rfid import DbUser
import logging
from sqlalchemy.future import select
from sqlalchemy import delete, update

class Users:
    async def create_user(self, user_id: str, card_id: str):
        """
        Create a new user in the system.
        """
        try:
            async with database_engine.get_db() as db:
                new_user = DbUser(user_id=user_id, card_id=card_id)
                db.add(new_user)
                await db.commit()
            return {"msg": "User created successfully", "user_id": user_id, "card_id": card_id}
        except Exception as e:
            logging.error(f"Error creating user: {e}")
            return {"msg": "Error creating user", "error": str(e)}
        
    
    async def get_user_by_card(self, card_id: str):
        """
        Retrieve a user by their card ID.
        """
        try:
            async with database_engine.get_db() as db:
                stmt = select(DbUser).where(DbUser.card_id == card_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                if user:
                    logging.info(f"User found for card {card_id}: {user.user_id}")
                    return user
                else:
                    logging.info(f"No user found for card {card_id}")
                    return None
        except Exception as e:
            logging.error(f"Error retrieving user by card {card_id}: {e}")
            return None
    
    async def delete_user(self, user_id: str):
        """
        Delete a user by their user ID.
        """
        try:
            async with database_engine.get_db() as db:
                stmt = delete(DbUser).where(DbUser.user_id == user_id)
                await db.execute(stmt)
                await db.commit()
            logging.info(f"User {user_id} deleted successfully")
            return {"msg": "User deleted successfully", "user_id": user_id}
        except Exception as e:
            logging.error(f"Error deleting user {user_id}: {e}")
            return {"msg": "Error deleting user", "error": str(e)}
        
    async def update_user_card(self, user_id: str, new_card_id: str):
        """
        Update a user's card ID.
        """
        try:
            async with database_engine.get_db() as db:
                stmt = update(DbUser).where(DbUser.user_id == user_id).values(card_id=new_card_id)
                await db.execute(stmt)
                await db.commit()
            logging.info(f"User {user_id} card updated to {new_card_id}")
            return {"msg": "User card updated successfully", "user_id": user_id, "new_card_id": new_card_id}
        except Exception as e:
            logging.error(f"Error updating card for user {user_id}: {e}")
            return {"msg": "Error updating user card", "error": str(e)}
        
    async def get_all_users(self):
        """
        Retrieve all users in the system.
        """
        try:
            async with database_engine.get_db() as db:
                stmt = select(DbUser)
                result = await db.execute(stmt)
                users = result.scalars().all()
                logging.info(f"Retrieved {len(users)} users from the database")
                return users
        except Exception as e:
            logging.error(f"Error retrieving all users: {e}")
            return []