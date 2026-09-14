# 无正则输运依赖

直接使用 PythonOT/POT 的 C++ 网络单纯形内核, 不调用 Python。
来源: https://github.com/PythonOT/POT/tree/85113e9a380f5fcf684c50c73c1ff6a164a7366e/ot/lp
固定提交: `85113e9a380f5fcf684c50c73c1ff6a164a7366e` (`0.9.6.post1`)。
仅包含三个原样头文件, 许可证及 SHA-256 校验值。
版权与许可说明保留于各文件; POT 为 MIT, LEMON 衍生内核为宽松许可。
算法应用层位于 `src/transport/network_simplex.cpp`, 零权重源先剔除, 解后检查边际和对偶间隙。
