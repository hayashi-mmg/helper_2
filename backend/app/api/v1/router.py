from fastapi import APIRouter

from app.api.v1.endpoints import auth, menus, messages, pantry, qr, recipe_ingredients, recipes, shopping, tasks, users

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(recipe_ingredients.router)
api_router.include_router(recipes.router)
api_router.include_router(menus.router)
api_router.include_router(tasks.router)
api_router.include_router(messages.router)
api_router.include_router(shopping.router)
api_router.include_router(pantry.router)
api_router.include_router(qr.router)
