import matplotlib.pyplot as plt
import numpy as np

# 支持中文显示
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# --- 数据定义 ---

# 测试场景1.1: 以图搜图响应时间
image_search_metrics = ['平均响应时间', 'P90响应时间']
image_search_targets = [1.00, 1.25]     # 预期目标 (秒)
image_search_actuals = [0.85, 1.02] # 实际结果 (秒)

# 测试场景1.2: 以文搜图响应时间
text_search_metrics = ['平均响应时间', 'P90响应时间']
text_search_targets = [1.00, 1.25]
text_search_actuals = [0.73, 0.98]

# --- 绘图函数 (蓝-橙配色 & 窄柱宽) ---
def plot_performance_chart(title, metrics, targets, actuals):
    x = np.arange(len(metrics))
    width = 0.2  # 调细柱宽

    fig, ax = plt.subplots(figsize=(10, 7))

    # 蓝-橙色
    color_target = 'tab:blue'    # 预期目标
    color_actual = 'tab:orange'  # 实际测试

    rects1 = ax.bar(x - width/2, targets, width,
                    label='预期目标值', color=color_target, alpha=0.85)
    rects2 = ax.bar(x + width/2, actuals, width,
                    label='实际测试值', color=color_actual, alpha=0.85)

    ax.set_ylabel('时间 (秒)', fontsize=13, labelpad=10)
    ax.set_title(title, fontsize=16, pad=20, weight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(metrics, fontsize=12)
    ax.legend(fontsize=11, loc='upper right')

    # 留出空间给标签
    ax.set_ylim(0, max(max(targets), max(actuals)) * 1.15)

    # 在柱顶加数值
    def autolabel(rects):
        for rect in rects:
            h = rect.get_height()
            ax.annotate(f'{h:.2f}',
                        xy=(rect.get_x() + rect.get_width()/2, h),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=10)

    autolabel(rects1)
    autolabel(rects2)

    # 移除上、右边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.grid(axis='y', linestyle=':', linewidth=0.7, alpha=0.7, color='gray')
    fig.tight_layout()
    plt.savefig(f"{title.replace(' ', '_').replace(':','')}.png",
                dpi=300, bbox_inches='tight')
    plt.show()

# --- 生成图表 ---
plot_performance_chart(
    title='以图搜图响应时间性能',
    metrics=image_search_metrics,
    targets=image_search_targets,
    actuals=image_search_actuals
)

plot_performance_chart(
    title='以文搜图响应时间性能',
    metrics=text_search_metrics,
    targets=text_search_targets,
    actuals=text_search_actuals
)

print("蓝-橙色柱状图已生成并保存。")