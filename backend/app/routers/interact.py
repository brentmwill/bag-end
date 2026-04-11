from fastapi import APIRouter
from app.services.trello import complete_task

router = APIRouter()


@router.get("/api/interact")
async def get_interact():
    return {
        "recipes": [],       # TODO: return recent/featured recipes
        "meal_plan": [],     # TODO: return current week meal plan
        "tasks": [],         # TODO: return Trello tasks
        "grocery_list": [],  # TODO: return AnyList grocery list
        "freezer": [],       # TODO: return freezer inventory
    }


@router.post("/api/tasks/{card_id}/complete")
async def complete_trello_task(card_id: str):
    ok = await complete_task(card_id)
    return {"ok": ok}
