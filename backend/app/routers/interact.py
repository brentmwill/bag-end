from fastapi import APIRouter

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
