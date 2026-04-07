<template>
  <div class="taobao-recommend">
    <!-- 顶部 header -->
    <div class="tb-header">
      <div class="tb-logo">
        <h1>Chinese-CLIP商品检索系统</h1>
      </div>
      <div class="tb-user-info">
        <span v-if="user" class="username">
          <el-icon><User /></el-icon> {{ user.username }}
        </span>
        <el-button type="text" class="logout-btn" @click="handleLogout">退出登录</el-button>
      </div>
    </div>

    <!-- 导航栏 -->
    <div class="tb-nav">
      <div class="tb-nav-item" @click="router.replace('/ImageSearch')">
        <el-icon><Search /></el-icon>
        商品搜索
      </div>
      <div class="tb-nav-item" @click="router.replace('/favorites')">
        <el-icon><Star /></el-icon>
        我的收藏
      </div>
      <div class="tb-nav-item tb-active">
        <el-icon><MagicStick /></el-icon>
        猜你喜欢
      </div>
    </div>

    <!-- 主体 -->
    <div class="tb-recommend-container">
      <el-tabs v-model="activeTab" class="tb-tabs" @tab-change="onTabChange">

        <!-- ── 猜你喜欢 Tab ───────────────────────────────────────── -->
        <el-tab-pane label="猜你喜欢" name="recommend">
          <div class="tb-recommend-header">
            <span class="tb-sub" v-if="basedOnCount > 0">
              根据您的浏览、点击和收藏行为智能推荐
              <el-tag size="small" type="warning" effect="plain" style="margin-left:6px;" v-if="favoriteCount > 0">
                <el-icon><StarFilled /></el-icon> 收藏 {{ favoriteCount }} 件
              </el-tag>
            </span>
            <el-button size="small" :loading="loading" @click="fetchRecommendations" style="margin-left:auto;">
              刷新推荐
            </el-button>
          </div>

          <div class="tb-loading-wrapper" v-if="loading">
            <el-icon class="tb-loading-icon" :size="32"><Loading /></el-icon>
            <div class="tb-loading-text">正在为您生成个性化推荐，请稍候…</div>
          </div>

          <div class="tb-results" v-else-if="results.length">
            <div
              v-for="(item, index) in results"
              :key="index"
              class="tb-item"
              @click="handleProductClick(item)"
            >
              <div class="tb-item-image">
                <img :src="'http://localhost:5000' + item.image_url" :alt="'推荐商品' + (index + 1)" />
              </div>
              <div class="tb-item-info">
                <div class="tb-item-price">¥ {{ formatPrice(item.price) }}</div>
                <div class="tb-item-title" :title="item.description">
                  {{ item.description || '商品 ' + item.product_code }}
                </div>
                <div class="tb-item-shop">智能搜索旗舰店</div>
                <div class="tb-item-footer">
                  <span class="tb-similarity">匹配度 {{ (item.similarity * 100).toFixed(1) }}%</span>
                </div>
              </div>
              <div class="tb-item-actions">
                <el-button
                  :type="favoriteCodes.has(item.product_code) ? 'warning' : 'primary'"
                  size="small"
                  :icon="favoriteCodes.has(item.product_code) ? 'StarFilled' : 'Star'"
                  circle
                  @click.stop="toggleFavorite(item)"
                  :loading="togglingItem === item.product_code"
                />
              </div>
            </div>
          </div>

          <div class="tb-empty" v-else-if="!loading">
            <el-empty :description="emptyMessage || '暂无推荐内容'" :image-size="120">
              <el-button type="primary" @click="router.replace('/ImageSearch')">
                去浏览商品
              </el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <!-- ── 最近浏览 Tab ───────────────────────────────────────── -->
        <el-tab-pane label="最近浏览" name="browse">
          <div class="tb-loading-wrapper" v-if="browseLoading">
            <el-icon class="tb-loading-icon" :size="32"><Loading /></el-icon>
            <div class="tb-loading-text">加载浏览记录…</div>
          </div>

          <div class="tb-results" v-else-if="browseHistory.length">
            <div
              v-for="(item, index) in browseHistory"
              :key="index"
              class="tb-item"
              @click="handleHistoryClick(item)"
            >
              <div class="tb-item-image">
                <img :src="'http://localhost:5000' + item.image_url" :alt="'浏览商品'" />
                <div class="tb-duration-badge" v-if="item.duration > 0">
                  {{ formatDuration(item.duration) }}
                </div>
              </div>
              <div class="tb-item-info">
                <div class="tb-item-price">¥ {{ formatPrice(item.price) }}</div>
                <div class="tb-item-title" :title="item.description">
                  {{ item.description || '商品 ' + item.product_code }}
                </div>
                <div class="tb-item-shop">智能搜索旗舰店</div>
                <div class="tb-item-footer">
                  <span class="tb-time-tag">{{ item.updated_at }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="tb-empty" v-else-if="!browseLoading">
            <el-empty description="暂无浏览记录，去逛逛吧" :image-size="120">
              <el-button type="primary" @click="router.replace('/ImageSearch')">去搜索</el-button>
            </el-empty>
          </div>
        </el-tab-pane>

        <!-- ── 搜索历史 Tab ───────────────────────────────────────── -->
        <el-tab-pane label="搜索历史" name="search">
          <div class="tb-search-history" v-if="searchHistory.length">
            <div
              v-for="(item, index) in searchHistory"
              :key="index"
              class="tb-history-row"
            >
              <div class="tb-history-main">
                <el-icon class="tb-history-icon"><Search /></el-icon>
                <span
                  class="tb-history-query"
                  @click="goSearch(item.query)"
                >{{ item.query }}</span>
                <div class="tb-history-tags" v-if="item.expanded_queries && item.expanded_queries.length > 1">
                  <el-tag
                    v-for="(q, qi) in item.expanded_queries.slice(1)"
                    :key="qi"
                    size="small"
                    type="info"
                    effect="plain"
                    class="tb-expand-tag"
                    @click="goSearch(q)"
                  >{{ q }}</el-tag>
                </div>
              </div>
              <div class="tb-history-meta">
                <span class="tb-history-count">{{ item.result_count }} 件</span>
                <span class="tb-history-time">{{ item.created_at }}</span>
              </div>
            </div>
          </div>
          <div class="tb-empty" v-else>
            <el-empty description="暂无搜索历史" :image-size="120" />
          </div>
        </el-tab-pane>

      </el-tabs>
    </div>

    <!-- 商品详情弹窗 -->
    <el-dialog v-model="dialogVisible" title="商品详情" width="420px" center
      @close="onDialogClose">
      <div v-if="selectedProduct" class="tb-dialog-content">
        <img
          :src="'http://localhost:5000' + selectedProduct.image_url"
          class="tb-dialog-image"
          alt="商品图片"
        />
        <div class="tb-dialog-info">
          <p class="tb-dialog-price">¥ {{ formatPrice(selectedProduct.price) }}</p>
          <p class="tb-dialog-desc">{{ selectedProduct.description }}</p>
          <p class="tb-dialog-code">商品编号：{{ selectedProduct.product_code }}</p>
        </div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button
          :type="selectedProduct && favoriteCodes.has(selectedProduct.product_code) ? 'warning' : 'primary'"
          @click="toggleFavorite(selectedProduct)"
        >
          {{ selectedProduct && favoriteCodes.has(selectedProduct.product_code) ? '取消收藏' : '加入收藏' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Search, Star, StarFilled, MagicStick, Loading } from '@element-plus/icons-vue'

const router = useRouter()
const user = ref(null)
const results = ref([])
const loading = ref(false)
const emptyMessage = ref('')
const basedOnCount = ref(0)
const favoriteCount = ref(0)
const favoriteCodes = ref(new Set())
const togglingItem = ref(null)
const dialogVisible = ref(false)
const selectedProduct = ref(null)
let _browseStartTime = 0

// ── 标签页 ────────────────────────────────────────────────────────────────────
const activeTab = ref('recommend')
const browseHistory = ref([])
const browseLoading = ref(false)
const searchHistory = ref([])
const searchLoading = ref(false)

const onTabChange = (tab) => {
  if (tab === 'browse' && browseHistory.value.length === 0) fetchBrowseHistory()
  if (tab === 'search' && searchHistory.value.length === 0) fetchSearchHistory()
}

// ── 浏览历史 ──────────────────────────────────────────────────────────────────
const fetchBrowseHistory = async () => {
  browseLoading.value = true
  try {
    const res = await fetch('http://localhost:5000/api/behavior/browse-history', {
      credentials: 'include'
    })
    const data = await res.json()
    if (data.status === 'success') {
      browseHistory.value = data.history || []
    }
  } catch (e) {
    console.error('获取浏览历史失败:', e)
  } finally {
    browseLoading.value = false
  }
}

// ── 搜索历史 ──────────────────────────────────────────────────────────────────
const fetchSearchHistory = async () => {
  searchLoading.value = true
  try {
    const res = await fetch('http://localhost:5000/api/behavior/search-history', {
      credentials: 'include'
    })
    const data = await res.json()
    if (data.status === 'success') {
      searchHistory.value = data.history || []
    }
  } catch (e) {
    console.error('获取搜索历史失败:', e)
  } finally {
    searchLoading.value = false
  }
}

// ── 浏览历史商品点击 ──────────────────────────────────────────────────────────
const handleHistoryClick = (item) => {
  // 构造兼容格式的对象
  selectedProduct.value = {
    product_code: item.product_code,
    image_url: item.image_url,
    description: item.description || '',
    price: item.price || 0,
    similarity: 0,
  }
  dialogVisible.value = true
  _browseStartTime = Date.now()
  reportClick(item.product_code)
}

// ── 从历史记录跳转搜索 ──────────────────────────────────────────────────────
const goSearch = (query) => {
  localStorage.setItem('pending_search_query', query)
  router.replace('/ImageSearch')
}

// ── 格式化浏览时长 ────────────────────────────────────────────────────────────
const formatDuration = (seconds) => {
  if (seconds < 60) return `${seconds}s`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return s > 0 ? `${m}m${s}s` : `${m}m`
}

// ── 工具函数 ──────────────────────────────────────────────────────────────────
const formatPrice = (price) => {
  if (!price && price !== 0) return '0.00'
  return parseFloat(price).toFixed(2)
}

// ── 鉴权检查 ─────────────────────────────────────────────────────────────────
const checkUserSession = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/auth/check', {
      method: 'GET',
      credentials: 'include'
    })
    if (!res.ok) {
      localStorage.removeItem('user')
      ElMessage.warning('您的登录已过期，请重新登录')
      router.push('/')
      return false
    }
    const data = await res.json()
    if (data.authenticated) {
      user.value = data.user
      localStorage.setItem('user', JSON.stringify(data.user))
      return true
    }
    router.push('/')
    return false
  } catch {
    const cached = localStorage.getItem('user')
    if (cached) {
      user.value = JSON.parse(cached)
      return true
    }
    router.push('/')
    return false
  }
}

