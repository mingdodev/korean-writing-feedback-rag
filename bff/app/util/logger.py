import asyncio
import logging
from typing import Any, Callable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

DoneCallback = Callable[[asyncio.Task], None]

def log_task_exception(task: asyncio.Task[Any]) -> None:
    """
    백그라운드 태스크의 완료를 확인하고, 발생한 예외를 안전하게 로깅하는 콜백 함수입니다.
    
    이 함수는 asyncio.Task.add_done_callback()에 등록되어, 
    태스크가 완료되거나 실패했을 때 호출됩니다.
    
    Args:
        task (asyncio.Task): 완료된 asyncio 태스크 객체.
    """
    task_name = task.get_name() if task.get_name() else "Unnamed Task"
    
    print(f"\n[DEBUG_CB] Task '{task_name}' finished. Status: {task.done()}")

    try:
        # 1. 태스크가 성공적으로 완료되었는지 확인하고 결과를 가져옵니다. 
        result = task.result()
        print(f"[DEBUG_CB] Task '{task_name}' completed successfully. Result Type: {type(result)}")
    except asyncio.CancelledError:
        # 2. 태스크가 취소된 경우
        print(f"[DEBUG_CB] WARNING: Task '{task_name}' was cancelled.")
        logger.warning(f"Background task '{task.get_name()}' was cancelled.")
    except Exception as e:
        # 3. 태스크 실행 중 예외가 발생한 경우
        print(f"[DEBUG_CB] ERROR: Task '{task_name}' failed with an exception!")
        print(f"[DEBUG_CB] EXCEPTION TYPE: {type(e).__name__}")
        print(f"[DEBUG_CB] EXCEPTION DETAILS: {e}")
        logger.error(
            f"!!! Background Task Failed: '{task.get_name()}' !!!", 
            exc_info=e
        )
        
        # TODO: 별도의 알림 시스템(Slack, Sentry) 연동 로직을 추가