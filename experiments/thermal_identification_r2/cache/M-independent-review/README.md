# TTO 0.2.4中等负载：独立实测核对

先读`独立核对.md`。本包只有独立复核结果和必要代码，不是安装包、修复版本或新训练模型。
原始实验包不重复嵌套，不含真实端点配置或请求正文。

## 重跑

在已有Python 3.10+和NumPy环境运行（无设备访问、不训练）：

```sh
OPENBLAS_NUM_THREADS=1 python review.py \
  --archive /path/to/TTO-0.2.4中等负载-完整实测证据.zip \
  --summary /path/to/runner-summary.json \
  --workdir /path/to/NEW-review-directory
```

`--summary`可省略，此时单独上传summary对比标为未执行。`--workdir`应选新目录。
脚本自行读取并解开输入归档、核对清单，复算请求/时序/资格并重放生产处理与两套健康判定。
不会启动采集器、请求器或任何网络服务。输入ZIP按SHA追溯，运行中不改原件。

结果数字是同一次实验的多层核验，不相加称多次独立实测。新研究起点覆盖不是历史已发G2预测。
