# 接口样例使用说明

四份example全部是本包生成的**合成接口测试数据**，不来自实时设备，也不用于模型效果宣传。tracking数字仅说明结构。部署不得默认回退到example，演示/回放必须明确标识且不连接设备。

dashboard.schema.json约束公开snapshot基本类型；03接口合同还约束无法只靠JSON Schema表示的关系：目标=起点+时距、error=预测−实测、同run/clock、无效撤销、成熟标签及数据拥有权。模型/provider细节在独立GET接口返回，snapshot只承载UI所需摘要，不允许借extra raw JSON泄露凭据。

Phase与模型置信度不是同义。公开calibrated_confidence强制null，当前没有真实校准定义，不允许填虚构0—1数。

节点图是当前模型关系模板：只有相应provider/依赖有效时才启用对应边；future advisory尚无映射不表示已经在真实核心里实现。
