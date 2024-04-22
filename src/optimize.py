def optimize_target_queue(target_queue):
    sub_target_queues = []

    last_center = None
    temp_taget_queue = []

    for idx in range(len(target_queue) + 1):
        if idx == len(target_queue) or (target_queue[idx]["type"] == "CENTER" and last_center != target_queue[idx]["id"]):
            if last_center is not None:
                temp_taget_queue.insert(0, last_center)
            sub_target_queues.append(temp_taget_queue)
            if idx >= len(target_queue):
                break
            temp_taget_queue = []
            last_center = target_queue[idx]["id"]
        elif target_queue[idx]["type"] == "CENTER" and last_center == target_queue[idx]["id"]:
            continue
        else:
            temp_taget_queue.append(target_queue[idx])


if __name__ == "__main__":
    target_queue = [
        {"type": "ORDER", "id": "order1_1"},
        {"type": "ORDER", "id": "order1_2"},
        {"type": "CENTER", "id": "center1"},
        {"type": "ORDER", "id": "order2_1"},
        {"type": "ORDER", "id": "order2_2"},
        {"type": "CENTER", "id": "center1"},
        {"type": "ORDER", "id": "order3_1"},
        {"type": "ORDER", "id": "order3_2"},
        {"type": "CENTER", "id": "center2"},
        {"type": "ORDER", "id": "order4_1"},
        {"type": "ORDER", "id": "order4_2"},
        {"type": "CENTER", "id": "center1"},
        {"type": "ORDER", "id": "order5_1"},
        {"type": "ORDER", "id": "order5_2"},
    ]

    optimize_target_queue(target_queue)
