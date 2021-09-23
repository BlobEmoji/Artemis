import asyncio
import datetime

def daily(scheduled_time: datetime.time) -> int:
    current_time = datetime.datetime.utcnow()
    td = current_time - datetime.datetime.combine(datetime.datetime.utcnow().date(), scheduled_time)

    if td.total_seconds() < -59:
        return int(1-td.total_seconds())
    else:
        return int(86401-td.total_seconds())

async def async_scheduler(task, time, delay, *args, **kwargs):
    while True:
        try:
            await asyncio.sleep(delay(time))
            await task(*args, **kwargs)
        except TypeError as e:
            print(e)

async def do_daily(task, time, *args, **kwargs):
    return await async_scheduler(task, time, daily, *args, **kwargs)
