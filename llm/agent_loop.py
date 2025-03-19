import asyncio

global_loop = None

def get_agent_loop():
    """
    글로벌(전역) 이벤트 루프를 한 번만 생성해 재사용
    """
    global global_loop
    print(global_loop)
    if global_loop is None:
        global_loop = asyncio.new_event_loop()
        # 절대 loop.close() 하지 않음
    return global_loop