// ── 获取推荐 ──────────────────────────────────────────────────────────────────
const fetchRecommendations = async () => {
  loading.value = true
  results.value = []
  emptyMessage.value = ''
  try {
    const res = await fetch('http://localhost:5000/api/recommend?top_k=20', {
      method: 'GET',
      credentials: 'include'
    })
    const data = await res.json()
    if (data.status === 'success') {
      results.value = data.results || []
      basedOnCount.value = data.based_on_count || 0
      favoriteCount.value = data.favorite_count || 0
      if (results.value.length === 0) {
        emptyMessage.value = data.message || '暂无推荐内容'
      }
    } else {
      emptyMessage.value = data.message || '获取推荐失败'
      if (res.status === 401) {
        ElMessage.warning('请先登录')
        router.push('/')
      }
    }
  } catch (e) {
    emptyMessage.value = '网络出错，请稍后重试'
    console.error('获取推荐失败:', e)
  } finally {
    loading.value = false
  }
}

// ── 获取收藏状态（批量） ────────────────────────────────────────────────────────
const fetchFavorites = async () => {
  try {
    const res = await fetch('http://localhost:5000/api/favorites', {
      credentials: 'include'
    })
    const data = await res.json()
    if (data.status === 'success') {
      favoriteCodes.value = new Set((data.favorites || []).map(f => f.product_code))
    }
  } catch {
    // 静默失败，收藏状态不影响推荐展示
  }
}

