# Min-Max 归一化工具函数


def min_max_normalize(value, f_min, f_max):
    """Min-Max 归一化，将值映射到 [0, 1]

    参数:
        value: 待归一化的值
        f_min: 当前已知最小值
        f_max: 当前已知最大值
    返回:
        归一化后的值，当 f_max == f_min 时返回 0（除零保护）
    """
    if f_max == f_min:
        return 0.0
    return (value - f_min) / (f_max - f_min)
