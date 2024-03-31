from fastapi import FastAPI, Body
from solve import Determinant

solver = Determinant()

app = FastAPI()


@app.post("/captcha")
async def root(data=Body()):
    image = data.get('base64')
    return solver.get_angle(image)


@app.post("/status")
async def get_status():
    return {'status': 'success'}


@app.get("/solver_settings")
async def get_solver_settings():
    return solver.info()


@app.post("/change_settings")
async def solver_change_settings(data=Body()):
    solver.change_settings(data)


@app.get("/rebuild")
async def solver_rebuild():
    solver.rebuild()