// ── 收藏/取消收藏 ──────────────────────────────────────────────────────────────
const toggleFavorite = async (item) => {
  if (!item) return
  const code = item.product_code
  togglingItem.value = code
  const isFav = favoriteCodes.value.has(code)
  const url = isFav
    ? 'http://localhost:5000/api/favorites/remove'
    : 'http://localhost:5000/api/favorites/add'
  try {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_code: code })
    })
    const data = await res.json()
    if (data.status === 'success' || data.status === 'info') {
      if (isFav) {
        favoriteCodes.value.delete(code)
        ElMessage.success('已取消收藏')
      } else {
        favoriteCodes.value.add(code)
        ElMessage.success('已加入收藏')
      }
      // 刷新收藏集合引用，触发响应式更新
      favoriteCodes.value = new Set(favoriteCodes.value)
    } else {
      ElMessage.error(data.message || '操作失败')
    }
  } catch (e) {
    ElMessage.error('网络出错，请稍后重试')
  } finally {
    togglingItem.value = null
    if (dialogVisible.value && selectedProduct.value?.product_code === code) {
      // 弹窗内状态同步已通过 favoriteCodes 响应式驱动
    }
  }
}

// ── 行为上报 ────────────────────────────────────────────────────────────────────────
const reportClick = (code) => {
  fetch('http://localhost:5000/api/behavior/click', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_code: code })
  }).catch(() => {})
}
const reportBrowse = (code, duration) => {
  if (duration <= 0) return
  fetch('http://localhost:5000/api/behavior/browse', {
    method: 'POST', credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_code: code, duration })
  }).catch(() => {})
}

