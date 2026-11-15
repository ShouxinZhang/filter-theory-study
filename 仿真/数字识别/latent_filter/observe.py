"""观测模型：窗口按从左到右、从上到下扫描图像，每步揭示一个窗口内的带噪像素。"""
import torch


def window_masks(window: int, device):
    """返回 (单步掩码, 累积掩码)，形状均为 [K, 784]，取值 0/1。"""
    g = 28 // window
    masks = torch.zeros(g * g, 28, 28, device=device)
    for k in range(g * g):
        r, c = divmod(k, g)
        masks[k, r * window:(r + 1) * window, c * window:(c + 1) * window] = 1
    masks = masks.flatten(1)
    return masks, masks.cumsum(0).clamp_(max=1)


def log_likelihood(x_hat, y_full, mask, sigma):
    """高斯观测的对数似然（差一个常数）。

    x_hat: [B, N, 784] 还原出的粒子图像；y_full: [B, 784] 带噪完整图像；mask: [784]。
    """
    diff = (x_hat - y_full[:, None]) * mask
    return -diff.square().sum(-1) / (2 * sigma ** 2)
