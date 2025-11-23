# import asyncio
# from app.db.session import engine, Base
# from app.models.user import User
# from app.models.project import Project
# from app.models.module import Module
# from app.models.page import Page
# from app.models.element import PageElement
# from app.models.case import TestCase
# from app.models.suite import TestSuite

# async def reset_db():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.drop_all)
#         await conn.run_sync(Base.metadata.create_all)
#     print("Database reset successfully.")

# if __name__ == "__main__":
#     asyncio.run(reset_db())