// ── 对话框关闭 ───────────────────────────────────────────────────────────────────
const onDialogClose = () => {
  if (_browseStartTime > 0 && selectedProduct.value?.product_code) {
    const duration = Math.round((Date.now() - _browseStartTime) / 1000)
    reportBrowse(selectedProduct.value.product_code, duration)
    _browseStartTime = 0
  }
}

// ── 点击商品卡片 ───────────────────────────────────────────────────────────────────
const handleProductClick = (item) => {
  selectedProduct.value = item
  dialogVisible.value = true
  _browseStartTime = Date.now()
  if (item?.product_code) reportClick(item.product_code)
}

// ── 退出登录 ──────────────────────────────────────────────────────────────────
const handleLogout = async () => {
  try {
    await fetch('http://localhost:5000/auth/logout', {
      method: 'POST',
      credentials: 'include'
    })
  } catch {}
  localStorage.removeItem('user')
  ElMessage.success('已退出登录')
  router.push('/')
}

// ── 挂载 ──────────────────────────────────────────────────────────────────────
onMounted(async () => {
  const ok = await checkUserSession()
  if (!ok) return
  // 并行加载推荐 + 收藏状态，浏览/搜索历史按需加载（切换 Tab 时触发）
  await Promise.all([fetchRecommendations(), fetchFavorites()])
})
</script>

<style scoped>
.taobao-recommend {
  min-height: 100vh;
  background: #f5f5f5;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* ── Header ── */
.tb-header {
  background: #ff4400;
  color: #fff;
  padding: 12px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.tb-logo h1 {
  margin: 0;
  font-size: 20px;
  font-weight: bold;
}
.tb-user-info {
  display: flex;
  align-items: center;
  gap: 16px;
}
.username {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
}
.logout-btn {
  color: #fff !important;
  font-size: 13px;
}

/* ── Nav ── */
.tb-nav {
  background: #fff;
  display: flex;
  padding: 0 24px;
  border-bottom: 2px solid #f0f0f0;
  gap: 8px;
}
.tb-nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 14px 20px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  transition: color 0.2s;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}
.tb-nav-item:hover {
  color: #ff4400;
}
.tb-nav-item.tb-active {
  color: #ff4400;
  font-weight: bold;
  border-bottom-color: #ff4400;
}

/* ── Main container ── */
.tb-recommend-container {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 16px;
}
.tb-recommend-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}
.tb-recommend-header h2 {
  margin: 0;
  font-size: 20px;
  color: #333;
}
.tb-sub {
  font-size: 13px;
  color: #999;
}

