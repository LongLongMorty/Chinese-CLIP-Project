<template>
  <div class="taobao-image-search">
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
    <div class="tb-nav  tb-active">
      <router-link to="/search" class="tb-nav-item" :class="{ 'tb-active': $route.path === '/ImageSearch' }">
        <el-icon>
          <Search/>
        </el-icon>
        商品搜索
      </router-link>
      <router-link to="/favorites" class="tb-nav-item" :class="{ 'tb-active': $route.path === '/favorites' }">
        <el-icon>
          <Star/>
        </el-icon>
        我的收藏
      </router-link>
      <router-link to="/recommend" class="tb-nav-item" :class="{ 'tb-active': $route.path === '/recommend' }">
        <el-icon>
          <MagicStick/>
        </el-icon>
        猜你喜欢
      </router-link>
    </div>

    <!-- 搜索容器 -->
    <div class="tb-search-container">
      <div class="tb-search-mode">
        <el-radio-group v-model="searchMode" size="large">
          <el-radio-button label="text">文本搜索</el-radio-button>
          <el-radio-button label="image">图片搜索</el-radio-button>
        </el-radio-group>
      </div>

      <div class="tb-search-box">
        <el-input
          v-if="searchMode === 'text'"
          v-model="searchQuery"
          placeholder="请输入搜索内容"
          @keyup.enter="handleSearch"
          :disabled="loading"
          size="large"
          class="tb-input"
        >
          <template #append>
            <el-button
              :loading="loading"
              @click="handleSearch"
              type="primary"
              class="tb-search-btn"
            >
              搜索
            </el-button>
          </template>
        </el-input>

        <div v-if="searchMode === 'image'" class="tb-image-search">
          <el-upload
            class="tb-image-uploader"
            action="#"
            :auto-upload="false"
            :show-file-list="false"
            :on-change="handleImageChange"
            accept="image/*"
          >
            <div class="tb-upload-inner">
              <template v-if="imageUrl">
                <img :src="imageUrl" class="tb-preview-image"/>
                <div class="tb-change-image">更换图片</div>
              </template>
              <template v-else>
                <el-icon class="tb-image-uploader-icon">
                  <Plus/>
                </el-icon>
                <div class="tb-upload-text">上传图片</div>
              </template>
            </div>
          </el-upload>

          <el-button
            v-if="imageFile"
            type="primary"
            :loading="loading"
            @click="handleSearch"
            class="tb-image-search-btn"
          >
            <el-icon class="tb-search-icon">
              <Search/>
            </el-icon>
            搜同款
          </el-button>
        </div>
      </div>
    </div>

    <div class="tb-filter-bar" v-if="searchResults.length">
      <span class="tb-result-count">共找到 <span class="tb-result-num">{{
          searchResults.length
        }}</span> 个相似商品</span>
      <!-- 查询扩展标签 -->
      <div v-if="expandedQueries.length > 1" class="tb-expanded-tags">
        <span class="tb-expand-label">同义扩展：</span>
        <el-tag
          v-for="(q, i) in expandedQueries.slice(1)"
          :key="i"
          size="small"
          type="info"
          effect="plain"
          class="tb-expand-tag"
          @click="searchQuery = q; handleSearch()"
        >{{ q }}</el-tag>
      </div>
      <div class="tb-sort-options">
        <span
          class="tb-sort-option"
          :class="{'tb-active': sortBy === 'similarity'}"
          @click="changeSort('similarity')"
        >
          综合
        </span>
        <span
          class="tb-sort-option"
          :class="{'tb-active': sortBy === 'price'}"
          @click="changeSort('price')"
        >
          价格
          <span v-if="sortBy === 'price'" class="tb-sort-direction">
            <i :class="sortDirection === 'asc' ? 'el-icon-caret-top' : 'el-icon-caret-bottom'"></i>
          </span>
        </span>
      </div>
    </div>

    <div class="tb-loading-wrapper" v-if="loading">
      <el-icon class="tb-loading-icon" :size="32">
        <Loading/>
      </el-icon>
      <div class="tb-loading-text">正在搜索中，请稍候...</div>
    </div>

    <div class="tb-results" v-else-if="searchResults.length">
      <div
        v-for="(result, index) in paginatedResults"
        :key="index"
        class="tb-item"
        @click="handleProductClick(result)"
      >
        <div class="tb-item-image">
          <img :src="'http://localhost:5000' + result.image_url" :alt="'商品' + (index + 1)">
          <div class="tb-similarity">
            <span class="tb-similarity-text">相似度 </span>
            <span class="tb-similarity-value">{{ (result.similarity * 100).toFixed(1) }}%</span>
          </div>
        </div>
        <div class="tb-item-info">
          <div class="tb-item-price">¥ {{ formatPrice(result.price) }}</div>
          <div class="tb-item-title" :title="result.description">
            {{ result.description || '商品 ' + result.product_code }}
          </div>
          <div class="tb-item-shop">智能搜索旗舰店</div>
          <div class="tb-item-footer">
            <span class="tb-item-sales">热销299件</span>
            <span class="tb-item-location">杭州</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页组件 -->
    <div class="tb-pagination-container" v-if="searchResults.length > 0">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="sortedResults.length"
        layout="prev, pager, next, jumper, total"
        background
        @current-change="handlePageChange"
        class="tb-pagination"
      />
    </div>

    <el-empty v-else-if="!loading" description="暂无搜索结果" class="tb-empty"/>

    <!-- 商品详情对话框 -->
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
              <span class="tb-attribute-label">相似度</span>
              <div class="tb-attribute-content">
                <span class="tb-similarity-badge">{{
                    (selectedProduct.similarity * 100).toFixed(2)
                  }}%</span>
              </div>
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
              class="tb-add-favorite"
              :class="{'tb-favorited': isFavorite}"
              @click="toggleFavorite"
              :loading="favoriteLoading"
            >
              <el-icon>
                <Star/>
              </el-icon>
              {{ isFavorite ? '已收藏' : '收藏' }}
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
import {ref, watch, onMounted, computed} from 'vue'
import {ElMessage} from 'element-plus'
import {
  Plus,
  View,
  User,
  Search,
  Loading,
  ZoomIn,
  Star,
  ShoppingCart,
  CaretTop,
  CaretBottom
} from '@element-plus/icons-vue'
import {useRouter} from 'vue-router'

