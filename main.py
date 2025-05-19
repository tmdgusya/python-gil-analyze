import random
import time
import threading
from threading import Thread
from viztracer import VizTracer # VizTracer import
import os

# CPU-bound 작업을 시뮬레이션하는 함수
# def work_cpu(label="", iterations=2):
#     """CPU를 많이 사용하는 작업을 시뮬레이션합니다."""
#     # 매우 긴 리스트를 생성하고 최소값을 찾는 작업
#     min_val = min([random.random() * 100 for _ in range(iterations)])
def work_cpu(label="", iterations=2):
    """CPU를 많이 사용하는 작업을 시뮬레이션합니다."""
    # yield 간격을 설정 (작은 값으로 설정하면 더 자주 전환)
    yield_interval = iterations // 100  # 전체 작업을 100번으로 나눔
    
    for i in range(0, iterations, yield_interval):
        # yield_interval 크기만큼의 작업 수행
        chunk = [random.random() * 100 for _ in range(min(yield_interval, iterations - i))]
        min_val = min(chunk)
        # 주기적으로 yield하여 다른 스레드에 실행 기회 제공
        if i + yield_interval < iterations:
            time.sleep(0)  # yield 효과를 내기 위한 짧은 sleep

# I/O-bound 작업을 시뮬레이션하는 함수
def work_io(label="", sleep_duration=0.5):
    """I/O 대기 작업을 시뮬레이션합니다. time.sleep()은 GIL을 해제합니다."""
    time.sleep(sleep_duration)

# --- 실행 함수들 ---

def run_single_thread_sequential_cpu(num_tasks=2, iterations_per_task=20_000_000):
    """단일 스레드에서 CPU 바운드 작업을 순차적으로 실행합니다."""
    for i in range(num_tasks):
        work_cpu(label=f"SingleCPU-{i+1}", iterations=iterations_per_task)

def run_multi_threaded_cpu(num_threads=2, iterations_per_task=20_000_000):
    """다중 스레드에서 CPU 바운드 작업을 실행합니다."""
    threads = []
    for i in range(num_threads):
        thread = Thread(target=work_cpu, args=(f"MultiCPU-Thread-{i+1}", iterations_per_task))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

def run_single_thread_sequential_io(num_tasks=4, sleep_per_task=0.5):
    """단일 스레드에서 I/O 바운드 작업을 순차적으로 실행합니다."""
    for i in range(num_tasks):
        work_io(label=f"SingleIO-{i+1}", sleep_duration=sleep_per_task)

def run_multi_threaded_io(num_threads=4, sleep_per_task=0.5):
    """다중 스레드에서 I/O 바운드 작업을 실행합니다."""
    threads = []
    for i in range(num_threads):
        thread = Thread(target=work_io, args=(f"MultiIO-Thread-{i+1}", sleep_per_task))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    # 분석을 위한 파라미터 (필요시 조정)
    # CPU 작업 반복 횟수를 줄여서 트레이스 파일 크기 및 시간 단축 가능
    # GIL 효과를 보려면 여전히 충분히 커야 함
    CPU_ITERATIONS = 500_00 # 기존 20_000_000에서 줄여서 테스트 시간 단축
    NUM_CPU_TASKS_OR_THREADS = 2

    IO_SLEEP_DURATION = 0.25 # IO 작업 시간 줄여서 테스트 시간 단축
    NUM_IO_TASKS_OR_THREADS = 4

    # --- 1. CPU-Bound, Single-Thread Sequential ---
    trace_file_single_cpu = "trace_single_thread_cpu.json"
    print(f"--- Tracing: Single-Thread Sequential (CPU-Bound) to {trace_file_single_cpu} ---")
    start_time = time.time()
    with VizTracer(output_file=trace_file_single_cpu, file_info=True, log_gc=True) as _: # tracer 변수 사용 안 할 시 _
        run_single_thread_sequential_cpu(num_tasks=NUM_CPU_TASKS_OR_THREADS, iterations_per_task=CPU_ITERATIONS)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.3f}s")
    print(f"Trace saved. To view: python -m viztracer {trace_file_single_cpu}\n")

    # --- 2. CPU-Bound, Multi-Thread ---
    # 이 시나리오에서 GIL의 영향을 가장 잘 관찰할 수 있습니다.
    trace_file_multi_cpu = "trace_multi_thread_cpu.json"
    print(f"--- Tracing: Multi-Thread (CPU-Bound) to {trace_file_multi_cpu} ---")
    start_time = time.time()
    # log_async=True는 스레드 활동을 더 잘 추적하는 데 도움이 될 수 있습니다.
    # max_stack_depth를 적절히 설정하여 너무 깊은 호출 스택으로 인한 성능 저하 방지 (기본값은 보통 괜찮음)
    with VizTracer(output_file=trace_file_multi_cpu, file_info=True, log_gc=True, log_async=True) as _:
        run_multi_threaded_cpu(num_threads=NUM_CPU_TASKS_OR_THREADS, iterations_per_task=CPU_ITERATIONS)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.3f}s")
    print(f"Trace saved. To view: python -m viztracer {trace_file_multi_cpu}\n")

    # --- 3. I/O-Bound, Single-Thread Sequential ---
    trace_file_single_io = "trace_single_thread_io.json"
    print(f"--- Tracing: Single-Thread Sequential (I/O-Bound) to {trace_file_single_io} ---")
    start_time = time.time()
    with VizTracer(output_file=trace_file_single_io, file_info=True, log_gc=True) as _:
        run_single_thread_sequential_io(num_tasks=NUM_IO_TASKS_OR_THREADS, sleep_per_task=IO_SLEEP_DURATION)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.3f}s")
    print(f"Trace saved. To view: python -m viztracer {trace_file_single_io}\n")

    # --- 4. I/O-Bound, Multi-Thread ---
    # 이 시나리오에서 스레드가 I/O 대기 중 GIL을 해제하여 다른 스레드가 실행되는 것을 관찰할 수 있습니다.
    trace_file_multi_io = "trace_multi_thread_io.json"
    print(f"--- Tracing: Multi-Thread (I/O-Bound) to {trace_file_multi_io} ---")
    start_time = time.time()
    with VizTracer(output_file=trace_file_multi_io, file_info=True, log_gc=True, log_async=True) as _:
        run_multi_threaded_io(num_threads=NUM_IO_TASKS_OR_THREADS, sleep_per_task=IO_SLEEP_DURATION)
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.3f}s")
    print(f"Trace saved. To view: python -m viztracer {trace_file_multi_io}\n")

    print("All tracing complete.")
    print("Open the generated .json files with 'python -m viztracer <filename.json>' to analyze.")