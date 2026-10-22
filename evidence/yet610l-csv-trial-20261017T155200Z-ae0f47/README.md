# YET-610L 仪表CSV试录

编号：yet610l-csv-trial-20261017T155200Z-ae0f47

状态：准备完成，等待明确“试录开始”；尚无开始/结束事件或CSV。无TTO采集、无推理负载。

原CSV接收：original-csv/；原字节及SHA保留。实际文件到达后建立真实格式映射并使用既有ref.py import导入，结果存normalized/，核对说明存checks/。暂不登记未知通道、时间格式或虚构时钟锚点。

开始/结束另追加operation-events.jsonl，保存实际落盘UTC、主机时区/身份、同机单调时钟；消息时间不可读取则null，手动近似误差未知，不把按钮时间当首末样本。