const searchMode = ref('text')
const searchQuery = ref('')
const searchResults = ref([])
const loading = ref(false)
const imageUrl = ref('')
const imageFile = ref(null)
const user = ref(null)
const router = useRouter()

// 用于产品详情的变量
const dialogVisible = ref(false)
const selectedProduct = ref(null)
// 查询扩展词
const expandedQueries = ref([])
// 浏览计时
let _browseStartTime = 0

// 分页相关变量
const currentPage = ref(1)
const pageSize = ref(5) // 每页显示5项

// 排序相关变量
const sortBy = ref('similarity')  // 默认按相似度排序
const sortDirection = ref('desc') // 默认降序（相似度高的在前）

// 添加收藏状态变量和加载状态
const isFavorite = ref(false)
const favoriteLoading = ref(false)

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
// 添加这一行来获取当前路由
import { useRoute } from 'vue-router'
const route = useRoute()
// 处理图片上传变化：用 Canvas 将任意格式（AVIF/HEIC/WebP等）统一转为 JPEG
// 避免后端 Pillow 遇到不支持的格式报错
const handleImageChange = (file) => {
  const raw = file.raw
  // 预览用原始 URL
  imageUrl.value = URL.createObjectURL(raw)

  // 用 createImageBitmap + Canvas 转为 JPEG Blob
  createImageBitmap(raw).then((bitmap) => {
    const canvas = document.createElement('canvas')
    canvas.width = bitmap.width
    canvas.height = bitmap.height
    const ctx = canvas.getContext('2d')
    ctx.drawImage(bitmap, 0, 0)
    canvas.toBlob((blob) => {
      // 把 Blob 包装成带 filename 的 File，方便后端识别
      imageFile.value = new File([blob], 'upload.jpg', { type: 'image/jpeg' })
    }, 'image/jpeg', 0.92)
  }).catch(() => {
    // createImageBitmap 不支持时退回原始文件
    imageFile.value = raw
  })
}

