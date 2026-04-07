<template>
  <div class="taobao-favorites">
    <div class="tb-header">
      <div class="tb-logo">
        <h1>Chinese-CLIP商品检索系统</h1>
      </div>
      <div class="tb-user-info">
        <span v-if="user" class="username">
          <el-icon><User/></el-icon> {{ user.username }}
        </span>
        <el-button type="text" class="logout-btn" @click="handleLogout">退出登录</el-button>
      </div>
    </div>

    <div class="tb-nav ">
      <!-- 使用普通div和点击事件实现路由导航 -->
      <div
        class="tb-nav-item"
        @click="navigateToSearch"
      >
        <el-icon>
          <Search/>
        </el-icon>
        商品搜索
      </div>
      <div class="tb-nav-item tb-active">
        <el-icon>
          <Star/>
        </el-icon>
        我的收藏
      </div>
      <div
        class="tb-nav-item"
        @click="router.replace('/recommend')"
      >
        <el-icon>
          <MagicStick/>
        </el-icon>
        猜你喜欢
      </div>
    </div>

    <div class="tb-favorites-container">
      <div class="tb-favorites-header">
        <h2>我的收藏</h2>
        <span class="tb-favorites-count" v-if="favorites.length > 0">共 {{ favorites.length }} 件商品</span>
      </div>

      <div class="tb-loading-wrapper" v-if="loading">
        <el-icon class="tb-loading-icon" :size="32">
          <Loading/>
        </el-icon>
        <div class="tb-loading-text">正在加载收藏商品，请稍候...</div>
      </div>

      <div class="tb-results tb-favorites-list" v-else-if="favorites.length">
        <div
          v-for="(item, index) in paginatedFavorites"
          :key="index"
          class="tb-item tb-favorite-item"
          @click="handleProductClick(item)"
        >
          <div class="tb-item-image">
            <img :src="'http://localhost:5000' + item.image_url" :alt="'商品' + (index + 1)">
          </div>
          <div class="tb-item-info">
            <div class="tb-item-price">¥ {{ formatPrice(item.price) }}</div>
            <div class="tb-item-title" :title="item.description">
              {{ item.description || '商品 ' + item.product_code }}
            </div>
            <div class="tb-item-shop">智能搜索旗舰店</div>
            <div class="tb-item-footer">
              <span class="tb-item-add-time">收藏于 {{ formatDate(item.created_at) }}</span>
            </div>
          </div>
          <div class="tb-item-actions">
            <el-button
              type="danger"
              size="small"
              icon="Delete"
              circle
              @click.stop="removeFromFavorites(item.product_code)"
              :loading="removingItem === item.product_code"
            ></el-button>
          </div>
        </div>
      </div>

      <div class="tb-empty-favorites" v-else-if="!loading">
        <el-empty description="暂无收藏商品">
          <template #extra>
            <el-button type="primary" @click="goToSearch">去逛逛</el-button>
          </template>
        </el-empty>
      </div>

      <!-- 分页组件 -->
      <div class="tb-pagination-container" v-if="favorites.length > 0">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="favorites.length"
          layout="prev, pager, next, jumper, total"
          background
          @current-change="handlePageChange"
          class="tb-pagination"
        />
      </div>
    </div>

    <!-- 商品详情对话框 - 修改为与ImageSearch中相同的实现 -->
    <el-dialog
      v-model="dialogVisible"
      title="商品详情"
      width="80%"
      :destroy-on-close="true"
      :before-close="handleCloseDialog"
      class="tb-dialog"
    >
      <div class="tb-product-details" v-if="selectedProduct">
        <div class="tb-product-gallery">
          <div class="tb-product-main-image">
            <img :src="'http://localhost:5000' + selectedProduct.image_url"
                 :alt="selectedProduct.description || '商品图片'">
            <div class="tb-zoom-hint">
              <el-icon>
                <ZoomIn/>
              </el-icon>
              鼠标移入可查看大图
            </div>
          </div>
          <div class="tb-product-thumbnails">
            <div class="tb-thumbnail tb-active">
              <img :src="'http://localhost:5000' + selectedProduct.image_url" alt="缩略图">
            </div>
            <div class="tb-thumbnail tb-disabled" v-for="i in 4" :key="i">
              <img
                src="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' fill='%23f5f5f5'/><text x='50%' y='50%' font-size='8' text-anchor='middle' alignment-baseline='middle' fill='%23ccc'>暂无</text></svg>"
                alt="暂无图片">
            </div>
          </div>
        </div>

        <div class="tb-product-info">
          <h1 class="tb-product-title">
            {{ selectedProduct.description || '商品 ' + selectedProduct.product_code }}</h1>

          <div class="tb-product-meta">
            <span class="tb-meta-item">商品编号: {{ selectedProduct.product_code }}</span>
            <span class="tb-meta-item">智能搜索旗舰店</span>
          </div>

          <div class="tb-product-price-wrapper">
            <div class="tb-price-label">价格</div>
            <div class="tb-product-price">
              <span class="tb-price-symbol">¥</span>
              <span class="tb-price-value">{{ formatPrice(selectedProduct.price) }}</span>
            </div>
          </div>

          <div class="tb-product-promotion">
            <div class="tb-promotion-item">
              <span class="tb-promotion-tag">促销</span>
              <span class="tb-promotion-text">限时特惠，购买享8折优惠</span>
            </div>
            <div class="tb-promotion-item">
              <span class="tb-promotion-tag">活动</span>
              <span class="tb-promotion-text">满199元减20元</span>
            </div>
          </div>

          <div class="tb-product-attribute">
            <div class="tb-attribute-item">
              <span class="tb-attribute-label">收藏时间</span>
              <div class="tb-attribute-content">{{ formatDate(selectedProduct.created_at) }}</div>
            </div>

            <div class="tb-attribute-item">
              <span class="tb-attribute-label">销量</span>
              <div class="tb-attribute-content">299件</div>
            </div>

            <div class="tb-attribute-item">
              <span class="tb-attribute-label">发货</span>
              <div class="tb-attribute-content">浙江杭州</div>
            </div>

            <div class="tb-attribute-item">
              <span class="tb-attribute-label">运费</span>
              <div class="tb-attribute-content">免运费</div>
            </div>
          </div>

          <div class="tb-product-action">
            <el-button
              type="danger"
              @click="removeFromFavorites(selectedProduct.product_code)"
              :loading="removingItem === selectedProduct.product_code"
            >
              <el-icon>
                <Delete/>
              </el-icon>
              取消收藏
            </el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <span class="dialog-footer">
          <el-button plain @click="dialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="dialogVisible = false">确认</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  User,
  Search,
  Star,
  Loading,
  ZoomIn,
  Delete
} from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const user = ref(null)
const favorites = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(8)
const dialogVisible = ref(false)
const selectedProduct = ref(null)
const removingItem = ref(null)