/* ── Loading ── */
.tb-loading-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0;
  color: #999;
  gap: 12px;
}
.tb-loading-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ── Grid ── */
.tb-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}
.tb-item {
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  position: relative;
  transition: box-shadow 0.2s, transform 0.2s;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.tb-item:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,.15);
  transform: translateY(-2px);
}
.tb-item-image {
  width: 100%;
  aspect-ratio: 1;
  overflow: hidden;
  background: #f9f9f9;
}
.tb-item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s;
}
.tb-item:hover .tb-item-image img {
  transform: scale(1.05);
}
.tb-item-info {
  padding: 10px 12px 6px;
}
.tb-item-price {
  color: #ff4400;
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 4px;
}
.tb-item-title {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tb-item-shop {
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
.tb-item-footer {
  margin-top: 4px;
}
.tb-similarity {
  font-size: 11px;
  color: #52c41a;
  background: #f6ffed;
  border: 1px solid #b7eb8f;
  border-radius: 4px;
  padding: 1px 5px;
}
.tb-item-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.2s;
}
.tb-item:hover .tb-item-actions {
  opacity: 1;
}

/* ── Empty ── */
.tb-empty {
  padding: 60px 0;
  text-align: center;
}

/* ── Dialog ── */
.tb-dialog-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.tb-dialog-image {
  width: 240px;
  height: 240px;
  object-fit: cover;
  border-radius: 8px;
}
.tb-dialog-info {
  width: 100%;
}
.tb-dialog-price {
  color: #ff4400;
  font-size: 20px;
  font-weight: bold;
  margin: 0 0 8px;
}
.tb-dialog-desc {
  color: #333;
  font-size: 14px;
  margin: 0 0 6px;
}
.tb-dialog-code {
  color: #999;
  font-size: 12px;
  margin: 0;
}

/* ── Tabs ── */
.tb-tabs {
  background: #fff;
  border-radius: 8px;
  padding: 0 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.tb-tabs :deep(.el-tabs__item.is-active) {
  color: #ff4400;
}
.tb-tabs :deep(.el-tabs__active-bar) {
  background-color: #ff4400;
}

/* ── Recommend header row ── */
.tb-recommend-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0 8px;
  flex-wrap: wrap;
}

/* ── Duration badge ── */
.tb-duration-badge {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background: rgba(0,0,0,.55);
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 10px;
}

/* ── Time tag ── */
.tb-time-tag {
  font-size: 11px;
  color: #bbb;
}

/* ── Search history list ── */
.tb-search-history {
  padding: 8px 0;
}
.tb-history-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 10px 8px;
  border-bottom: 1px solid #f0f0f0;
  cursor: default;
  transition: background 0.15s;
  gap: 12px;
}
.tb-history-row:hover {
  background: #fafafa;
}
.tb-history-main {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  flex: 1;
}
.tb-history-icon {
  color: #999;
  flex-shrink: 0;
}
.tb-history-query {
  font-size: 14px;
  color: #333;
  cursor: pointer;
  font-weight: 500;
}
.tb-history-query:hover {
  color: #ff4400;
  text-decoration: underline;
}
.tb-history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tb-expand-tag {
  cursor: pointer;
}
.tb-expand-tag:hover {
  border-color: #ff4400;
  color: #ff4400;
}
.tb-history-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.tb-history-count {
  font-size: 12px;
  color: #52c41a;
}
.tb-history-time {
  font-size: 11px;
  color: #bbb;
}
</style>