// 检查商品是否已收藏
const checkFavoriteStatus = async (productCode) => {
  try {
    favoriteLoading.value = true
    const response = await fetch('http://localhost:5000/api/favorites/check', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        product_code: productCode
      }),
      credentials: 'include'
    })

    if (!response.ok) {
      // 如果响应不成功，检查是否是未授权错误
      if (response.status === 401) {
        await refreshSession()
        // 重新尝试检查收藏状态
        return checkFavoriteStatus(productCode)
      }
      throw new Error('检查收藏状态失败')
    }

    const data = await response.json()
    if (data.status === 'success') {
      isFavorite.value = data.is_favorite
    }
  } catch (error) {
    console.error('检查收藏状态失败:', error)
    // 即使失败也不要中断流程
    isFavorite.value = false
  } finally {
    favoriteLoading.value = false
  }
}

// 刷新用户会话
const refreshSession = async () => {
  try {
    const storedUser = localStorage.getItem('user')
    if (!storedUser) {
      ElMessage.warning('您尚未登录或登录已过期')
      router.push('/')
      return false
    }

    const userInfo = JSON.parse(storedUser)

    // 这里应该调用一个后端刷新会话的API
    // 如果后端没有提供，可以尝试重新登录
    const response = await fetch('http://localhost:5000/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: userInfo.username,
        // 如果需要，可以添加其他字段
      }),
      credentials: 'include'
    })

    if (!response.ok) {
      // 如果刷新失败，重定向到登录页
      localStorage.removeItem('user')
      router.push('/')
      return false
    }

    const data = await response.json()
    console.log('会话刷新响应:', data)
    return true
  } catch (error) {
    console.error('刷新会话失败:', error)
    return false
  }
}

