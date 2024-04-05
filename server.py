import time

from fastapi import FastAPI, Body
from solve import Determinant

solver = Determinant()
solver.rebuild()

app = FastAPI()

print("START SERVER")

@app.post("/captcha")
async def root(data=Body()):
    image = data.get('base64')
    curt = time.time()
    solve_data = await solver.get_angle(image)
    solve_data.update(await solver.info())
    endt = time.time()
    print(endt - curt)
    return solve_data


@app.post("/status")
async def get_status():
    return {'status': 'success'}


@app.get("/solver_settings")
async def get_solver_settings():
    info = await solver.info()
    return info


@app.post("/change_settings")
async def solver_change_settings(data=Body()):
    await solver.change_settings(data)


@app.get("/rebuild")
async def solver_rebuild():
    await solver.rebuild()
