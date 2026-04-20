"""Standalone scene generation worker.

Runs independently from the API server. Polls queued tasks and processes them.
Supports multiple parallel workers for higher throughput.

Usage:
    cd backend
    python scripts/run_scene_worker.py                        # run once, exit when idle
    python scripts/run_scene_worker.py --daemon               # run continuously
    python scripts/run_scene_worker.py --daemon --workers 3   # 3 parallel workers
    python scripts/run_scene_worker.py --poll 5               # custom poll interval
"""

import argparse
import multiprocessing
import os
import signal
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.settings import (
    CORE100_MODEL,
    CORE100_TTS_URL,
    GENERATED_DIR,
    TASKS_FILE,
    UPLOADS_DIR,
    UPLOADS_FILE,
    WORKER_POLL_INTERVAL,
    ZHIPUAI_API_KEY,
)
from app.scene_store_factory import create_generated_scene_store, create_public_scene_store
from app.task_store import TaskStore
from app.upload_store import UploadStore
from app.worker_runner import InlineSceneWorker


def create_worker(poll_interval: float) -> InlineSceneWorker:
    task_store = TaskStore(TASKS_FILE, cross_process=True)
    upload_store = UploadStore(UPLOADS_FILE, UPLOADS_DIR)
    generated_store = create_generated_scene_store()
    public_store = create_public_scene_store()

    return InlineSceneWorker(
        task_store=task_store,
        upload_store=upload_store,
        generated_scene_store=generated_store,
        generated_root=GENERATED_DIR,
        tts_url=CORE100_TTS_URL,
        model=CORE100_MODEL,
        public_scene_store=public_store,
        api_key=ZHIPUAI_API_KEY,
        poll_interval=poll_interval,
    )


def run_once(poll_interval: float) -> int:
    """Process all queued tasks once, then exit. Returns count of processed tasks."""
    task_store = TaskStore(TASKS_FILE, cross_process=True)
    task_store.requeue_unfinished_tasks()
    worker = create_worker(poll_interval)

    processed = 0
    while True:
        task = task_store.claim_next_task()
        if not task:
            break
        print(f'[worker-{os.getpid()}] Processing: {task["taskId"]} ({task.get("title") or task.get("uploadId", "")})')
        worker._process_task(task)
        processed += 1
        print(f'[worker-{os.getpid()}] Completed: {task["taskId"]}')

    return processed


def run_daemon_worker(worker_id: int, poll_interval: float) -> None:
    """Entry point for a single daemon worker process."""
    worker = create_worker(poll_interval)
    task_store = TaskStore(TASKS_FILE, cross_process=True)

    # Only the first worker requeues stuck tasks
    if worker_id == 0:
        task_store.requeue_unfinished_tasks()

    print(f'[worker-{worker_id} pid={os.getpid()}] Started (daemon mode, poll={poll_interval}s)')

    stop = multiprocessing.Event()

    def handle_signal(signum, frame):
        stop.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while not stop.is_set():
        task = task_store.claim_next_task()
        if not task:
            stop.wait(poll_interval)
            continue
        print(f'[worker-{worker_id}] Processing: {task["taskId"]}')
        try:
            worker._process_task(task)
            print(f'[worker-{worker_id}] Completed: {task["taskId"]}')
        except Exception as exc:
            print(f'[worker-{worker_id}] Failed: {task["taskId"]} - {exc}')

    print(f'[worker-{worker_id}] Stopped.')


def main() -> None:
    parser = argparse.ArgumentParser(description='Scene generation worker')
    parser.add_argument('--daemon', action='store_true', help='Run continuously (default: exit when no tasks)')
    parser.add_argument('--poll', type=float, default=WORKER_POLL_INTERVAL, help='Poll interval in seconds')
    parser.add_argument('--workers', type=int, default=1, help='Number of parallel workers (daemon mode only)')
    args = parser.parse_args()

    workers = max(1, args.workers)

    print(f'Scene Worker | model={CORE100_MODEL} | tts={CORE100_TTS_URL} | poll={args.poll}s | workers={workers}')

    if not args.daemon:
        # Single-shot mode: process all queued tasks, then exit
        count = run_once(args.poll)
        if count == 0:
            print('No queued tasks found.')
        else:
            print(f'Processed {count} task(s).')
        return

    # Daemon mode with multiple workers
    if workers == 1:
        run_daemon_worker(0, args.poll)
    else:
        print(f'Starting {workers} parallel workers...')
        processes = []
        for i in range(workers):
            p = multiprocessing.Process(
                target=run_daemon_worker,
                args=(i, args.poll),
                name=f'scene-worker-{i}',
                daemon=True,
            )
            p.start()
            processes.append(p)
            print(f'  Started worker-{i} (pid={p.pid})')

        # Wait for any worker to exit (shouldn't happen unless error)
        try:
            for p in processes:
                p.join()
        except KeyboardInterrupt:
            print('\nShutting down all workers...')
            for p in processes:
                p.terminate()
            for p in processes:
                p.join(timeout=5)
            print('All workers stopped.')


if __name__ == '__main__':
    main()
