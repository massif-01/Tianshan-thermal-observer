# TTO 中等负载测试操作卡

**0.2.4候选｜TTO-MIDLOAD-DEV-v1.0｜先独立复审，再由用户确认现场窗口。下面现场命令本轮未执行。**

1. 把本次 `TTO-v1-0.2.4-R1-R2返修-Conda安装候选.zip` 放到N305的 `~/Downloads/`，在已初始化Conda的终端安装到新目录。保留原 `~/TTO`。

   ```sh
   mkdir -p "$HOME/TTO-midload-prep-r1-r2"
   unzip -n "$HOME/Downloads/TTO-v1-0.2.4-R1-R2返修-Conda安装候选.zip" -d "$HOME/TTO-midload-prep-r1-r2"
   sh "$HOME/TTO-midload-prep-r1-r2/TTO-v1-0.2.4-Conda安装包/install.sh" --prefix "$HOME/TTO-midload-0.2.4"
   "$HOME/TTO-midload-0.2.4/tto" doctor --config "$HOME/TTO-midload-0.2.4/config/local.json"
   ```

2. 先用安装生成的隔离入口运行离线预览。它显示实际TTO版本和导入位置，不访问设备，不读凭据。plan、dry-run和现场命令都用同一tto-midload入口，不直接运行Python脚本。现场配置复用旧 `~/TTO/config/local.json`；推理配置已按旧记录填入本地候选的 `site/local-midload.json`。尚未现场确认端点、驻留或空闲，原AUTO、曲线、gain、保护必须保持，其他任务停止。

   ```sh
   "$HOME/TTO-midload-0.2.4/tto-midload" --plan --trial-config "$HOME/TTO-midload-prep-r1-r2/TTO-v1-0.2.4-Conda安装包/site/local-midload.json" --tto-config "$HOME/TTO/config/local.json"
   ```

3. **仅在复审通过、用户确认现场窗口后**，运行下面一条命令。先记录600秒背景；前180秒在同一采集流检查，首个工作块前须有近期60秒完整输入。依次20/60/180秒单路发起窗口，回落420/600/600秒；已有请求自然结束再计回落。约41分20秒，总上限45分钟。无需逐题打点。

   ```sh
   "$HOME/TTO-midload-0.2.4/tto-midload" --live --trial-config "$HOME/TTO-midload-prep-r1-r2/TTO-v1-0.2.4-Conda安装包/site/local-midload.json" --tto-config "$HOME/TTO/config/local.json" --output-root "$HOME/TTO-midload-0.2.4/trials"
   ```

4. 数据缺口会暂停新请求；明确异常、采集退出或超时会停止后续负载。需要手动停止时按 **Ctrl-C一次**。客户端退出不能证明服务器计算结束；若提示“最后一条请求是否结束仍未确认”，不要重启或叠加测试，用现有服务方式人工确认。不要杀推理服务、重启设备或改风扇。结束时交回终端给出的 `~/TTO-midload-0.2.4/trials/midload-…/trial-result.zip`；未完成的记录也要交回。

**回退：**停止本runner后，保留新候选和结果，继续使用原 `~/TTO/tto` 入口；未替换旧环境、配置或服务，无需重启。现场若没有室温读数，保留null并说明热前史，结果仅属缺边界观测的开发数据。可选环境侧文件与离线安装方法见《TTO中等负载候选安装说明.md》。
