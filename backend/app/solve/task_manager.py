# 算法任务线程管理器 —— 异步执行算法求解，支持 SSE 消息队列
import uuid
import threading
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor


class TaskManager:
    """管理算法求解任务的生命周期

    每个任务在独立线程中运行，通过 Queue 向 SSE 端点推送进度消息。
    """

    def __init__(self, max_workers=4):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._tasks = {}  # task_id → TaskInfo
        self._lock = threading.Lock()

    def submit(self, fn, *args, **kwargs):
        """提交一个算法求解任务

        参数:
            fn: 可调用对象，签名 fn(callback, *args, **kwargs)
        返回:
            task_id: 任务唯一标识
        """
        task_id = uuid.uuid4().hex[:12]
        queue = Queue()
        info = {
            "id": task_id,
            "queue": queue,
            "result": None,
            "error": None,
            "done": False,
        }

        with self._lock:
            self._tasks[task_id] = info

        def wrapper():
            try:
                result = fn(callback=lambda msg: queue.put(msg),
                            *args, **kwargs)
                info["result"] = result
            except Exception as e:
                info["error"] = str(e)
                queue.put({"type": "error", "message": str(e)})
            finally:
                info["done"] = True
                queue.put(None)  # 哨兵值，通知 SSE 结束

        self._executor.submit(wrapper)
        return task_id

    def get(self, task_id):
        """获取任务信息

        返回:
            dict 或 None（任务不存在时）
        """
        with self._lock:
            return self._tasks.get(task_id)

    def iter_messages(self, task_id, timeout=60):
        """迭代获取任务的 SSE 消息

        参数:
            task_id: 任务ID
            timeout: 单条消息等待超时（秒）
        生成:
            dict 消息，直到收到 None 哨兵值
        """
        info = self.get(task_id)
        if info is None:
            return

        queue = info["queue"]
        while True:
            try:
                msg = queue.get(timeout=timeout)
            except Empty:
                break
            if msg is None:
                break
            yield msg

    def get_result(self, task_id):
        """获取已完成任务的结果

        返回:
            (result, error) 元组
        """
        info = self.get(task_id)
        if info is None:
            return None, "任务不存在"
        if not info["done"]:
            return None, "任务尚未完成"
        return info["result"], info["error"]


# 全局单例
task_manager = TaskManager()