// 导航到搜索页面
const navigateToSearch = () => {
  console.log('导航到搜索页面')
  router.replace('/ImageSearch')
}

// 去逛逛
const goToSearch = () => {
  console.log('去逛逛')
  router.replace('/ImageSearch')
}

// 检查用户会话是否有效
const checkUserSession = async () => {
  try {
    console.log('正在检查用户会话...')
    const response = await fetch('http://localhost:5000/api/auth/check', {
      method: 'GET',
      credentials: 'include'
    })

    console.log('会话检查响应状态:', response.status)

    if (!response.ok) {
      // 如果会话无效，重新登录
      localStorage.removeItem('user')
      ElMessage.warning('您的登录已过期，请重新登录')
      router.push('/')
      return false
    }

    const data = await response.json()
    console.log('会话检查响应:', data)
    return true
  } catch (error) {
    console.error('检查用户会话时出错:', error)
    return false
  }
}

// 获取收藏列表
const fetchFavorites = async () => {
  loading.value = true
  try {
    // 检查会话是否有效
    const sessionValid = await checkUserSession()
    if (!sessionValid) {
      loading.value = false
      return
    }

    const response = await fetch('http://localhost:5000/api/favorites', {
      method: 'GET',
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(`获取收藏失败: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()
    console.log('收藏数据:', data)

    if (data.status === 'success') {
      favorites.value = data.favorites || []
      // 重置分页到第一页
      currentPage.value = 1
    } else {
      throw new Error(data.message || '获取收藏失败')
    }
  } catch (error) {
    console.error('获取收藏失败:', error)
    ElMessage.error(`获取收藏失败: ${error.message}`)
    favorites.value = []
  } finally {
    loading.value = false
  }
}

// 从收藏中移除商品
const removeFromFavorites = async (productCode) => {
  if (removingItem.value) return

  try {
    removingItem.value = productCode

    // 确认删除
    await ElMessageBox.confirm(
      '确定要移除这个收藏商品吗？',
      '移除收藏',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    const response = await fetch('http://localhost:5000/api/favorites/remove', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        product_code: productCode
      }),
      credentials: 'include'
    })

    if (!response.ok) {
      throw new Error(`移除收藏失败: ${response.status} ${response.statusText}`)
    }

    const data = await response.json()

    if (data.status === 'success') {
      ElMessage.success('已成功移除收藏')

      // 如果当前在详情对话框中，则关闭对话框
      if (dialogVisible.value && selectedProduct.value && selectedProduct.value.product_code === productCode) {
        dialogVisible.value = false
      }

      // 重新获取收藏列表
      await fetchFavorites()
    } else {
      throw new Error(data.message || '移除收藏失败')
    }
  } catch (error) {
    // 如果用户取消了确认框，不显示错误消息
    if (error !== 'cancel' && error.message !== 'cancel') {
      console.error('移除收藏失败:', error)
      ElMessage.error(`移除收藏失败: ${error.message}`)
    }
  } finally {
    removingItem.value = null
  }
}

// 处理页面变化
const handlePageChange = (page) => {
  currentPage.value = page
  // 滚动到顶部
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  })
}

// 格式化价格
const formatPrice = (price) => {
  if (!price && price !== 0) return '暂无价格'
  return Number(price).toFixed(2)
}

// 格式化日期
const formatDate = (dateString) => {
  if (!dateString) return '未知时间'
  try {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch (e) {
    return dateString
  }
}

// 处理商品点击 - 仿照ImageSearch界面修改
const handleProductClick = (product) => {
  console.log('显示商品详情:', product)
  selectedProduct.value = product
  dialogVisible.value = true
}

// 关闭对话框
const handleCloseDialog = () => {
  dialogVisible.value = false
  setTimeout(() => {
    selectedProduct.value = null
  }, 200)
}

// 登出处理
const handleLogout = async () => {
  try {
    console.log('正在登出...')
    await fetch('http://localhost:5000/auth/logout', {
      method: 'POST',
      credentials: 'include'
    })
    localStorage.removeItem('user')
    ElMessage.success('已成功退出登录')
    router.push('/')
  } catch (error) {
    console.error('登出时出错:', error)
    localStorage.removeItem('user')
    router.push('/')
  }
}

// 显示的收藏商品（分页）
const paginatedFavorites = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return favorites.value.slice(start, end)
})

// 组件挂载时
onMounted(async () => {
  console.log('收藏页面组件挂载中...')
  // 检查用户登录状态
  const storedUser = localStorage.getItem('user')
  if (storedUser) {
    try {
      // 解析用户信息
      user.value = JSON.parse(storedUser)
      console.log('从本地存储获取到用户:', user.value)

      // 验证用户信息和会话
      if (!user.value.username) {
        throw new Error('用户名不存在')
      }
      const sessionValid = await checkUserSession()
      if (!sessionValid) {
        throw new Error('会话已过期')
      }

      // 获取收藏列表
      await fetchFavorites()
    } catch (error) {
      console.error('用户信息解析或验证失败:', error)
      localStorage.removeItem('user')
      router.push('/')
    }
  } else {
    console.log('未找到用户信息，重定向到登录页')
    router.push('/')
  }
})
</script>

<style scoped>
/* 收藏页面特定样式 */
.tb-favorites-container {
  margin: 20px 0;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tb-favorites-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.tb-favorites-header h2 {
  margin: 0;
  font-size: 18px;
  color: #333;
}

.tb-favorites-count {
  color: #999;
  font-size: 14px;
}

.tb-favorite-item {
  position: relative;
}

.tb-item-add-time {
  font-size: 12px;
  color: #999;
}

.tb-item-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  display: none;
  z-index: 10;
}

.tb-favorite-item:hover .tb-item-actions {
  display: block;
}

.tb-empty-favorites {
  padding: 40px 0;
  text-align: center;
}

/* 共享/通用样式 */
.tb-nav {
  display: flex;
  background: #fff;
  margin: 15px 0;
  padding: 0;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tb-nav-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 15px 25px;
  font-size: 16px;
  color: #666;
  text-decoration: none;
  border-bottom: 3px solid transparent;
  transition: all 0.3s;
  cursor: pointer;
}

.tb-nav-item:hover {
  color: #ff5000;
}

.tb-nav-item.tb-active {
  color: #ff5000;
  border-bottom-color: #ff5000;
  font-weight: bold;
}

/* 淘宝风格的通用样式 */
.taobao-favorites {
  max-width: 1220px;
  margin: 0 auto;
  padding: 0 10px;
  min-height: 100vh;
  background-color: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  color: #333;
}

/* 头部样式 */
.tb-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 60px;
  padding: 10px 0;
  background-color: #ffffff;
  border-bottom: 1px solid #e8e8e8;
}

.tb-logo h1 {
  margin: 0;
  color: #ff5000;
  font-size: 22px;
  font-weight: bold;
}

.tb-user-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.username {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #666;
  font-size: 14px;
}

.logout-btn {
  color: #ff5000;
  font-size: 14px;
}

/* 加载中样式 */
.tb-loading-wrapper {
  text-align: center;
  padding: 40px 0;
}

.tb-loading-icon {
  animation: rotate 1s linear infinite;
  color: #ff5000;
}

.tb-loading-text {
  margin-top: 15px;
  color: #999;
  font-size: 14px;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* 结果列表样式 */
.tb-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 15px;
  padding: 10px 0;
}

.tb-item {
  background: #fff;
  border-radius: 4px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.3s;
  cursor: pointer;
}

.tb-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.08);
}

.tb-item-image {
  position: relative;
  padding-top: 100%;
  overflow: hidden;
}

.tb-item-image img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s;
}

.tb-item:hover .tb-item-image img {
  transform: scale(1.05);
}

.tb-item-info {
  padding: 10px;
}

.tb-item-price {
  color: #ff5000;
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 8px;
}

.tb-item-title {
  font-size: 14px;
  color: #333;
  margin-bottom: 8px;
  line-height: 1.4;
  height: 2.8em;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.tb-item-shop {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.tb-item-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

/* 分页容器样式 */
.tb-pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  background: #fff;
  margin: 15px 0;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tb-pagination :deep(.el-pagination.is-background .el-pager li:not(.is-disabled).is-active) {
  background-color: #ff5000;
  color: #fff;
}

.tb-pagination :deep(.el-pagination.is-background .el-pager li:not(.is-disabled):hover) {
  color: #ff5000;
}

.tb-pagination :deep(.el-pagination .btn-next),
.tb-pagination :deep(.el-pagination .btn-prev) {
  background: #fff;
  color: #666;
  border: 1px solid #e8e8e8;
}

.tb-pagination :deep(.el-pagination .btn-next:hover),
.tb-pagination :deep(.el-pagination .btn-prev:hover) {
  color: #ff5000;
  border-color: #ff5000;
}

/* 商品详情对话框样式 */
.tb-dialog :deep(.el-dialog__header) {
  padding: 15px 20px;
  border-bottom: 1px solid #f0f0f0;
  margin: 0;
}

.tb-dialog :deep(.el-dialog__body) {
  padding: 20px;
}

.tb-dialog :deep(.el-dialog__footer) {
  padding: 15px 20px;
  border-top: 1px solid #f0f0f0;
}

.tb-product-details {
  display: flex;
  gap: 30px;
}

.tb-product-gallery {
  flex: 0 0 350px;
}

.tb-product-main-image {
  width: 350px;
  height: 350px;
  border: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.tb-product-main-image img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.tb-zoom-hint {
  position: absolute;
  bottom: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 12px;
  padding: 5px 10px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.tb-product-thumbnails {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}

.tb-thumbnail {
  width: 60px;
  height: 60px;
  border: 1px solid #e8e8e8;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
}

.tb-thumbnail.tb-active {
  border-color: #ff5000;
}

.tb-thumbnail.tb-disabled {
  opacity: 0.5;
  cursor: default;
}

.tb-thumbnail img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.tb-product-info {
  flex: 1;
}

.tb-product-title {
  font-size: 18px;
  color: #333;
  margin: 0 0 15px;
  line-height: 1.5;
}

.tb-product-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  font-size: 12px;
  color: #999;
  margin-bottom: 15px;
}

.tb-product-price-wrapper {
  background: #fff2e8;
  padding: 15px;
  margin-bottom: 15px;
}

.tb-price-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 5px;
}

.tb-product-price {
  display: flex;
  align-items: baseline;
}

.tb-price-symbol {
  color: #ff5000;
  font-size: 16px;
  margin-right: 3px;
}

.tb-price-value {
  color: #ff5000;
  font-size: 28px;
  font-weight: bold;
}

.tb-product-promotion {
  margin-bottom: 15px;
}

.tb-promotion-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.tb-promotion-tag {
  background: #ff5000;
  color: white;
  font-size: 12px;
  padding: 2px 5px;
  margin-right: 10px;
  border-radius: 2px;
}

.tb-promotion-text {
  font-size: 14px;
}

.tb-product-attribute {
  margin-bottom: 20px;
}

.tb-attribute-item {
  display: flex;
  padding: 10px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.tb-attribute-label {
  width: 80px;
  color: #999;
  font-size: 14px;
}

.tb-attribute-content {
  flex: 1;
  font-size: 14px;
}

/* 响应式设计 */
@media (max-width: 992px) {
  .tb-product-details {
    flex-direction: column;
  }

  .tb-product-gallery {
    margin-bottom: 20px;
  }
}

@media (max-width: 768px) {
  .tb-results {
    grid-template-columns: repeat(auto-fill, minmax(45%, 1fr));
  }

  .tb-product-main-image {
    width: 100%;
    height: auto;
    aspect-ratio: 1/1;
  }

  .tb-product-action {
    flex-wrap: wrap;
  }
}

@media (max-width: 576px) {
  .tb-results {
    grid-template-columns: repeat(auto-fill, minmax(100%, 1fr));
  }
}
</style>