// 收藏或取消收藏
const toggleFavorite = async () => {
  if (!selectedProduct.value || favoriteLoading.value) return

  favoriteLoading.value = true
  try {
    // 先检查用户会话是否有效
    const sessionValid = await checkUserSession()
    if (!sessionValid) {
      return
    }

    const endpoint = isFavorite.value ? '/api/favorites/remove' : '/api/favorites/add'

    const response = await fetch(`http://localhost:5000${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        product_code: selectedProduct.value.product_code
      }),
      credentials: 'include'
    })

    if (!response.ok) {
      // 如果响应不成功，检查是否是未授权错误
      if (response.status === 401) {
        const refreshed = await refreshSession()
        if (refreshed) {
          // 刷新会话后重试
          favoriteLoading.value = false
          return toggleFavorite()
        } else {
          throw new Error('您的登录已过期，请重新登录')
        }
      }

      const errorData = await response.json()
      throw new Error(errorData.message || '操作失败')
    }

    const data = await response.json()
    isFavorite.value = !isFavorite.value
    ElMessage.success(data.message)

  } catch (error) {
    console.error('处理收藏操作失败:', error)
    if (error.message.includes('登录已过期') || error.message.includes('请先登录')) {
      ElMessage.warning(error.message)
      router.push('/')
    } else {
      ElMessage.error(`操作失败: ${error.message}`)
    }
  } finally {
    favoriteLoading.value = false
  }
}

// ── 行为上报工具函数 ─────────────────────────────────────────────────────────
const reportClick = (productCode) => {
  fetch('http://localhost:5000/api/behavior/click', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_code: productCode })
  }).catch(() => {})
}

const reportBrowse = (productCode, duration) => {
  if (duration <= 0) return
  fetch('http://localhost:5000/api/behavior/browse', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ product_code: productCode, duration })
  }).catch(() => {})
}

// 处理商品点击 - 统一入口函数
const handleProductClick = async (product) => {
  try {
    console.log('显示商品详情:', product)
    selectedProduct.value = product
    dialogVisible.value = true
    _browseStartTime = Date.now()

    // 上报点击行为
    if (product && product.product_code) {
      reportClick(product.product_code)
      await checkFavoriteStatus(product.product_code)
    }
  } catch (error) {
    console.error('显示商品详情时出错:', error)
    ElMessage.error('无法显示商品详情，请重试')
  }
}

// 计算排序后的结果
const sortedResults = computed(() => {
  // 创建一个副本来排序，避免修改原始数据
  const results = [...searchResults.value]

  // 根据排序字段和方向进行排序
  if (sortBy.value === 'price') {
    results.sort((a, b) => {
      // 处理可能的无效价格
      const priceA = parseFloat(a.price) || 0
      const priceB = parseFloat(b.price) || 0

      return sortDirection.value === 'asc' ? priceA - priceB : priceB - priceA
    })
  } else if (sortBy.value === 'similarity') {
    results.sort((a, b) => {
      return sortDirection.value === 'asc' ? a.similarity - b.similarity : b.similarity - a.similarity
    })
  }

  return results
})

// 计算当前页的结果
const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return sortedResults.value.slice(start, end)
})

// 更改排序方式
const changeSort = (newSortBy) => {
  // 如果点击当前排序方式，则切换排序方向
  if (newSortBy === sortBy.value) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    // 否则切换排序方式，并设置默认排序方向
    sortBy.value = newSortBy
    sortDirection.value = newSortBy === 'price' ? 'asc' : 'desc'
  }

  // 排序后回到第一页
  currentPage.value = 1
}

// 处理页面变化
const handlePageChange = (page) => {
  currentPage.value = page
  // 页面滚动到顶部
  try {
    const resultsElement = document.querySelector('.tb-results')
    if (resultsElement) {
      window.scrollTo({
        top: resultsElement.offsetTop - 20,
        behavior: 'smooth'
      })
    }
  } catch (error) {
    console.error('滚动到顶部时出错:', error)
  }
}

// 格式化价格，保留两位小数
const formatPrice = (price) => {
  if (!price && price !== 0) return '暂无价格'
  return Number(price).toFixed(2)
}

// 处理搜索
const handleSearch = async () => {
  if (searchMode.value === 'text' && !searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }

  if (searchMode.value === 'image' && !imageFile.value) {
    ElMessage.warning('请选择要搜索的图片')
    return
  }

  loading.value = true
  // 重置排序和分页
  currentPage.value = 1
  sortBy.value = 'similarity'
  sortDirection.value = 'desc'
  expandedQueries.value = []

  try {
    // 检查用户会话是否有效
    const sessionValid = await checkUserSession()
    if (!sessionValid) {
      loading.value = false
      return
    }

    console.log(`执行${searchMode.value}搜索...`)
    let response
    if (searchMode.value === 'text') {
      response = await fetch('http://localhost:5000/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery.value,
          top_k: 20  // 修改为请求20个结果
        }),
        credentials: 'include'
      })
    } else {
      const formData = new FormData()
      formData.append('image', imageFile.value)
      formData.append('top_k', 20)  // 修改为请求20个结果

      response = await fetch('http://localhost:5000/api/image-search', {
        method: 'POST',
        body: formData,
        credentials: 'include'
      })
    }

    console.log('搜索响应状态:', response.status)

    if (!response.ok) {
      if (response.status === 401) {
        const refreshed = await refreshSession()
        if (!refreshed) {
          throw new Error('您的登录已过期，请重新登录')
        } else {
          // 重新尝试搜索
          loading.value = false
          return handleSearch()
        }
      } else {
        const errorData = await response.json()
        throw new Error(errorData.message || '搜索失败')
      }
    }

    const data = await response.json()
    console.log('搜索响应:', data)

    if (data.status === 'success') {
      console.log('搜索结果:', data.results)
      searchResults.value = data.results || []
      expandedQueries.value = data.expanded_queries || []
      if (searchResults.value.length === 0) {
        ElMessage.info('未找到匹配的商品')
      } else {
        const expandInfo = expandedQueries.value.length > 1
          ? `（含扩展词：${expandedQueries.value.slice(1).join('、')}）`
          : ''
        ElMessage.success(`找到 ${searchResults.value.length} 个相似商品${expandInfo}`)
      }
    } else {
      ElMessage.error('搜索失败：' + data.message)
    }
  } catch (error) {
    console.error('搜索请求失败:', error)
    if (error.message.includes('登录已过期') || error.message.includes('请先登录')) {
      ElMessage.warning(error.message)
      router.push('/')
    } else {
      ElMessage.error('请求失败：' + (error.message || '未知错误'))
    }
    searchResults.value = []
  } finally {
    loading.value = false
  }
}

// 关闭详情对话框
const handleCloseDialog = () => {
  // 计算浏览时长并上报
  if (_browseStartTime > 0 && selectedProduct.value?.product_code) {
    const duration = Math.round((Date.now() - _browseStartTime) / 1000)
    reportBrowse(selectedProduct.value.product_code, duration)
    _browseStartTime = 0
  }
  dialogVisible.value = false
  setTimeout(() => {
    selectedProduct.value = null
    isFavorite.value = false
  }, 200)
}

// 登出处理
const handleLogout = async () => {
  try {
    console.log('正在登出...')
    // 调用后端登出API
    await fetch('http://localhost:5000/auth/logout', {
      method: 'POST',
      credentials: 'include'
    })

    // 清除本地存储
    localStorage.removeItem('user')

    // 显示成功消息
    ElMessage.success('已成功退出登录')

    // 重定向到登录页
    router.push('/')
  } catch (error) {
    console.error('登出时出错:', error)

    // 即使API调用失败，也清除本地存储并重定向
    localStorage.removeItem('user')
    router.push('/')
  }
}

onMounted(async () => {
  console.log('组件挂载中...')
  const storedUser = localStorage.getItem('user')
  if (storedUser) {
    try {
      user.value = JSON.parse(storedUser)
      if (!user.value.username) throw new Error('用户名不存在')
      const sessionValid = await checkUserSession()
      if (!sessionValid) throw new Error('会话已过期')
      console.log('用户已登录:', user.value.username)
    } catch (error) {
      console.error('用户信息解析或验证失败:', error)
      localStorage.removeItem('user')
      router.push('/')
      return
    }
  } else {
    console.log('未找到用户信息，重定向到登录页')
    router.push('/')
    return
  }

  // 处理从推荐页/历史记录传来的待搜索词
  const pendingQuery = localStorage.getItem('pending_search_query')
  if (pendingQuery) {
    localStorage.removeItem('pending_search_query')
    searchQuery.value = pendingQuery
    await handleSearch()
  }
})

// 替代原来的logout函数
const logout = handleLogout
</script>

<style scoped>
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
}

.tb-nav-item:hover {
  color: #ff5000;
}

.tb-nav-item.tb-active {
  color: #ff5000;
  border-bottom-color: #ff5000;
  font-weight: bold;
}

/* 淘宝风格的样式 */
.taobao-image-search {
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

/* 搜索容器样式 */
.tb-search-container {
  margin: 20px 0;
  background: #fff;
  padding: 20px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.tb-search-mode {
  margin-bottom: 20px;
  text-align: center;
}

.tb-search-mode .el-radio-button :deep(.el-radio-button__inner) {
  background-color: #fff;
  border-color: #ff5000;
  color: #ff5000;
}

.tb-search-mode .el-radio-button.is-active :deep(.el-radio-button__inner) {
  background-color: #ff5000;
  border-color: #ff5000;
  color: #fff;
  box-shadow: -1px 0 0 0 #ff5000;
}

.tb-search-box {
  max-width: 800px;
  margin: 0 auto;
}

.tb-input :deep(.el-input__wrapper) {
  border-color: #ff5000;
  border-radius: 20px 0 0 20px;
}

.tb-search-btn {
  background-color: #ff5000;
  border-color: #ff5000;
  border-radius: 0 20px 20px 0;
  padding: 0 20px;
  font-size: 16px;
}

.tb-image-search {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.tb-image-uploader {
  width: 300px;
  height: 300px;
  background: #fafafa;
  border: 2px dashed #e8e8e8;
  border-radius: 4px;
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}
.tb-favorited {
  background-color: #fff2e8;
  border-color: #ff5000;
  color: #ff5000;
}

.tb-favorited:hover {
  background-color: #fff7f2;
}
.tb-image-uploader:hover {
  border-color: #ff5000;
  background: #fff;
}

.tb-upload-inner {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.tb-image-uploader-icon {
  font-size: 48px;
  color: #ff5000;
  margin-bottom: 10px;
}

.tb-upload-text {
  font-size: 16px;
  color: #999;
}

.tb-preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.tb-change-image {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 10px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  text-align: center;
  font-size: 14px;
}

.tb-image-search-btn {
  width: 180px;
  height: 45px;
  background-color: #ff5000;
  border-color: #ff5000;
  border-radius: 22px;
  font-size: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.tb-search-icon {
  font-size: 18px;
}

/* 筛选栏样式 */
.tb-filter-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  min-height: 40px;
  background: #fff;
  margin: 10px 0;
  padding: 6px 15px;
  border-radius: 4px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  gap: 8px;
}
.tb-expanded-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 13px;
}
.tb-expand-label {
  color: #999;
}
.tb-expand-tag {
  cursor: pointer;
}
.tb-expand-tag:hover {
  border-color: #ff5000;
  color: #ff5000;
}

.tb-result-count {
  font-size: 14px;
  color: #666;
}

.tb-result-num {
  color: #ff5000;
  font-weight: bold;
}

.tb-sort-options {
  display: flex;
  gap: 20px;
}

.tb-sort-option {
  font-size: 14px;
  color: #666;
  cursor: pointer;
  position: relative;
  padding-bottom: 2px;
  display: flex;
  align-items: center;
}

.tb-sort-option:hover {
  color: #ff5000;
}

.tb-sort-option.tb-active {
  color: #ff5000;
  font-weight: bold;
}

.tb-sort-option.tb-active::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 0;
  right: 0;
  height: 2px;
  background: #ff5000;
}

/* 排序方向图标样式 */
.tb-sort-direction {
  margin-left: 3px;
  display: inline-flex;
  align-items: center;
}

.tb-sort-direction i {
  font-size: 12px;
}

.el-icon-caret-top, .el-icon-caret-bottom {
  color: #ff5000;
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

.tb-similarity {
  position: absolute;
  bottom: 0;
  right: 0;
  background: rgba(255, 80, 0, 0.9);
  color: white;
  padding: 3px 8px;
  font-size: 12px;
}

.tb-similarity-text {
  font-size: 11px;
}

.tb-similarity-value {
  font-weight: bold;
  margin-left: 2px;
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

.tb-empty {
  background: #fff;
  padding: 40px 0;
  margin: 20px 0;
  border-radius: 4px;
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

.tb-pagination :deep(.el-pagination .el-pagination__jump) {
  color: #666;
}

/* 商品详情对话框 */
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

.tb-similarity-badge {
  background: #ff5000;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 12px;
}

.tb-product-action {
  display: flex;
  gap: 10px;
  margin-top: 30px;
}

.tb-buy-now {
  background-color: #ff5000;
  border-color: #ff5000;
  color: white;
  padding: 0 30px;
  height: 40px;
  font-size: 16px;
}

.tb-add-cart {
  background-color: #ff9000;
  border-color: #ff9000;
  color: white;
  padding: 0 20px;
  height: 40px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.tb-add-favorite {
  border-color: #ff5000;
  color: #ff5000;
  padding: 0 15px;
  height: 40px;
  font-size: 16px;
  display: flex;
  align-items: center;
  gap: 5px;
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

  .tb-buy-now, .tb-add-cart {
    flex: 1;
  }

  .tb-add-favorite {
    width: 100%;
    margin-top: 10px;
  }
}

@media (max-width: 576px) {
  .tb-results {
    grid-template-columns: repeat(auto-fill, minmax(100%, 1fr));
  }
}
</style>
