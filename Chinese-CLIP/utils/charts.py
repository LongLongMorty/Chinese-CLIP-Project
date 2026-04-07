import matplotlib.pyplot as plt
import numpy as np

# 支持中文显示 (根据您的操作系统和matplotlib配置，可能需要调整字体)
plt.rcParams['font.sans-serif'] = ['SimHei']  # 使用黑体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号'-'显示为方块的问题

# --- 数据定义 ---

# 测试场景1.1: 以图搜图响应时间
image_search_metrics = ['平均响应时间', 'P90响应时间']
image_search_targets = [3, 4]  # 预期目标 (秒)
image_search_actuals = [2.65, 3.1]  # 实际结果 (秒)

# 测试场景1.2: 以文搜图平均响应时间
text_search_metrics = ['平均响应时间', 'P90响应时间']
text_search_targets = [2, 2.5]  # 预期目标 (秒)
text_search_actuals = [1.72, 2.1]  # 实际结果 (秒)

# --- 绘图函数 ---
def plot_performance_chart(title, metrics, targets, actuals, figure_number):
    x = np.arange(len(metrics))  # aabel 位置
    width = 0.35  # bar 宽度

    fig, ax = plt.subplots(figsize=(10, 6)) # 可以调整图形大小
    rects1 = ax.bar(x - width/2, targets, width, label='预期目标值', color='skyblue', alpha=0.8)
    rects2 = ax.bar(x + width/2, actuals, width, label='实际测试值', color='lightcoral', alpha=0.8)

    # 添加文本标签、标题和自定义x轴刻度标签等
    ax.set_ylabel('时间 (秒)', fontsize=12)
    ax.set_title(title, fontsize=16, pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=12)
    ax.legend(fontsize=10)

    # 在bar上显示数值
    def autolabel(rects):
        for rect in rects:
            height = rect.get_height()
            ax.annotate('{}'.format(round(height, 2)),
                        xy=(rect.get_x() + rect.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)

    autolabel(rects1)
    autolabel(rects2)

    fig.tight_layout() # 调整整体布局，防止标签重叠
    plt.grid(axis='y', linestyle='--', alpha=0.7) # 添加水平网格线
    plt.savefig(f"{title.replace(' ', '_')}.png", dpi=300) # 保存图片
    plt.show()

# --- 生成图表 ---

# 图1: 以图搜图响应时间性能
plot_performance_chart(
    title='图6.8.1 以图搜图响应时间性能',
    metrics=image_search_metrics,
    targets=image_search_targets,
    actuals=image_search_actuals,
    figure_number=1
)

# 图2: 以文搜图响应时间性能
plot_performance_chart(
    title='图6.8.2 以文搜图响应时间性能',
    metrics=text_search_metrics,
    targets=text_search_targets,
    actuals=text_search_actuals,
    figure_number=2
)

print("图表已生成并显示。如果配置正确，也会保存为PNG文件。")

if __name__ == "__main__":
    main()