from concurrent.futures import ThreadPoolExecutor, as_completed

def run_concurrently(task_fn, data_list, max_workers=10):
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_data = {executor.submit(task_fn, item): item for item in data_list}
        for future in as_completed(future_to_data):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(e)
    return results