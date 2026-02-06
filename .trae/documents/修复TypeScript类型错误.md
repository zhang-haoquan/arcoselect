## 修复计划

修复 `ChartConfigModal.vue` 中的 59 个 TypeScript 类型错误：

### 1. 修复对象 undefined 检查 (约40处)
- 在访问 `countMap[xValue][groupValue]`、`valueMap[x][g]` 等嵌套对象时添加非空检查
- 使用可选链操作符或默认值确保类型安全

### 2. 修复 animationEasing 类型 (4处)
- 将 `animationEasing: 'cubicOut'` 改为 ECharts 支持的具体类型
- 需要将 series 配置对象的类型显式声明或使用 `as const` 断言

### 3. 修复未使用变量 (1处)
- 将 `(newVal, oldVal)` 改为 `(newVal, _oldVal)` 或删除 `oldVal`

### 修改文件
- `d:\traeproject\arcoselect\src\components\ChartConfigModal.vue`

修复后运行 `npm run build` 验证。